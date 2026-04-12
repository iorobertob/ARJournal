from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='reviews.Review')
def on_review_saved(sender, instance, **kwargs):
    """Recompute reviewer profile stats when a review is submitted or moderated."""
    if instance.status in ('submitted', 'moderated', 'released'):
        from apps.reviewers.profile_stats import recompute_reviewer_profile
        recompute_reviewer_profile(instance.invitation.reviewer)
