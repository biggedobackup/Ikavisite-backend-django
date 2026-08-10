"""
IKAVISITE — API Visites
Django Ninja — CRUD complet pour les visites et types de visite.
Routes : /api/visites/*
"""
import threading
from typing import Optional, List
from datetime import date, time, datetime
import base64
from ninja import Router, Schema, FilterSchema, Field
from ninja.errors import HttpError
from ninja.pagination import paginate, PageNumberPagination
from django.db.models import Q
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.cache import cache
from ninja_jwt.authentication import JWTAuth

from .models import TypeVisite, Visite, Visiteur, VisiteEnCours, VisiteTerminee, VisiteExcedee
from .views import _detect_matches
from incidents.models import Incident
from entreprise.models import PorteEntree, Personnel


jwt_auth = JWTAuth()


# ═══════════════════════════════════════════════════════════════════════════════
# SCHÉMAS
# ═══════════════════════════════════════════════════════════════════════════════

# ─── TypeVisite ───────────────────────────────────────────────────────────────

class TypeVisiteOut(Schema):
    id: int
    uuid: str
    nom: str
    description: Optional[str] = None
    duree_max_minutes: Optional[int] = None
    statut: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @staticmethod
    def resolve_uuid(obj): return str(obj.uuid)
    @staticmethod
    def resolve_created_at(obj): return obj.created_at.isoformat() if obj.created_at else None
    @staticmethod
    def resolve_updated_at(obj): return obj.updated_at.isoformat() if obj.updated_at else None

class TypeVisiteCreateIn(Schema):
    nom: str
    description: Optional[str] = None
    duree_max_minutes: Optional[int] = None
    statut: str = "ACTIF"

class TypeVisiteUpdateIn(Schema):
    nom: Optional[str] = None
    description: Optional[str] = None
    duree_max_minutes: Optional[int] = None
    statut: Optional[str] = None


# ─── Visiteur (résumé) ────────────────────────────────────────────────────────

class VisiteurOut(Schema):
    id: int
    uuid: str
    nom: str
    prenom: str
    genre: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    numero_piece: Optional[str] = None
    numero_nip: Optional[str] = None
    nationalite: Optional[str] = None
    profession: Optional[str] = None
    adresse: Optional[str] = None
    piece_identite: Optional[str] = None
    date_naissance: Optional[str] = None
    lieu_naissance: Optional[str] = None
    pays_delivrance: Optional[str] = None
    date_delivrance: Optional[str] = None
    photo: Optional[str] = None
    document_recto: Optional[str] = None
    document_verso: Optional[str] = None
    statut: str

    @staticmethod
    def resolve_uuid(obj): return str(obj.uuid)
    @staticmethod
    def resolve_photo(obj): return obj.photo.url if obj.photo else None
    @staticmethod
    def resolve_document_recto(obj): return obj.document_recto.url if obj.document_recto else None
    @staticmethod
    def resolve_document_verso(obj): return obj.document_verso.url if obj.document_verso else None


# ─── PorteEntree (résumé) ─────────────────────────────────────────────────────

class PorteEntreeResumeOut(Schema):
    id: int
    titre: str
    emplacement: Optional[str] = None

class PersonnelResumeOut(Schema):
    id: int
    nom: str
    prenom: str
    fonction: Optional[str] = None
    departement: Optional[str] = None
    departement_id: Optional[int] = None

    @staticmethod
    def resolve_departement(obj): return obj.departement.nom if obj.departement else None
    @staticmethod
    def resolve_departement_id(obj): return obj.departement_id


# ─── Visite ───────────────────────────────────────────────────────────────────

class VisiteOut(Schema):
    id: int
    uuid: str
    type_visite: TypeVisiteOut
    type_visite_id: int
    visiteur: VisiteurOut
    visiteur_id: int
    porte_entree: Optional[PorteEntreeResumeOut] = None
    porte_entree_id: Optional[int] = None
    genre: Optional[str] = None
    personnel: Optional[PersonnelResumeOut] = None
    personnel_id: Optional[int] = None
    departement: Optional[str] = None
    departement_id: Optional[int] = None
    date_visite: Optional[str] = None
    heure_arrivee: Optional[str] = None
    date_depart_prevue: Optional[str] = None
    heure_depart_prevue: Optional[str] = None
    date_depart: Optional[str] = None
    date_expiration: Optional[str] = None
    heure_depart: Optional[str] = None
    numero_badge: Optional[str] = None
    motif: Optional[str] = None
    observations: Optional[str] = None
    signature_entree: Optional[str] = None
    signature_sortie: Optional[str] = None
    statut: str
    duree_max_minutes: int = 60
    heure_arrivee_dt: Optional[str] = None
    heure_fin_prevue_dt: Optional[str] = None
    est_excedee: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @staticmethod
    def resolve_uuid(obj): return str(obj.uuid)
    @staticmethod
    def resolve_date_visite(obj): return obj.date_visite.isoformat() if obj.date_visite else None
    @staticmethod
    def resolve_heure_arrivee(obj): return obj.heure_arrivee.strftime('%H:%M') if obj.heure_arrivee else None
    @staticmethod
    def resolve_date_depart_prevue(obj): return obj.date_depart_prevue.isoformat() if obj.date_depart_prevue else None
    @staticmethod
    def resolve_heure_depart_prevue(obj): return obj.heure_depart_prevue.strftime('%H:%M') if obj.heure_depart_prevue else None
    @staticmethod
    def resolve_date_depart(obj): return obj.date_depart.isoformat() if obj.date_depart else None
    @staticmethod
    def resolve_date_expiration(obj): return obj.date_expiration.isoformat() if obj.date_expiration else None
    @staticmethod
    def resolve_heure_depart(obj): return obj.heure_depart.strftime('%H:%M') if obj.heure_depart else None
    @staticmethod
    def resolve_signature_entree(obj): return obj.signature_entree.url if obj.signature_entree else None
    @staticmethod
    def resolve_signature_sortie(obj): return obj.signature_sortie.url if obj.signature_sortie else None
    @staticmethod
    def resolve_created_at(obj): return obj.created_at.isoformat() if obj.created_at else None
    @staticmethod
    def resolve_updated_at(obj): return obj.updated_at.isoformat() if obj.updated_at else None
    @staticmethod
    def resolve_heure_arrivee_dt(obj):
        dt = obj.heure_arrivee_dt
        return dt.isoformat() if dt else None
    @staticmethod
    def resolve_heure_fin_prevue_dt(obj):
        dt = obj.heure_fin_prevue_dt
        return dt.isoformat() if dt else None
    @staticmethod
    def resolve_departement(obj): return obj.departement.nom if obj.departement else None
    @staticmethod
    def resolve_departement_id(obj): return obj.departement_id
    @staticmethod
    def resolve_est_excedee(obj): return obj.est_excedee
    @staticmethod
    def resolve_duree_max_minutes(obj): return obj.duree_max_minutes


# ─── Visite (création) ────────────────────────────────────────────────────────

class VisiteCreateIn(Schema):
    # Visiteur — soit un ID existant, soit les données pour chercher/créer
    visiteur_id: Optional[int] = None
    v_nom: Optional[str] = None
    v_prenom: Optional[str] = None
    v_genre: Optional[str] = None
    v_date_naissance: Optional[str] = None
    v_lieu_naissance: Optional[str] = None
    v_nationalite: Optional[str] = None
    v_profession: Optional[str] = None
    v_telephone: Optional[str] = None
    v_adresse: Optional[str] = None
    v_email: Optional[str] = None
    v_piece_identite: Optional[str] = None
    v_numero_piece: Optional[str] = None
    v_nip: Optional[str] = None
    v_pays_delivrance: Optional[str] = None
    v_date_delivrance: Optional[str] = None
    # Visite
    type_visite_id: int
    porte_entree_id: Optional[int] = None
    personnel_id: Optional[int] = None
    departement_id: Optional[int] = None
    genre: Optional[str] = None
    date_visite: Optional[str] = None          # ISO datetime
    heure_arrivee: Optional[str] = None        # HH:MM
    date_depart_prevue: Optional[str] = None   # YYYY-MM-DD
    heure_depart_prevue: Optional[str] = None  # HH:MM
    date_depart: Optional[str] = None          # YYYY-MM-DD
    date_expiration: Optional[str] = None      # YYYY-MM-DD
    heure_depart: Optional[str] = None         # HH:MM
    numero_badge: Optional[str] = None
    motif: Optional[str] = None
    observations: Optional[str] = None
    signature_entree: Optional[str] = None     # base64 data URI (data:image/png;base64,...)
    signature_sortie: Optional[str] = None     # base64 data URI (data:image/png;base64,...)
    photo_base64: Optional[str] = None         # base64 data URI — photo du visiteur
    document_recto_base64: Optional[str] = None  # base64 data URI — recto pièce d'identité
    document_verso_base64: Optional[str] = None  # base64 data URI — verso pièce d'identité
    statut: str = "EN_COURS"

class VisiteUpdateIn(Schema):
    type_visite_id: Optional[int] = None
    visiteur_id: Optional[int] = None
    porte_entree_id: Optional[int] = None
    personnel_id: Optional[int] = None
    departement_id: Optional[int] = None
    genre: Optional[str] = None
    date_visite: Optional[str] = None
    heure_arrivee: Optional[str] = None
    date_depart_prevue: Optional[str] = None
    heure_depart_prevue: Optional[str] = None
    date_depart: Optional[str] = None
    date_expiration: Optional[str] = None
    heure_depart: Optional[str] = None
    numero_badge: Optional[str] = None
    motif: Optional[str] = None
    observations: Optional[str] = None
    signature_entree: Optional[str] = None     # base64 data URI
    signature_sortie: Optional[str] = None     # base64 data URI
    statut: Optional[str] = None


# ─── Terminer une visite ──────────────────────────────────────────────────────

class TerminerVisiteIn(Schema):
    date_depart: Optional[str] = None          # YYYY-MM-DD
    heure_depart: Optional[str] = None         # HH:MM
    observations: Optional[str] = None
    signature_sortie: Optional[str] = None     # base64 data URI (data:image/png;base64,...)
    incident: Optional[bool] = None            # True = signaler un incident
    incident_gravite: Optional[str] = None     # FAIBLE, MOYENNE, HAUTE, CRITIQUE
    incident_description: Optional[str] = None # Description de l'incident


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


def _get_visite_or_404(visite_id: int) -> Visite:
    try:
        return Visite.objects.select_related(
            'type_visite', 'visiteur', 'porte_entree',
            'personnel__departement',
        ).get(id=visite_id)
    except Visite.DoesNotExist:
        raise HttpError(404, "Visite introuvable")


def _base_visite_qs():
    """QuerySet de base avec select_related pour éviter les N+1."""
    return Visite.objects.select_related(
        'type_visite', 'visiteur', 'porte_entree',
        'personnel__departement',
    )


def _parse_time(v: str) -> Optional[time]:
    if not v:
        return None
    for fmt in ('%H:%M', '%H:%M:%S'):
        try:
            return datetime.strptime(v, fmt).time()
        except ValueError:
            continue
    raise HttpError(400, f"Format d'heure invalide : {v} (attendu HH:MM)")


def _parse_date(v: str) -> Optional[date]:
    if not v:
        return None
    try:
        return datetime.strptime(v, '%Y-%m-%d').date()
    except ValueError:
        raise HttpError(400, f"Format de date invalide : {v} (attendu YYYY-MM-DD)")


def _save_signature_base64(signature_data: Optional[str], prefix: str = 'signature') -> Optional[ContentFile]:
    """Décode une signature en base64 (data URI) et retourne un ContentFile."""
    if not signature_data:
        return None
    try:
        fmt, data = signature_data.split(';base64,')
        ext = fmt.split('/')[-1]
        return ContentFile(base64.b64decode(data), name=f'{prefix}_{timezone.now().timestamp()}.{ext}')
    except (ValueError, TypeError, Exception):
        raise HttpError(400, "Format de signature invalide (attendu: data:image/...;base64,...)")


def _normalize_genre(value: Optional[str]) -> Optional[str]:
    """Normalise le genre : HOMME→Homme, FEMME→Femme, M→Homme, F→Femme."""
    if not value:
        return None
    val = value.strip().upper()
    if val in ('HOMME', 'M', 'MASCULIN', 'MALE'):
        return 'Homme'
    if val in ('FEMME', 'F', 'FEMININ', 'FEMALE'):
        return 'Femme'
    # already properly capitalized
    return value.strip()


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

router = Router(tags=["Visites"], auth=jwt_auth)


# ═══════════════════════════════════════════════════════════════════════════════
# TYPES DE VISITE  /api/visites/types/*
# ═══════════════════════════════════════════════════════════════════════════════

types_router = Router(tags=["Types de visite"], auth=jwt_auth)


@types_router.get("/", response=List[TypeVisiteOut])
def api_list_types(request):
    """Liste des types de visite."""
    cached = cache.get('types_visite_list')
    if cached:
        return cached
    qs = TypeVisite.objects.all().order_by('nom')
    cache.set('types_visite_list', list(qs), 1800)
    return qs


@types_router.post("/", response=TypeVisiteOut)
def api_create_type(request, payload: TypeVisiteCreateIn):
    """Créer un type de visite."""
    _check_perm(request, "visites.add_typevisite")
    if TypeVisite.objects.filter(nom=payload.nom).exists():
        raise HttpError(400, "Ce type de visite existe déjà")
    obj = TypeVisite.objects.create(
        nom=payload.nom,
        description=payload.description,
        duree_max_minutes=payload.duree_max_minutes,
        statut=payload.statut,
        created_by=request.user,
    )
    return obj


@types_router.get("/{type_id}", response=TypeVisiteOut)
def api_get_type(request, type_id: int):
    """Détail d'un type de visite."""
    try:
        return TypeVisite.objects.get(id=type_id)
    except TypeVisite.DoesNotExist:
        raise HttpError(404, "Type de visite introuvable")


@types_router.put("/{type_id}", response=TypeVisiteOut)
def api_update_type(request, type_id: int, payload: TypeVisiteUpdateIn):
    """Modifier un type de visite."""
    _check_perm(request, "visites.change_typevisite")
    try:
        obj = TypeVisite.objects.get(id=type_id)
    except TypeVisite.DoesNotExist:
        raise HttpError(404, "Type de visite introuvable")

    if payload.nom is not None:
        if TypeVisite.objects.filter(nom=payload.nom).exclude(id=type_id).exists():
            raise HttpError(400, "Ce nom existe déjà")
        obj.nom = payload.nom
    if payload.description is not None:
        obj.description = payload.description
    if payload.duree_max_minutes is not None:
        obj.duree_max_minutes = payload.duree_max_minutes
    if payload.statut is not None:
        obj.statut = payload.statut
    obj.updated_by = request.user
    obj.save()
    return obj


@types_router.delete("/{type_id}", response=MessageOut)
def api_delete_type(request, type_id: int):
    """Supprimer un type de visite."""
    _check_perm(request, "visites.delete_typevisite")
    try:
        obj = TypeVisite.objects.get(id=type_id)
    except TypeVisite.DoesNotExist:
        raise HttpError(404, "Type de visite introuvable")
    obj.delete()
    return {"success": True, "message": "Type de visite supprimé"}


# ═══════════════════════════════════════════════════════════════════════════════
# VISITES  /api/visites/*
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/", response=List[VisiteOut])
@paginate(PageNumberPagination, page_size=10)
def api_list_visites(
    request,
    statut: Optional[str] = None,
    type_visite_id: Optional[int] = None,
    visiteur_id: Optional[int] = None,
    porte_entree_id: Optional[int] = None,
    personnel_id: Optional[int] = None,
    departement_id: Optional[int] = None,
    date_start: Optional[str] = None,
    date_end: Optional[str] = None,
    q: Optional[str] = None,
    aujourdhui: Optional[bool] = None,
):
    """
    Liste des visites avec filtres optionnels.

    Filtres :
    - **statut** : EN_COURS, TERMINE, EXCEDE
    - **type_visite_id** : filtre par type
    - **visiteur_id** : filtre par visiteur
    - **porte_entree_id** : filtre par porte d'entrée
    - **personnel_id** : filtre par employé
    - **departement_id** : filtre par département de l'employé
    - **date_start** : date début (YYYY-MM-DD)
    - **date_end** : date fin (YYYY-MM-DD)
    - **q** : recherche texte (nom/prénom visiteur, motif, numéro badge)
    - **aujourdhui** : si `true`, filtre uniquement les visites d'aujourd'hui
    """
    qs = _base_visite_qs()

    if statut:
        qs = qs.filter(statut=statut)
    if type_visite_id:
        qs = qs.filter(type_visite_id=type_visite_id)
    if visiteur_id:
        qs = qs.filter(visiteur_id=visiteur_id)
    if porte_entree_id:
        qs = qs.filter(porte_entree_id=porte_entree_id)
    if personnel_id:
        qs = qs.filter(personnel_id=personnel_id)
    if departement_id:
        qs = qs.filter(personnel__departement_id=departement_id)
    if aujourdhui:
        qs = qs.filter(date_visite__date=timezone.now().date())
    if date_start:
        qs = qs.filter(date_visite__date__gte=date_start)
    if date_end:
        qs = qs.filter(date_visite__date__lte=date_end)
    if q:
        qs = qs.filter(
            Q(visiteur__nom__icontains=q) |
            Q(visiteur__prenom__icontains=q) |
            Q(motif__icontains=q) |
            Q(numero_badge__icontains=q)
        )

    return qs.order_by('-date_visite', '-id')


@router.post("/", response=VisiteOut)
def api_create_visite(request, payload: VisiteCreateIn):
    """Créer une visite.

    Deux modes pour le visiteur :
    - **visiteur_id** : utiliser un visiteur existant
    - **v_nom + v_prenom + v_numero_piece / v_nip** : chercher ou créer automatiquement
    """
    _check_perm(request, "visites.add_visite")

    # ── Résoudre le visiteur ──────────────────────────────────────────────
    visiteur = None
    if payload.visiteur_id:
        try:
            visiteur = Visiteur.objects.get(id=payload.visiteur_id)
        except Visiteur.DoesNotExist:
            raise HttpError(404, "Visiteur introuvable")
    elif payload.v_nom and payload.v_prenom:
        visitor_data = {}
        for field, v_field in [
            ('nom', 'v_nom'), ('prenom', 'v_prenom'), ('genre', 'v_genre'),
            ('date_naissance', 'v_date_naissance'), ('lieu_naissance', 'v_lieu_naissance'),
            ('nationalite', 'v_nationalite'), ('profession', 'v_profession'),
            ('telephone', 'v_telephone'), ('adresse', 'v_adresse'),
            ('email', 'v_email'), ('piece_identite', 'v_piece_identite'),
            ('numero_piece', 'v_numero_piece'), ('numero_nip', 'v_nip'),
            ('pays_delivrance', 'v_pays_delivrance'), ('date_delivrance', 'v_date_delivrance'),
        ]:
            val = getattr(payload, v_field, None)
            if val is not None:
                visitor_data[field] = val
        # Normaliser le genre du visiteur (accepte HOMME, M, etc.)
        if 'genre' in visitor_data:
            visitor_data['genre'] = _normalize_genre(visitor_data['genre'])
        # Nettoyer les chaînes vides
        visitor_data = {k: v.strip() if isinstance(v, str) else v for k, v in visitor_data.items() if v is not None and (not isinstance(v, str) or v.strip())}
        # Images du visiteur (base64 → ContentFile)
        visitor_files = {}
        if payload.photo_base64:
            f = _save_signature_base64(payload.photo_base64, 'photo')
            if f:
                visitor_files['photo'] = f
        if payload.document_recto_base64:
            f = _save_signature_base64(payload.document_recto_base64, 'recto')
            if f:
                visitor_files['document_recto'] = f
        if payload.document_verso_base64:
            f = _save_signature_base64(payload.document_verso_base64, 'verso')
            if f:
                visitor_files['document_verso'] = f
        visiteur = Visiteur.chercher_ou_creer(visitor_data, visitor_files if visitor_files else None)
    else:
        raise HttpError(400, "Fournissez un visiteur_id ou les données du visiteur (v_nom, v_prenom)")

    # ── Détection Liste Noire / Incidents ═══════════════════════════════════
    from .views import _detect_matches
    pre_matches = _detect_matches(
        visiteur.nom, visiteur.prenom,
        visiteur.numero_piece or '', visiteur.numero_nip or '',
        save_detections=False
    )
    if any(m.get('severity') == 'BLOCK' for m in pre_matches):
        block_details = [m['detail'] for m in pre_matches if m.get('severity') == 'BLOCK']
        raise HttpError(
            403,
            '🔴 Accès REFUSÉ — {} {} est inscrit(e) sur la Liste Noire. Motif : {}'.format(
                visiteur.prenom, visiteur.nom, ' ; '.join(block_details)
            )
        )

    # ── Vérifier les autres entités ─────────────────────────────────────────
    try:
        TypeVisite.objects.get(id=payload.type_visite_id)
    except TypeVisite.DoesNotExist:
        raise HttpError(404, "Type de visite introuvable")

    if payload.porte_entree_id:
        try:
            PorteEntree.objects.get(id=payload.porte_entree_id)
        except PorteEntree.DoesNotExist:
            raise HttpError(404, "Porte d'entrée introuvable")

    if payload.personnel_id:
        try:
            Personnel.objects.get(id=payload.personnel_id)
        except Personnel.DoesNotExist:
            raise HttpError(404, "Employé introuvable")

    # Valider le champ "Personne visitée" selon le mode (Hors-Normes / Heures Normales)
    if not payload.personnel_id:
        dt_check = payload.date_visite
        hr_check = payload.heure_arrivee
        if dt_check and hr_check:
            try:
                from entreprise.utils import determine_visit_mode, MODE_HORS_NORMES
                d = datetime.fromisoformat(dt_check).date() if isinstance(dt_check, str) else dt_check
                h = _parse_time(hr_check) if isinstance(hr_check, str) else hr_check
                mode = determine_visit_mode(d, h)
                if mode == MODE_HORS_NORMES:
                    raise HttpError(400, "En période Hors-Normes, le champ 'Personne visitée' est obligatoire")
            except HttpError:
                raise
            except Exception:
                pass  # Si erreur de parsing, on laisse passer

    # Parser les dates/heures
    dt = None
    hr = None
    if payload.date_visite:
        try:
            dt = datetime.fromisoformat(payload.date_visite)
            if dt and timezone.is_naive(dt):
                dt = timezone.make_aware(dt)
        except ValueError:
            raise HttpError(400, "Format de date_visite invalide (ISO attendu)")
    if payload.heure_arrivee:
        hr = _parse_time(payload.heure_arrivee)

    date_depart_prevue = _parse_date(payload.date_depart_prevue)
    heure_depart_prevue = _parse_time(payload.heure_depart_prevue)
    date_depart = _parse_date(payload.date_depart)
    date_expiration = _parse_date(payload.date_expiration)
    heure_depart = _parse_time(payload.heure_depart)

    visite = Visite(
        type_visite_id=payload.type_visite_id,
        visiteur=visiteur,
        genre=_normalize_genre(payload.genre) or visiteur.genre,
        porte_entree_id=payload.porte_entree_id,
        personnel_id=payload.personnel_id,
        date_visite=dt,
        heure_arrivee=hr,
        date_depart_prevue=date_depart_prevue,
        heure_depart_prevue=heure_depart_prevue,
        date_depart=date_depart,
        date_expiration=date_expiration,
        heure_depart=heure_depart,
        numero_badge=payload.numero_badge,
        motif=payload.motif,
        observations=payload.observations,
        statut=payload.statut,
        created_by=request.user,
    )

    # Signature d'entrée (base64)
    if payload.signature_entree:
        sig_file = _save_signature_base64(payload.signature_entree, 'signature_entree')
        if sig_file:
            visite.signature_entree = sig_file
    # Signature de sortie (base64) — optionnelle dès la création
    if payload.signature_sortie:
        sig_file = _save_signature_base64(payload.signature_sortie, 'signature_sortie')
        if sig_file:
            visite.signature_sortie = sig_file
    try:
        visite.save()
    except Exception as e:
        raise HttpError(400, f"Erreur lors de la création : {str(e)}")

    threading.Thread(
        target=_detect_matches,
        args=(payload.v_nom or '', payload.v_prenom or '',
              payload.v_numero_piece or '', payload.v_nip or ''),
        kwargs={
            'save_detections': True,
            'user': request.user,
            'porte_entree_id': payload.porte_entree_id,
        },
        daemon=True,
    ).start()

    return _get_visite_or_404(visite.id)


@router.get("/{visite_id}", response=VisiteOut)
def api_get_visite(request, visite_id: int):
    """Détail d'une visite."""
    return _get_visite_or_404(visite_id)


@router.put("/{visite_id}", response=VisiteOut)
def api_update_visite(request, visite_id: int, payload: VisiteUpdateIn):
    """Modifier une visite."""
    _check_perm(request, "visites.change_visite")
    visite = _get_visite_or_404(visite_id)

    field_map = {
        'type_visite_id': 'type_visite_id',
        'visiteur_id': 'visiteur_id',
        'porte_entree_id': 'porte_entree_id',
        'personnel_id': 'personnel_id',
        'genre': 'genre',
        'numero_badge': 'numero_badge',
        'motif': 'motif',
        'observations': 'observations',
        'statut': 'statut',
    }
    for payload_key, model_field in field_map.items():
        val = getattr(payload, payload_key, None)
        if val is not None:
            if model_field == 'genre':
                val = _normalize_genre(val)
            setattr(visite, model_field, val)

    # Parser les dates/heures
    if payload.date_visite is not None:
        try:
            dt = datetime.fromisoformat(payload.date_visite) if payload.date_visite else None
            if dt and timezone.is_naive(dt):
                dt = timezone.make_aware(dt)
            visite.date_visite = dt
        except ValueError:
            raise HttpError(400, "Format de date_visite invalide")
    if payload.heure_arrivee is not None:
        visite.heure_arrivee = _parse_time(payload.heure_arrivee) if payload.heure_arrivee else None
    if payload.date_depart_prevue is not None:
        visite.date_depart_prevue = _parse_date(payload.date_depart_prevue) if payload.date_depart_prevue else None
    if payload.heure_depart_prevue is not None:
        visite.heure_depart_prevue = _parse_time(payload.heure_depart_prevue) if payload.heure_depart_prevue else None
    if payload.date_depart is not None:
        visite.date_depart = _parse_date(payload.date_depart) if payload.date_depart else None
    if payload.date_expiration is not None:
        visite.date_expiration = _parse_date(payload.date_expiration) if payload.date_expiration else None
    if payload.heure_depart is not None:
        visite.heure_depart = _parse_time(payload.heure_depart) if payload.heure_depart else None

    # Signatures (base64)
    if payload.signature_entree is not None:
        sig_file = _save_signature_base64(payload.signature_entree, 'signature_entree')
        if sig_file:
            visite.signature_entree = sig_file
    if payload.signature_sortie is not None:
        sig_file = _save_signature_base64(payload.signature_sortie, 'signature_sortie')
        if sig_file:
            visite.signature_sortie = sig_file

    visite.updated_by = request.user
    try:
        visite.save()
    except Exception as e:
        raise HttpError(400, f"Erreur lors de la modification : {str(e)}")

    return _get_visite_or_404(visite.id)


@router.delete("/{visite_id}", response=MessageOut)
def api_delete_visite(request, visite_id: int):
    """Supprimer une visite."""
    _check_perm(request, "visites.delete_visite")
    visite = _get_visite_or_404(visite_id)
    visite.delete()
    return {"success": True, "message": "Visite supprimée avec succès"}


# ═══════════════════════════════════════════════════════════════════════════════
# ACTIONS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{visite_id}/terminer", response=VisiteOut)
def api_terminer_visite(request, visite_id: int, payload: TerminerVisiteIn):
    """
    Terminer une visite en cours.

    Met à jour la date/heure de départ, les observations optionnelles,
    et passe le statut à TERMINE.
    """
    visite = _get_visite_or_404(visite_id)

    if visite.statut not in ('EN_COURS', 'EXCEDE'):
        raise HttpError(400, f"Impossible de terminer une visite avec le statut {visite.statut}")

    if payload.date_depart is not None:
        visite.date_depart = _parse_date(payload.date_depart)
    else:
        visite.date_depart = timezone.now().date()

    if payload.heure_depart is not None:
        visite.heure_depart = _parse_time(payload.heure_depart)
    else:
        visite.heure_depart = timezone.now().time()

    if payload.observations is not None:
        visite.observations = payload.observations

    # Signature de sortie (base64)
    if payload.signature_sortie is not None:
        sig_file = _save_signature_base64(payload.signature_sortie, 'signature_sortie')
        if sig_file:
            visite.signature_sortie = sig_file

    # Incident lors de la sortie
    if payload.incident:
        desc = (payload.incident_description or '').strip()
        if desc:
            obs = visite.observations or ''
            suffix = f'\nIncident: {desc}'
            visite.observations = (obs + suffix) if obs else suffix.lstrip()
        Incident.objects.create(
            type_incident='AUTRE',
            motif=payload.incident_description or '',
            date_incident=timezone.now(),
            gravite=payload.incident_gravite or 'MOYENNE',
            visite=visite,
            created_by=request.user,
        )

    visite.statut = 'TERMINE'
    visite.updated_by = request.user
    visite.save()

    return _get_visite_or_404(visite.id)


# ═══════════════════════════════════════════════════════════════════════════════
# FILTRES PAR STATUT
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/en-cours/", response=List[VisiteOut])
@paginate(PageNumberPagination, page_size=10)
def api_list_visites_encours(
    request,
    aujourdhui: Optional[bool] = None,
):
    """Liste des visites en cours.
    
    - **aujourdhui** : si `true`, filtre uniquement les visites d'aujourd'hui
    """
    qs = _base_visite_qs().filter(statut='EN_COURS')
    if aujourdhui:
        qs = qs.filter(date_visite__date=timezone.now().date())
    return qs.order_by('-date_visite', '-id')


@router.get("/terminees/", response=List[VisiteOut])
@paginate(PageNumberPagination, page_size=10)
def api_list_visites_terminees(
    request,
    aujourdhui: Optional[bool] = None,
):
    """
    Liste des visites terminées.

    - **aujourdhui** : si `true`, filtre uniquement les visites terminées aujourd'hui
    """
    qs = _base_visite_qs().filter(statut__in=['TERMINE', 'SORTIE_SYSTEME'])
    if aujourdhui:
        qs = qs.filter(date_visite__date=timezone.now().date())
    return qs.order_by('-date_visite', '-id')


@router.get("/excedees/", response=List[VisiteOut])
@paginate(PageNumberPagination, page_size=10)
def api_list_visites_excedees(
    request,
    aujourdhui: Optional[bool] = None,
):
    """Liste des visites excédées.
    
    - **aujourdhui** : si `true`, filtre uniquement les visites d'aujourd'hui
    """
    qs = _base_visite_qs().filter(statut='EXCEDE')
    if aujourdhui:
        qs = qs.filter(date_visite__date=timezone.now().date())
    return qs.order_by('-date_visite', '-id')


# ═══════════════════════════════════════════════════════════════════════════════
# CHECK MODE (Hors-Normes / Heures Normales)  GET /api/visites/check-mode
# ═══════════════════════════════════════════════════════════════════════════════

class CheckModeOut(Schema):
    mode: str
    personnel_required: bool
    label: str


@router.get("/check-mode/", response=CheckModeOut, auth=None, url_name="api_check_mode")
def api_check_mode(request):
    """
    Vérifie si une date/heure donnée est en mode Hors-Normes ou Heures Normales.
    Utilisé par le frontend pour rendre le champ 'Personne visitée' obligatoire/optionnel.

    Paramètres : date (YYYY-MM-DD), heure (HH:MM)
    Si omis, utilise l'instant présent.
    """
    date_str = request.GET.get("date")
    heure_str = request.GET.get("heure")

    if not date_str or not heure_str:
        date_today = timezone.now().date()
        heure_now = timezone.now().time()
        d = date_today
        h = time(heure_now.hour, heure_now.minute)
    else:
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HttpError(400, "Format date invalide (YYYY-MM-DD)")
        try:
            h = datetime.strptime(heure_str, "%H:%M").time()
        except ValueError:
            raise HttpError(400, "Format heure invalide (HH:MM)")

    from entreprise.utils import determine_visit_mode, MODE_HEURES_NORMALES, MODE_HORS_NORMES
    mode = determine_visit_mode(d, h)
    return {
        "mode": mode,
        "personnel_required": mode == MODE_HORS_NORMES,
        "label": "Heures Normales" if mode == MODE_HEURES_NORMALES else "Hors-Normes",
    }
