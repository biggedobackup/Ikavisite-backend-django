from io import BytesIO
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from alertes_et_notifications.models import Alerte
from .models import Incident, TypeIncident, GRAVITE_CHOICES, STATUT_INCIDENT_CHOICES, DetectionDecision, DECISION_CHOICES
from utilisateurs.models import HistoriqueAction
from visites.models import Visite, Visiteur


def _base_ctx():
    return {
        'type_incident_choices': TypeIncident.objects.filter(actif=True).order_by('ordre', 'nom'),
        'gravite_choices': GRAVITE_CHOICES,
        'statut_choices': STATUT_INCIDENT_CHOICES,
    }


def _export_pdf(rows, headers, title, filename, col_ratios=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), title=title,
                            leftMargin=1.5*cm, rightMargin=1.5*cm)
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'],
                                fontSize=8, leading=10, alignment=1)
    elements = []
    elements.append(Paragraph(title, styles['Title']))
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph(f"Généré le {timezone.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 0.5 * cm))
    col_count = len(headers)
    available_width = landscape(A4)[0] - 3 * cm
    if col_ratios is None:
        col_ratios = [1] * col_count
    total_ratio = sum(col_ratios)
    col_widths = [available_width * r / total_ratio for r in col_ratios]
    wrapped_rows = [[Paragraph(str(c), cell_style) for c in row] for row in rows]
    data = [headers] + wrapped_rows
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1270b8')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8fafc'), colors.white]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(table)
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}_{timezone.now().strftime("%Y%m%d")}.pdf"'
    return response


def _export_excel(rows, headers, title, filename):
    wb = Workbook()
    ws = wb.active
    ws.title = title[:31]
    ws.append(headers)
    for row in rows:
        ws.append(row)
    for col_idx in range(1, len(headers) + 1):
        ws.column_dimensions[chr(64 + col_idx)].width = 22
    header_fill = PatternFill(start_color='1270b8', end_color='1270b8', fill_type='solid')
    header_font = Font(bold=True, color='ffffff', size=11)
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    return response


@login_required
def liste_incidents(request):
    query = request.GET.get('q', '').strip()
    gravite = request.GET.get('gravite', '')
    statut = request.GET.get('statut', '')
    items = Incident.objects.select_related(
        'type_incident', 'visite__visiteur', 'personne'
    )
    if query:
        items = items.filter(
            Q(titre__icontains=query) | Q(type_incident__nom__icontains=query) | Q(motif__icontains=query) |
            Q(visite__visiteur__nom__icontains=query) | Q(visite__visiteur__prenom__icontains=query) |
            Q(personne__nom__icontains=query) | Q(personne__prenom__icontains=query)
        )
    if gravite:
        items = items.filter(gravite=gravite)
    if statut:
        items = items.filter(statut=statut)
    items = items.order_by('-created_at')
    paginator = Paginator(items, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    page_links = paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1)
    fp = {k: v for k, v in [('q', query), ('gravite', gravite), ('statut', statut)] if v}
    return render(request, 'incidents/liste.html', {
        'page_obj': page_obj, 'page_links': page_links, 'query': query,
        'gravite_filter': gravite, 'statut_filter': statut,
        'filter_params': urlencode(fp) + '&' if fp else '',
    })


@login_required
def recherche_visiteurs_json(request):
    """Endpoint JSON pour rechercher des visiteurs par nom, prénom, NIP ou numéro de document."""
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})

    from visites.models import DocumentIdentite

    # Recherche directe sur Visiteur
    qs = Visiteur.objects.filter(
        Q(nom__icontains=q) | Q(prenom__icontains=q) |
        Q(numero_piece__icontains=q) | Q(numero_nip__icontains=q)
    ).order_by('nom', 'prenom')[:20]

    # Élargir via DocumentIdentite — chercher les visiteurs par numéro de document
    doc_visitor_ids = DocumentIdentite.objects.filter(
        numero_document__icontains=q
    ).values_list('visiteur_id', flat=True)[:20]

    if doc_visitor_ids:
        qs = qs | Visiteur.objects.filter(pk__in=doc_visitor_ids).order_by('nom', 'prenom')
        qs = qs[:20]

    results = []
    for v in qs:
        label = f"{v.nom} {v.prenom or ''}"
        pieces = []
        if v.numero_nip:
            pieces.append(f"NIP:{v.numero_nip}")
        if v.numero_piece:
            pieces.append(f"Pièce:{v.numero_piece}")
        # Ajouter les documents liés depuis DocumentIdentite
        docs = DocumentIdentite.objects.filter(visiteur=v, statut='ACTIF').values_list(
            'type_document', 'numero_document'
        )[:5]
        for td, nd in docs:
            short_type = td[:4] if td else 'Doc'
            pieces.append(f"{short_type}:{nd}")
        if pieces:
            label += f" ({', '.join(pieces)})"
        results.append({
            'id': v.pk,
            'label': label,
        })
    return JsonResponse({'results': results})


@login_required
def ajouter_incident(request):
    visite_preset = request.GET.get('visite') or None
    if request.method == 'POST':
        titre = request.POST.get('titre', '').strip()
        type_incident_pk = request.POST.get('type_incident', '').strip()
        if not titre:
            messages.error(request, 'Le titre / objet de l\'incident est requis.')
            return render(request, 'incidents/ajouter.html', {**_base_ctx(), 'visite_preset': visite_preset})
        if not type_incident_pk:
            messages.error(request, 'Le type d\'incident est requis.')
            return render(request, 'incidents/ajouter.html', {**_base_ctx(), 'visite_preset': visite_preset})
        try:
            type_incident = TypeIncident.objects.get(pk=type_incident_pk, actif=True)
        except TypeIncident.DoesNotExist:
            messages.error(request, 'Le type d\'incident sélectionné n\'est pas valide ou est inactif.')
            return render(request, 'incidents/ajouter.html', {**_base_ctx(), 'visite_preset': visite_preset})

        # La visite vient du paramètre GET (pas du formulaire)
        visite_id = visite_preset
        personne_id = request.POST.get('personne') or None

        # Auto-remplir personne depuis la visite si non spécifié manuellement
        if visite_id and not personne_id:
            from visites.models import Visite
            try:
                v = Visite.objects.only('visiteur_id').get(pk=visite_id)
                personne_id = v.visiteur_id
            except Visite.DoesNotExist:
                pass

        # La personne concernée est obligatoire
        if not personne_id:
            messages.error(request, 'La personne concernée par l\'incident est obligatoire. '
                           'Recherchez une personne par nom, prénom, NIP ou numéro de pièce.')
            return render(request, 'incidents/ajouter.html', {**_base_ctx(), 'visite_preset': visite_preset})

        inc = Incident.objects.create(
            titre=titre,
            type_incident=type_incident,
            motif=request.POST.get('motif', '').strip() or None,
            date_incident=request.POST.get('date_incident', '').strip() or None,
            visite_id=visite_id,
            personne_id=personne_id,
            gravite=request.POST.get('gravite', 'MOYENNE'),
            created_by=request.user,
        )
        HistoriqueAction.objects.create(utilisateur=request.user, action='AJOUT', entite='Incident', entite_id=inc.pk,
                                        details=f'Incident créé : {titre} ({inc.get_gravite_display()})')
        nom_visiteur = ''
        if inc.visite and inc.visite.visiteur:
            nom_visiteur = f'{inc.visite.visiteur.prenom} {inc.visite.visiteur.nom}'
        elif inc.personne:
            nom_visiteur = f'{inc.personne.prenom} {inc.personne.nom}'
        Alerte.objects.create(
            type='INCIDENT',
            entite_id=inc.pk,
            message=f"Incident {inc.get_gravite_display()} — {nom_visiteur} — {inc.type_incident.nom}: {titre}" if nom_visiteur else f"Incident {inc.get_gravite_display()} — {inc.type_incident.nom}: {titre}",
        )
        messages.success(request, 'Incident créé avec succès.')
        # --- Règles métier automatiques (Phase 2) ---
        visiteur = inc.personne or (inc.visite.visiteur if inc.visite else None)
        if visiteur:
            if inc.gravite in ('GRAVE', 'CRITIQUE'):
                # Auto-création Liste Noire ACTIF
                from liste_noire.models import ListeNoire, TypeListeNoire
                typ = TypeListeNoire.objects.filter(
                    niveau_risque__in=['HAUT', 'ELEVE', 'GRAVE']
                ).first() or TypeListeNoire.objects.filter(statut='ACTIF').first()
                if typ is None:
                    typ = TypeListeNoire.objects.create(
                        nom='INCIDENT GRAVE',
                        description='Créé automatiquement depuis un incident GRAVE/CRITIQUE',
                        niveau_risque='HAUT',
                        statut='ACTIF',
                        created_by=request.user,
                    )
                ListeNoire.objects.create(
                    type_liste_noire=typ,
                    nom=visiteur.nom,
                    prenom=visiteur.prenom,
                    motif=f"[Auto] Incident #{inc.pk}: {titre}",
                    piece_identite=visiteur.piece_identite,
                    numero_piece=visiteur.numero_piece,
                    numero_nip=visiteur.numero_nip,
                    date_debut=timezone.now(),
                    statut='ACTIF',
                    created_by=request.user,
                )
            elif inc.gravite in ('FAIBLE', 'MOYENNE'):
                # Drapeau d'avertissement (vigilance accrue)
                visiteur.flag_avertissement = True
                visiteur.save(update_fields=['flag_avertissement'])
        return redirect('liste_incidents')
    ctx = _base_ctx()
    ctx['visite_preset'] = visite_preset
    if visite_preset:
        from visites.models import Visite
        try:
            v = Visite.objects.select_related('visiteur').get(pk=visite_preset)
            ctx['visite_preset_info'] = {
                'personne_id': v.visiteur_id,
                'personne_nom': f"{v.visiteur.prenom} {v.visiteur.nom}",
            }
        except Visite.DoesNotExist:
            pass
    # Support ?personne=XX pour préremplir depuis la liste des visiteurs
    personne_preset = request.GET.get('personne') or None
    if personne_preset and not ctx.get('visite_preset_info'):
        from visites.models import Visiteur
        try:
            p = Visiteur.objects.get(pk=personne_preset)
            ctx['visite_preset_info'] = {
                'personne_id': p.pk,
                'personne_nom': f"{p.prenom} {p.nom}",
            }
        except Visiteur.DoesNotExist:
            pass
    return render(request, 'incidents/ajouter.html', ctx)


@login_required
def detail_incident(request, pk):
    item = get_object_or_404(
        Incident.objects.select_related(
            'type_incident', 'visite__visiteur', 'personne', 'created_by', 'updated_by'
        ),
        pk=pk
    )
    historique = HistoriqueAction.objects.filter(
        entite='Incident', entite_id=item.pk
    ).order_by('-created_at')[:10]
    # Liste Noire associée
    visiteur = item.personne or (item.visite.visiteur if item.visite else None)
    liste_noire_entries = []
    if visiteur and visiteur.numero_nip:
        from liste_noire.models import ListeNoire
        liste_noire_entries = ListeNoire.objects.filter(
            numero_nip=visiteur.numero_nip
        ).order_by('-date_debut')
    return render(request, 'incidents/detail.html', {
        'item': item, 'historique': historique, 'liste_noire_entries': liste_noire_entries,
        **_base_ctx(),
    })


@login_required
def modifier_incident(request, pk):
    item = get_object_or_404(Incident, pk=pk)
    if request.method == 'POST':
        type_incident_pk = request.POST.get('type_incident', '').strip()
        titre = request.POST.get('titre', '').strip()
        if not titre:
            messages.error(request, 'Le titre / objet de l\'incident est requis.')
            return render(request, 'incidents/modifier.html', {'item': item, **_base_ctx()})
        if not type_incident_pk:
            messages.error(request, 'Le type d\'incident est requis.')
            return render(request, 'incidents/modifier.html', {'item': item, **_base_ctx()})
        try:
            type_incident = TypeIncident.objects.get(pk=type_incident_pk, actif=True)
        except TypeIncident.DoesNotExist:
            messages.error(request, 'Le type d\'incident sélectionné n\'est pas valide.')
            return render(request, 'incidents/modifier.html', {'item': item, **_base_ctx()})

        old_gravite = item.gravite
        old_statut = item.statut
        new_gravite = request.POST.get('gravite', 'MOYENNE')
        new_statut = request.POST.get('statut', 'OUVERT')
        justification = request.POST.get('justification', '').strip()

        # Si gravité ou statut change → justification obligatoire
        gravite_changed = old_gravite != new_gravite
        statut_changed = old_statut != new_statut
        if (gravite_changed or statut_changed) and not justification:
            messages.error(request, 'Une justification est obligatoire pour modifier la gravité ou le statut.')
            return render(request, 'incidents/modifier.html', {'item': item, **_base_ctx()})

        item.titre = titre
        item.type_incident = type_incident
        item.motif = request.POST.get('motif', '').strip() or None
        item.date_incident = request.POST.get('date_incident', '').strip() or None
        item.visite_id = request.POST.get('visite') or None
        item.personne_id = request.POST.get('personne') or None
        item.gravite = new_gravite
        item.statut = new_statut
        item.justification = justification or None
        item.updated_by = request.user
        item.save()

        # Piste d'audit détaillée
        changes = []
        if gravite_changed:
            changes.append(f'Gravité : {old_gravite} → {new_gravite}')
        if statut_changed:
            changes.append(f'Statut : {old_statut} → {new_statut}')
        if justification:
            changes.append(f'Justification : {justification}')
        HistoriqueAction.objects.create(
            utilisateur=request.user, action='MODIFICATION', entite='Incident', entite_id=item.pk,
            details=f'Incident modifié : {titre} | {" | ".join(changes)}'
        )

        # Désactivation automatique de la ListeNoire si requalification
        visiteur = item.personne or (item.visite.visiteur if item.visite else None)
        deactivate_ln = request.POST.get('deactivate_liste_noire') == 'on'
        if deactivate_ln and visiteur and visiteur.numero_nip:
            from liste_noire.models import ListeNoire
            ln_entries = ListeNoire.objects.filter(
                numero_nip=visiteur.numero_nip, statut='ACTIF'
            )
            for ln in ln_entries:
                ln.statut = 'INACTIF'
                ln.date_fin = timezone.now()
                ln.save(update_fields=['statut', 'date_fin'])
                HistoriqueAction.objects.create(
                    utilisateur=request.user, action='DESACTIVATION', entite='ListeNoire',
                    entite_id=ln.pk,
                    details=f'Désactivé suite à requalification de l\'incident #{item.pk} : {justification}'
                )
            if ln_entries.exists():
                messages.success(request, f'{ln_entries.count()} entrée(s) Liste Noire désactivée(s).')

        # Si classé sans suite → désactiver la ListeNoire automatiquement
        if new_statut == 'CLASSE_SANS_SUITE' and visiteur and visiteur.numero_nip:
            from liste_noire.models import ListeNoire
            ln_auto = ListeNoire.objects.filter(
                numero_nip=visiteur.numero_nip, statut='ACTIF'
            )
            for ln in ln_auto:
                ln.statut = 'INACTIF'
                ln.date_fin = timezone.now()
                ln.save(update_fields=['statut', 'date_fin'])
                HistoriqueAction.objects.create(
                    utilisateur=request.user, action='DESACTIVATION', entite='ListeNoire',
                    entite_id=ln.pk,
                    details=f'Désactivé automatiquement car incident #{item.pk} classé sans suite : {justification}'
                )
            if ln_auto.exists():
                messages.success(request, f'{ln_auto.count()} entrée(s) Liste Noire désactivée(s) automatiquement (classement sans suite).')

        messages.success(request, 'Incident modifié avec succès.')
        return redirect('detail_incident', pk=item.pk)
    return render(request, 'incidents/modifier.html', {'item': item, **_base_ctx()})


@login_required
def supprimer_incident(request, pk):
    item = get_object_or_404(Incident, pk=pk)
    if request.method == 'POST':
        item.delete()
        HistoriqueAction.objects.create(utilisateur=request.user, action='SUPPRESSION', entite='Incident', entite_id=item.pk)
        messages.success(request, 'Incident supprimé avec succès.')
        return redirect('liste_incidents')
    return render(request, 'incidents/detail.html', {'item': item, 'confirm_delete': True})



@login_required
def fermer_incident(request, pk):
    item = get_object_or_404(Incident, pk=pk)
    if request.method == 'POST':
        item.statut = 'RESOLU'
        item.updated_by = request.user
        item.save()
        HistoriqueAction.objects.create(utilisateur=request.user, action='MODIFICATION', entite='Incident', entite_id=item.pk,
                                        details='Incident résolu')
        messages.success(request, 'Incident résolu avec succès.')
    return redirect('liste_incidents')


@login_required
def export_pdf_incidents(request):
    items = Incident.objects.select_related(
        'type_incident', 'visite__visiteur', 'personne'
    ).order_by('-created_at')
    headers = ['N°', 'Titre', 'Type', 'Gravité', 'Personne', 'Statut', 'Date']
    rows = [[i + 1, inc.titre, inc.type_incident.nom if inc.type_incident else '-', inc.get_gravite_display(),
             str(inc.visite.visiteur) if inc.visite and inc.visite.visiteur else (str(inc.personne) if inc.personne else '-'),
             inc.get_statut_display(),
             inc.date_incident.strftime('%d/%m/%Y %H:%M') if inc.date_incident else '-']
            for i, inc in enumerate(items)]
    return _export_pdf(rows, headers, 'Liste des incidents', 'incidents', [0.5, 2, 1.5, 1, 2, 1, 1.5])


@login_required
def export_excel_incidents(request):
    items = Incident.objects.select_related(
        'type_incident', 'visite__visiteur', 'personne'
    ).order_by('-created_at')
    headers = ['N°', 'Titre', 'Type', 'Gravité', 'Personne', 'Statut', 'Date']
    rows = [[i + 1, inc.titre, inc.type_incident.nom if inc.type_incident else '-', inc.get_gravite_display(),
             str(inc.visite.visiteur) if inc.visite and inc.visite.visiteur else (str(inc.personne) if inc.personne else ''),
             inc.get_statut_display(),
             inc.date_incident.strftime('%d/%m/%Y %H:%M') if inc.date_incident else '']
            for i, inc in enumerate(items)]
    return _export_excel(rows, headers, 'Incidents', 'incidents')


# ─── Types d'incident (CRUD) ────────────────────────────────────────────────


@login_required
@permission_required('incidents.view_typeincident', raise_exception=True)
def liste_types_incident(request):
    query = request.GET.get('q', '').strip()
    items = TypeIncident.objects.all()
    if query:
        items = items.filter(
            Q(nom__icontains=query) | Q(description__icontains=query)
        )
    items = items.order_by('ordre', 'nom')
    paginator = Paginator(items, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    page_links = paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1)
    return render(request, 'incidents/types/liste.html', {
        'page_obj': page_obj,
        'page_links': page_links,
        'query': query,
        'gravite_choices': GRAVITE_CHOICES,
    })


@login_required
@permission_required('incidents.add_typeincident', raise_exception=True)
def ajouter_type_incident(request):
    if request.method == 'POST':
        nom = request.POST.get('nom', '').strip()
        if not nom:
            messages.error(request, "Le nom du type d'incident est requis.")
            return render(request, 'incidents/types/ajouter.html', {
                'gravite_choices': GRAVITE_CHOICES,
            })
        if TypeIncident.objects.filter(nom__iexact=nom).exists():
            messages.error(request, "Ce nom de type d'incident existe déjà.")
            return render(request, 'incidents/types/ajouter.html', {
                'gravite_choices': GRAVITE_CHOICES,
            })
        obj = TypeIncident.objects.create(
            nom=nom,
            description=request.POST.get('description', '').strip() or None,
            gravite_defaut=request.POST.get('gravite_defaut', 'MOYENNE'),
            actif=request.POST.get('actif') == 'on',
        )
        HistoriqueAction.objects.create(
            utilisateur=request.user, action='AJOUT', entite='TypeIncident',
            entite_id=obj.pk,
            details=f"Type d'incident créé : {obj.nom} (gravité par défaut : {obj.get_gravite_defaut_display()})"
        )
        messages.success(request, "Type d'incident créé avec succès.")
        return redirect('liste_types_incident')
    return render(request, 'incidents/types/ajouter.html', {
        'gravite_choices': GRAVITE_CHOICES,
    })


@login_required
@permission_required('incidents.change_typeincident', raise_exception=True)
def modifier_type_incident(request, pk):
    item = get_object_or_404(TypeIncident, pk=pk)
    if request.method == 'POST':
        nom = request.POST.get('nom', '').strip()
        if not nom:
            messages.error(request, "Le nom du type d'incident est requis.")
            return render(request, 'incidents/types/modifier.html', {
                'item': item, 'gravite_choices': GRAVITE_CHOICES,
            })
        if TypeIncident.objects.filter(nom__iexact=nom).exclude(pk=item.pk).exists():
            messages.error(request, "Ce nom de type d'incident existe déjà.")
            return render(request, 'incidents/types/modifier.html', {
                'item': item, 'gravite_choices': GRAVITE_CHOICES,
            })
        old_nom = item.nom
        item.nom = nom
        item.description = request.POST.get('description', '').strip() or None
        item.gravite_defaut = request.POST.get('gravite_defaut', 'MOYENNE')
        item.actif = request.POST.get('actif') == 'on'
        item.save()
        HistoriqueAction.objects.create(
            utilisateur=request.user, action='MODIFICATION', entite='TypeIncident',
            entite_id=item.pk,
            details=f"Type d'incident modifié : {old_nom} → {item.nom} (gravité : {item.get_gravite_defaut_display()})"
        )
        messages.success(request, "Type d'incident modifié avec succès.")
        return redirect('liste_types_incident')
    return render(request, 'incidents/types/modifier.html', {
        'item': item, 'gravite_choices': GRAVITE_CHOICES,
    })


@login_required
@permission_required('incidents.delete_typeincident', raise_exception=True)
def supprimer_type_incident(request, pk):
    item = get_object_or_404(TypeIncident, pk=pk)
    if request.method == 'POST':
        # Vérifier si des incidents utilisent ce type
        if Incident.objects.filter(type_incident=item).exists():
            messages.error(
                request,
                "Impossible de supprimer ce type d'incident car il est utilisé par des incidents."
            )
            return redirect('liste_types_incident')
        nom = item.nom
        item.delete()
        HistoriqueAction.objects.create(
            utilisateur=request.user, action='SUPPRESSION', entite='TypeIncident',
            entite_id=pk,
            details=f"Type d'incident supprimé : {nom}"
        )
        messages.success(request, "Type d'incident supprimé avec succès.")
        return redirect('liste_types_incident')
    # GET non autorisé
    return redirect('liste_types_incident')


@login_required
@permission_required('incidents.view_detectiondecision', raise_exception=True)
def liste_decisions(request):
    qs = DetectionDecision.objects.all().select_related('agent', 'visite')
    # Filtres
    decision_filter = request.GET.get('decision', '').strip()
    type_filter = request.GET.get('type_detection', '').strip()
    q = request.GET.get('q', '').strip()

    if decision_filter:
        qs = qs.filter(decision=decision_filter)
    if type_filter:
        qs = qs.filter(type_detection=type_filter)
    if q:
        qs = qs.filter(
            Q(visiteur_nom__icontains=q) |
            Q(visiteur_prenom__icontains=q) |
            Q(visiteur_nip__icontains=q) |
            Q(visiteur_piece__icontains=q)
        )

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))

    # Types uniques pour le filtre (déjà vus dans les données)
    types_disponibles = DetectionDecision.objects.values_list('type_detection', flat=True).distinct().order_by('type_detection')

    return render(request, 'incidents/decisions/liste.html', {
        'page_obj': page,
        'query': q,
        'decision_filter': decision_filter,
        'type_filter': type_filter,
        'types_disponibles': types_disponibles,
        'decision_choices': DECISION_CHOICES,
    })
