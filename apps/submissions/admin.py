from django.contrib import admin
from .models import Submission, SubmissionRevision, SubmissionAsset, SimilarityCheck


class RevisionInline(admin.StackedInline):
    model = SubmissionRevision
    extra = 0
    readonly_fields = ('created_at',)


class AssetInline(admin.TabularInline):
    model = SubmissionAsset
    extra = 0


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'article_type', 'status', 'submission_date', 'created_at')
    list_filter = ('status', 'article_type', 'language')
    search_fields = ('title', 'author__email', 'abstract')
    readonly_fields = ('created_at', 'updated_at', 'slug')
    inlines = [RevisionInline]


@admin.register(SubmissionRevision)
class SubmissionRevisionAdmin(admin.ModelAdmin):
    list_display = ('submission', 'version', 'status', 'submitted_at')
    inlines = [AssetInline]
