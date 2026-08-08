"""
Script de nettoyage complet :
Supprime toutes les visites, listes noires, incidents et objets oubliés
Ordre respecté (enfants avant parents pour éviter les erreurs FK)
"""
import sys
import os

# Chemin Django
sys.path.insert(0, '/var/www/ikavisite')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from django.db import transaction, connection
from django.utils import timezone

# Modèles
from visites.models import Visite, Visiteur, TypeVisite
from liste_noire.models import ListeNoire, TypeListeNoire, DetectionListeNoire
from incidents.models import Incident
from objets_oublies.models import ObjetOublie, DetectionObjetOublie
from alertes_et_notifications.models import Alerte
from utilisateurs.models import HistoriqueAction


def compter():
    """Compte les enregistrements avant suppression"""
    return {
        'Visites': Visite.objects.count(),
        'Visiteurs': Visiteur.objects.count(),
        'Types de visite': TypeVisite.objects.count(),
        'Incidents': Incident.objects.count(),
        'Objets oubliés': ObjetOublie.objects.count(),
        'Détections objets oubliés': DetectionObjetOublie.objects.count(),
        'Listes noires': ListeNoire.objects.count(),
        'Types liste noire': TypeListeNoire.objects.count(),
        'Détections liste noire': DetectionListeNoire.objects.count(),
        'Alertes': Alerte.objects.count() if hasattr(Alerte, 'objects') else '?',
        'Historique actions': HistoriqueAction.objects.count(),
    }


def nettoyer():
    with transaction.atomic():
        # 1. Alertes
        print("Suppression des alertes...")
        Alerte.objects.all().delete()
        HistoriqueAction.objects.all().delete()

        # 2. Incident
        print("Suppression des incidents...")
        Incident.objects.all().delete()

        # 3. Détections objets oubliés → Objets oubliés
        print("Suppression des détections d'objets oubliés...")
        DetectionObjetOublie.objects.all().delete()
        print("Suppression des objets oubliés...")
        ObjetOublie.objects.all().delete()

        # 4. Détections liste noire → Liste noire → Type liste noire
        print("Suppression des détections liste noire...")
        DetectionListeNoire.objects.all().delete()
        print("Suppression des listes noires...")
        ListeNoire.objects.all().delete()
        print("Suppression des types de liste noire...")
        TypeListeNoire.objects.all().delete()

        # 5. Visites → Visiteurs → Types visite
        print("Suppression des visites...")
        Visite.objects.all().delete()
        print("Suppression des visiteurs...")
        Visiteur.objects.all().delete()
        print("Suppression des types de visite...")
        TypeVisite.objects.all().delete()


def main():
    print("=" * 60)
    print("🧹 NETTOYAGE COMPLET DE LA BASE IKA VISITE")
    print(f"Date : {timezone.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)

    avant = compter()
    total_avant = sum(v for v in avant.values() if isinstance(v, int))
    print(f"\n📊 Enregistrements trouvés avant suppression : {total_avant}")
    for table, count in avant.items():
        print(f"   • {table} : {count}")

    if total_avant == 0:
        print("\n✅ Rien à supprimer — la base est déjà vide.")
        return

    print(f"\n🗑️  Suppression en cours...\n")
    nettoyer()

    apres = compter()
    total_apres = sum(v for v in apres.values() if isinstance(v, int))
    print(f"\n✅  Nettoyage terminé !")
    print(f"   • Avant : {total_avant} enregistrements")
    print(f"   • Après : {total_apres} enregistrements")
    print(f"   • Supprimés : {total_avant - total_apres}")

    # Vérification finale
    for table, count in apres.items():
        if count > 0:
            print(f"\n⚠️  {table} : {count} enregistrements restants (vérifier manuellement)")


if __name__ == '__main__':
    main()
