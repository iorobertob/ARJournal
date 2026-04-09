from django.contrib import admin
from .models import JournalConfig, Issue, Section, EditorialBoardMember


@admin.register(JournalConfig)
class JournalConfigAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Identity', {'fields': ('name', 'tagline', 'description', 'logo', 'favicon', 'issn_print', 'issn_online')}),
        ('Contact', {'fields': ('contact_email', 'editorial_email', 'instagram_url')}),
        ('Institution', {'fields': ('institution', 'country', 'publisher', 'imprint')}),
        ('Editorial Policy', {'fields': ('review_model', 'submission_open')}),
        ('Content', {'fields': ('about_text', 'mission_text', 'methodology_text', 'submission_guidelines', 'footer_partners')}),
    )

    def has_add_permission(self, request):
        return not JournalConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


class SectionInline(admin.TabularInline):
    model = Section
    extra = 0


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ('number', 'volume', 'year', 'title', 'is_current', 'is_published', 'published_at')
    list_editable = ('is_current', 'is_published')
    inlines = [SectionInline]


@admin.register(EditorialBoardMember)
class EditorialBoardMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'institution', 'country', 'order', 'is_active')
    list_editable = ('order', 'is_active')
