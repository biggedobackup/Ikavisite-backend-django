from io import BytesIO

from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.conf import settings
from entreprise.models import Departement, PorteEntree
from utilisateurs.models import Utilisateur, HistoriqueAction
from django.contrib.auth.models import Group
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def connexion_view(request):
    if request.user.is_authenticated:
        return redirect('tableau_de_bord')

    if request.method == 'POST':
        identifiant = request.POST.get('username', '').strip() or request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        remember = request.POST.get('remember') == 'on'

        user = authenticate(request, username=identifiant, password=password, email=identifiant)
        if user is not None:
            login(request, user)
            if not remember:
                request.session.set_expiry(0)
            HistoriqueAction.log(request, 'CONNEXION', 'Session', details=f'Utilisateur connecté : {user.get_full_name() or user.username}')
            return redirect('tableau_de_bord')
        else:
            messages.error(request, 'Email ou mot de passe incorrect')

    return render(request, 'connexion.html')


def deconnexion_view(request):
    HistoriqueAction.log(request, 'DECONNEXION', 'Session', details=f'Utilisateur déconnecté : {request.user.get_full_name() or request.user.username}')
    logout(request)
    return redirect('connexion')


@login_required
def profil_view(request):
    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'change_password':
            current = request.POST.get('current_password', '')
            new_pwd = request.POST.get('new_password', '')
            confirm = request.POST.get('confirm_password', '')

            if not request.user.check_password(current):
                messages.error(request, 'Mot de passe actuel incorrect')
            elif len(new_pwd) < 8:
                messages.error(request, 'Le nouveau mot de passe doit contenir au moins 8 caractères')
            elif new_pwd != confirm:
                messages.error(request, 'Les mots de passe ne correspondent pas')
            else:
                request.user.set_password(new_pwd)
                request.user.save()
                messages.success(request, 'Mot de passe modifié avec succès')
                return redirect('connexion')
        else:
            nom = request.POST.get('nom_complet', '').strip()
            tel = request.POST.get('telephone_mobile', '').strip()
            if nom:
                parts = nom.split(' ', 1)
                request.user.first_name = parts[0]
                request.user.last_name = parts[1] if len(parts) > 1 else ''
            if tel:
                request.user.telephone_mobile = tel
            request.user.save()
            messages.success(request, 'Modification effectuée avec succès')

        return redirect('profil')

    return render(request, 'profil.html')


# ─── Gestion des utilisateurs (CRUD) ─────────────────────────────────────

@login_required
def liste_utilisateurs(request):
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('statut', 'TOUS')

    items = Utilisateur.objects.all()

    if query:
        items = items.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )
    if status_filter != 'TOUS':
        items = items.filter(statut=status_filter)

    items = items.order_by('-date_joined')

    paginator = Paginator(items, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    page_links = paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1)

    context = {
        'page_obj': page_obj,
        'page_links': page_links,
        'query': query,
        'status_filter': status_filter,
    }
    return render(request, 'utilisateurs/liste.html', context)


@login_required
def ajouter_utilisateur(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()

        _ctx = {'portes': PorteEntree.objects.filter(statut='ACTIF'), 'groupes': Group.objects.all().order_by('name')}
        if not username or not email or not password:
            messages.error(request, 'Nom d\'utilisateur, email et mot de passe sont requis.')
            return render(request, 'utilisateurs/ajouter.html', _ctx)

        if Utilisateur.objects.filter(username=username).exists():
            messages.error(request, 'Ce nom d\'utilisateur existe déjà.')
            return render(request, 'utilisateurs/ajouter.html', _ctx)

        if Utilisateur.objects.filter(email=email).exists():
            messages.error(request, 'Cet email est déjà utilisé.')
            return render(request, 'utilisateurs/ajouter.html', _ctx)

        porte_id = request.POST.get('porte_entree', '').strip()
        porte_entree = None
        if porte_id:
            try:
                porte_entree = PorteEntree.objects.get(pk=int(porte_id))
            except (ValueError, PorteEntree.DoesNotExist):
                pass

        user = Utilisateur.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            telephone_mobile=request.POST.get('telephone_mobile', '').strip() or None,
            porte_entree=porte_entree,
            statut=request.POST.get('statut', 'ACTIF'),
        )
        group_id = request.POST.get('group', '').strip()
        if group_id:
            try:
                grp = Group.objects.get(pk=int(group_id))
                user.groups.set([grp])
            except (ValueError, Group.DoesNotExist):
                pass
        # is_active = ACTIF dans le statut
        user.is_active = (user.statut == 'ACTIF')
        user.save(update_fields=['is_active'])
        HistoriqueAction.log(request, 'AJOUT', 'Utilisateur', entite_id=user.pk, details=f'Utilisateur créé : {user.get_full_name() or user.username}')
        messages.success(request, 'Ajout effectué avec succès.')
        return redirect('liste_utilisateurs')

    portes = PorteEntree.objects.filter(statut='ACTIF')
    groupes = Group.objects.all().order_by('name')
    return render(request, 'utilisateurs/ajouter.html', {'portes': portes, 'groupes': groupes})


@login_required
def detail_utilisateur(request, pk):
    item = get_object_or_404(Utilisateur, pk=pk)
    return render(request, 'utilisateurs/detail.html', {'item': item})


@login_required
def modifier_utilisateur(request, pk):
    item = get_object_or_404(Utilisateur, pk=pk)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()

        _ctx = {'item': item, 'portes': PorteEntree.objects.filter(statut='ACTIF'), 'groupes': Group.objects.all().order_by('name')}
        if not username or not email:
            messages.error(request, 'Nom d\'utilisateur et email sont requis.')
            return render(request, 'utilisateurs/modifier.html', _ctx)

        if Utilisateur.objects.filter(username=username).exclude(pk=pk).exists():
            messages.error(request, 'Ce nom d\'utilisateur existe déjà.')
            return render(request, 'utilisateurs/modifier.html', _ctx)

        if Utilisateur.objects.filter(email=email).exclude(pk=pk).exists():
            messages.error(request, 'Cet email est déjà utilisé.')
            return render(request, 'utilisateurs/modifier.html', _ctx)

        porte_id = request.POST.get('porte_entree', '').strip()
        porte_entree = None
        if porte_id:
            try:
                porte_entree = PorteEntree.objects.get(pk=int(porte_id))
            except (ValueError, PorteEntree.DoesNotExist):
                pass

        item.username = username
        item.email = email
        item.first_name = request.POST.get('first_name', '').strip()
        item.last_name = request.POST.get('last_name', '').strip()
        item.telephone_mobile = request.POST.get('telephone_mobile', '').strip() or None
        item.porte_entree = porte_entree
        item.statut = request.POST.get('statut', 'ACTIF')
        item.is_active = (item.statut == 'ACTIF')
        item.is_staff = False
        item.is_superuser = False

        new_password = request.POST.get('new_password', '')
        if new_password:
            item.set_password(new_password)

        group_id = request.POST.get('group', '').strip()
        if group_id:
            try:
                grp = Group.objects.get(pk=int(group_id))
                item.groups.set([grp])
            except (ValueError, Group.DoesNotExist):
                pass
        else:
            item.groups.clear()
        item.save()
        HistoriqueAction.log(request, 'MODIFICATION', 'Utilisateur', entite_id=item.pk, details=f'Utilisateur modifié : {item.get_full_name() or item.username}')
        messages.success(request, 'Modification effectuée avec succès.')
        return redirect('liste_utilisateurs')

    portes = PorteEntree.objects.filter(statut='ACTIF')
    groupes = Group.objects.all().order_by('name')
    return render(request, 'utilisateurs/modifier.html', {'item': item, 'portes': portes, 'groupes': groupes})


@login_required
def export_pdf_utilisateurs(request):
    items = Utilisateur.objects.all().order_by('-date_joined')

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), title="Utilisateurs",
                            leftMargin=1.5*cm, rightMargin=1.5*cm)
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'],
                                fontSize=9, leading=12, alignment=1)
    elements = []

    elements.append(Paragraph("Utilisateurs", styles['Title']))
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph(f"Généré le {timezone.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 0.5 * cm))

    headers = ['N°', 'Nom', 'Email', 'Statut', 'Staff', 'Superuser', 'Créé le']
    col_ratios = [0.5, 2, 2.5, 1, 1, 1, 1.5]
    available_width = landscape(A4)[0] - 3 * cm
    total_ratio = sum(col_ratios)
    col_widths = [available_width * r / total_ratio for r in col_ratios]

    data = [headers]
    for i, u in enumerate(items, 1):
        data.append([
            Paragraph(str(i), cell_style),
            Paragraph(u.get_full_name() or u.username, cell_style),
            Paragraph(u.email, cell_style),
            Paragraph(u.statut, cell_style),
            Paragraph('Oui' if u.is_staff else 'Non', cell_style),
            Paragraph('Oui' if u.is_superuser else 'Non', cell_style),
            Paragraph(u.date_joined.strftime('%d/%m/%Y %H:%M') if u.date_joined else '-', cell_style),
        ])

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1270b8')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8fafc'), colors.white]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(table)

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="utilisateurs_{timezone.now().strftime("%Y%m%d")}.pdf"'
    return response


@login_required
def export_excel_utilisateurs(request):
    items = Utilisateur.objects.all().order_by('-date_joined')

    wb = Workbook()
    ws = wb.active
    ws.title = "Utilisateurs"
    ws.append(['N°', 'Nom', 'Email', 'Téléphone', 'Statut', 'Staff', 'Superuser', 'Créé le'])

    for i, u in enumerate(items, 1):
        ws.append([i, u.get_full_name() or u.username, u.email, u.telephone_mobile or '', u.statut, 'Oui' if u.is_staff else 'Non', 'Oui' if u.is_superuser else 'Non', u.date_joined.strftime('%d/%m/%Y %H:%M') if u.date_joined else ''])

    ws.column_dimensions['A'].width = 6
    ws.column_dimensions['B'].width = 28
    ws.column_dimensions['C'].width = 30
    ws.column_dimensions['D'].width = 18
    ws.column_dimensions['E'].width = 10
    ws.column_dimensions['F'].width = 10
    ws.column_dimensions['G'].width = 12
    ws.column_dimensions['H'].width = 18

    header_fill = PatternFill(start_color='1270b8', end_color='1270b8', fill_type='solid')
    header_font = Font(bold=True, color='ffffff', size=11)
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="utilisateurs_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    return response


@login_required
def supprimer_utilisateur(request, pk):
    item = get_object_or_404(Utilisateur, pk=pk)

    if item.is_superuser:
        messages.error(request, 'Impossible de supprimer un super administrateur.')
        return redirect('detail_utilisateur', pk=pk)

    if request.method == 'POST':
        HistoriqueAction.log(request, 'SUPPRESSION', 'Utilisateur', entite_id=item.pk, details=f'Utilisateur supprimé : {item.get_full_name() or item.username}')
        from django.contrib.auth import get_user_model
        User = get_user_model()
        item.delete()
        messages.success(request, 'Suppression effectuée avec succès.')
        return redirect('liste_utilisateurs')

    return render(request, 'utilisateurs/detail.html', {'item': item, 'confirm_delete': True})


# ─── Historique des actions ────────────────────────────────────────────────

@login_required
def liste_historique_actions(request):
    query = request.GET.get('q', '').strip()
    action_filter = request.GET.get('action', '')
    entite_filter = request.GET.get('entite', '')
    start_date = request.GET.get('start', '')
    end_date = request.GET.get('end', '')

    items = HistoriqueAction.objects.select_related('utilisateur')
    if query:
        items = items.filter(
            Q(action__icontains=query) | Q(entite__icontains=query) |
            Q(details__icontains=query) | Q(ip_address__icontains=query) |
            Q(utilisateur__first_name__icontains=query) |
            Q(utilisateur__last_name__icontains=query) |
            Q(utilisateur__username__icontains=query)
        )
    if action_filter:
        items = items.filter(action__icontains=action_filter)
    if entite_filter:
        items = items.filter(entite__icontains=entite_filter)
    if start_date:
        items = items.filter(created_at__date__gte=start_date)
    if end_date:
        items = items.filter(created_at__date__lte=end_date)

    items = items.order_by('-created_at')

    paginator = Paginator(items, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    page_links = paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1)

    # Cache en mémoire les listes de filtres (très peu changeantes)
    actions_list = list(HistoriqueAction.objects.values_list('action', flat=True).distinct().order_by('action'))
    entites_list = list(HistoriqueAction.objects.values_list('entite', flat=True).distinct().order_by('entite'))

    return render(request, 'historique_actions.html', {
        'page_obj': page_obj,
        'page_links': page_links,
        'query': query,
        'action_filter': action_filter,
        'entite_filter': entite_filter,
        'start_date': start_date,
        'end_date': end_date,
        'actions_list': actions_list,
        'entites_list': entites_list,
    })
