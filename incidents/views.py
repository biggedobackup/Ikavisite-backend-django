from io import BytesIO
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
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
from .models import Incident, DetectionIncident, TYPE_INCIDENT_CHOICES
from utilisateurs.models import HistoriqueAction
from visites.models import Visite


def _base_ctx():
    return {
        'visites': Visite.objects.select_related('visiteur')[:100],
        'type_incident_choices': TYPE_INCIDENT_CHOICES,
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
        'visite__visiteur'
    )
    if query:
        items = items.filter(
            Q(type_incident__icontains=query) | Q(motif__icontains=query) |
            Q(visite__visiteur__nom__icontains=query) | Q(visite__visiteur__prenom__icontains=query)
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
def ajouter_incident(request):
    if request.method == 'POST':
        type_incident = request.POST.get('type_incident', '').strip()
        valid_types = [c[0] for c in TYPE_INCIDENT_CHOICES]
        if not type_incident or type_incident not in valid_types:
            messages.error(request, 'Le type d\'incident est requis.')
            return render(request, 'incidents/ajouter.html', _base_ctx())
        inc = Incident.objects.create(
            type_incident=type_incident,
            motif=request.POST.get('motif', '').strip() or None,
            date_incident=request.POST.get('date_incident', '').strip() or None,
            visite_id=request.POST.get('visite') or None,
            gravite=request.POST.get('gravite', 'MOYENNE'),
            statut=request.POST.get('statut', 'OUVERT'),
            created_by=request.user,
        )
        HistoriqueAction.objects.create(utilisateur=request.user, action='AJOUT', entite='Incident', entite_id=inc.pk)
        nom_visiteur = ''
        if inc.visite and inc.visite.visiteur:
            nom_visiteur = f'{inc.visite.visiteur.prenom} {inc.visite.visiteur.nom}'
        Alerte.objects.create(
            type='INCIDENT',
            entite_id=inc.pk,
            message=f"Incident — {nom_visiteur} — {inc.get_type_incident_display()} ({inc.gravite})" if nom_visiteur else f"Incident — {inc.get_type_incident_display()} ({inc.gravite})",
        )
        messages.success(request, 'Incident créé avec succès.')
        return redirect('liste_incidents')
    return render(request, 'incidents/ajouter.html', _base_ctx())


@login_required
def detail_incident(request, pk):
    item = get_object_or_404(
        Incident.objects.select_related(
            'visite__visiteur', 'created_by', 'updated_by'
        ),
        pk=pk
    )
    return render(request, 'incidents/detail.html', {'item': item})


@login_required
def modifier_incident(request, pk):
    item = get_object_or_404(Incident, pk=pk)
    if request.method == 'POST':
        type_incident = request.POST.get('type_incident', '').strip()
        valid_types = [c[0] for c in TYPE_INCIDENT_CHOICES]
        if not type_incident or type_incident not in valid_types:
            messages.error(request, 'Le type d\'incident est requis.')
            return render(request, 'incidents/modifier.html', {'item': item, **_base_ctx()})
        item.type_incident = type_incident
        item.motif = request.POST.get('motif', '').strip() or None
        item.date_incident = request.POST.get('date_incident', '').strip() or None
        item.visite_id = request.POST.get('visite') or None
        item.gravite = request.POST.get('gravite', 'MOYENNE')
        item.statut = request.POST.get('statut', 'OUVERT')
        item.updated_by = request.user
        item.save()
        HistoriqueAction.objects.create(utilisateur=request.user, action='MODIFICATION', entite='Incident', entite_id=item.pk)
        messages.success(request, 'Incident modifié avec succès.')
        return redirect('liste_incidents')
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
def detection_incidents(request):
    items = DetectionIncident.objects.select_related(
        'incident__visite__visiteur'
    ).order_by('-created_at')
    paginator = Paginator(items, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    page_links = paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1)
    return render(request, 'incidents/detection.html', {
        'page_obj': page_obj, 'page_links': page_links,
    })


@login_required
def fermer_incident(request, pk):
    item = get_object_or_404(Incident, pk=pk)
    if request.method == 'POST':
        item.statut = 'FERME'
        item.updated_by = request.user
        item.save()
        HistoriqueAction.objects.create(utilisateur=request.user, action='MODIFICATION', entite='Incident', entite_id=item.pk)
        messages.success(request, 'Incident fermé avec succès.')
    return redirect('detection_incidents')


@login_required
def export_pdf_incidents(request):
    items = Incident.objects.select_related(
        'visite__visiteur'
    ).order_by('-created_at')
    headers = ['N°', 'Type', 'Gravité', 'Visiteur', 'Statut', 'Date']
    rows = [[i + 1, inc.type_incident, inc.gravite,
             str(inc.visite.visiteur) if inc.visite and inc.visite.visiteur else '-',
             inc.statut,
             inc.date_incident.strftime('%d/%m/%Y %H:%M') if inc.date_incident else '-']
            for i, inc in enumerate(items)]
    return _export_pdf(rows, headers, 'Liste des incidents', 'incidents', [0.5, 2, 1, 2, 1, 1.5])


@login_required
def export_excel_incidents(request):
    items = Incident.objects.select_related(
        'visite__visiteur'
    ).order_by('-created_at')
    headers = ['N°', 'Type', 'Gravité', 'Visiteur', 'Statut', 'Date']
    rows = [[i + 1, inc.type_incident, inc.gravite,
             str(inc.visite.visiteur) if inc.visite and inc.visite.visiteur else '',
             inc.statut,
             inc.date_incident.strftime('%d/%m/%Y %H:%M') if inc.date_incident else '']
            for i, inc in enumerate(items)]
    return _export_excel(rows, headers, 'Incidents', 'incidents')
