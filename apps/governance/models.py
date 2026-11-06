from django.db import models
from django.conf import settings


class Meeting(models.Model):
    """Free-form minutes from a meeting of an editorial team or subteam.

    The team/subteam is a free-text label (no team entities). Attendees are
    picked ad-hoc. TODO items, planned actions and decisions are written as
    plain (rich) text inside the minutes body.
    """
    title = models.CharField(max_length=255)
    team_label = models.CharField(
        max_length=255, blank=True, default='',
        help_text='Free-text team / subteam, e.g. "Editorial board" or "Review subteam".',
    )
    meeting_date = models.DateField()
    attendees = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name='governance_meetings',
    )
    minutes = models.TextField(
        blank=True, default='',
        help_text='Minutes, decisions and TODO / action items (sanitized rich text).',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='governance_meetings_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-meeting_date', '-created_at']

    def __str__(self):
        return f'{self.title} ({self.meeting_date})'


class MilestoneKind(models.TextChoices):
    CALL_OPEN = 'call_open', 'Call opens'
    SUBMISSION_DEADLINE = 'submission_deadline', 'Submission deadline'
    SCREENING = 'screening', 'Technical screening'
    REVIEW_DEADLINE = 'review_deadline', 'Review deadline'
    REVISION_DEADLINE = 'revision_deadline', 'Revision deadline'
    DECISION = 'decision', 'Final decision'
    PRODUCTION = 'production', 'Production'
    PUBLICATION = 'publication', 'Publication'
    CUSTOM = 'custom', 'Custom'


class Milestone(models.Model):
    """An editable schedule entry (a point on the timeline) for a call or issue.

    A milestone belongs to a call OR an issue. Dates are planned/editable by
    editors — they are not auto-derived from submission history.
    """
    call = models.ForeignKey(
        'journal.Call', on_delete=models.CASCADE, null=True, blank=True,
        related_name='milestones',
    )
    issue = models.ForeignKey(
        'journal.Issue', on_delete=models.CASCADE, null=True, blank=True,
        related_name='milestones',
    )
    kind = models.CharField(max_length=30, choices=MilestoneKind.choices, default=MilestoneKind.CUSTOM)
    label = models.CharField(
        max_length=255, blank=True, default='',
        help_text='Optional label; falls back to the milestone kind.',
    )
    due_date = models.DateField(null=True, blank=True)
    note = models.TextField(blank=True, default='')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['due_date', 'order']

    def __str__(self):
        return f'{self.display_label} — {self.due_date or "TBD"}'

    @property
    def display_label(self):
        return self.label or self.get_kind_display()

    @property
    def target(self):
        return self.call or self.issue


class ReviewerPlan(models.Model):
    """A planned (internal, no-email) reviewer assignment recorded in governance.

    This is bookkeeping only — it does NOT create a ReviewerInvitation or send
    any email. Real invitations are triggered later from the editorial
    workspace.
    """
    submission = models.ForeignKey(
        'submissions.Submission', on_delete=models.CASCADE, related_name='reviewer_plans',
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='governance_reviewer_plans',
    )
    note = models.CharField(max_length=500, blank=True, default='')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='governance_reviewer_plans_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['submission', 'reviewer'], name='unique_reviewer_plan_per_submission',
            ),
        ]

    def __str__(self):
        return f'Planned reviewer {self.reviewer} → {self.submission}'
