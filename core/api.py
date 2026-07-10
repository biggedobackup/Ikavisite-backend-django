"""
IKAVISITE API — Django Ninja
Point d'entrée unique pour l'API REST.
Authentification par Bearer JWT.
"""
from typing import Optional, List
from ninja import NinjaAPI, Schema
from django.db.models import Count, Q
from django.db.models.functions import ExtractWeekDay, ExtractMonth
from django.utils import timezone
from django.core.cache import cache
from visites.models import Visite, TypeVisite, Visiteur
from incidents.models import Incident
from entreprise.models import Departement, PorteEntree
from liste_noire.models import ListeNoire, DetectionListeNoire
from objets_oublies.models import ObjetOublie
from utilisateurs.models import Utilisateur
from ninja_jwt.authentication import JWTAuth

jwt_auth = JWTAuth()


api = NinjaAPI(
    title="IKAVISITE API",
    version="1.0.0",
    description="API de gestion de visites — IKA SOLUTION\n\n"
                "Authentification : **Bearer JWT** — cliquer sur \"Authorize\" en haut à droite\n"
                "1. `POST /api/auth/login` → obtenir access + refresh tokens\n"
                "2. Copier l'**access** token dans le champ Bearer",
    docs_url="/docs/",
    auth=jwt_auth,
)

# ─── Enregistrement des routers ───────────────────────────────────────────────
from utilisateurs.api import auth_router, users_router
from visites.api import router as visites_router, types_router
from entreprise.api import router as entreprise_router, portes_router, depts_router, personnel_router, creneaux_router

api.add_router("/auth", auth_router)
api.add_router("/users", users_router)
api.add_router("/visites", visites_router)
api.add_router("/visites/types", types_router)
api.add_router("/entreprise", entreprise_router)
api.add_router("/entreprise/portes", portes_router)
api.add_router("/entreprise/departements", depts_router)
api.add_router("/entreprise/personnel", personnel_router)
api.add_router("/entreprise/creneaux", creneaux_router)


# ─── Health check ────────────────────────────────────────────────────────────
@api.get("/health", tags=["Système"], auth=None)
def health(request):
    """Vérification du fonctionnement de l'API."""
    return {"status": "ok", "version": "1.0.0"}

# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD STATISTIQUES  /api/dashboard/*
# ═══════════════════════════════════════════════════════════════════════════════

class VisitsByDepartmentOut(Schema):
    label: str
    value: int
    width: float

class VisitsByDayOut(Schema):
    day: str
    value: int
    height: float

class VisitsByEntryPointOut(Schema):
    label: str
    value: int
    width: float

class IncidentsFlowOut(Schema):
    month: str
    value: int
    height: float

class VisitTypeOut(Schema):
    label: str
    value: float
    color: str

class StatsTileOut(Schema):
    icon: str
    tone: str
    label: str
    value: int
    sub: str

class DashboardStatsOut(Schema):
    period: dict
    stats: List[StatsTileOut]
    visits_by_department: List[VisitsByDepartmentOut]
    visits_by_day: List[VisitsByDayOut]
    visits_by_entry_point: List[VisitsByEntryPointOut]
    incidents_flow: List[IncidentsFlowOut]
    visit_types: List[VisitTypeOut]
    total_visites_par_type: int
    show_chart_departments: bool
    show_chart_weekday: bool
    show_chart_entry_points: bool
    show_chart_incidents: bool
    show_chart_visit_types: bool


def _has_perm(request, perm: str) -> bool:
    return request.user.is_superuser or request.user.has_perm(perm)

def _has_perm_fast(request, perm: str, perms: set) -> bool:
    return request.user.is_superuser or perm in perms


@api.get("/dashboard/stats", response=DashboardStatsOut, tags=["Tableau de bord"])
def api_dashboard_stats(
    request,
    start: Optional[str] = None,
    end: Optional[str] = None,
    type_id: Optional[int] = None,
):
    """
    Statistiques du tableau de bord.

    Paramètres optionnels :
    - **start** : date début (YYYY-MM-DD)
    - **end** : date fin (YYYY-MM-DD)
    - **type_id** : id du type de visite
    """
    now = timezone.now()
    today = now.date()

    # Cache key based on filters (results cached 60s since dashboard data changes frequently)
    cache_key = f'dashboard_data_{start or ""}_{end or ""}_{type_id or ""}'
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        period_label, stats_agg, total_incidents, visits_by_department, visits_by_day, visits_by_entry_point, incidents_flow, visit_types, total_vt, visiteurs_liste_noire, utilisateurs_total, utilisateurs_actifs, total_departements, total_portes_entree, total_objets, objets_non_recuperes, personnes_liste_noire, detections_liste_noire = cached_data
    else:
        # ── Filtres communs ────────────────────────────────────────────────────
        vqs = Visite.objects.all()
        if start:
            vqs = vqs.filter(date_visite__date__gte=start)
        if end:
            vqs = vqs.filter(date_visite__date__lte=end)
        if type_id:
            vqs = vqs.filter(type_visite_id=type_id)

        # ── Stats agrégées ────────────────────────────────────────────────────
        stats_agg = vqs.aggregate(
            total=Count('id'),
            en_cours=Count('id', filter=Q(statut='EN_COURS')),
            termine=Count('id', filter=Q(statut='TERMINE')),
            excede=Count('id', filter=Q(statut='EXCEDE')),
            aujourdhui=Count('id', filter=Q(date_visite__date=today)),
            termine_aujourdhui=Count('id', filter=Q(statut='TERMINE', date_visite__date=today)),
            visiteurs_distincts=Count('visiteur_id', distinct=True),
        )

        # ── Liste noire ────────────────────────────────────────────────────────
        ln_qs = Visiteur.objects.filter(statut='BLOQUE')
        if start:
            ln_qs = ln_qs.filter(created_at__date__gte=start)
        if end:
            ln_qs = ln_qs.filter(created_at__date__lte=end)
        visiteurs_liste_noire = ln_qs.count()

        # ── Utilisateurs, départements, portes ──────────────────────────────────
        utilisateurs_total = Utilisateur.objects.count()
        utilisateurs_actifs = Utilisateur.objects.filter(statut='ACTIF').count()
        total_departements = Departement.objects.count()
        total_portes_entree = PorteEntree.objects.count()

        # ── Incidents ───────────────────────────────────────────────────────────
        iqs = Incident.objects.all()
        if start:
            iqs = iqs.filter(created_at__date__gte=start)
        if end:
            iqs = iqs.filter(created_at__date__lte=end)
        total_incidents = iqs.count()

        # ── Objets oubliés ─────────────────────────────────────────────────────
        total_objets = ObjetOublie.objects.count()
        objets_non_recuperes = ObjetOublie.objects.filter(statut='NON_RESTITUÉ').count()

        # ── Détections liste noire ─────────────────────────────────────────────
        personnes_liste_noire = ListeNoire.objects.filter(statut='ACTIF').count()
        dln_qs = DetectionListeNoire.objects.filter(statut='ACTIF')
        if start:
            dln_qs = dln_qs.filter(date_detection__date__gte=start)
        if end:
            dln_qs = dln_qs.filter(date_detection__date__lte=end)
        detections_liste_noire = dln_qs.count()

        # ── Stats par département ──────────────────────────────────────────────
        depts = Departement.objects.annotate(
            num_visites=Count('personnel__visite'),
        ).order_by('-num_visites')[:5]
        max_dept = max((d.num_visites for d in depts), default=1)
        visits_by_department = [
            {'label': d.nom, 'value': d.num_visites,
             'width': round(d.num_visites / max_dept * 100) if max_dept else 0}
            for d in depts
        ]

        # ── Visites par jour ───────────────────────────────────────────────────
        wd_raw = dict(
            vqs.filter(date_visite__isnull=False)
            .annotate(wd=ExtractWeekDay('date_visite'))
            .values('wd')
            .annotate(c=Count('id'))
            .values_list('wd', 'c')
        )
        jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        visits_by_day = [
            {'day': j[:3], 'value': wd_raw.get(d, 0), 'height': min(wd_raw.get(d, 0) * 6, 160)}
            for j, d in zip(jours, [2, 3, 4, 5, 6, 7, 1])
        ]

        # ── Visites par point d'entrée ────────────────────────────────────────
        entrances = PorteEntree.objects.annotate(
            num_visites=Count('visite'),
        ).order_by('-num_visites')[:5]
        max_entrance = max((e.num_visites for e in entrances), default=1)
        visits_by_entry_point = [
            {'label': e.titre, 'value': e.num_visites,
             'width': round(e.num_visites / max_entrance * 100) if max_entrance else 0}
            for e in entrances
        ]

        # ── Flux incidents par mois ────────────────────────────────────────────
        months_qs = iqs.filter(created_at__year=now.year) \
            .annotate(m=ExtractMonth('created_at')) \
            .values('m') \
            .annotate(c=Count('id')) \
            .values_list('m', 'c')
        months_raw = dict(months_qs)
        months_abbr = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun',
                       'Juil', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
        incidents_flow = [
            {'month': months_abbr[m - 1], 'value': months_raw.get(m, 0),
             'height': min(months_raw.get(m, 0) * 12, 160)}
            for m in range(1, 13)
        ]

        # ── Types de visite ────────────────────────────────────────────────────
        types_all = TypeVisite.objects.annotate(
            num_visites=Count('visite'),
        ).order_by('-num_visites')
        total_vt = sum(t.num_visites for t in types_all) or 1
        visit_types = [
            {'label': t.nom, 'value': round(t.num_visites / total_vt * 100), 'color': '#1270b8'}
            for t in types_all
        ]

        period_label = 'Toutes les dates'
        if start and end:
            period_label = f'Du {start} au {end}'
        elif start:
            period_label = f'Du {start}'
        elif end:
            period_label = f"Jusqu'au {end}"

        cache.set(cache_key, (period_label, stats_agg, total_incidents, visits_by_department, visits_by_day, visits_by_entry_point, incidents_flow, visit_types, total_vt, visiteurs_liste_noire, utilisateurs_total, utilisateurs_actifs, total_departements, total_portes_entree, total_objets, objets_non_recuperes, personnes_liste_noire, detections_liste_noire), 60)

    stats_raw = [
        {'icon': 'calendar', 'tone': 'primary', 'label': 'Total des visites',  'value': stats_agg['total'],          'sub': f"{stats_agg['en_cours']} en cours",          'perm': 'visites.view_stat_total_visits'},
        {'icon': 'today',   'tone': 'primary', 'label': 'Visites du jour',     'value': stats_agg['aujourdhui'],     'sub': "aujourd'hui",                              'perm': 'visites.view_stat_today_visits'},
        {'icon': 'clock',   'tone': 'danger',  'label': 'Visites en cours',    'value': stats_agg['en_cours'],       'sub': 'en cours',                                  'perm': 'visites.view_stat_en_cours'},
        {'icon': 'check',   'tone': 'success', 'label': 'Visites terminées',   'value': stats_agg['termine'],        'sub': 'terminées',                                  'perm': 'visites.view_stat_termine'},
        {'icon': 'check-circle', 'tone': 'success', 'label': 'Visites terminées du jour', 'value': stats_agg['termine_aujourdhui'], 'sub': "aujourd'hui", 'perm': 'visites.view_stat_termine_aujourdhui'},
        {'icon': 'alert',   'tone': 'danger',  'label': 'Visites excédées',    'value': stats_agg['excede'],         'sub': 'excédées',                                  'perm': 'visites.view_stat_excede'},
        {'icon': 'users',   'tone': 'primary', 'label': 'Total des visiteurs', 'value': stats_agg['visiteurs_distincts'],'sub': f'{visiteurs_liste_noire} en liste noire','perm': 'visites.view_stat_visiteurs'},
        {'icon': 'users',   'tone': 'primary', 'label': 'Total utilisateurs',  'value': utilisateurs_total,     'sub': f'{utilisateurs_actifs} comptes actifs',      'perm': 'visites.view_stat_utilisateurs'},
        {'icon': 'building','tone': 'primary', 'label': 'Total départements',  'value': total_departements,     'sub': 'services enregistrés',                       'perm': 'visites.view_stat_departements'},
        {'icon': 'door',    'tone': 'primary', 'label': "Total portes d'entrée",'value': total_portes_entree,   'sub': "points d'accès",                            'perm': 'visites.view_stat_portes'},
        {'icon': 'shield',  'tone': 'danger',  'label': 'Total des incidents', 'value': total_incidents,        'sub': 'incidents signalés',                         'perm': 'visites.view_stat_incidents'},
        {'icon': 'box',     'tone': 'primary', 'label': 'Total objets oubliés','value': total_objets,           'sub': f'{objets_non_recuperes} objets non récupérés','perm': 'visites.view_stat_objets'},
        {'icon': 'users',   'tone': 'danger',  'label': 'Personnes liste noire','value': personnes_liste_noire, 'sub': 'personnes interdites',                       'perm': 'visites.view_stat_personnes_liste_noire'},
        {'icon': 'shield',  'tone': 'danger',  'label': 'Détections liste noire','value': detections_liste_noire,'sub': 'alertes déclenchées',                        'perm': 'visites.view_stat_detections_liste_noire'},
    ]

    # Filtrer par permissions (pré-fetchées pour éviter 14+ appels DB)
    user_perms = set(request.user.get_all_permissions()) if not request.user.is_superuser else None
    stats = [s for s in stats_raw if _has_perm_fast(request, s['perm'], user_perms)]

    return {
        'period': {'label': period_label, 'start': start or '', 'end': end or ''},
        'stats': stats,
        'visits_by_department': visits_by_department,
        'visits_by_day': visits_by_day,
        'visits_by_entry_point': visits_by_entry_point,
        'incidents_flow': incidents_flow,
        'visit_types': visit_types,
        'total_visites_par_type': total_vt,
        'show_chart_departments': _has_perm_fast(request, 'visites.view_chart_departments', user_perms),
        'show_chart_weekday': _has_perm_fast(request, 'visites.view_chart_weekday', user_perms),
        'show_chart_entry_points': _has_perm_fast(request, 'visites.view_chart_entry_points', user_perms),
        'show_chart_incidents': _has_perm_fast(request, 'visites.view_chart_incidents', user_perms),
        'show_chart_visit_types': _has_perm_fast(request, 'visites.view_chart_visit_types', user_perms),
    }
