"""
IKAVISITE — API Entreprise
Django Ninja — CRUD : Portes d'entrée, Départements, Personnels, Créneaux semaine.
Routes : /api/entreprise/*
"""
from typing import Optional, List
from datetime import time, datetime
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.pagination import paginate, PageNumberPagination
from ninja_jwt.authentication import JWTAuth
from django.core.cache import cache

from .models import ParametreEntreprise, PorteEntree, Departement, Personnel, CreneauSemaine


jwt_auth = JWTAuth()


# ═══════════════════════════════════════════════════════════════════════════════
# SCHÉMAS
# ═══════════════════════════════════════════════════════════════════════════════

# ─── PorteEntree ──────────────────────────────────────────────────────────────

class PorteEntreeOut(Schema):
    id: int
    uuid: str
    titre: str
    emplacement: Optional[str] = None
    description: Optional[str] = None
    statut: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @staticmethod
    def resolve_uuid(obj): return str(obj.uuid)
    @staticmethod
    def resolve_created_at(obj): return obj.created_at.isoformat() if obj.created_at else None
    @staticmethod
    def resolve_updated_at(obj): return obj.updated_at.isoformat() if obj.updated_at else None

class PorteEntreeCreateIn(Schema):
    titre: str
    emplacement: Optional[str] = None
    description: Optional[str] = None
    statut: str = "ACTIF"

class PorteEntreeUpdateIn(Schema):
    titre: Optional[str] = None
    emplacement: Optional[str] = None
    description: Optional[str] = None
    statut: Optional[str] = None


# ─── Departement ──────────────────────────────────────────────────────────────

class DepartementOut(Schema):
    id: int
    uuid: str
    nom: str
    description: Optional[str] = None
    statut: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @staticmethod
    def resolve_uuid(obj): return str(obj.uuid)
    @staticmethod
    def resolve_created_at(obj): return obj.created_at.isoformat() if obj.created_at else None
    @staticmethod
    def resolve_updated_at(obj): return obj.updated_at.isoformat() if obj.updated_at else None

class DepartementCreateIn(Schema):
    nom: str
    description: Optional[str] = None
    statut: str = "ACTIF"

class DepartementUpdateIn(Schema):
    nom: Optional[str] = None
    description: Optional[str] = None
    statut: Optional[str] = None


# ─── Personnel ────────────────────────────────────────────────────────────────

class PersonnelOut(Schema):
    id: int
    uuid: str
    nom: str
    prenom: str
    fonction: Optional[str] = None
    email: Optional[str] = None
    telephone: Optional[str] = None
    departement_id: Optional[int] = None
    departement_nom: Optional[str] = None
    statut: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @staticmethod
    def resolve_uuid(obj): return str(obj.uuid)
    @staticmethod
    def resolve_departement_nom(obj): return obj.departement.nom if obj.departement else None
    @staticmethod
    def resolve_created_at(obj): return obj.created_at.isoformat() if obj.created_at else None
    @staticmethod
    def resolve_updated_at(obj): return obj.updated_at.isoformat() if obj.updated_at else None

class PersonnelCreateIn(Schema):
    nom: str
    prenom: str
    fonction: Optional[str] = None
    email: Optional[str] = None
    telephone: Optional[str] = None
    departement_id: Optional[int] = None
    statut: str = "ACTIF"

class PersonnelUpdateIn(Schema):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    fonction: Optional[str] = None
    email: Optional[str] = None
    telephone: Optional[str] = None
    departement_id: Optional[int] = None
    statut: Optional[str] = None


# ─── CreneauSemaine ───────────────────────────────────────────────────────────

class CreneauSemaineOut(Schema):
    id: int
    uuid: str
    jour_semaine: str
    heure_debut: str
    heure_fin: str
    statut: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @staticmethod
    def resolve_uuid(obj): return str(obj.uuid)
    @staticmethod
    def resolve_heure_debut(obj): return obj.heure_debut.strftime('%H:%M') if obj.heure_debut else ""
    @staticmethod
    def resolve_heure_fin(obj): return obj.heure_fin.strftime('%H:%M') if obj.heure_fin else ""
    @staticmethod
    def resolve_created_at(obj): return obj.created_at.isoformat() if obj.created_at else None
    @staticmethod
    def resolve_updated_at(obj): return obj.updated_at.isoformat() if obj.updated_at else None

class CreneauSemaineCreateIn(Schema):
    jour_semaine: str
    heure_debut: str     # HH:MM
    heure_fin: str       # HH:MM
    statut: str = "ACTIF"

class CreneauSemaineUpdateIn(Schema):
    jour_semaine: Optional[str] = None
    heure_debut: Optional[str] = None
    heure_fin: Optional[str] = None
    statut: Optional[str] = None


# ─── Message simple ───────────────────────────────────────────────────────────

class MessageOut(Schema):
    success: bool
    message: str


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _check_perm(request, perm: str) -> None:
    if not (request.user.is_superuser or request.user.has_perm(perm)):
        raise HttpError(403, "Permission refusée")


def _parse_time(v: str) -> time:
    """Parse HH:MM → time."""
    for fmt in ('%H:%M', '%H:%M:%S'):
        try:
            return datetime.strptime(v, fmt).time()
        except ValueError:
            continue
    raise HttpError(400, f"Format d'heure invalide : {v} (attendu HH:MM)")


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

router = Router(tags=["Entreprise"], auth=jwt_auth)


# ═══════════════════════════════════════════════════════════════════════════════
# DONNÉES DE RÉFÉRENCE  /api/entreprise/references/
# ═══════════════════════════════════════════════════════════════════════════════

# Nationalités prédéfinies (identique à visites/views.py)
NATIONALITE_OPTIONS = [
    'Afghane', 'Albanaise', 'Algérienne', 'Allemande', 'Américaine', 'Andorrane',
    'Angolaise', 'Argentine', 'Arménienne', 'Australienne', 'Autrichienne',
    'Bahamienne', 'Bahreïnienne', 'Bangladeshie', 'Barbadienne', 'Belge',
    'Bélizienne', 'Béninoise', 'Bhoutanaise', 'Biélorusse', 'Birmane',
    'Bolivienne', 'Bosnienne', 'Botswanaise', 'Brésilienne', 'Britannique',
    'Brunéienne', 'Bulgare', 'Burkinabè', 'Burundaise',
    'Cambodgienne', 'Camerounaise', 'Canadienne', 'Cap-verdienne',
    'Centrafricaine', 'Chilienne', 'Chinoise', 'Chypriote', 'Colombienne',
    'Comorienne', 'Congolaise', 'Coréenne', 'Costaricaine', 'Croate', 'Cubaine',
    'Danoise', 'Djiboutienne', 'Dominicaine', 'Dominiquaise',
    'Égyptienne', 'Émiratie', 'Équatorienne', 'Érythréenne', 'Espagnole',
    'Estonienne', 'Eswatinienne', 'Éthiopienne',
    'Fidjienne', 'Finlandaise', 'Française',
    'Gabonaise', 'Gambienne', 'Géorgienne', 'Ghanéenne', 'Grecque',
    'Grenadienne', 'Guatémaltèque', 'Guinéenne', 'Bissau-Guinéenne', 'Guyanienne',
    'Haïtienne', 'Hondurienne', 'Hongroise',
    'Indienne', 'Indonésienne', 'Irakienne', 'Iranienne', 'Irlandaise',
    'Islandaise', 'Israélienne', 'Italienne', 'Ivoirienne',
    'Jamaïcaine', 'Japonaise', 'Jordanienne',
    'Kazakhstanaise', 'Kényane', 'Kirghize', 'Kiribatienne', 'Koweïtienne',
    'Laotienne', 'Lesothane', 'Lettone', 'Libanaise', 'Libérienne', 'Libyenne',
    'Liechtensteinoise', 'Lituanienne', 'Luxembourgeoise',
    'Macédonienne', 'Malgache', 'Malaisienne', 'Malawienne', 'Maldivienne',
    'Malienne', 'Maltaise', 'Marocaine', 'Marshallaise', 'Mauritanienne',
    'Mauricienne', 'Mexicaine', 'Micronésienne', 'Moldave', 'Monégasque',
    'Mongole', 'Monténégrine', 'Mozambicaine',
    'Namibienne', 'Nauruane', 'Néerlandaise', 'Néo-zélandaise', 'Népalaise',
    'Nicaraguayenne', 'Nigérienne', 'Nigériane', 'Nord-coréenne', 'Norvégienne',
    'Omanaise', 'Ougandaise', 'Ouzbèke',
    'Pakistanaise', 'Palaosienne', 'Palestinienne', 'Panaméenne',
    'Papouane-néo-guinéenne', 'Paraguayenne', 'Péruvienne', 'Philippine',
    'Polonaise', 'Portugaise',
    'Qatarie', 'Roumaine', 'Russe', 'Rwandaise',
    'Saint-lucienne', 'Saint-marinaise', 'Salomonaise', 'Salvadorienne',
    'Samoane', 'Santoméenne', 'Saoudienne', 'Sénégalaise', 'Serbe',
    'Seychelloise', 'Sierra-léonaise', 'Singapourienne', 'Slovaque',
    'Slovène', 'Somalienne', 'Soudanaise', 'Sri-lankaise', 'Sud-africaine',
    'Suédoise', 'Suisse', 'Surinamaise', 'Syrienne',
    'Tadjike', 'Tanzanienne', 'Tchadienne', 'Tchèque', 'Thaïlandaise',
    'Timoraise', 'Togolaise', 'Tongienne', 'Trinidadienne', 'Tunisienne',
    'Turkmène', 'Turque', 'Tuvaluane',
    'Ukrainienne', 'Uruguayenne',
    'Vanuatuane', 'Vaticane', 'Vénézuélienne', 'Vietnamienne',
    'Yéménite', 'Zaïroise', 'Zambienne', 'Zimbabwéenne',
]

PAYS_OPTIONS = [
    'Afghanistan', 'Afrique du Sud', 'Albanie', 'Algérie', 'Allemagne', 'Angola',
    'Arabie Saoudite', 'Argentine', 'Australie', 'Autriche', 'Belgique', 'Bénin',
    'Brésil', 'Burkina Faso', 'Burundi', 'Cambodge', 'Cameroun', 'Canada',
    'Cap-Vert', 'Chine', 'Colombie', 'Comores', 'Corée du Sud', 'Costa Rica',
    "Côte d'Ivoire", 'Croatie', 'Danemark', 'Djibouti', 'Égypte', 'Émirats arabes unis',
    'Espagne', 'Estonie', 'États-Unis', 'Éthiopie', 'Finlande', 'France', 'Gabon',
    'Gambie', 'Ghana', 'Grèce', 'Guinée', 'Guinée-Bissau', 'Guinée équatoriale',
    'Haïti', 'Hongrie', 'Inde', 'Indonésie', 'Iran', 'Iraq', 'Irlande', 'Islande',
    'Israël', 'Italie', 'Japon', 'Jordanie', 'Kenya', 'Koweït', 'Laos', 'Lesotho',
    'Lettonie', 'Liban', 'Liberia', 'Libye', 'Liechtenstein', 'Lituanie', 'Luxembourg',
    'Madagascar', 'Malaisie', 'Malawi', 'Mali', 'Malte', 'Maroc', 'Maurice',
    'Mauritanie', 'Mexique', 'Monaco', 'Mongolie', 'Monténégro', 'Mozambique',
    'Namibie', 'Népal', 'Nicaragua', 'Niger', 'Nigeria', 'Norvège', 'Nouvelle-Zélande',
    'Ouganda', 'Ouzbékistan', 'Pakistan', 'Panama', 'Paraguay', 'Pays-Bas', 'Pérou',
    'Philippines', 'Pologne', 'Portugal', 'Qatar', 'République centrafricaine',
    'République démocratique du Congo', 'République du Congo', 'Roumanie',
    'Royaume-Uni', 'Russie', 'Rwanda', 'Sénégal', 'Serbie', 'Seychelles',
    'Sierra Leone', 'Singapour', 'Slovaquie', 'Slovénie', 'Somalie', 'Soudan',
    'Soudan du Sud', 'Sri Lanka', 'Suède', 'Suisse', 'Suriname', 'Syrie',
    'Tadjikistan', 'Tanzanie', 'Tchad', 'République tchèque', 'Thaïlande', 'Togo',
    'Tunisie', 'Turkménistan', 'Turquie', 'Ukraine', 'Uruguay', 'Vatican',
    'Venezuela', 'Viêt Nam', 'Yémen', 'Zambie', 'Zimbabwe',
]


class ReferencesOut(Schema):
    nationalites: List[str]
    pays: List[str]
    types_piece: List[str]
    duree_moyenne_visites: Optional[int] = 60


@router.get("/references/", response=ReferencesOut, tags=["Références"])
def api_references(request):
    """Données de référence pour les formulaires (nationalités, pays, types de pièce)."""
    cached = cache.get('entreprise_references')
    if cached:
        return cached
    entreprise = ParametreEntreprise.objects.first()
    duree = entreprise.duree_moyenne_visites if (entreprise and entreprise.duree_moyenne_visites) else 60
    result = {
        'nationalites': NATIONALITE_OPTIONS,
        'pays': PAYS_OPTIONS,
        'types_piece': ['CNI', 'PASSEPORT', 'PERMIS', 'AUTRE'],
        'duree_moyenne_visites': duree,
    }
    cache.set('entreprise_references', result, 3600)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# PORTES D'ENTRÉE  /api/entreprise/portes/*
# ═══════════════════════════════════════════════════════════════════════════════

portes_router = Router(tags=["Portes d'entrée"], auth=jwt_auth)


@portes_router.get("/", response=List[PorteEntreeOut])
def api_list_portes(request):
    """Liste des portes d'entrée."""
    cached = cache.get('portes_entree_list')
    if cached:
        return cached
    qs = PorteEntree.objects.all().order_by('titre')
    cache.set('portes_entree_list', list(qs), 1800)
    return qs


@portes_router.post("/", response=PorteEntreeOut)
def api_create_porte(request, payload: PorteEntreeCreateIn):
    """Créer une porte d'entrée."""
    _check_perm(request, "entreprise.add_porteentree")
    obj = PorteEntree.objects.create(
        titre=payload.titre,
        emplacement=payload.emplacement,
        description=payload.description,
        statut=payload.statut,
        created_by=request.user,
    )
    return obj


@portes_router.get("/{porte_id}", response=PorteEntreeOut)
def api_get_porte(request, porte_id: int):
    """Détail d'une porte d'entrée."""
    try:
        return PorteEntree.objects.get(id=porte_id)
    except PorteEntree.DoesNotExist:
        raise HttpError(404, "Porte d'entrée introuvable")


@portes_router.put("/{porte_id}", response=PorteEntreeOut)
def api_update_porte(request, porte_id: int, payload: PorteEntreeUpdateIn):
    """Modifier une porte d'entrée."""
    _check_perm(request, "entreprise.change_porteentree")
    try:
        obj = PorteEntree.objects.get(id=porte_id)
    except PorteEntree.DoesNotExist:
        raise HttpError(404, "Porte d'entrée introuvable")
    if payload.titre is not None:
        obj.titre = payload.titre
    if payload.emplacement is not None:
        obj.emplacement = payload.emplacement
    if payload.description is not None:
        obj.description = payload.description
    if payload.statut is not None:
        obj.statut = payload.statut
    obj.updated_by = request.user
    obj.save()
    return obj


@portes_router.delete("/{porte_id}", response=MessageOut)
def api_delete_porte(request, porte_id: int):
    """Supprimer une porte d'entrée."""
    _check_perm(request, "entreprise.delete_porteentree")
    try:
        obj = PorteEntree.objects.get(id=porte_id)
    except PorteEntree.DoesNotExist:
        raise HttpError(404, "Porte d'entrée introuvable")
    obj.delete()
    return {"success": True, "message": "Porte d'entrée supprimée"}


# ═══════════════════════════════════════════════════════════════════════════════
# DÉPARTEMENTS  /api/entreprise/departements/*
# ═══════════════════════════════════════════════════════════════════════════════

depts_router = Router(tags=["Départements"], auth=jwt_auth)


@depts_router.get("/", response=List[DepartementOut])
def api_list_departements(request):
    """Liste des départements."""
    cached = cache.get('departements_list')
    if cached:
        return cached
    qs = Departement.objects.all().order_by('nom')
    cache.set('departements_list', list(qs), 1800)
    return qs


@depts_router.post("/", response=DepartementOut)
def api_create_departement(request, payload: DepartementCreateIn):
    """Créer un département."""
    _check_perm(request, "entreprise.add_departement")
    if Departement.objects.filter(nom=payload.nom).exists():
        raise HttpError(400, "Ce département existe déjà")
    obj = Departement.objects.create(
        nom=payload.nom,
        description=payload.description,
        statut=payload.statut,
        created_by=request.user,
    )
    return obj


@depts_router.get("/{dept_id}", response=DepartementOut)
def api_get_departement(request, dept_id: int):
    """Détail d'un département."""
    try:
        return Departement.objects.get(id=dept_id)
    except Departement.DoesNotExist:
        raise HttpError(404, "Département introuvable")


@depts_router.put("/{dept_id}", response=DepartementOut)
def api_update_departement(request, dept_id: int, payload: DepartementUpdateIn):
    """Modifier un département."""
    _check_perm(request, "entreprise.change_departement")
    try:
        obj = Departement.objects.get(id=dept_id)
    except Departement.DoesNotExist:
        raise HttpError(404, "Département introuvable")
    if payload.nom is not None:
        if Departement.objects.filter(nom=payload.nom).exclude(id=dept_id).exists():
            raise HttpError(400, "Ce nom existe déjà")
        obj.nom = payload.nom
    if payload.description is not None:
        obj.description = payload.description
    if payload.statut is not None:
        obj.statut = payload.statut
    obj.updated_by = request.user
    obj.save()
    return obj


@depts_router.delete("/{dept_id}", response=MessageOut)
def api_delete_departement(request, dept_id: int):
    """Supprimer un département."""
    _check_perm(request, "entreprise.delete_departement")
    try:
        obj = Departement.objects.get(id=dept_id)
    except Departement.DoesNotExist:
        raise HttpError(404, "Département introuvable")
    obj.delete()
    return {"success": True, "message": "Département supprimé"}


# ═══════════════════════════════════════════════════════════════════════════════
# PERSONNEL  /api/entreprise/personnel/*
# ═══════════════════════════════════════════════════════════════════════════════

personnel_router = Router(tags=["Personnel"], auth=jwt_auth)


@personnel_router.get("/", response=List[PersonnelOut])
def api_list_personnel(request):
    """Liste du personnel."""
    return Personnel.objects.select_related('departement').all().order_by('nom', 'prenom')


@personnel_router.post("/", response=PersonnelOut)
def api_create_personnel(request, payload: PersonnelCreateIn):
    """Créer un employé."""
    _check_perm(request, "entreprise.add_personnel")
    if payload.departement_id:
        if not Departement.objects.filter(id=payload.departement_id).exists():
            raise HttpError(404, "Département introuvable")
    obj = Personnel.objects.create(
        nom=payload.nom,
        prenom=payload.prenom,
        fonction=payload.fonction,
        email=payload.email,
        telephone=payload.telephone,
        departement_id=payload.departement_id,
        statut=payload.statut,
        created_by=request.user,
    )
    return obj


@personnel_router.get("/{personnel_id}", response=PersonnelOut)
def api_get_personnel(request, personnel_id: int):
    """Détail d'un employé."""
    try:
        return Personnel.objects.select_related('departement').get(id=personnel_id)
    except Personnel.DoesNotExist:
        raise HttpError(404, "Employé introuvable")


@personnel_router.put("/{personnel_id}", response=PersonnelOut)
def api_update_personnel(request, personnel_id: int, payload: PersonnelUpdateIn):
    """Modifier un employé."""
    _check_perm(request, "entreprise.change_personnel")
    try:
        obj = Personnel.objects.select_related('departement').get(id=personnel_id)
    except Personnel.DoesNotExist:
        raise HttpError(404, "Employé introuvable")
    if payload.nom is not None:
        obj.nom = payload.nom
    if payload.prenom is not None:
        obj.prenom = payload.prenom
    if payload.fonction is not None:
        obj.fonction = payload.fonction
    if payload.email is not None:
        obj.email = payload.email
    if payload.telephone is not None:
        obj.telephone = payload.telephone
    if payload.departement_id is not None:
        if not Departement.objects.filter(id=payload.departement_id).exists():
            raise HttpError(404, "Département introuvable")
        obj.departement_id = payload.departement_id
    if payload.statut is not None:
        obj.statut = payload.statut
    obj.updated_by = request.user
    obj.save()
    return obj


@personnel_router.delete("/{personnel_id}", response=MessageOut)
def api_delete_personnel(request, personnel_id: int):
    """Supprimer un employé."""
    _check_perm(request, "entreprise.delete_personnel")
    try:
        obj = Personnel.objects.get(id=personnel_id)
    except Personnel.DoesNotExist:
        raise HttpError(404, "Employé introuvable")
    obj.delete()
    return {"success": True, "message": "Employé supprimé"}


# ═══════════════════════════════════════════════════════════════════════════════
# CRÉNEAUX SEMAINE  /api/entreprise/creneaux/*
# ═══════════════════════════════════════════════════════════════════════════════

creneaux_router = Router(tags=["Créneaux semaine"], auth=jwt_auth)


@creneaux_router.get("/", response=List[CreneauSemaineOut])
def api_list_creneaux(request):
    """Liste des créneaux de semaine."""
    return CreneauSemaine.objects.all().order_by('jour_semaine', 'heure_debut')


@creneaux_router.post("/", response=CreneauSemaineOut)
def api_create_creneau(request, payload: CreneauSemaineCreateIn):
    """Créer un créneau de semaine."""
    _check_perm(request, "entreprise.add_creneausemaine")
    obj = CreneauSemaine.objects.create(
        jour_semaine=payload.jour_semaine,
        heure_debut=_parse_time(payload.heure_debut),
        heure_fin=_parse_time(payload.heure_fin),
        statut=payload.statut,
        created_by=request.user,
    )
    return obj


@creneaux_router.get("/{creneau_id}", response=CreneauSemaineOut)
def api_get_creneau(request, creneau_id: int):
    """Détail d'un créneau."""
    try:
        return CreneauSemaine.objects.get(id=creneau_id)
    except CreneauSemaine.DoesNotExist:
        raise HttpError(404, "Créneau introuvable")


@creneaux_router.put("/{creneau_id}", response=CreneauSemaineOut)
def api_update_creneau(request, creneau_id: int, payload: CreneauSemaineUpdateIn):
    """Modifier un créneau."""
    _check_perm(request, "entreprise.change_creneausemaine")
    try:
        obj = CreneauSemaine.objects.get(id=creneau_id)
    except CreneauSemaine.DoesNotExist:
        raise HttpError(404, "Créneau introuvable")
    if payload.jour_semaine is not None:
        obj.jour_semaine = payload.jour_semaine
    if payload.heure_debut is not None:
        obj.heure_debut = _parse_time(payload.heure_debut)
    if payload.heure_fin is not None:
        obj.heure_fin = _parse_time(payload.heure_fin)
    if payload.statut is not None:
        obj.statut = payload.statut
    obj.updated_by = request.user
    obj.save()
    return obj


@creneaux_router.delete("/{creneau_id}", response=MessageOut)
def api_delete_creneau(request, creneau_id: int):
    """Supprimer un créneau."""
    _check_perm(request, "entreprise.delete_creneausemaine")
    try:
        obj = CreneauSemaine.objects.get(id=creneau_id)
    except CreneauSemaine.DoesNotExist:
        raise HttpError(404, "Créneau introuvable")
    obj.delete()
    return {"success": True, "message": "Créneau supprimé"}
