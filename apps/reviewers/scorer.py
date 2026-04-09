"""
Deterministic reviewer suggestion engine (Spec §6.6).

Phase 1: weighted scoring, no black-box AI.
Phase 2 (scaffolded): OpenAI embedding-based semantic similarity
  — enabled when settings.AI_FEATURES_ENABLED = True.

Weights (must sum to 1.0):
  expertise_similarity  0.26
  discipline_match      0.14
  keyword_overlap       0.10
  methodology_match     0.08
  artistic_medium_match 0.06
  semantic_similarity   0.10  (0 if AI disabled)
  language_match        0.04
  availability_score    0.06
  timeliness_score      0.05
  workload_balance      0.04
  editor_quality_score  0.03
  diversity_score       0.04
  ─────────────────────────
  Total                 1.00
"""
import random
import math
from datetime import date, timedelta
from django.conf import settings
from django.utils.timezone import now


# ── Constants ─────────────────────────────────────────────────────────────────

WEIGHTS = {
    'expertise_similarity':   0.26,
    'discipline_match':       0.14,
    'keyword_overlap':        0.10,
    'methodology_match':      0.08,
    'artistic_medium_match':  0.06,
    'semantic_similarity':    0.10,
    'language_match':         0.04,
    'availability_score':     0.06,
    'timeliness_score':       0.05,
    'workload_balance':       0.04,
    'editor_quality_score':   0.03,
    'diversity_score':        0.04,
}

MAX_ACTIVE_INVITATIONS = 3   # hard overload threshold
TEMPERATURE = 0.15           # randomness injected into final selection


# ── Public entry point ────────────────────────────────────────────────────────

def suggest_reviewers(submission, n_primary=3, n_alternates=3) -> dict:
    """
    Return top reviewer suggestions for a submission.

    Returns:
        {
          'primary': [SuggestionResult, ...],    # n_primary entries
          'alternates': [SuggestionResult, ...], # n_alternates entries
        }
    """
    from apps.reviewers.models import ReviewerProfile
    profiles = ReviewerProfile.objects.filter(
        is_active=True,
        is_suspended=False,
    ).select_related('user')

    sub_meta = _build_submission_meta(submission)
    scored = []

    for profile in profiles:
        exclusion = _check_hard_exclusions(profile, submission)
        if exclusion:
            continue
        breakdown, raw_score = _compute_score(profile, sub_meta)
        final_score = _apply_penalties(raw_score, profile, submission, sub_meta)
        scored.append({
            'reviewer': profile.user,
            'profile': profile,
            'score': round(final_score * 100, 1),
            'breakdown': breakdown,
            'rationale': _build_rationale(breakdown, profile, sub_meta),
            'workload_status': _workload_label(profile),
            'avg_turnaround': profile.avg_turnaround_days,
            'last_invited': profile.last_invited_at,
            'reviews_last_12m': _reviews_last_12m(profile),
        })

    scored.sort(key=lambda x: x['score'], reverse=True)

    # Apply temperature-based weighted random selection from top-N pool
    pool_size = max(n_primary * 3, 9)
    pool = scored[:pool_size]
    primary = _temperature_select(pool, n_primary)
    remaining = [s for s in scored if s not in primary]
    alternates = _temperature_select(remaining[:pool_size], n_alternates)

    # Diversity check
    _flag_diversity_warnings(primary)

    return {'primary': primary, 'alternates': alternates}


# ── Score components ──────────────────────────────────────────────────────────

def _build_submission_meta(submission) -> dict:
    revision = submission.get_current_revision()
    canonical = getattr(getattr(revision, 'canonical_document', None), 'data', {}) if revision else {}
    meta = canonical.get('metadata', {})
    return {
        'keywords': set(k.lower() for k in (meta.get('keywords') or submission.keywords or [])),
        'disciplines': set(d.lower() for d in (meta.get('disciplines') or submission.disciplines or [])),
        'artistic_mediums': set(m.lower() for m in (meta.get('artisticMediums') or submission.artistic_mediums or [])),
        'abstract': meta.get('abstract', [{}])[0].get('text', '') if meta.get('abstract') else '',
        'language': submission.language,
        'methodologies': set(),  # extracted from canonical if available
    }


def _compute_score(profile, sub_meta: dict) -> tuple[dict, float]:
    breakdown = {}

    # 1. Expertise similarity: keyword overlap between reviewer expertise and submission keywords
    rev_kw = set(k.lower() for k in profile.expertise_keywords)
    sub_kw = sub_meta['keywords']
    breakdown['expertise_similarity'] = _jaccard(rev_kw, sub_kw) if (rev_kw or sub_kw) else 0.0

    # 2. Discipline match
    rev_disc = set(d.lower() for d in profile.disciplines)
    breakdown['discipline_match'] = _overlap_score(rev_disc, sub_meta['disciplines'])

    # 3. Keyword overlap (same as expertise but weighted separately)
    breakdown['keyword_overlap'] = _jaccard(rev_kw, sub_kw)

    # 4. Methodology match
    rev_meth = set(m.lower() for m in profile.methodologies)
    breakdown['methodology_match'] = _overlap_score(rev_meth, sub_meta['methodologies'])

    # 5. Artistic medium match
    rev_med = set(m.lower() for m in profile.artistic_mediums)
    breakdown['artistic_medium_match'] = _overlap_score(rev_med, sub_meta['artistic_mediums'])

    # 6. Semantic similarity (AI layer — zero if disabled)
    if getattr(settings, 'AI_FEATURES_ENABLED', False) and settings.OPENAI_API_KEY:
        breakdown['semantic_similarity'] = _openai_similarity(
            profile.expertise_statement, sub_meta['abstract']
        )
    else:
        breakdown['semantic_similarity'] = 0.0

    # 7. Language match
    rev_langs = [l.lower() for l in profile.languages]
    breakdown['language_match'] = 1.0 if sub_meta['language'] in rev_langs else 0.0

    # 8. Availability
    breakdown['availability_score'] = _availability_score(profile)

    # 9. Timeliness
    breakdown['timeliness_score'] = _timeliness_score(profile)

    # 10. Workload balance
    active = profile.active_invitations_count
    breakdown['workload_balance'] = max(0.0, 1.0 - (active / MAX_ACTIVE_INVITATIONS))

    # 11. Editor quality score
    breakdown['editor_quality_score'] = float(profile.quality_score)

    # 12. Diversity (placeholder — computed at list level, per-reviewer contribution)
    breakdown['diversity_score'] = 0.5  # neutral; adjusted at ensemble level

    raw_score = sum(WEIGHTS[k] * v for k, v in breakdown.items())
    return breakdown, raw_score


def _apply_penalties(raw_score: float, profile, submission, sub_meta: dict) -> float:
    score = raw_score

    # Reuse penalty: if same editor kept using this reviewer
    from apps.reviewers.models import ReviewerInvitation
    recent = ReviewerInvitation.objects.filter(
        reviewer=profile.user,
        sent_at__gte=now() - timedelta(days=180),
    ).count()
    if recent >= 2:
        score -= 0.05 * (recent - 1)

    # Overload penalty
    active = profile.active_invitations_count
    if active >= MAX_ACTIVE_INVITATIONS:
        score -= 0.30  # heavy penalty

    return max(0.0, min(1.0, score))


def _check_hard_exclusions(profile, submission) -> str | None:
    """Return exclusion reason string if reviewer must be excluded, else None."""
    # Same person as author
    if profile.user == submission.author:
        return 'same_as_author'
    # Declared conflict
    sub_email = submission.author.email.lower()
    if sub_email in [c.lower() for c in profile.conflicts]:
        return 'declared_conflict'
    # Inactive or suspended
    if not profile.is_active or profile.is_suspended:
        return 'inactive_or_suspended'
    # Hard overload
    if profile.active_invitations_count >= MAX_ACTIVE_INVITATIONS * 2:
        return 'overloaded'
    return None


def _temperature_select(pool: list, n: int) -> list:
    """Weighted random selection with temperature to avoid always picking top-N."""
    if len(pool) <= n:
        return pool[:]
    scores = [item['score'] for item in pool]
    # Add temperature noise
    weights = [max(0.01, s + random.gauss(0, TEMPERATURE * 100)) for s in scores]
    selected = []
    available = list(range(len(pool)))
    for _ in range(n):
        if not available:
            break
        w = [weights[i] for i in available]
        total = sum(w)
        if total == 0:
            idx = random.choice(available)
        else:
            r = random.random() * total
            cum = 0.0
            idx = available[-1]
            for i, wi in zip(available, w):
                cum += wi
                if r <= cum:
                    idx = i
                    break
        selected.append(pool[idx])
        available.remove(idx)
    return selected


def _flag_diversity_warnings(suggestions: list):
    """Flag if all suggestions share the same institution."""
    institutions = [s['profile'].user.profile.institution for s in suggestions if hasattr(s['profile'].user, 'profile')]
    if len(set(institutions)) == 1 and len(institutions) > 1:
        for s in suggestions:
            s['diversity_warning'] = 'All suggestions from same institution.'


# ── Utility functions ─────────────────────────────────────────────────────────

def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def _overlap_score(reviewer_set: set, submission_set: set) -> float:
    if not submission_set:
        return 0.5  # neutral if submission has no data
    if not reviewer_set:
        return 0.0
    return min(1.0, len(reviewer_set & submission_set) / len(submission_set))


def _availability_score(profile) -> float:
    today = date.today()
    for period in profile.unavailable_dates:
        try:
            start = date.fromisoformat(period.get('from', ''))
            end = date.fromisoformat(period.get('to', ''))
            if start <= today <= end:
                return 0.0
        except (ValueError, AttributeError):
            pass
    return 1.0


def _timeliness_score(profile) -> float:
    avg = profile.avg_turnaround_days
    # Target: 14–21 days. >45 days = poor.
    if avg <= 14:
        return 1.0
    if avg <= 21:
        return 0.9
    if avg <= 30:
        return 0.7
    if avg <= 45:
        return 0.4
    return 0.1


def _reviews_last_12m(profile) -> int:
    from apps.reviews.models import Review
    from datetime import timedelta
    cutoff = now() - timedelta(days=365)
    return Review.objects.filter(
        invitation__reviewer=profile.user,
        submitted_at__gte=cutoff,
    ).count()


def _workload_label(profile) -> str:
    active = profile.active_invitations_count
    if active == 0:
        return 'Available'
    if active < MAX_ACTIVE_INVITATIONS:
        return f'Moderate ({active} active)'
    return f'Heavy ({active} active)'


def _build_rationale(breakdown: dict, profile, sub_meta: dict) -> str:
    reasons = []
    if breakdown.get('discipline_match', 0) > 0.5:
        reasons.append('strong discipline match')
    if breakdown.get('artistic_medium_match', 0) > 0.5:
        reasons.append('artistic medium alignment')
    if breakdown.get('methodology_match', 0) > 0.5:
        reasons.append('methodological fit')
    if breakdown.get('language_match', 0) == 1.0:
        reasons.append('language match')
    if breakdown.get('timeliness_score', 0) >= 0.9:
        reasons.append(f'fast avg turnaround ({profile.avg_turnaround_days:.0f} days)')
    if not reasons:
        reasons.append('general expertise alignment')
    return f"Suggested because: {', '.join(reasons)}."


def _openai_similarity(text_a: str, text_b: str) -> float:
    """Semantic similarity via OpenAI embeddings. Returns 0-1 cosine similarity."""
    if not text_a or not text_b:
        return 0.0
    try:
        import openai
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        resp = client.embeddings.create(input=[text_a, text_b], model='text-embedding-3-small')
        va = resp.data[0].embedding
        vb = resp.data[1].embedding
        dot = sum(a * b for a, b in zip(va, vb))
        na = math.sqrt(sum(a * a for a in va))
        nb = math.sqrt(sum(b * b for b in vb))
        if na == 0 or nb == 0:
            return 0.0
        return max(0.0, min(1.0, dot / (na * nb)))
    except Exception:
        return 0.0
