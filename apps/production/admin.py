from django.contrib import admin
from .models import HTMLBuild, PDFExport, DOIDeposit


@admin.register(HTMLBuild)
class HTMLBuildAdmin(admin.ModelAdmin):
    list_display = ('document', 'slug', 'is_published', 'access_mode', 'published_at', 'built_at')
    list_editable = ('is_published', 'access_mode')


@admin.register(PDFExport)
class PDFExportAdmin(admin.ModelAdmin):
    list_display = ('document', 'mode', 'downloaded', 'expires_at', 'created_at')
    list_filter = ('mode', 'downloaded')


@admin.register(DOIDeposit)
class DOIDepositAdmin(admin.ModelAdmin):
    list_display = ('document', 'doi', 'status', 'deposited_at')
    list_filter = ('status',)
