"""
Seed — Types de visite par défaut
Crée les types de visite de base pour IkaVisite
"""
import sys, os
sys.path.insert(0, '/var/www/ikavisite')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django; django.setup()
from django.db import transaction
from visites.models import TypeVisite

TYPES = [
    {"nom": "Visite Standard",      "duree_max_minutes": 120, "description": "Visite classique pour un rendez-vous professionnel"},
    {"nom": "Visite Express",       "duree_max_minutes": 30,  "description": "Visite rapide pour dépôt ou récupération de documents"},
    {"nom": "Visite Longue Durée",  "duree_max_minutes": 480, "description": "Visite de longue durée pour réunions ou formations"},
    {"nom": "Visite VIP",           "duree_max_minutes": 240, "description": "Visite pour invités spéciaux ou partenaires"},
    {"nom": "Visite Technique",     "duree_max_minutes": 180, "description": "Visite pour maintenance, réparation ou installation"},
]

@transaction.atomic
def seed():
    created = 0
    for data in TYPES:
        _, was_created = TypeVisite.objects.get_or_create(nom=data["nom"], defaults=data)
        if was_created:
            created += 1
            print(f"  ✓ {data['nom']}")
        else:
            print(f"  – {data['nom']} (déjà existant)")
    print(f"\n✅ {created} type(s) de visite créé(s) sur {len(TYPES)}")

if __name__ == "__main__":
    print("🌱 Seed Types de Visite\n")
    seed()
