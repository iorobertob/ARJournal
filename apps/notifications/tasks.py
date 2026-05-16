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
    return settings.SITE_URL.rstrip('/')



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
    """Send a multipart email and log the result.

    Creates an EmailLog record before sending (to obtain the tracking token),
    injects a 1×1 tracking pixel into the HTML, sends, then updates the log
    status to 'sent' or 'failed'. Raises on failure so callers can add their
    own Notification / in-app logic in the except block.
    """
    from .models import EmailLog
    from apps.journal.models import JournalConfig
    from django.core.mail import get_connection

    # Create the log entry first so we have a tracking token before sending.
    log = EmailLog.objects.create(
        to_email=to,
        subject=subject,
        status='pending',
        plain_body=plain,
        html_body=html_body,
    )

    # Inject tracking pixel into the HTML body before wrapping.
    pixel_url = f'{_site_url()}/notifications/t/{log.tracking_token}/'
    pixel_tag = (
        f'<img src="{pixel_url}" width="1" height="1" '
        f'style="display:none;border:0;outline:none;" alt="">'
    )
    full_html = _html_wrapper(html_body + pixel_tag)

    journal = JournalConfig.get()

    if journal.email_from_name and journal.email_from_address:
        from_email = f'{journal.email_from_name} <{journal.email_from_address}>'
    elif journal.email_from_address:
        from_email = journal.email_from_address
    else:
        from_email = settings.DEFAULT_FROM_EMAIL

    connection = None
    if journal.email_backend_type == 'smtp' and journal.smtp_host:
        connection = get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host=journal.smtp_host,
            port=journal.smtp_port,
            username=journal.smtp_username,
            password=journal.smtp_password,
            use_tls=journal.smtp_use_tls,
            fail_silently=False,
        )
    elif journal.email_backend_type == 'mailersend' and journal.mailersend_api_token:
        connection = get_connection(
            backend='anymail.backends.mailersend.EmailBackend',
            api_token=journal.mailersend_api_token,
        )

    msg = EmailMultiAlternatives(
        subject=subject,
        body=plain,
        from_email=from_email,
        to=[to],
        connection=connection,
    )
    msg.attach_alternative(full_html, 'text/html')

    try:
        msg.send()
        log.status = 'sent'
        log.sent_at = timezone.now()
        log.save(update_fields=['status', 'sent_at'])
    except Exception as exc:
        log.status = 'failed'
        log.error = str(exc)
        log.save(update_fields=['status', 'error'])
        raise


def _log_email(to: str, subject: str, status: str, error: str = '') -> None:
    # No-op: logging is now handled inside _send(). Kept so callers don't break.
    pass


# ── Editor helpers ────────────────────────────────────────────────────────────

def _editorial_users():
    """Return all active users with editorial access (including superusers)."""
    from django.db.models import Q
    from apps.accounts.models import User, UserRole
    editorial_roles = [
        UserRole.EDITORIAL_ASSISTANT, UserRole.HANDLING_EDITOR,
        UserRole.EDITOR_IN_CHIEF, UserRole.MANAGING_EDITOR,
        UserRole.JOURNAL_ADMIN, UserRole.SYSTEM_ADMIN,
    ]
    q = Q(is_superuser=True)
    for role in editorial_roles:
        q |= Q(roles__contains=[role])
    return list(User.objects.filter(is_active=True).filter(q))


def _assigned_editors(submission):
    """Return the active assigned editors for a submission."""
    from apps.editorial.models import EditorialAssignment
    return [
        a.editor for a in
        EditorialAssignment.objects.filter(submission=submission, is_active=True).select_related('editor')
        if a.editor
    ]


def _notify_editors_inapp(editors, notif_type, message, url):
    """Create an in-app Notification for each editor in the list."""
    from .models import Notification
    for editor in editors:
        Notification.objects.create(
            user=editor,
            notification_type=notif_type,
            message=message,
            url=url,
        )


def _editors_email_opted_in(editors):
    """Return the subset of editors who have email_notifications=True (default True if no profile)."""
    result = []
    for editor in editors:
        try:
            if editor.profile.email_notifications:
                result.append(editor)
        except Exception:
            result.append(editor)
    return result


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

    from .models import Notification, NotificationType
    Notification.objects.create(
        user=inv.reviewer,
        notification_type=NotificationType.REVIEWER_INVITED,
        message=f'You have been invited to review "{inv.submission.title[:80]}" — deadline {deadline_str}.',
        url=f'/review/invitation/{inv.magic_token}/',
    )

    # ── In-app badge for all editorial users ─────────────────────────────────
    try:
        _notify_editors_inapp(
            _editorial_users(),
            'reviewer_invited',
            f'Invitation sent to {inv.reviewer.display_name} ({inv.reviewer.email}) for "{inv.submission.title[:50]}".',
            f'/editorial/submission/{inv.submission.pk}/',
        )
    except Exception:
        pass


@shared_task
def notify_review_submitted(review_pk):
    """Notify handling editors AND the author that a review has been submitted."""
    from apps.reviews.models import Review
    review = Review.objects.select_related('invitation__submission__author').get(pk=review_pk)
    submission = review.invitation.submission
    author = submission.author
    subject_editors = f'Review submitted — {submission.title[:70]}'

    # ── Notify editors ────────────────────────────────────────────────────────
    for assignment in submission.assignments.filter(is_active=True).select_related('editor__profile'):
        editor = assignment.editor
        if not editor:
            continue
        try:
            if not editor.profile.email_notifications:
                continue
        except Exception:
            pass
        dashboard_url = f'{_site_url()}/editorial/submission/{submission.pk}/'
        html_body = (
            _greeting(editor.display_name)
            + _p('A peer review has been submitted for the following manuscript and is '
                 'now available in the editorial dashboard.')
            + _detail_box('Submission title', submission.title)
            + _p('Please log in to review the submitted assessment and determine next steps '
                 'in the editorial process.')
            + _btn(dashboard_url, 'View submission in dashboard')
            + _signature()
        )
        plain = (
            f'Dear {editor.display_name},\n\n'
            f'A peer review has been submitted for "{submission.title}" '
            f'and is available in the editorial dashboard.\n\n'
            f'{dashboard_url}\n\n'
            f'Warm regards,\nThe Trans/Act Editorial Office'
        )
        try:
            _send(editor.email, subject_editors, plain, html_body)
            _log_email(editor.email, subject_editors, 'sent')
        except Exception as exc:
            _log_email(editor.email, subject_editors, 'failed', str(exc))

    # ── In-app badge for all editorial users ─────────────────────────────────
    try:
        _notify_editors_inapp(
            _editorial_users(),
            'review_submitted',
            f'Peer review submitted for "{submission.title[:55]}".',
            f'/editorial/submission/{submission.pk}/',
        )
    except Exception:
        pass

    # ── Notify author (in-app only — review not yet moderated) ───────────────
    try:
        from .models import Notification
        Notification.objects.create(
            user=author,
            notification_type='review_submitted',
            message=(
                f'A peer review has been received for "{submission.title[:55]}". '
                f'The editorial team will review the feedback before sharing it with you.'
            ),
            url=f'/author/submission/{submission.pk}/',
        )
    except Exception:
        pass


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

    # \u2500\u2500 Notify assigned editors \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    editorial_url = f'{_site_url()}/editorial/submission/{submission.pk}/'
    editor_subject = f'Decision recorded \u2014 {submission.title[:70]}'
    editors = _assigned_editors(submission)
    for editor in _editors_email_opted_in(editors):
        editor_html = (
            _greeting(editor.display_name)
            + _p('An editorial decision has been recorded and sent to the author for the following submission.')
            + _detail_box('Submission', submission.title)
            + _detail_box('Decision', decision_label)
            + _btn(editorial_url, 'View submission')
            + _signature()
        )
        editor_plain = (
            f'Dear {editor.display_name},\n\n'
            f'An editorial decision has been recorded and sent to the author.\n\n'
            f'Submission: {submission.title}\n'
            f'Decision: {decision_label}\n\n'
            f'{editorial_url}\n\n'
            f'Warm regards,\nThe Trans/Act Editorial System'
        )
        try:
            _send(editor.email, editor_subject, editor_plain, editor_html)
            _log_email(editor.email, editor_subject, 'sent')
        except Exception as exc:
            _log_email(editor.email, editor_subject, 'failed', str(exc))
    try:
        _notify_editors_inapp(
            _editorial_users(),
            'decision_sent',
            f'Decision \u201c{decision_label}\u201d recorded for \u201c{submission.title[:50]}\u201d.',
            f'/editorial/submission/{submission.pk}/',
        )
    except Exception:
        pass


@shared_task
def notify_revision_submitted(revision_pk):
    """Notify assigned editors that a revised submission has been received."""
    from apps.submissions.models import SubmissionRevision
    from apps.editorial.models import EditorialAssignment

    revision = SubmissionRevision.objects.select_related(
        'submission__author'
    ).get(pk=revision_pk)
    submission = revision.submission
    subject = f'Revision received — {submission.title[:70]}'
    editorial_url = f'{_site_url()}/editorial/submission/{submission.pk}/'

    html_body = (
        _p(f'A revised manuscript (version {revision.version}) has been submitted for:')
        + _detail_box('Submission', submission.title)
        + _detail_box('Author', submission.author.display_name)
        + _btn(editorial_url, 'Review revision')
        + _signature()
    )
    plain = (
        f'A revised manuscript (version {revision.version}) has been submitted.\n\n'
        f'Submission: {submission.title}\n'
        f'Author: {submission.author.display_name}\n\n'
        f'Review it here:\n{editorial_url}\n\n'
        f'Warm regards,\nThe Trans/Act Editorial System'
    )

    # Email assigned active editors who have email notifications enabled.
    assigned_editor_users = [
        a.editor for a in
        EditorialAssignment.objects.filter(submission=submission, is_active=True)
        .select_related('editor', 'editor__profile')
        if a.editor
    ]
    email_recipients = _editors_email_opted_in(assigned_editor_users)
    recipient_emails = [e.email for e in email_recipients] or [
        getattr(settings, 'EDITORIAL_EMAIL', settings.DEFAULT_FROM_EMAIL)
    ]

    for email in recipient_emails:
        try:
            _send(email, subject, plain, html_body)
            _log_email(email, subject, 'sent')
        except Exception as exc:
            _log_email(email, subject, 'failed', str(exc))

    # In-app badge for all editorial users
    try:
        _notify_editors_inapp(
            _editorial_users(),
            'revision_submitted',
            f'Revised manuscript received for "{submission.title[:55]}".',
            f'/editorial/submission/{submission.pk}/',
        )
    except Exception:
        pass

    # \u2500\u2500 Email and badge active reviewers \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    from apps.reviewers.models import ReviewerInvitation, InvitationStatus
    active_invitations = (
        ReviewerInvitation.objects
        .filter(submission=submission, status=InvitationStatus.ACCEPTED)
        .select_related('reviewer')
    )
    reviewer_subject = f'Revised manuscript submitted \u2014 {submission.title[:65]}'
    reviewer_url = f'{_site_url()}/review/my-reviews/'

    for inv in active_invitations:
        reviewer = inv.reviewer
        reviewer_html = (
            _greeting(reviewer.display_name)
            + _p(f'The author of a submission you reviewed has submitted a revised '
                 f'manuscript (version {revision.version}).')
            + _detail_box('Submission', submission.title)
            + _p('The editorial team will be in touch if a further round of review '
                 'is required. You can view your completed reviews from your dashboard.')
            + _btn(reviewer_url, 'Go to my reviews')
            + _signature()
        )
        reviewer_plain = (
            f'Dear {reviewer.display_name},\n\n'
            f'The author of a submission you reviewed has submitted a revised manuscript '
            f'(version {revision.version}).\n\n'
            f'Submission: {submission.title}\n\n'
            f'The editorial team will be in touch if a further round of review is required.\n\n'
            f'Your reviewer dashboard:\n{reviewer_url}\n\n'
            f'Warm regards,\nThe Trans/Act Editorial Office'
        )
        try:
            _send(reviewer.email, reviewer_subject, reviewer_plain, reviewer_html)
            _log_email(reviewer.email, reviewer_subject, 'sent')
        except Exception as exc:
            _log_email(reviewer.email, reviewer_subject, 'failed', str(exc))

        try:
            from .models import Notification
            Notification.objects.create(
                user=reviewer,
                notification_type='revision_submitted',
                message=(
                    f'A revised manuscript (v{revision.version}) has been submitted '
                    f'for \u201c{submission.title[:50]}\u201d.'
                ),
                url='/review/my-reviews/',
            )
        except Exception:
            pass

    # \u2500\u2500 In-app notification for the author confirming receipt \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    try:
        from .models import Notification
        Notification.objects.create(
            user=submission.author,
            notification_type='revision_submitted',
            message=f'Your revision of \u201c{submission.title[:50]}\u201d has been submitted.',
            url=f'/author/submission/{submission.pk}/',
        )
    except Exception:
        pass


@shared_task
def notify_screening_resubmission(revision_pk):
    """Email the author (confirmation) and editorial team when a corrected manuscript is resubmitted."""
    from apps.submissions.models import SubmissionRevision
    revision = SubmissionRevision.objects.select_related('submission__author').get(pk=revision_pk)
    submission = revision.submission
    dashboard_url = f'{_site_url()}/author/submission/{submission.pk}/'
    editorial_url = f'{_site_url()}/editorial/submission/{submission.pk}/'

    # ── Confirmation email to author ──────────────────────────────────────────
    author_subject = f'Corrected manuscript received — {submission.title[:70]}'
    author_html = (
        _greeting(submission.author.display_name)
        + _p('Thank you. We have received your corrected manuscript for:')
        + _detail_box('Submission title', submission.title)
        + _p('Our editorial team will carry out a fresh technical check and notify you of '
             'the outcome. You can monitor the status of your submission from your author dashboard.')
        + _btn(dashboard_url, 'View your submission')
        + _signature()
    )
    author_plain = (
        f'Dear {submission.author.display_name},\n\n'
        f'Thank you. We have received your corrected manuscript for:\n\n'
        f'Submission: {submission.title}\n\n'
        f'Our editorial team will carry out a fresh technical check and notify you of the outcome.\n\n'
        f'Track your submission status at any time:\n{dashboard_url}\n\n'
        f'Warm regards,\nThe Trans/Act Editorial Office'
    )
    try:
        _send(submission.author.email, author_subject, author_plain, author_html)
        _log_email(submission.author.email, author_subject, 'sent')
    except Exception as exc:
        _log_email(submission.author.email, author_subject, 'failed', str(exc))

    # ── In-app badge for the author ───────────────────────────────────────────
    try:
        from .models import Notification
        Notification.objects.create(
            user=submission.author,
            notification_type='revision_submitted',
            message=f'Your corrected manuscript for "{submission.title[:50]}" has been received.',
            url=f'/author/submission/{submission.pk}/',
        )
    except Exception:
        pass

    # ── Email to editorial team ───────────────────────────────────────────────
    editorial_subject = f'Corrected manuscript resubmitted — {submission.title[:65]}'
    editorial_html = (
        _p(f'A corrected manuscript (version {revision.version}) has been resubmitted '
           f'after technical screening for:')
        + _detail_box('Submission', submission.title)
        + _detail_box('Author', submission.author.display_name)
        + _btn(editorial_url, 'Review resubmission')
        + _signature()
    )
    editorial_plain = (
        f'A corrected manuscript (version {revision.version}) has been resubmitted '
        f'after technical screening.\n\n'
        f'Submission: {submission.title}\n'
        f'Author: {submission.author.display_name}\n\n'
        f'Review it here:\n{editorial_url}\n\n'
        f'Warm regards,\nThe Trans/Act Editorial System'
    )
    editorial_email = getattr(settings, 'EDITORIAL_EMAIL', settings.DEFAULT_FROM_EMAIL)
    try:
        _send(editorial_email, editorial_subject, editorial_plain, editorial_html)
        _log_email(editorial_email, editorial_subject, 'sent')
    except Exception as exc:
        _log_email(editorial_email, editorial_subject, 'failed', str(exc))

    # Also email each individual editor who has opted in.
    all_editors = _editorial_users()
    for editor in _editors_email_opted_in(all_editors):
        if editor.email == editorial_email:
            continue
        editor_html = (
            _greeting(editor.display_name)
            + _p(f'A corrected manuscript (version {revision.version}) has been resubmitted '
                 f'after technical screening for:')
            + _detail_box('Submission', submission.title)
            + _detail_box('Author', submission.author.display_name)
            + _btn(editorial_url, 'Review resubmission')
            + _signature()
        )
        editor_plain = f'Dear {editor.display_name},\n\n' + editorial_plain
        try:
            _send(editor.email, editorial_subject, editor_plain, editor_html)
            _log_email(editor.email, editorial_subject, 'sent')
        except Exception as exc:
            _log_email(editor.email, editorial_subject, 'failed', str(exc))

    # ── In-app badge for all editors ──────────────────────────────────────────
    try:
        _notify_editors_inapp(
            all_editors,
            'revision_submitted',
            f'Corrected manuscript resubmitted: "{submission.title[:50]}".',
            f'/editorial/submission/{submission.pk}/',
        )
    except Exception:
        pass


@shared_task
def notify_returned_to_author(submission_pk):
    """Notify the author that their submission has been returned from technical screening."""
    from apps.submissions.models import Submission
    sub = Submission.objects.select_related('author').get(pk=submission_pk)

    last_check = sub.screening_checks.order_by('-checked_at').first()
    notes = last_check.notes if last_check and last_check.notes else ''

    subject = f'Your submission has been returned for correction — {sub.title[:60]}'
    dashboard_url = f'{_site_url()}/author/submission/{sub.pk}/'

    html_body = (
        _greeting(sub.author.display_name)
        + _p('Thank you for your submission to <strong>Trans/Act: Journal of Artistic '
             'Research</strong>. Our editorial team has reviewed your manuscript and '
             'is returning it for correction before it can proceed to peer review.')
        + _detail_box('Submission title', sub.title)
        + (_quoted_block(notes) if notes else '')
        + _p('Please log in to your author dashboard, correct the issues described '
             'above, and upload the revised manuscript.')
        + _btn(dashboard_url, 'Correct & resubmit')
        + _signature()
    )

    plain = (
        f'Dear {sub.author.display_name},\n\n'
        f'Your submission "{sub.title}" has been returned for correction.\n\n'
        + (f'Notes from the editorial team:\n{notes}\n\n' if notes else '')
        + f'Please log in and upload a corrected version:\n{dashboard_url}\n\n'
        f'Warm regards,\nThe Trans/Act Editorial Office'
    )

    try:
        _send(sub.author.email, subject, plain, html_body)
        _log_email(sub.author.email, subject, 'sent')
        from .models import Notification
        Notification.objects.create(
            user=sub.author,
            notification_type='returned_to_author',
            message=f'Your submission "{sub.title[:55]}" has been returned for correction.',
            url=f'/author/submission/{sub.pk}/',
        )
    except Exception as exc:
        _log_email(sub.author.email, subject, 'failed', str(exc))

    # ── In-app badge for all editors ─────────────────────────────────────────
    try:
        _notify_editors_inapp(
            _editorial_users(),
            'returned_to_author',
            f'Submission returned for correction: "{sub.title[:55]}".',
            f'/editorial/submission/{sub.pk}/',
        )
    except Exception:
        pass


@shared_task
def notify_review_released(review_pk):
    """Notify the author that a moderated review is now available to them."""
    from apps.reviews.models import Review
    review = Review.objects.select_related('invitation__submission__author').get(pk=review_pk)
    submission = review.invitation.submission
    author = submission.author

    subject = f'Reviewer feedback available — {submission.title[:65]}'
    dashboard_url = f'{_site_url()}/author/submission/{submission.pk}/'

    # ── HTML ─────────────────────────────────────────────────────────────────
    html_body = (
        _greeting(author.display_name)
        + _p('The editorial team has reviewed the peer assessment of your submission and '
             'has made the reviewer feedback available to you.')
        + _detail_box('Submission title', submission.title)
        + _p('Please log in to your author dashboard to read the reviewer comments '
             'and any paragraph annotations.')
        + _btn(dashboard_url, 'Read reviewer feedback')
        + _signature()
    )

    # ── Plain text ────────────────────────────────────────────────────────────
    plain = (
        f'Dear {author.display_name},\n\n'
        f'Reviewer feedback for your submission "{submission.title}" is now available.\n\n'
        f'Log in to read the reviewer comments:\n{dashboard_url}\n\n'
        f'Warm regards,\nThe Trans/Act Editorial Office'
    )

    try:
        _send(author.email, subject, plain, html_body)
        _log_email(author.email, subject, 'sent')
        from .models import Notification
        Notification.objects.create(
            user=author,
            notification_type='review_released',
            message=f'Reviewer feedback is now available for "{submission.title[:55]}".',
            url=f'/author/submission/{submission.pk}/',
        )
    except Exception as exc:
        _log_email(author.email, subject, 'failed', str(exc))

    # ── In-app badge for assigned editors ────────────────────────────────────
    try:
        _notify_editors_inapp(
            _editorial_users(),
            'review_released',
            f'Review released to author for "{submission.title[:55]}".',
            f'/editorial/submission/{submission.pk}/',
        )
    except Exception:
        pass


@shared_task
def notify_article_published(submission_pk):
    """Notify the author that their article has been published."""
    from apps.submissions.models import Submission
    sub = Submission.objects.select_related('author').get(pk=submission_pk)
    author = sub.author

    subject = f'Your article has been published — {sub.title[:65]}'
    # Try to build the public article URL from slug
    article_url = f'{_site_url()}/articles/{sub.slug}/'
    dashboard_url = f'{_site_url()}/author/submission/{sub.pk}/'

    # ── HTML ─────────────────────────────────────────────────────────────────
    html_body = (
        _greeting(author.display_name)
        + _p('Congratulations — your article has been published in '
             '<strong>Trans/Act: Journal of Artistic Research</strong>.')
        + _detail_box('Article title', sub.title)
        + _p('Your work is now accessible to readers online.')
        + _btn(article_url, 'View published article')
        + _signature()
    )

    # ── Plain text ────────────────────────────────────────────────────────────
    plain = (
        f'Dear {author.display_name},\n\n'
        f'Congratulations — your article "{sub.title}" has been published in '
        f'Trans/Act: Journal of Artistic Research.\n\n'
        f'Read it here:\n{article_url}\n\n'
        f'Warm regards,\nThe Trans/Act Editorial Office'
    )

    try:
        _send(author.email, subject, plain, html_body)
        _log_email(author.email, subject, 'sent')
        from .models import Notification
        Notification.objects.create(
            user=author,
            notification_type='published',
            message=f'Your article "{sub.title[:55]}" has been published.',
            url=f'/articles/{sub.slug}/',
        )
    except Exception as exc:
        _log_email(author.email, subject, 'failed', str(exc))


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


# ── Editor-facing notification tasks ─────────────────────────────────────────

@shared_task
def notify_editors_new_submission(submission_pk):
    """Email the editorial office and badge all editors when a new submission arrives."""
    from apps.submissions.models import Submission
    sub = Submission.objects.select_related('author').get(pk=submission_pk)

    editorial_url = f'{_site_url()}/editorial/submission/{sub.pk}/'
    subject = f'New submission — {sub.title[:70]}'

    html_body = (
        _p('A new submission has been received and is awaiting technical screening.')
        + _detail_box('Title', sub.title)
        + _detail_box('Author', sub.author.display_name)
        + _detail_box('Type', sub.get_article_type_display())
        + _btn(editorial_url, 'Open in editorial dashboard')
        + _signature()
    )
    plain = (
        f'A new submission has been received.\n\n'
        f'Title: {sub.title}\n'
        f'Author: {sub.author.display_name}\n'
        f'Type: {sub.get_article_type_display()}\n\n'
        f'Open in editorial dashboard:\n{editorial_url}\n\n'
        f'Warm regards,\nThe Trans/Act Editorial System'
    )

    editorial_email = getattr(settings, 'EDITORIAL_EMAIL', settings.DEFAULT_FROM_EMAIL)
    try:
        _send(editorial_email, subject, plain, html_body)
        _log_email(editorial_email, subject, 'sent')
    except Exception as exc:
        _log_email(editorial_email, subject, 'failed', str(exc))

    # Also email each individual editor who has opted in (skip if same as editorial_email).
    all_editors = _editorial_users()
    for editor in _editors_email_opted_in(all_editors):
        if editor.email == editorial_email:
            continue
        editor_html = (
            _greeting(editor.display_name)
            + _p('A new submission has been received and is awaiting technical screening.')
            + _detail_box('Title', sub.title)
            + _detail_box('Author', sub.author.display_name)
            + _detail_box('Type', sub.get_article_type_display())
            + _btn(editorial_url, 'Open in editorial dashboard')
            + _signature()
        )
        editor_plain = (
            f'Dear {editor.display_name},\n\n'
            + plain
        )
        try:
            _send(editor.email, subject, editor_plain, editor_html)
            _log_email(editor.email, subject, 'sent')
        except Exception as exc:
            _log_email(editor.email, subject, 'failed', str(exc))

    try:
        _notify_editors_inapp(
            all_editors,
            'submission_received',
            f'New submission: "{sub.title[:60]}" by {sub.author.display_name}.',
            f'/editorial/submission/{sub.pk}/',
        )
    except Exception:
        pass


@shared_task
def notify_editors_reviewer_response(invitation_pk):
    """Email and badge assigned editors when a reviewer accepts or declines."""
    from apps.reviewers.models import ReviewerInvitation
    inv = ReviewerInvitation.objects.select_related('reviewer', 'submission').get(pk=invitation_pk)
    submission = inv.submission
    accepted = inv.status == 'accepted'
    verb = 'accepted' if accepted else 'declined'
    notif_type = 'reviewer_accepted' if accepted else 'reviewer_declined'
    subject = f'Reviewer {verb} — {submission.title[:65]}'
    editorial_url = f'{_site_url()}/editorial/submission/{submission.pk}/'

    reviewer_name = inv.reviewer.display_name
    reviewer_email = inv.reviewer.email

    html_body = (
        _p(f'A reviewer has <strong>{_e(verb)}</strong> their invitation to review '
           f'the following submission.')
        + _detail_box('Submission', submission.title)
        + _detail_box('Reviewer', f'{reviewer_name} ({reviewer_email})')
        + ((_detail_box('Decline reason', inv.decline_reason) if inv.decline_reason else '')
           if not accepted else '')
        + _btn(editorial_url, 'View submission')
        + _signature()
    )
    plain = (
        f'A reviewer has {verb} the review invitation for "{submission.title}".\n\n'
        f'Reviewer: {reviewer_name} ({reviewer_email})\n\n'
        + (f'Decline reason: {inv.decline_reason}\n\n' if not accepted and inv.decline_reason else '')
        + f'View submission:\n{editorial_url}\n\n'
        f'Warm regards,\nThe Trans/Act Editorial System'
    )

    editors = _assigned_editors(submission)
    recipients = [e.email for e in _editors_email_opted_in(editors)] or [
        getattr(settings, 'EDITORIAL_EMAIL', settings.DEFAULT_FROM_EMAIL)
    ]
    for email in recipients:
        try:
            _send(email, subject, plain, html_body)
            _log_email(email, subject, 'sent')
        except Exception as exc:
            _log_email(email, subject, 'failed', str(exc))

    try:
        _notify_editors_inapp(
            _editorial_users(),
            notif_type,
            f'{reviewer_name} ({reviewer_email}) {verb} the review invitation for "{submission.title[:45]}".',
            f'/editorial/submission/{submission.pk}/',
        )
    except Exception:
        pass


@shared_task
def notify_editors_article_published(submission_pk):
    """Badge assigned editors and email opted-in editors when an article goes live."""
    from apps.submissions.models import Submission
    sub = Submission.objects.get(pk=submission_pk)
    article_url = f'{_site_url()}/articles/{sub.slug}/'
    subject = f'Article published — {sub.title[:70]}'
    editors = _assigned_editors(sub) or _editorial_users()

    for editor in _editors_email_opted_in(editors):
        html_body = (
            _greeting(editor.display_name)
            + _p('The following article has just been published on the journal site.')
            + _detail_box('Title', sub.title)
            + _btn(article_url, 'View published article')
            + _signature()
        )
        plain = (
            f'Dear {editor.display_name},\n\n'
            f'The following article has just been published.\n\n'
            f'Title: {sub.title}\n\n'
            f'Read it here:\n{article_url}\n\n'
            f'Warm regards,\nThe Trans/Act Editorial System'
        )
        try:
            _send(editor.email, subject, plain, html_body)
            _log_email(editor.email, subject, 'sent')
        except Exception as exc:
            _log_email(editor.email, subject, 'failed', str(exc))

    try:
        _notify_editors_inapp(
            _editorial_users(),
            'published',
            f'"{sub.title[:60]}" is now live on the journal site.',
            f'/articles/{sub.slug}/',
        )
    except Exception:
        pass


@shared_task
def notify_editors_issue_published(issue_pk):
    """Badge all editors and email opted-in editors when an issue is published."""
    from apps.journal.models import Issue
    issue = Issue.objects.get(pk=issue_pk)
    article_count = issue.submissions.filter(status='published').count()
    vol_str = f' (Vol. {issue.volume})' if issue.volume else ''
    issue_url = f'{_site_url()}/issues/{issue.pk}/'
    message = (
        f'Issue #{issue.number}{vol_str} published — '
        f'{article_count} article{"s" if article_count != 1 else ""}.'
    )
    subject = f'Issue #{issue.number}{vol_str} published — Trans/Act'
    all_editors = _editorial_users()

    for editor in _editors_email_opted_in(all_editors):
        html_body = (
            _greeting(editor.display_name)
            + _p(f'Issue #{_e(str(issue.number))}{_e(vol_str)} of <strong>Trans/Act: Journal of '
                 f'Artistic Research</strong> has been published with '
                 f'{article_count} article{"s" if article_count != 1 else ""}.')
            + _btn(issue_url, 'View published issue')
            + _signature()
        )
        plain = (
            f'Dear {editor.display_name},\n\n'
            f'Issue #{issue.number}{vol_str} of Trans/Act has been published '
            f'with {article_count} article{"s" if article_count != 1 else ""}.\n\n'
            f'View it here:\n{issue_url}\n\n'
            f'Warm regards,\nThe Trans/Act Editorial System'
        )
        try:
            _send(editor.email, subject, plain, html_body)
            _log_email(editor.email, subject, 'sent')
        except Exception as exc:
            _log_email(editor.email, subject, 'failed', str(exc))

    try:
        _notify_editors_inapp(
            all_editors,
            'issue_published',
            message,
            f'/issues/{issue.pk}/',
        )
    except Exception:
        pass


@shared_task
def notify_editors_submission_withdrawn(submission_title, author_name, author_email):
    """Email opted-in editors and badge all editors when an author withdraws a submission.

    Receives raw strings instead of a PK because the submission is deleted
    before this task runs.
    """
    subject = f'Submission withdrawn — {submission_title[:70]}'
    editorial_url = f'{_site_url()}/editorial/'

    html_body = (
        _p('An author has withdrawn their submission.')
        + _detail_box('Title', submission_title)
        + _detail_box('Author', author_name)
        + _btn(editorial_url, 'Go to editorial queue')
        + _signature()
    )
    plain = (
        f'An author has withdrawn their submission.\n\n'
        f'Title: {submission_title}\n'
        f'Author: {author_name} ({author_email})\n\n'
        f'Editorial queue:\n{editorial_url}\n\n'
        f'Warm regards,\nThe Trans/Act Editorial System'
    )

    # Email the generic editorial inbox.
    editorial_email = getattr(settings, 'EDITORIAL_EMAIL', settings.DEFAULT_FROM_EMAIL)
    try:
        _send(editorial_email, subject, plain, html_body)
        _log_email(editorial_email, subject, 'sent')
    except Exception as exc:
        _log_email(editorial_email, subject, 'failed', str(exc))

    # Also email each individual editor who has opted in.
    all_editors = _editorial_users()
    for editor in _editors_email_opted_in(all_editors):
        if editor.email == editorial_email:
            continue
        editor_html = (
            _greeting(editor.display_name)
            + _p('An author has withdrawn their submission.')
            + _detail_box('Title', submission_title)
            + _detail_box('Author', author_name)
            + _btn(editorial_url, 'Go to editorial queue')
            + _signature()
        )
        editor_plain = f'Dear {editor.display_name},\n\n' + plain
        try:
            _send(editor.email, subject, editor_plain, editor_html)
            _log_email(editor.email, subject, 'sent')
        except Exception as exc:
            _log_email(editor.email, subject, 'failed', str(exc))

    # In-app badge for all editors.
    try:
        _notify_editors_inapp(
            all_editors,
            'general',
            f'Submission withdrawn: "{submission_title[:60]}" by {author_name}.',
            '/editorial/',
        )
    except Exception:
        pass


@shared_task
def notify_editor_assigned(assignment_pk):
    """Email and badge the assigned editor when they are assigned to a submission."""
    from apps.editorial.models import EditorialAssignment
    try:
        asgn = EditorialAssignment.objects.select_related(
            'editor', 'editor__profile', 'submission__author'
        ).get(pk=assignment_pk)
    except EditorialAssignment.DoesNotExist:
        return

    editor = asgn.editor
    submission = asgn.submission
    role_label = asgn.get_role_display()
    editorial_url = f'{_site_url()}/editorial/submission/{submission.pk}/'
    subject = f'You have been assigned as {role_label} — {submission.title[:60]}'

    html_body = (
        _greeting(editor.display_name)
        + _p(f'You have been assigned as <strong>{_e(role_label)}</strong> for the following submission.')
        + _detail_box('Submission title', submission.title)
        + _detail_box('Author', submission.author.display_name)
        + _btn(editorial_url, 'Open submission in dashboard')
        + _signature()
    )
    plain = (
        f'Dear {editor.display_name},\n\n'
        f'You have been assigned as {role_label} for the following submission.\n\n'
        f'Title: {submission.title}\n'
        f'Author: {submission.author.display_name}\n\n'
        f'Open in editorial dashboard:\n{editorial_url}\n\n'
        f'Warm regards,\nThe Trans/Act Editorial Office'
    )

    try:
        if getattr(getattr(editor, 'profile', None), 'email_notifications', True):
            _send(editor.email, subject, plain, html_body)
            _log_email(editor.email, subject, 'sent')
    except Exception as exc:
        _log_email(editor.email, subject, 'failed', str(exc))

    try:
        from .models import Notification
        Notification.objects.create(
            user=editor,
            notification_type='general',
            message=f'You have been assigned as {role_label} for "{submission.title[:60]}".',
            url=f'/editorial/submission/{submission.pk}/',
        )
    except Exception:
        pass


@shared_task
def notify_editor_removed(editor_pk, submission_title, role_label):
    """Email and badge an editor when they are removed from a submission.

    Receives raw strings because the assignment may be deactivated before the task runs.
    """
    from apps.accounts.models import User
    try:
        editor = User.objects.select_related('profile').get(pk=editor_pk)
    except User.DoesNotExist:
        return

    editorial_url = f'{_site_url()}/editorial/'
    subject = f'You have been removed as {role_label} — {submission_title[:60]}'

    html_body = (
        _greeting(editor.display_name)
        + _p(f'You have been removed as <strong>{_e(role_label)}</strong> for the following submission.')
        + _detail_box('Submission title', submission_title)
        + _btn(editorial_url, 'Go to editorial dashboard')
        + _signature()
    )
    plain = (
        f'Dear {editor.display_name},\n\n'
        f'You have been removed as {role_label} for "{submission_title}".\n\n'
        f'Editorial dashboard:\n{editorial_url}\n\n'
        f'Warm regards,\nThe Trans/Act Editorial Office'
    )

    try:
        if getattr(getattr(editor, 'profile', None), 'email_notifications', True):
            _send(editor.email, subject, plain, html_body)
            _log_email(editor.email, subject, 'sent')
    except Exception as exc:
        _log_email(editor.email, subject, 'failed', str(exc))

    try:
        from .models import Notification
        Notification.objects.create(
            user=editor,
            notification_type='general',
            message=f'You have been removed as {role_label} for "{submission_title[:60]}".',
            url='/editorial/',
        )
    except Exception:
        pass
