from django.contrib import admin
from .models import EditorialAssignment, ScreeningCheck, EditorialDecision


@admin.register(EditorialAssignment)
class EditorialAssignmentAdmin(admin.ModelAdmin):
    list_display = ('submission', 'editor', 'role', 'assigned_at', 'is_active')


@admin.register(ScreeningCheck)
class ScreeningCheckAdmin(admin.ModelAdmin):
    list_display = ('submission', 'checker', 'result', 'checked_at')


@admin.register(EditorialDecision)
class EditorialDecisionAdmin(admin.ModelAdmin):
    list_display = ('submission', 'round', 'decision_type', 'editor', 'sent_at')
    list_filter = ('decision_type',)
