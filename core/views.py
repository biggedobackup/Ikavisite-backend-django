from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Count, Q
from django.db.models.functions import ExtractWeekDay, ExtractMonth
from django.urls import reverse
from django.utils import timezone
from urllib.parse import urlencode
from visites.models import Visite, TypeVisite, Visiteur
from incidents.models import Incident
from entreprise.models import Departement, PorteEntree
from liste_noire.models import ListeNoire, DetectionListeNoire
from objets_oublies.models import ObjetOublie
from django.contrib.auth.models import Group, Permission
from django.contrib.auth import get_user_model
from utilisateurs.models import HistoriqueAction
from django.core.paginator import Paginator


@login_required
def tableau_de_bord(request):
    now = timezone.now()
    today = now.date()

    start = request.GET.get('start', '')
    end = request.GET.get('end', '')
    id_type = request.GET.get('type', '')

    # ── Filtres communs ────────────────────────────────────────────────────
    vqs = Visite.objects.all()
    if start:
        vqs = vqs.filter(date_visite__date__gte=start)
    if end:
        vqs = vqs.filter(date_visite__date__lte=end)
    if id_type and id_type.isdigit():
        vqs = vqs.filter(type_visite_id=int(id_type))

    # ── Stats visites : 1 aggregation au lieu de 6 count() ────────────────
    stats_agg = vqs.aggregate(
        total=Count('id'),
        en_cours=Count('id', filter=Q(statut='EN_COURS')),
        termine=Count('id', filter=Q(statut='TERMINE')),
        excede=Count('id', filter=Q(statut='EXCEDE')),
        aujourdhui=Count('id', filter=Q(date_visite__date=today)),
        termine_aujourdhui=Count('id', filter=Q(statut='TERMINE', date_visite__date=today)),
    )
    # Le distinct_count sur les visiteurs est plus rapide séparément
    visiteurs_total = vqs.values('visiteur_id').distinct().count()
    stats_agg['visiteurs_distincts'] = visiteurs_total

    # ── Liste noire ────────────────────────────────────────────────────────
    ln_qs = Visiteur.objects.filter(statut='BLOQUE')
    if start:
        ln_qs = ln_qs.filter(created_at__date__gte=start)
    if end:
        ln_qs = ln_qs.filter(created_at__date__lte=end)
    visiteurs_liste_noire = ln_qs.count()

    # ── Utilisateurs, départements, portes ──────────────────────────────────
    try:
        from utilisateurs.models import Utilisateur as U
        utilisateurs_total = U.objects.count()
        utilisateurs_actifs = U.objects.filter(statut='ACTIF').count()
    except Exception:
        utilisateurs_total = 0
        utilisateurs_actifs = 0
    total_departements = Departement.objects.count()
    total_portes_entree = PorteEntree.objects.count()

    # ── Incidents : 1 aggregation au lieu de count() séparé ────────────────
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

    # ── Stats par département : 1 requête ──────────────────────────────────
    depts = Departement.objects.annotate(
        num_visites=Count('personnel__visite'),
    ).order_by('-num_visites')[:5]
    max_dept = max((d.num_visites for d in depts), default=1)
    visits_by_department = [
        {'label': d.nom, 'value': d.num_visites,
         'width': round(d.num_visites / max_dept * 100) if max_dept else 0}
        for d in depts
    ]

    # ── Visites par jour de la semaine : 1 requête au lieu de 7 ──────────
    wd_raw = dict(
        vqs.filter(date_visite__isnull=False)
        .annotate(wd=ExtractWeekDay('date_visite'))
        .values('wd')
        .annotate(c=Count('id'))
        .values_list('wd', 'c')
    )
    jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
    visits_by_day = [
        {'day': j[:3], 'value': wd_raw.get(str(d), 0), 'height': min(wd_raw.get(str(d), 0) * 6, 160)}
        for j, d in zip(jours, [2, 3, 4, 5, 6, 7, 1])
    ]

    # ── Visites par point d'entrée : 1 requête ────────────────────────────
    entrances = PorteEntree.objects.annotate(
        num_visites=Count('visite'),
    ).order_by('-num_visites')[:5]
    max_entrance = max((e.num_visites for e in entrances), default=1)
    visits_by_entry_point = [
        {'label': e.titre, 'value': e.num_visites,
         'width': round(e.num_visites / max_entrance * 100) if max_entrance else 0}
        for e in entrances
    ]

    # ── Flux incidents par mois : 1 requête au lieu de 12 ─────────────────
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

    # ── Types de visite : 1 requête ───────────────────────────────────────
    types_all = TypeVisite.objects.annotate(
        num_visites=Count('visite'),
    ).order_by('-num_visites')
    total_vt = sum(t.num_visites for t in types_all) or 1
    visit_types_data = [
        {'label': t.nom, 'value': round(t.num_visites / total_vt * 100), 'color': '#1270b8'}
        for t in types_all
    ]

    today_start = f"{today.isoformat()}T01:00"
    today_end = f"{today.isoformat()}T23:00"
    today_url = reverse('liste_visites') + '?' + urlencode({'date_start': today_start, 'date_end': today_end})

    period_label = 'Toutes les dates'
    if start and end:
        period_label = f'Du {start} au {end}'
    elif start:
        period_label = f'Du {start}'
    elif end:
        period_label = f"Jusqu'au {end}"

    stats = [
        {'icon': 'calendar', 'tone': 'primary', 'label': 'Total des visites',  'value': stats_agg['total'],          'sub': f"{stats_agg['en_cours']} en cours",       'url': 'liste_visites',       'perm': 'view_stat_total_visits'},
        {'icon': 'today',   'tone': 'primary', 'label': 'Visites du jour',     'value': stats_agg['aujourdhui'],     'sub': f"{stats_agg['termine']} terminées",    'url': 'liste_visites', 'url_override': today_url, 'perm': 'view_stat_today_visits'},
        {'icon': 'clock',   'tone': 'danger',  'label': 'Visites en cours',    'value': stats_agg['en_cours'],       'sub': 'en cours',                           'url': 'liste_visites_encours', 'perm': 'view_stat_en_cours'},
        {'icon': 'check',   'tone': 'success', 'label': 'Visites terminées',   'value': stats_agg['termine'],        'sub': 'terminées',                          'url': 'liste_visites_terminees', 'perm': 'view_stat_termine'},
        {'icon': 'check-circle', 'tone': 'success', 'label': 'Visites terminées du jour', 'value': stats_agg.get('termine_aujourdhui', 0), 'sub': "aujourd'hui", 'url': 'liste_visites_terminees', 'perm': 'view_stat_termine_aujourdhui'},
        {'icon': 'alert',   'tone': 'danger',  'label': 'Visites excédées',    'value': stats_agg['excede'],         'sub': 'excédées',                           'url': 'liste_visites_excedees', 'perm': 'view_stat_excede'},
        {'icon': 'users',   'tone': 'primary', 'label': 'Total des visiteurs', 'value': stats_agg['visiteurs_distincts'],'sub': f'{visiteurs_liste_noire} en liste noire', 'url': 'liste_visiteurs', 'perm': 'view_stat_visiteurs'},
        {'icon': 'users',   'tone': 'primary', 'label': 'Total utilisateurs',  'value': utilisateurs_total,     'sub': f'{utilisateurs_actifs} comptes actifs',   'url': 'liste_utilisateurs', 'perm': 'view_stat_utilisateurs'},
        {'icon': 'building','tone': 'primary', 'label': 'Total départements',  'value': total_departements,     'sub': 'services enregistrés',               'url': 'liste_departements', 'perm': 'view_stat_departements'},
        {'icon': 'door',    'tone': 'primary', 'label': "Total portes d'entrée",'value': total_portes_entree,   'sub': "points d'accès",                     'url': 'liste_portes_entree', 'perm': 'view_stat_portes'},
        {'icon': 'shield',  'tone': 'danger',  'label': 'Total des incidents', 'value': total_incidents,        'sub': 'incidents signalés',                 'url': 'liste_incidents', 'perm': 'view_stat_incidents'},
        {'icon': 'box',     'tone': 'primary', 'label': 'Total objets oubliés','value': total_objets,           'sub': f'{objets_non_recuperes} objets non récupérés', 'url': 'liste_objets_oublies', 'perm': 'view_stat_objets'},
        {'icon': 'users',   'tone': 'danger',  'label': 'Personnes liste noire','value': personnes_liste_noire, 'sub': 'personnes interdites',               'url': 'liste_listes_noires', 'perm': 'view_stat_personnes_liste_noire'},
        {'icon': 'shield',  'tone': 'danger',  'label': 'Détections liste noire','value': detections_liste_noire,'sub': 'alertes déclenchées',                'url': 'liste_detections_liste_noire', 'perm': 'view_stat_detections_liste_noire'},
    ]

    # Filtre les stats visibles selon les permissions de l'utilisateur
    stats = [s for s in stats if request.user.has_perm(f'visites.{s["perm"]}')]

    type_choices = TypeVisite.objects.all().order_by('nom')
    user_perms = request.user.get_all_permissions()

    context = {
        'stats': stats,
        'visits_by_department': visits_by_department,
        'visits_by_day': visits_by_day,
        'visits_by_entry_point': visits_by_entry_point,
        'incidents_flow': incidents_flow,
        'visit_types': visit_types_data,
        'total_visites_par_type': total_vt,
        'period_start': start, 'period_end': end,
        'period_label': period_label,
        'type_choices': type_choices,
        'selected_type': id_type,
        # Permissions individuelles pour les graphiques
        'show_chart_departments': 'visites.view_chart_departments' in user_perms,
        'show_chart_weekday': 'visites.view_chart_weekday' in user_perms,
        'show_chart_entry_points': 'visites.view_chart_entry_points' in user_perms,
        'show_chart_incidents': 'visites.view_chart_incidents' in user_perms,
        'show_chart_visit_types': 'visites.view_chart_visit_types' in user_perms,
    }
    return render(request, 'tableau.html', context)


# ─── Gestion des rôles (Groupes) ─────────────────────────────────────────


User = get_user_model()


_app_label_fr = {
    'admin': 'Administration',
    'auth': 'Authentification',
    'authtoken': 'Token d\'authentification',
    'contenttypes': 'Types de contenu',
    'sessions': 'Sessions',
    'sites': 'Sites',
    'visites': 'Visites',
    'incidents': 'Incidents',
    'entreprise': 'Entreprise',
    'liste_noire': 'Liste noire',
    'objets_oublies': 'Objets oubliés',
    'utilisateurs': 'Utilisateurs',
    'alertes_et_notifications': 'Alertes et notifications',
    'taches_programmees': 'Tâches programmées',
}


def _app_label_fr_name(label):
    return _app_label_fr.get(label, label.replace('_', ' ').title())


def _is_dashboard_perm(perm):
    """Une permission du tableau de bord ? (statistiques ou graphiques)"""
    return perm.codename.startswith('view_stat_') or perm.codename.startswith('view_chart_')


def _perm_app_label(perm):
    """Groupe d'affichage pour Ajouter/Modifier rôle.
    Les permissions tableau de bord vont dans leur propre section."""
    if _is_dashboard_perm(perm):
        return 'Tableau de bord'
    return _app_label_fr_name(perm.content_type.app_label)


def _perm_name_fr(perm):
    action_map = {
        'add': 'Ajouter',
        'change': 'Modifier',
        'delete': 'Supprimer',
        'view': 'Voir',
    }
    if '_' in perm.codename:
        action, model_part = perm.codename.split('_', 1)
        action_fr = action_map.get(action, action)
        # Permission non standard (ex: view_dashboard sur le modèle Visite)
        # → on garde le nom original défini dans Meta.permissions
        if model_part != perm.content_type.model:
            return perm.name
        model_name = perm.content_type.name or model_part.replace('_', ' ').capitalize()
        return f"{action_fr} {model_name}"
    return perm.name


@login_required
def liste_groupes(request):
    query = request.GET.get('q', '').strip()
    items = Group.objects.all()
    if query:
        items = items.filter(name__icontains=query)
    items = items.annotate(nb_users=Count('user', distinct=True), nb_permissions=Count('permissions', distinct=True)).order_by('name')

    paginator = Paginator(items, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    page_links = paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1)

    return render(request, 'groupes/liste.html', {
        'page_obj': page_obj,
        'page_links': page_links,
        'query': query,
    })


@login_required
def ajouter_groupe(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Le nom du rôle est requis.')
            return render(request, 'groupes/ajouter.html')
        if Group.objects.filter(name=name).exists():
            messages.error(request, 'Ce nom de rôle existe déjà.')
            return render(request, 'groupes/ajouter.html')
        group = Group.objects.create(name=name)
        perm_ids = request.POST.getlist('permissions')
        if perm_ids:
            group.permissions.set(Permission.objects.filter(id__in=perm_ids))
        HistoriqueAction.objects.create(utilisateur=request.user, action='AJOUT', entite='Groupe', entite_id=group.pk)
        messages.success(request, 'Rôle créé avec succès.')
        return redirect('liste_groupes')
    perms = Permission.objects.select_related('content_type').order_by('content_type__app_label', 'name')
    perms = [{'id': p.id, 'name': _perm_name_fr(p), 'codename': p.codename, 'app_label': _perm_app_label(p)} for p in perms]
    return render(request, 'groupes/ajouter.html', {'permissions': perms})


@login_required
def detail_groupe(request, pk):
    group = get_object_or_404(Group, pk=pk)
    users = group.user_set.all().order_by('-date_joined')
    perms = group.permissions.select_related('content_type').order_by('content_type__app_label', 'name')
    perms_fr = [{'name': _perm_name_fr(p), 'app_label': _perm_app_label(p)} for p in perms]
    return render(request, 'groupes/detail.html', {'group': group, 'users': users, 'perms_fr': perms_fr})


@login_required
def modifier_groupe(request, pk):
    group = get_object_or_404(Group, pk=pk)
    perms_all = Permission.objects.select_related('content_type').order_by('content_type__app_label', 'name')
    perms_all = [{'id': p.id, 'name': _perm_name_fr(p), 'codename': p.codename, 'app_label': _perm_app_label(p)} for p in perms_all]
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Le nom du rôle est requis.')
            group_perm_ids = set(group.permissions.values_list('id', flat=True))
            return render(request, 'groupes/modifier.html', {'group': group, 'permissions': perms_all, 'group_perm_ids': group_perm_ids})
        if Group.objects.filter(name=name).exclude(pk=pk).exists():
            messages.error(request, 'Ce nom de rôle existe déjà.')
            group_perm_ids = set(group.permissions.values_list('id', flat=True))
            return render(request, 'groupes/modifier.html', {'group': group, 'permissions': perms_all, 'group_perm_ids': group_perm_ids})
        group.name = name
        perm_ids = request.POST.getlist('permissions')
        group.permissions.set(Permission.objects.filter(id__in=perm_ids))
        group.save()
        HistoriqueAction.objects.create(utilisateur=request.user, action='MODIFICATION', entite='Groupe', entite_id=group.pk)
        messages.success(request, 'Rôle modifié avec succès.')
        return redirect('liste_groupes')
    group_perm_ids = set(group.permissions.values_list('id', flat=True))
    return render(request, 'groupes/modifier.html', {'group': group, 'permissions': perms_all, 'group_perm_ids': group_perm_ids})


@login_required
def supprimer_groupe(request, pk):
    group = get_object_or_404(Group, pk=pk)
    if request.method == 'POST':
        group.delete()
        HistoriqueAction.objects.create(utilisateur=request.user, action='SUPPRESSION', entite='Groupe', entite_id=pk)
        messages.success(request, 'Rôle supprimé avec succès.')
        return redirect('liste_groupes')
    return render(request, 'groupes/detail.html', {'group': group, 'users': group.user_set.all(), 'confirm_delete': True})
