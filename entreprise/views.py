from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import ParametreEntreprise
from utilisateurs.models import HistoriqueAction

WEST_AFRICAN_COUNTRIES = [
    'Bénin', 'Burkina Faso', 'Cap-Vert', "Côte d'Ivoire",
    'Gambie', 'Ghana', 'Guinée', 'Guinée-Bissau',
    'Libéria', 'Mali', 'Mauritanie', 'Niger', 'Nigeria',
    'Sénégal', 'Sierra Leone', 'Togo',
]


@login_required
def entreprise_view(request):
    entreprise = ParametreEntreprise.objects.first()

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'upload_logo':
            if not entreprise:
                messages.error(request, "Veuillez d'abord enregistrer les informations de l'entreprise.")
            elif request.FILES.get('logo'):
                entreprise.logo = request.FILES['logo']
                entreprise.save(update_fields=['logo', 'updated_at'])
                HistoriqueAction.log(request, 'MODIFICATION', 'Entreprise', details='Logo mis à jour')
                messages.success(request, 'Logo mis à jour avec succès.')
            return redirect('entreprise')

        nom = request.POST.get('nom_entreprise', '').strip()
        if not nom:
            messages.error(request, 'Nom entreprise requis.')
            return redirect('entreprise')

        data = {
            'nom_entreprise': nom,
            'description': request.POST.get('description', '').strip() or None,
            'email': request.POST.get('email', '').strip() or None,
            'telephone': request.POST.get('telephone', '').strip() or None,
            'site_web': request.POST.get('site_web', '').strip() or None,
            'pays': request.POST.get('pays', '').strip() or None,
            'ville': request.POST.get('ville', '').strip() or None,
            'adresse': request.POST.get('adresse', '').strip() or None,
            'secteur_activite': request.POST.get('secteur_activite', '').strip() or None,
        }

        duree = request.POST.get('duree_moyenne_visites', '').strip()
        if duree:
            data['duree_moyenne_visites'] = int(duree)

        employes = request.POST.get('nombre_employes', '').strip()
        if employes:
            data['nombre_employes'] = int(employes)

        if entreprise:
            for key, value in data.items():
                setattr(entreprise, key, value)
            entreprise.updated_by = request.user
            entreprise.save()
            HistoriqueAction.log(request, 'MODIFICATION', 'Entreprise', entite_id=entreprise.pk, details=f'Paramètres entreprise modifiés')
            messages.success(request, 'Modification effectuée avec succès.')
        else:
            data['created_by'] = request.user
            ParametreEntreprise.objects.create(**data)
            HistoriqueAction.log(request, 'AJOUT', 'Entreprise', details=f'Paramètres entreprise créés')
            messages.success(request, 'Ajout effectué avec succès.')

        return redirect('entreprise')

    context = {
        'entreprise': entreprise,
        'countries': WEST_AFRICAN_COUNTRIES,
    }
    return render(request, 'entreprise.html', context)
