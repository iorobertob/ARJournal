"""
Tests for revising editor-authored (WYSIWYG) manuscripts.

Covers: routing WYSIWYG-origin submissions away from the legacy .tex upload
flow, cloning the previous revision's content + assets into a fresh draft with
remapped asset references, and submitting in both review and screening modes.
"""
from unittest.mock import patch

from django.test import TestCase, Client, override_settings
from django.urls import reverse

from apps.accounts.models import User, UserRole
from apps.journal.models import JournalConfig
from apps.submissions.models import (
    Submission, SubmissionRevision, SubmissionAsset,
    SubmissionStatus, RevisionSource,
)


def make_user(email, roles, **kwargs):
    u = User(email=email, **kwargs)
    u.set_password('testpass123')
    u.roles = roles
    u.save()
    return u


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class WysiwygResubmissionTest(TestCase):

    def setUp(self):
        JournalConfig.objects.get_or_create(pk=1, defaults={
            'name': 'inAct', 'tagline': 'Test', 'submission_open': True,
        })
        self.author = make_user('author@test.com', [UserRole.AUTHOR],
                                first_name='Au', last_name='Thor')
        self.client = Client()
        self.client.force_login(self.author)

    def _make_wysiwyg_submission(self, status):
        sub = Submission.objects.create(
            author=self.author, title='Editor Article',
            article_type='research_article', status=status,
        )
        rev = SubmissionRevision.objects.create(
            submission=sub, version=1, status='submitted',
            source_type=RevisionSource.WYSIWYG,
            wysiwyg_data={
                'content': [
                    {'type': 'paragraph', 'content': [{'type': 'text', 'text': 'Hello'}]},
                    {'type': 'figure', 'assetRef': 'asset_image_00{}'.format('X'),
                     'assetUrl': '/media/assets/old.png', 'caption': 'A figure'},
                ],
                'bibliography': [],
            },
        )
        asset = SubmissionAsset.objects.create(
            revision=rev, kind='image', file='assets/old.png',
            original_filename='old.png', mime_type='image/png',
        )
        # Point the figure block at the real asset id now that we know its pk.
        rev.wysiwyg_data['content'][1]['assetRef'] = f'asset_image_{asset.pk:03d}'
        rev.save(update_fields=['wysiwyg_data'])
        return sub, rev, asset

    def test_review_resubmit_routes_to_editor(self):
        """A revision-requested editor manuscript redirects from .tex step1 to the editor."""
        sub, _, _ = self._make_wysiwyg_submission(SubmissionStatus.REVISION_REQUESTED)
        resp = self.client.get(reverse('resubmit_step1', args=[sub.pk]))
        self.assertRedirects(resp, reverse('resubmit_wysiwyg_editor', args=[sub.pk]))

    def test_screening_resubmit_routes_to_editor(self):
        """A screening-returned editor manuscript redirects from the .tex correction flow."""
        sub, _, _ = self._make_wysiwyg_submission(SubmissionStatus.SUBMITTED)
        # Create the return-to-author screening check that flips is_returned_to_author.
        from apps.editorial.models import ScreeningCheck
        ScreeningCheck.objects.create(submission=sub, result='return_to_author', notes='Fix refs')
        self.assertTrue(sub.is_returned_to_author)
        resp = self.client.get(reverse('resubmit_after_screening', args=[sub.pk]))
        self.assertRedirects(resp, reverse('resubmit_wysiwyg_editor', args=[sub.pk]))

    def test_editor_clones_content_and_remaps_assets(self):
        """Opening the editor creates a v2 draft with copied content + remapped asset refs."""
        sub, rev1, asset1 = self._make_wysiwyg_submission(SubmissionStatus.REVISION_REQUESTED)
        resp = self.client.get(reverse('resubmit_wysiwyg_editor', args=[sub.pk]))
        self.assertEqual(resp.status_code, 200)

        draft = sub.revisions.get(status='draft')
        self.assertEqual(draft.version, 2)
        self.assertEqual(draft.source_type, RevisionSource.WYSIWYG)

        # Asset was cloned onto the new revision (new pk).
        new_asset = draft.assets.get()
        self.assertNotEqual(new_asset.pk, asset1.pk)

        # The figure block's assetRef points at the NEW asset, not the old one.
        fig = draft.wysiwyg_data['content'][1]
        self.assertEqual(fig['assetRef'], f'asset_image_{new_asset.pk:03d}')
        self.assertNotEqual(fig['assetRef'], f'asset_image_{asset1.pk:03d}')

    def test_editor_resumes_existing_draft(self):
        """Re-entering the editor reuses the same draft instead of creating v3, v4…"""
        sub, _, _ = self._make_wysiwyg_submission(SubmissionStatus.REVISION_REQUESTED)
        self.client.get(reverse('resubmit_wysiwyg_editor', args=[sub.pk]))
        self.client.get(reverse('resubmit_wysiwyg_editor', args=[sub.pk]))
        self.assertEqual(sub.revisions.filter(status='draft').count(), 1)

    @patch('apps.notifications.tasks.notify_revision_submitted')
    def test_confirm_submits_review_revision(self, mock_notify):
        sub, _, _ = self._make_wysiwyg_submission(SubmissionStatus.REVISION_REQUESTED)
        self.client.get(reverse('resubmit_wysiwyg_editor', args=[sub.pk]))
        draft = sub.revisions.get(status='draft')

        resp = self.client.post(
            reverse('resubmit_wysiwyg_confirm', args=[sub.pk, draft.pk]),
            {'notes': 'Addressed all comments', 'keywords': 'a; b'},
        )
        self.assertRedirects(resp, reverse('author_dashboard'))
        sub.refresh_from_db()
        draft.refresh_from_db()
        self.assertEqual(sub.status, SubmissionStatus.REVISED)
        self.assertEqual(draft.status, 'submitted')
        self.assertEqual(sub.keywords, ['a', 'b'])
        mock_notify.assert_called_once_with(draft.pk)

    @patch('apps.notifications.tasks.notify_screening_resubmission')
    def test_confirm_submits_screening_correction(self, mock_notify):
        sub, _, _ = self._make_wysiwyg_submission(SubmissionStatus.SUBMITTED)
        from apps.editorial.models import ScreeningCheck
        ScreeningCheck.objects.create(submission=sub, result='return_to_author', notes='Fix')
        self.client.get(reverse('resubmit_wysiwyg_editor', args=[sub.pk]))
        draft = sub.revisions.get(status='draft')

        resp = self.client.post(
            reverse('resubmit_wysiwyg_confirm', args=[sub.pk, draft.pk]),
            {'notes': 'Corrected'},
        )
        self.assertRedirects(resp, reverse('author_dashboard'))
        sub.refresh_from_db()
        self.assertEqual(sub.status, SubmissionStatus.SUBMITTED)
        mock_notify.assert_called_once_with(draft.pk)

    def test_latex_submission_still_uses_tex_flow(self):
        """A .tex-authored manuscript is NOT redirected to the editor."""
        sub = Submission.objects.create(
            author=self.author, title='LaTeX Article',
            article_type='research_article',
            status=SubmissionStatus.REVISION_REQUESTED,
        )
        SubmissionRevision.objects.create(
            submission=sub, version=1, status='submitted',
            source_type=RevisionSource.LATEX, manuscript_file='manuscripts/paper.tex',
        )
        resp = self.client.get(reverse('resubmit_step1', args=[sub.pk]))
        self.assertEqual(resp.status_code, 200)  # renders the .tex upload page, no redirect
