from django.contrib import admin

from .models import ObjetOublie, DetectionObjetOublie


@admin.register(ObjetOublie)
class ObjetOublieAdmin(admin.ModelAdmin):
    list_display = ('nom_objet', 'categorie', 'date_trouve', 'lieu_trouve', 'statut')
    search_fields = ('nom_objet', 'code', 'personne_recupere')
    list_filter = ('statut', 'categorie', 'date_trouve')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('visite', 'departement')


@admin.register(DetectionObjetOublie)
class DetectionObjetOublieAdmin(admin.ModelAdmin):
    list_display = ('objet_oublie', 'porte_entree', 'date_detection', 'confiance', 'statut')
    search_fields = ('objet_oublie__nom_objet', 'notes')
    list_filter = ('statut', 'confiance', 'date_detection')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('objet_oublie', 'porte_entree')
