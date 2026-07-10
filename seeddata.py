import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import time


def run():
    admin, _ = get_user_model().objects.get_or_create(
        username='admin',
        defaults={'is_superuser': True, 'is_staff': True},
    )
    if not admin.password or admin.password.startswith('!'):
        admin.set_password('admin123')
        admin.save()

    from entreprise.models import ParametreEntreprise
    ParametreEntreprise.objects.get_or_create(
        nom_entreprise='IKA SOLUTION',
        defaults={
            'description': 'Société de sécurité et de gardiennage basée à Ouagadougou, spécialisée dans la gestion de flux visiteurs et la sécurité des infrastructures.',
            'email': 'contact@ikasolution.bf',
            'telephone': '+226 25 00 00 00',
            'site_web': 'https://ikasolution.bf',
            'pays': 'Burkina Faso',
            'ville': 'Ouagadougou',
            'adresse': 'Avenue Kwame Nkrumah, 01 BP 0001 Ouagadougou 01',
            'secteur_activite': 'Sécurité et gestion des accès',
            'duree_moyenne_visites': 60,
            'nombre_employes': 50,
            'statut': 'ACTIF',
        }
    )

    portes_data = [
        ('Entrée principale', 'Accès principal du siège'),
        ('Entrée personnel', 'Accès réservé au personnel'),
        ('Entrée visiteurs', 'Accès pour les visiteurs externes'),
        ('Entrée véhicules', 'Accès véhicules et livraisons'),
        ('Entrée service', 'Accès technique et maintenance'),
    ]
    from entreprise.models import PorteEntree
    for titre, desc in portes_data:
        PorteEntree.objects.get_or_create(titre=titre, defaults={'emplacement': desc})

    depts_data = [
        'Direction générale', 'Ressources humaines', 'Sécurité',
        'Comptabilité / Finance', 'Commercial / Marketing',
        'Technique / Maintenance', 'Accueil / Réception',
    ]
    from entreprise.models import Departement
    dept_objects = {}
    for nom in depts_data:
        dept, _ = Departement.objects.get_or_create(nom=nom)
        dept_objects[nom] = dept

    personnel_data = [
        ('OUEDRAOGO', 'Mamadou', 'Directeur général', 'Direction générale'),
        ('TRAORE', 'Aminata', 'Directrice RH', 'Ressources humaines'),
        ('SAWADOGO', 'Issouf', 'Chef de la sécurité', 'Sécurité'),
        ('KABORE', 'Fatoumata', 'Comptable', 'Comptabilité / Finance'),
        ('DIALLO', 'Moussa', 'Commercial', 'Commercial / Marketing'),
        ('ZONGO', 'Adama', 'Technicien', 'Technique / Maintenance'),
        ('BARRY', 'Rokiatou', 'Réceptionniste', 'Accueil / Réception'),
        ('TAPSOBA', 'Hyacinthe', 'Agent de sécurité', 'Sécurité'),
        ('SANOU', 'Aïchatou', 'Assistante RH', 'Ressources humaines'),
        ('SANKARA', 'Wendlasida', 'Agent de sécurité', 'Sécurité'),
        ('OUATTARA', 'Salamata', 'Chef comptable', 'Comptabilité / Finance'),
        ('COMPAORE', 'Boris', 'Responsable marketing', 'Commercial / Marketing'),
        ('YAMEOGO', 'Esther', 'Agent d\'accueil', 'Accueil / Réception'),
        ('ILBOUDO', 'Christophe', 'Technicien maintenance', 'Technique / Maintenance'),
        ('NIKIEMA', 'Martine', 'Agent de sécurité', 'Sécurité'),
    ]
    from entreprise.models import Personnel
    for nom, prenom, fonction, dept in personnel_data:
        Personnel.objects.get_or_create(
            nom=nom, prenom=prenom,
            defaults={
                'fonction': fonction,
                'departement': dept_objects[dept],
                'statut': 'ACTIF',
            }
        )

    from entreprise.models import CreneauSemaine
    cr_data = [
        ('Lundi', time(7, 30), time(16, 0)),
        ('Mardi', time(7, 30), time(16, 0)),
        ('Mercredi', time(7, 30), time(16, 0)),
        ('Jeudi', time(7, 30), time(16, 0)),
        ('Vendredi', time(7, 30), time(16, 0)),
        ('Samedi', time(7, 30), time(12, 30)),
    ]
    for jour, debut, fin in cr_data:
        CreneauSemaine.objects.get_or_create(
            jour_semaine=jour, heure_debut=debut, heure_fin=fin,
        )

    types_ln_data = [
        ('Vol', 'Personne impliquée dans un vol', 'ELEVEE'),
        ('Escroquerie', 'Personne impliquée dans une escroquerie', 'CRITIQUE'),
        ('Violence', 'Personne impliquée dans des actes de violence', 'CRITIQUE'),
        ('Intrusion', 'Personne ayant tenté une intrusion non autorisée', 'ELEVEE'),
        ('Comportement suspect', 'Personne au comportement suspect', 'MOYENNE'),
        ('Interdiction administrative', 'Personne sous le coup d\'une interdiction', 'CRITIQUE'),
    ]
    from liste_noire.models import TypeListeNoire
    for nom, desc, risque in types_ln_data:
        TypeListeNoire.objects.get_or_create(
            nom=nom, defaults={'description': desc, 'niveau_risque': risque}
        )

    types_visite_data = [
        ('Visite professionnelle', 'Réunion, rendez-vous ou visite d\'affaires', 120),
        ('Visite personnelle', 'Visite à un membre du personnel', 60),
        ('Livraison', 'Livraison de marchandises ou de fournitures', 45),
        ('Entretien / Maintenance', 'Intervention technique ou maintenance', 90),
        ('Administration', 'Démarche administrative ou documentaire', 60),
    ]
    from visites.models import TypeVisite
    for nom, desc, duree in types_visite_data:
        TypeVisite.objects.get_or_create(
            nom=nom, defaults={'description': desc, 'duree_max_minutes': duree}
        )

    print('Seed data created successfully.')


if __name__ == '__main__':
    run()
