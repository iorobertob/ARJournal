"""
Tests for reviewer invitation email delivery.
Covers the full path: send_invitations view → notify_reviewer_invited task → send_mail.
"""
import datetime
from unittest.mock import patch
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.journal.models import JournalConfig
from apps.submissions.models import Submission, SubmissionStatus
from apps.reviewers.models import (
    ReviewerProfile, ReviewerSuggestion, ReviewerInvitation, SuggestionStatus,
)
from apps.notifications.models import EmailLog


def make_user(email, roles, **kwargs):
    u = User(email=email, **kwargs)
    u.set_password('testpass123')
    u.roles = roles
    u.save()
    return u


class InvitationEmailTest(TestCase):

    def setUp(self):
        JournalConfig.objects.get_or_create(pk=1, defaults={
            'name': 'Trans/Act', 'tagline': 'Test', 'submission_open': True,
        })
        self.editor = make_user('editor@test.com', [UserRole.HANDLING_EDITOR],
                                first_name='Ed', last_name='Itor')
        self.author = make_user('author@test.com', [UserRole.AUTHOR],
                                first_name='Au', last_name='Thor')
        self.reviewer = make_user('reviewer@test.com', [UserRole.REVIEWER],
                                  first_name='Rev', last_name='Iewer')
        ReviewerProfile.objects.create(user=self.reviewer)

        self.submission = Submission.objects.create(
            author=self.author,
            title='Test Submission',
            article_type='research_article',
            status=SubmissionStatus.DESK_REVIEW,
        )
        self.suggestion = ReviewerSuggestion.objects.create(
            submission=self.submission,
            reviewer=self.reviewer,
            score=0.75,
            status=SuggestionStatus.APPROVED,
            is_primary=True,
        )
        self.client = Client()
        self.client.force_login(self.editor)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_invitation_email_sent_on_first_send(self):
        """Clicking 'Send Invitations' for the first time sends an email to the reviewer."""
        with self.settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            from django.core import mail
            mail.outbox = []

            deadline = (timezone.now().date() + datetime.timedelta(days=21)).isoformat()
            resp = self.client.post(
                reverse('send_invitations', kwargs={'submission_pk': self.submission.pk}),
                {'deadline': deadline},
            )

        self.assertRedirects(resp, reverse('editorial_submission', kwargs={'pk': self.submission.pk}),
                             fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 1, f'Expected 1 email, got {len(mail.outbox)}')
        self.assertIn(self.reviewer.email, mail.outbox[0].to)
        self.assertIn('invitation', mail.outbox[0].subject.lower())

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_invitation_email_sent_on_resend(self):
        """Clicking 'Resend Invitations' when an invitation already exists still sends email."""
        # Pre-create the invitation (simulates a previous send)
        ReviewerInvitation.objects.create(
            submission=self.submission,
            reviewer=self.reviewer,
            deadline=timezone.now().date() + datetime.timedelta(days=14),
        )
        self.suggestion.status = SuggestionStatus.INVITED
        self.suggestion.save()

        with self.settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            from django.core import mail
            mail.outbox = []

            deadline = (timezone.now().date() + datetime.timedelta(days=21)).isoformat()
            self.client.post(
                reverse('send_invitations', kwargs={'submission_pk': self.submission.pk}),
                {'deadline': deadline},
            )

        self.assertEqual(len(mail.outbox), 1, f'Resend should send 1 email, got {len(mail.outbox)}')
        self.assertIn(self.reviewer.email, mail.outbox[0].to)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_email_logged_to_database(self):
        """Sent invitation emails are recorded in EmailLog."""
        with self.settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            from django.core import mail
            mail.outbox = []

            deadline = (timezone.now().date() + datetime.timedelta(days=21)).isoformat()
            self.client.post(
                reverse('send_invitations', kwargs={'submission_pk': self.submission.pk}),
                {'deadline': deadline},
            )

        log = EmailLog.objects.filter(to_email=self.reviewer.email).first()
        self.assertIsNotNone(log, 'No EmailLog entry found for invitation email')
        self.assertEqual(log.status, 'sent')

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_invitation_email_contains_magic_link(self):
        """Invitation email body contains the magic-link URL."""
        with self.settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            from django.core import mail
            mail.outbox = []

            deadline = (timezone.now().date() + datetime.timedelta(days=21)).isoformat()
            self.client.post(
                reverse('send_invitations', kwargs={'submission_pk': self.submission.pk}),
                {'deadline': deadline},
            )

        body = mail.outbox[0].body
        inv = ReviewerInvitation.objects.get(submission=self.submission, reviewer=self.reviewer)
        self.assertIn(str(inv.magic_token), body, 'Magic token not found in invitation email body')

    def test_no_email_without_approved_suggestions(self):
        """No email is sent if there are no approved suggestions."""
        self.suggestion.status = SuggestionStatus.SUGGESTED  # not approved
        self.suggestion.save()

        with self.settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            from django.core import mail
            mail.outbox = []

            deadline = (timezone.now().date() + datetime.timedelta(days=21)).isoformat()
            self.client.post(
                reverse('send_invitations', kwargs={'submission_pk': self.submission.pk}),
                {'deadline': deadline},
            )

        self.assertEqual(len(mail.outbox), 0)
