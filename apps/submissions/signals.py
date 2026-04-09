from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Submission, SubmissionStatus


@receiver(post_save, sender=Submission)
def log_status_change(sender, instance, created, **kwargs):
    from apps.notifications.models import AuditEvent
    if created:
        AuditEvent.objects.create(
            submission=instance,
            event_type='submission_created',
            actor=instance.author,
            payload={'title': instance.title},
        )
