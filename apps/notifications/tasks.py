"""Celery tasks for email notifications."""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone


def _log_email(to, subject, status, error=''):
    from .models import EmailLog
    EmailLog.objects.create(
        to_email=to,
        subject=subject,
        status=status,
        sent_at=timezone.now() if status == 'sent' else None,
        error=error,
    )


@shared_task
def notify_submission_received(submission_pk):
    from apps.submissions.models import Submission
    sub = Submission.objects.select_related('author').get(pk=submission_pk)
    subject = f'[Trans/Act] Submission received: {sub.title[:60]}'
    body = (
        f'Dear {sub.author.display_name},\n\n'
        f'We have received your submission "{sub.title}".\n'
        f'Our editorial team will perform a technical check and notify you of next steps.\n\n'
        f'Trans/Act Editorial Office'
    )
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [sub.author.email])
        _log_email(sub.author.email, subject, 'sent')
        from .models import Notification
        Notification.objects.create(
            user=sub.author,
            notification_type='submission_received',
            message=f'Your submission "{sub.title[:60]}" has been received.',
            url=f'/author/submission/{sub.pk}/',
        )
    except Exception as e:
        _log_email(sub.author.email, subject, 'failed', str(e))


@shared_task
def notify_reviewer_invited(invitation_pk):
    from apps.reviewers.models import ReviewerInvitation
    inv = ReviewerInvitation.objects.select_related('reviewer', 'submission').get(pk=invitation_pk)
    subject = f'[Trans/Act] Review invitation: {inv.submission.title[:60]}'
    accept_url = f'/review/invitation/{inv.magic_token}/'
    body = (
        f'Dear {inv.reviewer.display_name},\n\n'
        f'You are invited to review the submission "{inv.submission.title}".\n\n'
        f'To respond to this invitation, please visit:\n'
        f'{settings.BASE_URL if hasattr(settings, "BASE_URL") else ""}{accept_url}\n\n'
        f'Review deadline: {inv.deadline}\n\n'
        f'Trans/Act Editorial Office'
    )
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [inv.reviewer.email])
        _log_email(inv.reviewer.email, subject, 'sent')
    except Exception as e:
        _log_email(inv.reviewer.email, subject, 'failed', str(e))


@shared_task
def notify_review_submitted(review_pk):
    from apps.reviews.models import Review
    review = Review.objects.select_related('invitation__submission').get(pk=review_pk)
    submission = review.invitation.submission
    # Notify editorial team
    for assignment in submission.assignments.filter(is_active=True):
        if assignment.editor:
            subject = f'[Trans/Act] Review submitted for: {submission.title[:60]}'
            body = (
                f'A review has been submitted for "{submission.title}".\n'
                f'Please check the editorial dashboard for details.\n\n'
                f'Trans/Act System'
            )
            try:
                send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [assignment.editor.email])
                _log_email(assignment.editor.email, subject, 'sent')
            except Exception as e:
                _log_email(assignment.editor.email, subject, 'failed', str(e))


@shared_task
def notify_decision_sent(decision_pk):
    from apps.editorial.models import EditorialDecision
    decision = EditorialDecision.objects.select_related('submission__author').get(pk=decision_pk)
    submission = decision.submission
    subject = f'[Trans/Act] Editorial decision: {submission.title[:60]}'
    body = (
        f'Dear {submission.author.display_name},\n\n'
        f'The editors have reached a decision regarding your submission "{submission.title}".\n\n'
        f'Decision: {decision.get_decision_type_display()}\n\n'
        f'{decision.letter}\n\n'
        f'Trans/Act Editorial Office'
    )
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [submission.author.email])
        _log_email(submission.author.email, subject, 'sent')
        from .models import Notification
        Notification.objects.create(
            user=submission.author,
            notification_type='decision_sent',
            message=f'Editorial decision received for "{submission.title[:50]}".',
            url=f'/author/submission/{submission.pk}/',
        )
    except Exception as e:
        _log_email(submission.author.email, subject, 'failed', str(e))


@shared_task
def cleanup_expired_pdf_exports():
    """Celery beat task: remove expired ephemeral PDF exports."""
    from apps.production.models import PDFExport
    from django.utils import timezone
    expired = PDFExport.objects.filter(expires_at__lt=timezone.now())
    for exp in expired:
        if exp.file:
            try:
                exp.file.delete(save=False)
            except Exception:
                pass
    expired.delete()


@shared_task
def send_review_reminders():
    """Celery beat task: remind reviewers of upcoming deadlines."""
    from apps.reviewers.models import ReviewerInvitation, InvitationStatus
    from django.utils.timezone import now
    from datetime import timedelta
    upcoming = ReviewerInvitation.objects.filter(
        status=InvitationStatus.ACCEPTED,
        deadline__lte=(now() + timedelta(days=5)).date(),
    ).select_related('reviewer', 'submission')
    for inv in upcoming:
        subject = f'[Trans/Act] Review reminder: deadline {inv.deadline}'
        body = (
            f'Dear {inv.reviewer.display_name},\n\n'
            f'This is a reminder that your review for "{inv.submission.title}" '
            f'is due on {inv.deadline}.\n\n'
            f'Trans/Act Editorial Office'
        )
        try:
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [inv.reviewer.email])
            _log_email(inv.reviewer.email, subject, 'sent')
        except Exception as e:
            _log_email(inv.reviewer.email, subject, 'failed', str(e))
