"""Shared definitions for the InAct peer-review evaluation form.

The evaluation criteria and additional questions are stored on
``Review.scores`` (a JSONField) under the ``criteria`` and ``questions`` keys.
Keeping the canonical lists here means the reviewer form, the read-only review
detail, and the editorial moderation view all render the same labels in the
same order.
"""

# ── Evaluation criteria (rated 1 = Poor … 5 = Excellent) ────────────────────
# (slug, label) — slug is used as the form field suffix: criterion_<slug>.
EVALUATION_CRITERIA = [
    ('originality', 'Originality and significance of the contribution'),
    ('relevance', 'Relevance to the aims and scope of InAct'),
    ('methodology', 'Quality of research design, methodology, or artistic process'),
    ('literature', 'Critical engagement with relevant literature and context'),
    ('argumentation', 'Clarity and coherence of argumentation'),
    ('analysis', 'Quality of analysis, findings, or artistic outcomes'),
    ('collaboration', 'Contribution to collaborative, interdisciplinary, or artistic research'),
    ('integrity', 'Research integrity'),
    ('writing', 'Quality of writing and presentation'),
    ('suitability', 'Overall suitability for publication'),
]

CRITERION_SCALE = ['1', '2', '3', '4', '5']

# ── Additional yes / partially / no questions ───────────────────────────────
# (slug, question text, [(value, label), …])
YES_PARTIAL_NO = [
    ('yes', 'Yes'),
    ('partially', 'Partially'),
    ('no', 'No'),
]

ADDITIONAL_QUESTIONS = [
    (
        'contribution',
        'Does the manuscript make a clear contribution to knowledge, artistic '
        'research, or professional practice?',
        YES_PARTIAL_NO,
    ),
    (
        'conclusions',
        'Are the conclusions supported by the evidence, analysis, or artistic '
        'outcomes presented?',
        YES_PARTIAL_NO,
    ),
    (
        'ethics',
        'Have you identified any ethical concerns, conflicts of interest, '
        'plagiarism, or other issues requiring editorial attention?',
        [('no', 'No'), ('yes', 'Yes (please explain below, under Ethical Concerns)')],
    ),
]

_CRITERIA_LABELS = dict(EVALUATION_CRITERIA)
_QUESTION_LABELS = {slug: text for slug, text, _ in ADDITIONAL_QUESTIONS}
_QUESTION_VALUE_LABELS = {
    slug: dict(options) for slug, _, options in ADDITIONAL_QUESTIONS
}


def criteria_fields(scores):
    """Return the criteria as ``[{slug, label, value}, …]`` for form rendering."""
    stored = (scores or {}).get('criteria', {})
    return [
        {'slug': slug, 'label': label, 'value': str(stored.get(slug, ''))}
        for slug, label in EVALUATION_CRITERIA
    ]


def question_fields(scores):
    """Return the additional questions with the currently-selected value."""
    stored = (scores or {}).get('questions', {})
    return [
        {'slug': slug, 'text': text, 'options': options, 'value': str(stored.get(slug, ''))}
        for slug, text, options in ADDITIONAL_QUESTIONS
    ]


def criteria_display(scores):
    """Return ``[(label, '4/5'), …]`` for rated criteria (read-only views)."""
    stored = (scores or {}).get('criteria', {})
    rows = []
    for slug, label in EVALUATION_CRITERIA:
        val = stored.get(slug)
        if val:
            rows.append((label, f'{val}/5'))
    return rows


def questions_display(scores):
    """Return ``[(question, answer_label), …]`` for answered questions."""
    stored = (scores or {}).get('questions', {})
    rows = []
    for slug, text, _ in ADDITIONAL_QUESTIONS:
        val = stored.get(slug)
        if val:
            label = _QUESTION_VALUE_LABELS.get(slug, {}).get(val, val)
            rows.append((text, label))
    return rows


def collect_scores_from_payload(data, existing=None):
    """Merge ``criterion_*`` / ``q_*`` keys from a POST/JSON payload into a
    ``{'criteria': {...}, 'questions': {...}}`` scores dict."""
    scores = dict(existing or {})
    criteria = dict(scores.get('criteria', {}))
    questions = dict(scores.get('questions', {}))
    for key, val in data.items():
        if key.startswith('criterion_') and val not in ('', None):
            slug = key[len('criterion_'):]
            if slug in _CRITERIA_LABELS:
                criteria[slug] = str(val)
        elif key.startswith('q_') and val not in ('', None):
            slug = key[len('q_'):]
            if slug in _QUESTION_LABELS:
                questions[slug] = str(val)
    scores['criteria'] = criteria
    scores['questions'] = questions
    return scores
