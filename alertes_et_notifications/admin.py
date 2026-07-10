from django.contrib import admin

from .models import Alerte


@admin.register(Alerte)
class AlerteAdmin(admin.ModelAdmin):
    list_display = ('type', 'message', 'lu', 'created_at')
    search_fields = ('message',)
    list_filter = ('type', 'lu', 'created_at')
