from django.contrib import admin
from .models import ReviewerProfile, ReviewerSuggestion, ReviewerInvitation


@admin.register(ReviewerProfile)
class ReviewerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_active', 'is_suspended', 'active_invitations_count', 'total_reviews_completed', 'avg_turnaround_days')
    list_filter = ('is_active', 'is_suspended')
    search_fields = ('user__email',)


@admin.register(ReviewerSuggestion)
class ReviewerSuggestionAdmin(admin.ModelAdmin):
    list_display = ('reviewer', 'submission', 'score', 'is_primary', 'status')
    list_filter = ('status', 'is_primary')


@admin.register(ReviewerInvitation)
class ReviewerInvitationAdmin(admin.ModelAdmin):
    list_display = ('reviewer', 'submission', 'status', 'deadline', 'sent_at')
    list_filter = ('status',)
