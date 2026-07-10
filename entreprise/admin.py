from django.contrib import admin

from .models import ParametreEntreprise, PorteEntree, Departement, Personnel, CreneauSemaine


@admin.register(ParametreEntreprise)
class ParametreEntrepriseAdmin(admin.ModelAdmin):
    list_display = ('nom_entreprise', 'email', 'telephone', 'ville', 'pays', 'statut')
    search_fields = ('nom_entreprise', 'email', 'ville')
    list_filter = ('statut', 'pays')


@admin.register(PorteEntree)
class PorteEntreeAdmin(admin.ModelAdmin):
    list_display = ('titre', 'emplacement', 'statut', 'created_at')
    search_fields = ('titre', 'emplacement')
    list_filter = ('statut',)


@admin.register(Departement)
class DepartementAdmin(admin.ModelAdmin):
    list_display = ('nom', 'statut', 'created_at')
    search_fields = ('nom',)
    list_filter = ('statut',)


@admin.register(Personnel)
class PersonnelAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prenom', 'fonction', 'departement', 'statut', 'created_at')
    search_fields = ('nom', 'prenom', 'email')
    list_filter = ('statut', 'departement')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('departement')


@admin.register(CreneauSemaine)
class CreneauSemaineAdmin(admin.ModelAdmin):
    list_display = ('jour_semaine', 'heure_debut', 'heure_fin', 'statut')
    search_fields = ('jour_semaine',)
    list_filter = ('statut', 'jour_semaine')
