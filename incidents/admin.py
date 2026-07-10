from django.contrib import admin

from .models import Incident, DetectionIncident


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ('type_incident', 'gravite', 'visite', 'statut')
    search_fields = ('type_incident', 'motif')
    list_filter = ('statut', 'gravite', 'type_incident')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('visite')


@admin.register(DetectionIncident)
class DetectionIncidentAdmin(admin.ModelAdmin):
    list_display = ('incident', 'date_detection', 'confiance', 'statut')
    search_fields = ('incident__type_incident', 'notes')
    list_filter = ('statut', 'confiance', 'date_detection')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('incident')
