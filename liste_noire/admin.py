from django.contrib import admin

from .models import TypeListeNoire, ListeNoire, DetectionListeNoire


@admin.register(TypeListeNoire)
class TypeListeNoireAdmin(admin.ModelAdmin):
    list_display = ('nom', 'niveau_risque', 'statut')
    search_fields = ('nom',)
    list_filter = ('statut', 'niveau_risque')


@admin.register(ListeNoire)
class ListeNoireAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prenom', 'type_liste_noire', 'numero_piece', 'statut')
    search_fields = ('nom', 'prenom', 'numero_piece', 'numero_nip')
    list_filter = ('statut', 'type_liste_noire')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('type_liste_noire')


@admin.register(DetectionListeNoire)
class DetectionListeNoireAdmin(admin.ModelAdmin):
    list_display = ('liste_noire', 'porte_entree', 'date_detection', 'confiance', 'statut')
    search_fields = ('liste_noire__nom', 'liste_noire__prenom', 'notes')
    list_filter = ('statut', 'confiance', 'date_detection')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('liste_noire', 'porte_entree')
