from django.contrib import admin

from .models import Meeting, Milestone, ReviewerPlan


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ('title', 'team_label', 'meeting_date', 'created_by')
    list_filter = ('meeting_date',)
    search_fields = ('title', 'team_label', 'minutes')
    filter_horizontal = ('attendees',)


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ('display_label', 'kind', 'due_date', 'call', 'issue')
    list_filter = ('kind',)


@admin.register(ReviewerPlan)
class ReviewerPlanAdmin(admin.ModelAdmin):
    list_display = ('submission', 'reviewer', 'created_by', 'created_at')
    search_fields = ('submission__title', 'reviewer__email')
