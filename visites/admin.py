from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import mark_safe
from django.utils import timezone

from .models import TypeVisite, Visiteur, Visite, VisiteEnCours, VisiteTerminee, VisiteExcedee


class VisiteInline(admin.TabularInline):
    model = Visite
    extra = 0
    can_delete = False
    can_change = False
    fields = ('_date_visite', 'type_visite', 'genre', 'porte_entree', 'personnel', '_statut')
    readonly_fields = fields
    ordering = ('-date_visite',)

    @admin.display(description='Date visite')
    def _date_visite(self, obj):
        return obj.date_visite.strftime('%d %B %Y %H:%M') if obj.date_visite else '—'

    @admin.display(description='Statut')
    def _statut(self, obj):
        if obj.est_excedee:
            return mark_safe('<span style="color:red;font-weight:bold">⚠ EXCEDÉE</span>')
        return obj.get_statut_display() if hasattr(obj, 'get_statut_display') else obj.statut


@admin.register(TypeVisite)
class TypeVisiteAdmin(admin.ModelAdmin):
    list_display = ('nom', 'duree_max_minutes', 'statut')
    search_fields = ('nom',)
    list_filter = ('statut',)


@admin.register(Visiteur)
class VisiteurAdmin(admin.ModelAdmin):
    inlines = [VisiteInline]
    list_display = ('nom', 'prenom', 'genre', 'nationalite', 'telephone', '_nb_visites', 'statut')
    search_fields = ('nom', 'prenom', 'email', 'telephone', 'numero_piece')
    list_filter = ('statut', 'genre', 'nationalite')

    @admin.display(description='Nb visites')
    def _nb_visites(self, obj):
        return obj.nb_visites


class VisiteBaseAdmin(admin.ModelAdmin):
    change_list_template = 'admin/visites/visite/change_list.html'
    list_display = ('visiteur', 'genre', 'type_visite', 'porte_entree', 'date_visite', '_heure_fin', '_statut_excede')
    search_fields = ('visiteur__nom', 'visiteur__prenom', 'motif')
    list_filter = ('genre', 'type_visite', 'date_visite')

    @admin.display(description='Fin prévue')
    def _heure_fin(self, obj):
        fin = obj.heure_fin_prevue_dt
        return fin.strftime('%H:%M') if fin else '—'

    @admin.display(description='Statut')
    def _statut_excede(self, obj):
        if obj.est_excedee:
            return mark_safe('<span style="color:red;font-weight:bold">⚠ EXCEDÉE</span>')
        return obj.get_statut_display() if hasattr(obj, 'get_statut_display') else obj.statut

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'type_visite', 'visiteur', 'porte_entree', 'personnel'
        )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        agg = Visite.objects.aggregate(
            total=Count('id'),
            en_cours=Count('id', filter=Q(statut='EN_COURS')),
            terminees=Count('id', filter=Q(statut__in=['TERMINE', 'SORTIE_SYSTEME'])),
            excedees=Count('id', filter=Q(statut='EXCEDE')),
        )
        context = {
            'stat_total': agg['total'],
            'stat_en_cours': agg['en_cours'],
            'stat_terminees': agg['terminees'],
            'stat_excedees': agg['excedees'],
            'stat_visiteurs': Visiteur.objects.count(),
        }
        return super().changelist_view(request, {**(extra_context or {}), **context})


@admin.register(Visite)
class VisiteAdmin(VisiteBaseAdmin):
    list_filter = ('statut', 'type_visite', 'date_visite')


@admin.register(VisiteEnCours)
class VisiteEnCoursAdmin(VisiteBaseAdmin):
    verbose_name = 'Visite en cours'

    def get_queryset(self, request):
        return super().get_queryset(request).filter(statut='EN_COURS')


@admin.register(VisiteTerminee)
class VisiteTermineeAdmin(VisiteBaseAdmin):
    verbose_name = 'Visite terminée'

    def get_queryset(self, request):
        return super().get_queryset(request).filter(statut__in=['TERMINE', 'SORTIE_SYSTEME'])


@admin.register(VisiteExcedee)
class VisiteExcedeeAdmin(VisiteBaseAdmin):
    verbose_name = 'Visite excédée'

    def get_queryset(self, request):
        return super().get_queryset(request).filter(statut='EXCEDE')
