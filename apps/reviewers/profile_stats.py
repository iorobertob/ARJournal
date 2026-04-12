"""
Utility: recompute ReviewerProfile stats from live data.
Called from signals whenever invitations or reviews change state.
"""
from django.utils import timezone


def recompute_reviewer_profile(user):
    """
    Recompute all auto-tracked fields on the user's ReviewerProfile.
    Safe to call multiple times — always derives from current DB state.
    """
    from apps.reviewers.models import ReviewerProfile, ReviewerInvitation
    from apps.reviews.models import Review

    try:
        profile = user.reviewer_profile
    except ReviewerProfile.DoesNotExist:
        return  # no profile to update

    # ── Active invitations ────────────────────────────────────────────
    # Accepted invitations that do not yet have a submitted/completed review
    active = ReviewerInvitation.objects.filter(
        reviewer=user,
        status='accepted',
    ).exclude(
        review__status__in=['submitted', 'moderated', 'released']
    ).count()

    # ── Completed reviews ─────────────────────────────────────────────
    completed = list(
        Review.objects.filter(
            invitation__reviewer=user,
            status__in=['submitted', 'moderated', 'released'],
            submitted_at__isnull=False,
        ).select_related('invitation')
    )
    total_completed = len(completed)

    # ── Turnaround & responsiveness ───────────────────────────────────
    turnarounds = []
    on_time = 0
    for r in completed:
        delta = (r.submitted_at - r.invitation.sent_at).days
        turnarounds.append(max(0, delta))
        if r.submitted_at.date() <= r.invitation.deadline:
            on_time += 1

    avg_turnaround = (
        round(sum(turnarounds) / len(turnarounds), 1)
        if turnarounds else profile.avg_turnaround_days
    )
    responsiveness = (
        round(on_time / len(turnarounds), 2)
        if turnarounds else profile.responsiveness_score
    )

    # ── Quality score ─────────────────────────────────────────────────
    # Derived from reviewer's self-reported expertise rating (1–5 scale → 0–1).
    # Falls back to existing value if no ratings recorded.
    ratings = [r.expertise_self_rating for r in completed if r.expertise_self_rating]
    quality = (
        round(sum(ratings) / len(ratings) / 5.0, 2)
        if ratings else profile.quality_score
    )

    # ── Last invited ──────────────────────────────────────────────────
    last_inv = (
        ReviewerInvitation.objects
        .filter(reviewer=user)
        .order_by('-sent_at')
        .values_list('sent_at', flat=True)
        .first()
    )

    # ── Persist ───────────────────────────────────────────────────────
    profile.active_invitations_count = active
    profile.total_reviews_completed = total_completed
    profile.avg_turnaround_days = avg_turnaround
    profile.responsiveness_score = responsiveness
    profile.quality_score = quality
    if last_inv:
        profile.last_invited_at = last_inv
    profile.save(update_fields=[
        'active_invitations_count',
        'total_reviews_completed',
        'avg_turnaround_days',
        'responsiveness_score',
        'quality_score',
        'last_invited_at',
    ])
