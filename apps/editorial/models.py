from django.db import models
from django.conf import settings
from apps.submissions.models import Submission


class EditorialAssignment(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='assignments')
    editor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='editorial_assignments',
    )
    role = models.CharField(
        max_length=30,
        choices=[
            ('handling_editor', 'Handling Editor'),
            ('managing_editor', 'Managing Editor'),
            ('editor_in_chief', 'Editor-in-Chief'),
        ],
        default='handling_editor',
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.editor} → {self.submission}'


class ScreeningCheckResult(models.TextChoices):
    PASS_TO_DESK = 'pass_to_desk', 'Pass to Desk Review'
    RETURN_TO_AUTHOR = 'return_to_author', 'Return to Author for Corrections'
    REJECT = 'reject', 'Reject'


class ScreeningCheck(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='screening_checks')
    checker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='screening_checks',
    )
    completeness_ok = models.BooleanField(default=False)
    scope_fit_ok = models.BooleanField(default=False)
    ethics_ok = models.BooleanField(default=False)
    similarity_score = models.FloatField(null=True, blank=True)
    identity_leakage_risk = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default='')
    result = models.CharField(max_length=30, choices=ScreeningCheckResult.choices, blank=True)
    checked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Screening: {self.submission} — {self.result}'


class DecisionType(models.TextChoices):
    ACCEPT = 'accept', 'Accept'
    MINOR_REVISION = 'minor_revision', 'Minor Revision'
    MAJOR_REVISION = 'major_revision', 'Major Revision'
    REJECT = 'reject', 'Reject'
    DESK_REJECT = 'desk_reject', 'Desk Reject'
    REJECT_RESUBMIT = 'reject_resubmit', 'Reject — Invite Resubmission'


class EditorialDecision(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='editorial_decisions')
    round = models.PositiveIntegerField(default=1)
    decision_type = models.CharField(max_length=30, choices=DecisionType.choices)
    editor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='editorial_decisions',
    )
    letter = models.TextField(blank=True, default='')
    priority_issues = models.TextField(blank=True, default='')
    conflict_resolution_note = models.TextField(blank=True, default='')
    instructions_to_author = models.TextField(blank=True, default='')
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-round']

    def __str__(self):
        return f'{self.submission} — Round {self.round}: {self.get_decision_type_display()}'
