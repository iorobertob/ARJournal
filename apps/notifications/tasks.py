"""Celery tasks for email notifications.

All emails are sent as multipart (HTML + plain-text fallback) using
EmailMultiAlternatives. The HTML uses table-based layout with inline
styles for broad email-client compatibility.
"""
import html as _html
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone


# ── Helpers ───────────────────────────────────────────────────────────────────

def _site_url() -> str:
    return getattr(settings, 'SITE_URL', 'https://trans-act-journal.org').rstrip('/')


def _e(text: str) -> str:
    """HTML-escape a string for safe inline insertion."""
    return _html.escape(str(text))


def _btn(url: str, label: str, secondary: bool = False) -> str:
    """Render a CTA button compatible with most email clients."""
    bg = '#ffffff' if secondary else '#E86B1F'
    color = '#E86B1F' if secondary else '#ffffff'
    border = 'border:2px solid #E86B1F;' if secondary else ''
    return (
        f'<table cellpadding="0" cellspacing="0" border="0" style="margin:8px 0;">'
        f'<tr><td style="background-color:{bg};{border}border-radius:6px;">'
        f'<a href="{_e(url)}" style="display:inline-block;padding:11px 22px;'
        f'font-family:Arial,Helvetica,sans-serif;font-size:13px;font-weight:600;'
        f'color:{color};text-decoration:none;border-radius:6px;">{_e(label)}</a>'
        f'</td></tr></table>'
    )


def _detail_box(label: str, value: str) -> str:
    return (
        f'<table cellpadding="0" cellspacing="0" border="0" '
        f'style="margin:16px 0;width:100%;max-width:520px;">'
        f'<tr><td style="padding:12px 16px;background-color:#f9f8f5;'
        f'border:1px solid #e8e7e3;border-radius:6px;">'
        f'<p style="margin:0;font-family:Arial,Helvetica,sans-serif;font-size:11px;'
        f'color:#888888;text-transform:uppercase;letter-spacing:0.08em;">{_e(label)}</p>'
        f'<p style="margin:5px 0 0;font-family:Georgia,\'Times New Roman\',serif;'
        f'font-size:15px;color:#1A1A1A;font-weight:bold;">{_e(value)}</p>'
        f'</td></tr></table>'
    )


def _p(text: str) -> str:
    return (
        f'<p style="margin:0 0 16px;font-family:Georgia,\'Times New Roman\',serif;'
        f'font-size:15px;color:#1A1A1A;line-height:1.75;">{text}</p>'
    )


def _greeting(name: str) -> str:
    return _p(f'Dear {_e(name)},')


def _signature() -> str:
    return (
        '<p style="margin:24px 0 0;font-family:Georgia,\'Times New Roman\',serif;'
        'font-size:14px;color:#6B6B6B;line-height:1.6;">'
        'Warm regards,<br>'
        '<strong style="color:#1A1A1A;">The Trans/Act Editorial Office</strong>'
        '</p>'
    )


def _quoted_block(text: str) -> str:
    """Render a quoted block (e.g. decision letter) preserving line breaks."""
    return (
        '<div style="margin:20px 0;padding:20px 24px;background-color:#f9f8f5;'
        'border-left:3px solid #e8e7e3;border-radius:0 4px 4px 0;">'
        '<p style="margin:0;font-family:Georgia,\'Times New Roman\',serif;font-size:14px;'
        f'color:#444444;line-height:1.75;white-space:pre-line;">{_e(text)}</p>'
        '</div>'
    )


def _decision_badge(label: str, color: str = '#1A1A1A', bg: str = '#f4f3ef') -> str:
    return (
        f'<table cellpadding="0" cellspacing="0" border="0" style="margin:16px 0;">'
        f'<tr><td style="background-color:{bg};border-left:3px solid #E86B1F;'
        f'padding:10px 16px;border-radius:0 4px 4px 0;">'
        f'<p style="margin:0;font-family:Arial,Helvetica,sans-serif;font-size:11px;'
        f'color:#888888;text-transform:uppercase;letter-spacing:0.08em;">Editorial decision</p>'
        f'<p style="margin:5px 0 0;font-family:Georgia,\'Times New Roman\',serif;'
        f'font-size:17px;color:{color};font-weight:bold;">{_e(label)}</p>'
        f'</td></tr></table>'
    )


def _html_wrapper(body_html: str) -> str:
    """Wrap the email body content in the full branded Trans/Act email shell."""
    site_url = _site_url()
    domain = site_url.replace('https://', '').replace('http://', '')
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <title>Trans/Act</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f3ef;font-family:Georgia,'Times New Roman',serif;-webkit-font-smoothing:antialiased;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:#f4f3ef;padding:40px 16px;">
    <tr>
      <td align="center">
        <!-- Email card -->
        <table width="600" cellpadding="0" cellspacing="0" border="0"
               style="max-width:600px;width:100%;background-color:#ffffff;
                      border-radius:8px;overflow:hidden;
                      box-shadow:0 2px 12px rgba(0,0,0,0.08);">
          <!-- Orange accent bar -->
          <tr>
            <td style="background-color:#E86B1F;height:4px;font-size:0;line-height:0;">&nbsp;</td>
          </tr>
          <!-- Journal header -->
          <tr>
            <td style="padding:32px 40px 20px;">
              <p style="margin:0;font-family:Georgia,'Times New Roman',serif;
                         font-size:20px;font-weight:bold;color:#1A1A1A;
                         letter-spacing:-0.02em;">Trans/Act</p>
              <p style="margin:4px 0 0;font-family:Arial,Helvetica,sans-serif;
                         font-size:10px;color:#999999;text-transform:uppercase;
                         letter-spacing:0.14em;">Journal of Artistic Research</p>
            </td>
          </tr>
          <!-- Divider -->
          <tr>
            <td style="padding:0 40px;">
              <hr style="border:none;border-top:1px solid #e8e7e3;margin:0;">
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:32px 40px;">
              {body_html}
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="padding:20px 40px 32px;border-top:1px solid #e8e7e3;">
              <p style="margin:0;font-family:Arial,Helvetica,sans-serif;
                         font-size:11px;color:#999999;line-height:1.65;">
                Trans/Act: Journal of Artistic Research &mdash;
                <a href="{site_url}" style="color:#E86B1F;text-decoration:none;">{domain}</a><br>
                This is an automated message. Please do not reply to this email.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _send(
    to: str,
    subject: str,
    plain: str,
    html_body: str,
) -> None:
    """Send a multipart email and raise on failure (caller handles logging)."""
    msg = EmailMultiAlternatives(
        subject=subject,
        body=plain,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to],
    )
    msg.attach_alternative(_html_wrapper(html_body), 'text/html')
    msg.send()


def _log_email(to: str, subject: str, status: str, error: str = '') -> None:
    from .models import EmailLog
    EmailLog.objects.create(
        to_email=to,
        subject=subject,
        status=status,
        sent_at=timezone.now() if status == 'sent' else None,
        error=error,
    )


# ── Notification tasks ────────────────────────────────────────────────────────

@shared_task
def notify_submission_received(submission_pk):
    """Confirm to the author that their submission has been received."""
    from apps.submissions.models import Submission
    sub = Submission.objects.select_related('author').get(pk=submission_pk)

    subject = f'Submission received — {sub.title[:70]}'
    dashboard_url = f'{_site_url()}/author/submission/{sub.pk}/'

    # ── HTML ─────────────────────────────────────────────────────────────────
    html_body = (
        _greeting(sub.author.display_name)
        + _p('Thank you for submitting your work to <strong>Trans/Act: Journal of '
             'Artistic Research</strong>. We have successfully received your submission.')
        + _detail_box('Submission title', sub.title)
        + _p('Our editorial team will carry out a technical check to ensure your '
             'submission meets the journal\'s formatting and completeness requirements. '
             'You will be notified by email of each step in the review process.')
        + _p('You can monitor the status of your submission at any time from your '
             'author dashboard.')
        + _btn(dashboard_url, 'View your submission')
        + _signature()
    )

    # ── Plain text ────────────────────────────────────────────────────────────
    plain = (
        f'Dear {sub.author.display_name},\n\n'
        f'Thank you for submitting your work to Trans/Act: Journal of Artistic Research. '
        f'We have successfully received your submission.\n\n'
        f'Submission: {sub.title}\n\n'
        f'Our editorial team will carry out a technical check and notify you of next steps. '
        f'You can track your submission status at any time:\n{dashboard_url}\n\n'
        f'Warm regards,\nThe Trans/Act Editorial Office'
    )

    try:
        _send(sub.author.email, subject, plain, html_body)
        _log_email(sub.author.email, subject, 'sent')
        from .models import Notification
        Notification.objects.create(
            user=sub.author,
            notification_type='submission_received',
            message=f'Your submission \u201c{sub.title[:60]}\u201d has been received.',
            url=f'/author/submission/{sub.pk}/',
        )
    except Exception as exc:
        _log_email(sub.author.email, subject, 'failed', str(exc))


@shared_task
def notify_reviewer_invited(invitation_pk):
    """Invite a reviewer to assess a submission."""
    from apps.reviewers.models import ReviewerInvitation
    inv = ReviewerInvitation.objects.select_related('reviewer', 'submission').get(pk=invitation_pk)

    invitation_url = f'{_site_url()}/review/invitation/{inv.magic_token}/'
    subject = f'Invitation to review — {inv.submission.title[:70]}'
    deadline_str = inv.deadline.strftime('%-d %B %Y') if hasattr(inv.deadline, 'strftime') else str(inv.deadline)

    # ── HTML ─────────────────────────────────────────────────────────────────
    html_body = (
        _greeting(inv.reviewer.display_name)
        + _p('The editorial board of <strong>Trans/Act: Journal of Artistic Research</strong> '
             'would like to invite you to serve as a peer reviewer for the following submission.')
        + _detail_box('Submission title', inv.submission.title)
        + _detail_box('Review deadline', deadline_str)
        + _p('Please follow the link below to read the abstract, accept or decline this invitation, '
             'and — if you accept — access the full manuscript and review form. '
             'Your response helps us plan the review process and is appreciated at the earliest convenience.')
        + _btn(invitation_url, 'Respond to this invitation')
        + _p('If you are unable to review this submission, we would be grateful if you could suggest '
             'an alternative reviewer with relevant expertise.')
        + _p('<span style="font-size:13px;color:#6B6B6B;">All reviews are conducted under '
             'double-blind conditions. Your identity will not be disclosed to the authors.</span>')
        + _signature()
    )

    # ── Plain text ────────────────────────────────────────────────────────────
    plain = (
        f'Dear {inv.reviewer.display_name},\n\n'
        f'The editorial board of Trans/Act: Journal of Artistic Research invites you '
        f'to review the following submission.\n\n'
        f'Title: {inv.submission.title}\n'
        f'Review deadline: {deadline_str}\n\n'
        f'Please visit the link below to accept or decline:\n{invitation_url}\n\n'
        f'All reviews are conducted under double-blind conditions.\n\n'
        f'Warm regards,\nThe Trans/Act Editorial Office'
    )

    try:
        _send(inv.reviewer.email, subject, plain, html_body)
        _log_email(inv.reviewer.email, subject, 'sent')
    except Exception as exc:
        _log_email(inv.reviewer.email, subject, 'failed', str(exc))


@shared_task
def notify_review_submitted(review_pk):
    """Notify handling editors that a review has been submitted."""
    from apps.reviews.models import Review
    review = Review.objects.select_related('invitation__submission').get(pk=review_pk)
    submission = review.invitation.submission
    subject = f'Review submitted — {submission.title[:70]}'

    for assignment in submission.assignments.filter(is_active=True):
        editor = assignment.editor
        if not editor:
            continue

        dashboard_url = f'{_site_url()}/editorial/submission/{submission.pk}/'

        # ── HTML ─────────────────────────────────────────────────────────────
        html_body = (
            _greeting(editor.display_name)
            + _p(f'A peer review has been submitted for the following manuscript and is '
                 f'now available in the editorial dashboard.')
            + _detail_box('Submission title', submission.title)
            + _p('Please log in to review the submitted assessment and determine next steps '
                 'in the editorial process.')
            + _btn(dashboard_url, 'View submission in dashboard')
            + _signature()
        )

        # ── Plain text ────────────────────────────────────────────────────────
        plain = (
            f'Dear {editor.display_name},\n\n'
            f'A peer review has been submitted for "{submission.title}" '
            f'and is available in the editorial dashboard.\n\n'
            f'{dashboard_url}\n\n'
            f'Warm regards,\nThe Trans/Act Editorial Office'
        )

        try:
            _send(editor.email, subject, plain, html_body)
            _log_email(editor.email, subject, 'sent')
        except Exception as exc:
            _log_email(editor.email, subject, 'failed', str(exc))


@shared_task
def notify_decision_sent(decision_pk):
    """Notify the author of an editorial decision."""
    from apps.editorial.models import EditorialDecision
    decision = EditorialDecision.objects.select_related('submission__author').get(pk=decision_pk)
    submission = decision.submission
    decision_label = decision.get_decision_type_display()
    subject = f'Editorial decision — {submission.title[:70]}'
    dashboard_url = f'{_site_url()}/author/submission/{submission.pk}/'

    # Pick a badge colour to reflect the decision sentiment
    _positive = {'Accept', 'accept', 'accepted', 'Accept with minor revisions'}
    _neutral = {'Revise and resubmit', 'Major revision', 'Minor revision'}
    if any(kw in decision_label for kw in _positive):
        badge_color, badge_bg = '#16a34a', '#f0fdf4'
    elif any(kw in decision_label for kw in _neutral):
        badge_color, badge_bg = '#92400e', '#fffbeb'
    else:
        badge_color, badge_bg = '#1A1A1A', '#f4f3ef'

    # ── HTML ─────────────────────────────────────────────────────────────────
    html_body = (
        _greeting(submission.author.display_name)
        + _p(f'The editorial board of <strong>Trans/Act: Journal of Artistic Research</strong> '
             f'has reached a decision regarding your submission.')
        + _detail_box('Submission title', submission.title)
        + _decision_badge(decision_label, color=badge_color, bg=badge_bg)
        + _p('The editors have provided the following letter:')
        + _quoted_block(decision.letter)
        + _p('Please log in to your author dashboard to read the full decision, '
             'including any reviewer comments that have been made available to you.')
        + _btn(dashboard_url, 'View decision in dashboard')
        + _signature()
    )

    # ── Plain text ────────────────────────────────────────────────────────────
    plain = (
        f'Dear {submission.author.display_name},\n\n'
        f'The editorial board of Trans/Act: Journal of Artistic Research has reached '
        f'a decision regarding your submission "{submission.title}".\n\n'
        f'Decision: {decision_label}\n\n'
        f'{decision.letter}\n\n'
        f'Please visit your author dashboard for full details:\n{dashboard_url}\n\n'
        f'Warm regards,\nThe Trans/Act Editorial Office'
    )

    try:
        _send(submission.author.email, subject, plain, html_body)
        _log_email(submission.author.email, subject, 'sent')
        from .models import Notification
        Notification.objects.create(
            user=submission.author,
            notification_type='decision_sent',
            message=f'Editorial decision received for \u201c{submission.title[:50]}\u201d.',
            url=f'/author/submission/{submission.pk}/',
        )
    except Exception as exc:
        _log_email(submission.author.email, subject, 'failed', str(exc))


@shared_task
def cleanup_expired_pdf_exports():
    """Celery beat: remove expired ephemeral PDF exports."""
    from apps.production.models import PDFExport
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
    """Celery beat: remind reviewers of approaching deadlines (daily at 09:00 UTC)."""
    from apps.reviewers.models import ReviewerInvitation, InvitationStatus
    from django.utils.timezone import now
    from datetime import timedelta

    upcoming = ReviewerInvitation.objects.filter(
        status=InvitationStatus.ACCEPTED,
        deadline__lte=(now() + timedelta(days=5)).date(),
    ).select_related('reviewer', 'submission')

    for inv in upcoming:
        deadline_str = (
            inv.deadline.strftime('%-d %B %Y')
            if hasattr(inv.deadline, 'strftime')
            else str(inv.deadline)
        )
        days_left = (inv.deadline - now().date()).days
        subject = f'Review reminder — deadline {deadline_str}'
        workspace_url = f'{_site_url()}/review/invitation/{inv.magic_token}/'

        urgency_color = '#dc2626' if days_left <= 2 else '#92400e' if days_left <= 4 else '#1A1A1A'

        # ── HTML ──────────────────────────────────────────────────────────────
        days_label = '1 day' if days_left == 1 else f'{days_left} days'
        html_body = (
            _greeting(inv.reviewer.display_name)
            + _p(f'This is a friendly reminder that your peer review for the following '
                 f'submission is due shortly.')
            + _detail_box('Submission title', inv.submission.title)
            + (
                f'<table cellpadding="0" cellspacing="0" border="0" '
                f'style="margin:16px 0;width:100%;max-width:520px;">'
                f'<tr><td style="padding:12px 16px;background-color:#f9f8f5;'
                f'border:1px solid #e8e7e3;border-radius:6px;">'
                f'<p style="margin:0;font-family:Arial,Helvetica,sans-serif;font-size:11px;'
                f'color:#888888;text-transform:uppercase;letter-spacing:0.08em;">Deadline</p>'
                f'<p style="margin:5px 0 0;font-family:Georgia,\'Times New Roman\',serif;'
                f'font-size:15px;font-weight:bold;color:{urgency_color};">'
                f'{_e(deadline_str)}'
                f'<span style="font-size:12px;font-weight:normal;color:#888888;margin-left:8px;">'
                f'({_e(days_label)} remaining)</span></p>'
                f'</td></tr></table>'
            )
            + _p('Please log in to your review workspace to complete and submit your assessment.')
            + _btn(workspace_url, 'Go to review workspace')
            + _p('<span style="font-size:13px;color:#6B6B6B;">If you are no longer able to '
                 'complete this review, please let us know as soon as possible so that we can '
                 'make alternative arrangements.</span>')
            + _signature()
        )

        # ── Plain text ────────────────────────────────────────────────────────
        plain = (
            f'Dear {inv.reviewer.display_name},\n\n'
            f'This is a reminder that your review for "{inv.submission.title}" '
            f'is due on {deadline_str} ({days_label} remaining).\n\n'
            f'Review workspace:\n{workspace_url}\n\n'
            f'If you are unable to complete this review, please contact us as soon as possible.\n\n'
            f'Warm regards,\nThe Trans/Act Editorial Office'
        )

        try:
            _send(inv.reviewer.email, subject, plain, html_body)
            _log_email(inv.reviewer.email, subject, 'sent')
        except Exception as exc:
            _log_email(inv.reviewer.email, subject, 'failed', str(exc))
