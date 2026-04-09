from django.contrib import admin
from .models import CanonicalDocument, DocumentAsset


class DocumentAssetInline(admin.TabularInline):
    model = DocumentAsset
    extra = 0


@admin.register(CanonicalDocument)
class CanonicalDocumentAdmin(admin.ModelAdmin):
    list_display = ('revision', 'schema_version', 'html_build_ok', 'pdf_build_ok', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [DocumentAssetInline]
