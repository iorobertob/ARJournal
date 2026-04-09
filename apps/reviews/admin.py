from django.contrib import admin
from .models import Review, ReviewAnnotation, ReviewModeration


class AnnotationInline(admin.TabularInline):
    model = ReviewAnnotation
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('reviewer', 'submission', 'recommendation', 'status', 'submitted_at')
    list_filter = ('status', 'recommendation')
    inlines = [AnnotationInline]

    def reviewer(self, obj):
        return obj.invitation.reviewer.display_name
    reviewer.short_description = 'Reviewer'

    def submission(self, obj):
        return str(obj.invitation.submission)[:50]
    submission.short_description = 'Submission'


@admin.register(ReviewModeration)
class ReviewModerationAdmin(admin.ModelAdmin):
    list_display = ('review', 'status', 'conflict_flagged', 'moderated_at')
    list_filter = ('status', 'conflict_flagged')
