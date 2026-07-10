import os
import sys
import random
import uuid
from datetime import datetime, timedelta, time, date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from visites.models import TypeVisite, Visiteur, Visite
from entreprise.models import PorteEntree, Personnel

# ─── Configuration ───────────────────────────────────────────────────────────
NB_VISITEURS = 2000       # nombre de visiteurs uniques
NB_VISITES = 100_000      # nombre total de visites
BATCH_SIZE = 5000         # taille des lots bulk_create
SKIP_VALIDATION = True    # contourne la validation django (creneaux, etc.)
STATUTS = ['EN_COURS', 'TERMINE', 'EXCEDE']
STATUTS_WEIGHTS = [0.05, 0.80, 0.15]  # 5% en cours, 80% terminées, 15% excédées

# ─── Prénoms & noms burkinabè / ouest-africains ─────────────────────────────
PRENOMS_H = [
    'Adama', 'Abdoulaye', 'Boris', 'Boureima', 'Christophe', 'Daouda',
    'Drissa', 'Fousseini', 'Hassane', 'Hyacinthe', 'Idrissa', 'Issa',
    'Issouf', 'Ibrahim', 'Jacob', 'Karim', 'Lassina', 'Mamadou',
    'Mathieu', 'Mohamed', 'Moïse', 'Moussa', 'Nestor', 'Ousmane',
    'Parfait', 'Rachid', 'Roland', 'Salfo', 'Seydou', 'Souleymane',
    'Théophile', 'Wendlasida', 'Wilfried', 'Windé', 'Yacouba', 'Zacharie',
]
PRENOMS_F = [
    'Adèle', 'Aïcha', 'Aminata', 'Awa', 'Bénédicte', 'Céline',
    'Edwige', 'Esther', 'Fatoumata', 'Georgette', 'Halima', 'Hélène',
    'Inès', 'Irène', 'Jacqueline', 'Josiane', 'Kadiatou', 'Laetitia',
    'Lydie', 'Mariam', 'Martine', 'Mireille', 'Nadège', 'Nafissatou',
    'Patricia', 'Paulette', 'Rachida', 'Ramatou', 'Rokiatou', 'Rosalie',
    'Safiatou', 'Salamata', 'Salimata', 'Sylvie', 'Viviane', 'Zalissa',
]
NOMS = [
    'BARRY', 'COMPAORE', 'DAHO', 'DIALLO', 'DICKO', 'DIENDÉRÉ',
    'DRABO', 'GNANOU', 'GUEL', 'GUIRO', 'ILBOUDO', 'KABORE',
    'KAFANDO', 'KAM', 'KAMBOU', 'KANAZOE', 'KIEMA', 'KINDO',
    'KONATÉ', 'KONE', 'KOULIBALY', 'LEKOA', 'LENGANE', 'LOMPO',
    'MEDAH', 'NAON', 'NÉBIÉ', 'NIKIEMA', 'NITIEMA', 'OUATTARA',
    'OUBA', 'OUEDRAOGO', 'PALM', 'PASSERÉ', 'PODA', 'ROUAMBA',
    'SAKANDE', 'SAMA', 'SANKARA', 'SANOU', 'SAWADOGO', 'SEDGHO',
    'SERME', 'SOMÉ', 'SORGHO', 'TALL', 'TAPSOBA', 'TARNAGDA',
    'TIENDREBEOGO', 'TIENTORE', 'TRAORE', 'WANDAOGO', 'YAMEOGO',
    'YANOGO', 'YARO', 'YE', 'YONLI', 'ZABSONRÉ', 'ZONGO',
    'ZONGO', 'ZONOU', 'ZOUNDI', 'ZOURE',
]

# ─── Fonctions utilitaires ───────────────────────────────────────────────────

def generer_telephone():
    """Génère un numéro de téléphone burkinabè (+226 XX XX XX XX)"""
    return f"+226 {random.randint(60, 79)} {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)}"

def generer_email(nom, prenom):
    domaines = ['gmail.com', 'yahoo.fr', 'outlook.com', 'ikamail.bf', 'faso.net', 'orange.bf', 'afribone.bf']
    return f"{prenom.lower()}.{nom.lower()}{random.randint(1,999)}@{random.choice(domaines)}"

def generer_date_naissance():
    an = random.randint(1965, 2005)
    m = random.randint(1, 12)
    j = random.randint(1, 28)
    return f"{j:02d}/{m:02d}/{an}"

def generer_piece_identite():
    types = ['CNIB', 'PASSPORT']
    t = random.choice(types)
    num = ''.join(random.choices('0123456789', k=9))
    return f"{t}_{num}"

def generer_adresse():
    secteurs = [
        'Ouaga 2000', 'Zone du Bois', 'Dassasgho', 'Patte d\'Oie',
        'Tanghin', 'Cissin', 'Gounghin', 'Zogona', 'Tampouy',
        'Karpala', 'Pissy', 'Sigl-Noghin', 'Wemtenga', 'Baskuy',
    ]
    return f"{random.randint(1, 500)} Av. {random.choice(secteurs)}, Ouagadougou"

def generer_date_visite(debut, fin):
    """Génère une date aléatoire entre debut et fin"""
    delta = (fin - debut).days
    d = debut + timedelta(days=random.randint(0, delta))
    return d

def generer_heure():
    """Génère une heure aléatoire entre 7h et 17h"""
    h = random.randint(7, 16)
    m = random.randint(0, 59)
    return time(h, m)


def creer_visiteurs(nb, admin_user):
    """Crée `nb` visiteurs et les retourne dans une liste"""
    visiteurs = []
    used = set()

    for i in range(nb):
        genre = random.choice(['Homme', 'Femme'])
        prenom = random.choice(PRENOMS_H if genre == 'Homme' else PRENOMS_F)
        nom = random.choice(NOMS)
        key = f"{nom}_{prenom}"
        while key in used:
            prenom = random.choice(PRENOMS_H if genre == 'Homme' else PRENOMS_F)
            nom = random.choice(NOMS)
            key = f"{nom}_{prenom}"
        used.add(key)

        vis = Visiteur(
            uuid=uuid.uuid4(),
            nom=nom,
            prenom=prenom,
            genre=genre,
            date_naissance=generer_date_naissance(),
            lieu_naissance=f"{random.choice(['Ouagadougou', 'Bobo-Dioulasso', 'Koudougou', 'Banfora', 'Ouahigouya'])}",
            nationalite=random.choice(['Burkinabè', 'Burkinabè', 'Burkinabè', 'Ivoirienne', 'Malienne', 'Nigérienne', 'Togolaise']),
            profession=random.choice(['Agent commercial', 'Ingénieur', 'Technicien', 'Comptable', 'Médecin',
                                       'Enseignant', 'Avocat', 'Consultant', 'Journaliste', 'Étudiant',
                                       'Artisan', 'Commerçant', 'Fonctionnaire', 'Chef d\'entreprise']),
            adresse=generer_adresse(),
            email=generer_email(nom, prenom),
            telephone=generer_telephone(),
            piece_identite=generer_piece_identite(),
            numero_piece=''.join(random.choices('0123456789ABCDEF', k=12)),
            statut='ACTIF',
            created_by=admin_user,
        )
        visiteurs.append(vis)

    # Bulk insert par lots
    total = len(visiteurs)
    for start in range(0, total, BATCH_SIZE):
        batch = visiteurs[start:start + BATCH_SIZE]
        Visiteur.objects.bulk_create(batch, ignore_conflicts=True)
        print(f"  ✓ Visiteurs {start+1}..{min(start+BATCH_SIZE, total)}/{total}")

    return list(Visiteur.objects.filter(statut='ACTIF').order_by('?'))


def creer_visites(visiteurs, types_visite, portes, personnels, admin_user):
    """Crée 100 000 visites en bulk_create"""
    now = timezone.now()
    date_fin = now - timedelta(days=1)
    date_debut = now - timedelta(days=365)  # 1 an de données

    visites = []
    total = NB_VISITES

    print(f"\n  Génération de {total:,} visites...")
    for i in range(total):
        visiteur = random.choice(visiteurs)
        type_v = random.choice(types_visite)
        porte = random.choice(portes)
        personnel = random.choice(personnels) if random.random() < 0.7 else None
        statut = random.choices(STATUTS, weights=STATUTS_WEIGHTS, k=1)[0]

        # Date de visite
        d = generer_date_visite(date_debut, date_fin)
        heure_arr = generer_heure()

        # Départ prévu (type_visite.duree_max_minutes ou 60 par défaut)
        duree = type_v.duree_max_minutes or 60
        heures_depart = heure_arr.hour + (heure_arr.minute + duree) // 60
        minutes_depart = (heure_arr.minute + duree) % 60
        if heures_depart >= 24:
            heures_depart = 23
            minutes_depart = 59

        h_depart = time(min(heures_depart, 23), minutes_depart)

        # Date/heure de départ réel (pour TERMINE ou EXCEDE)
        date_dep = None
        heure_dep = None
        if statut in ['TERMINE', 'EXCEDE']:
            date_dep = d
            heure_arr_min = heure_arr.hour * 60 + heure_arr.minute
            dep_min = heure_arr_min + int(duree * random.uniform(0.5, 1.8))
            h_d = min(dep_min // 60, 23)
            m_d = dep_min % 60
            heure_dep = time(h_d, m_d)

        vis = Visite(
            uuid=uuid.uuid4(),
            type_visite=type_v,
            visiteur=visiteur,
            genre=visiteur.genre,
            porte_entree=porte,
            personnel=personnel,
            date_visite=d,
            heure_arrivee=heure_arr,
            date_depart_prevue=d,
            heure_depart_prevue=h_depart,
            date_depart=date_dep,
            heure_depart=heure_dep,
            date_expiration=d + timedelta(days=1),
            numero_badge=f"BADGE-{random.randint(1000, 9999)}",
            motif=random.choice([
                'Réunion d\'affaires', 'Rendez-vous client', 'Livraison de matériel',
                'Entretien technique', 'Visite de courtoisie', 'Dépôt de documents',
                'Entretien d\'embauche', 'Maintenance équipement', 'Consultation',
                'Formation', 'Audit', 'Visite médicale',
            ]),
            observations=random.choice(['', '', '', '', 'Visiteur ponctuel', 'A pris du retard',
                                         'Accompagné par le chef de service', 'Badge rendu']),
            statut=statut,
            created_by=admin_user,
        )
        visites.append(vis)

        if len(visites) >= BATCH_SIZE:
            _bulk_visites(visites, total)
            visites = []

    # Dernier lot
    if visites:
        _bulk_visites(visites, total)


def _bulk_visites(visites, total):
    """Insère un lot de visites sans validation"""
    for v in visites:
        v.clean = lambda: None  # Désactive la validation
    Visite.objects.bulk_create(visites, ignore_conflicts=True)
    count = Visite.objects.count()
    pct = count / total * 100 if total else 0
    print(f"  ✓ {count:,} / {total:,} visites ({pct:.0f}%)")


# ─── MAIN ────────────────────────────────────────────────────────────────────
def run():
    start_time = datetime.now()
    print(f"Début : {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Objectif : {NB_VISITES:,} visites avec {NB_VISITEURS:,} visiteurs")

    # 1. Récupérer l'admin
    admin = get_user_model().objects.filter(is_superuser=True).first()
    if not admin:
        print("ERREUR : Aucun super-utilisateur trouvé. Lance seeddata.py d'abord.")
        sys.exit(1)
    print(f"\n✓ Admin : {admin.username}")

    # 2. Récupérer les références existantes
    types_visite = list(TypeVisite.objects.filter(statut='ACTIF'))
    portes = list(PorteEntree.objects.filter(statut='ACTIF'))
    personnels = list(Personnel.objects.filter(statut='ACTIF'))

    print(f"✓ Types de visite : {len(types_visite)}")
    print(f"✓ Portes d'entrée : {len(portes)}")
    print(f"✓ Personnel : {len(personnels)}")

    if not types_visite or not portes:
        print("ERREUR : Types de visite ou portes d'entrée manquants. Lance seeddata.py d'abord.")
        sys.exit(1)

    # 3. Créer les visiteurs
    print(f"\n--- Création de {NB_VISITEURS:,} visiteurs ---")
    visiteurs = creer_visiteurs(NB_VISITEURS, admin)
    print(f"✓ Total visiteurs en base : {len(visiteurs)}")

    # 4. Créer les visites
    print(f"\n--- Création de {NB_VISITES:,} visites ---")
    creer_visites(visiteurs, types_visite, portes, personnels, admin)

    # 5. Résultat final
    final_count = Visite.objects.count()
    vis_count = Visiteur.objects.count()
    elapsed = datetime.now() - start_time
    print(f"\n{'='*50}")
    print(f"RÉSULTAT FINAL")
    print(f"{'='*50}")
    print(f"  Visiteurs : {vis_count:,}")
    print(f"  Visites   : {final_count:,}")
    print(f"  Temps     : {elapsed}")
    print(f"{'='*50}")


if __name__ == '__main__':
    run()
