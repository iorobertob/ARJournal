from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='accounts.User')
def ensure_reviewer_profile(sender, instance, **kwargs):
    """Auto-create a ReviewerProfile whenever a user has the reviewer role."""
    if 'reviewer' in (instance.roles or []):
        from apps.reviewers.models import ReviewerProfile
        ReviewerProfile.objects.get_or_create(
            user=instance,
            defaults={'is_active': True, 'is_suspended': False},
        )


@receiver(post_save, sender='reviewers.ReviewerInvitation')
def on_invitation_saved(sender, instance, **kwargs):
    """Recompute reviewer profile stats when an invitation changes state."""
    from apps.reviewers.profile_stats import recompute_reviewer_profile
    recompute_reviewer_profile(instance.reviewer)
