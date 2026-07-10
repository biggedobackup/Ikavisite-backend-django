"""
IKAVISITE — API Authentification & Utilisateurs
Django Ninja — Authentification par Bearer JWT
Routes : /api/auth/*, /api/users/*
"""
from typing import Optional, List
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.pagination import paginate, PageNumberPagination
from django.contrib.auth import authenticate
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.tokens import RefreshToken
from .models import Utilisateur
from entreprise.models import PorteEntree


# ─── Auth JWT partagé ─────────────────────────────────────────────────────────
jwt_auth = JWTAuth()


# ─── Schémas ──────────────────────────────────────────────────────────────────

class LoginIn(Schema):
    username: str
    password: str

class UserOut(Schema):
    id: int
    uuid: str
    username: str
    email: str
    first_name: str
    last_name: str
    telephone_mobile: Optional[str] = None
    statut: str
    is_superuser: bool
    is_staff: bool
    is_active: bool
    role: str = ""
    porte_entree: Optional[str] = None
    porte_entree_id: Optional[int] = None
    last_login: Optional[str] = None
    date_joined: str

    @staticmethod
    def resolve_uuid(obj): return str(obj.uuid)
    @staticmethod
    def resolve_role(obj):
        groups = obj.groups.all()
        if groups:
            return groups[0].name
        if obj.is_superuser:
            return "Super administrateur"
        if obj.is_staff:
            return "Staff"
        return "Utilisateur"
    @staticmethod
    def resolve_porte_entree(obj):
        if obj.porte_entree_id:
            try:
                return obj.porte_entree.titre
            except PorteEntree.DoesNotExist:
                return None
        return None
    @staticmethod
    def resolve_porte_entree_id(obj):
        return obj.porte_entree_id
    @staticmethod
    def resolve_last_login(obj):
        return obj.last_login.isoformat() if obj.last_login else None
    @staticmethod
    def resolve_date_joined(obj): return obj.date_joined.isoformat() if obj.date_joined else ""

class TokenOut(Schema):
    access: str
    refresh: str
    user: UserOut

class RefreshIn(Schema):
    refresh: str

class TokenRefreshOut(Schema):
    access: str

class TokenVerifyOut(Schema):
    success: bool
    message: str

class UserCreateIn(Schema):
    username: str
    email: str
    password: str
    first_name: str = ""
    last_name: str = ""
    telephone_mobile: Optional[str] = None
    statut: str = "ACTIF"
    is_staff: bool = False
    is_superuser: bool = False

class UserUpdateIn(Schema):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    telephone_mobile: Optional[str] = None
    statut: Optional[str] = None
    is_staff: Optional[bool] = None
    is_superuser: Optional[bool] = None

class ProfileUpdateIn(Schema):
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    telephone_mobile: Optional[str] = None

class MessageOut(Schema):
    success: bool
    message: str


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_user_or_404(user_id: int) -> Utilisateur:
    try:
        return Utilisateur.objects.select_related('porte_entree').prefetch_related('groups').get(id=user_id)
    except Utilisateur.DoesNotExist:
        raise HttpError(404, "Utilisateur introuvable")


def _check_perm(request, perm: str) -> None:
    """Vérifie une permission Django, ou superuser."""
    if not (request.user.is_superuser or request.user.has_perm(perm)):
        raise HttpError(403, "Permission refusée")


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER AUTHENTIFICATION  /api/auth/*
# ═══════════════════════════════════════════════════════════════════════════════

auth_router = Router(tags=["Authentification"])


@auth_router.post("/login", response=TokenOut, auth=None)
def api_login(request, payload: LoginIn):
    """
    Connexion — reçoit access + refresh token + données utilisateur.

    Envoyer le **refresh** token à `/api/auth/refresh` pour obtenir
    un nouvel access token quand il expire (24h).
    """
    user = authenticate(request, username=payload.username, password=payload.password)
    if not user:
        raise HttpError(401, "Identifiants invalides")
    if user.statut != "ACTIF":
        raise HttpError(403, "Compte désactivé")

    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": user,
    }


@auth_router.post("/refresh", response=TokenRefreshOut, auth=None)
def api_refresh(request, payload: RefreshIn):
    """Rafraîchir l'access token à l'aide du refresh token."""
    try:
        refresh = RefreshToken(payload.refresh)
        return {"access": str(refresh.access_token)}
    except Exception:
        raise HttpError(401, "Refresh token invalide ou expiré")


@auth_router.post("/verify", response=TokenVerifyOut, auth=None)
def api_verify(request, payload: RefreshIn):
    """Vérifier si un refresh token est toujours valide."""
    try:
        token = RefreshToken(payload.refresh)
        # L'instanciation vérifie la signature et l'expiration
        return {"success": True, "message": "Token valide"}
    except Exception as e:
        raise HttpError(401, f"Token invalide ou expiré") from e


@auth_router.get("/me", response=UserOut, auth=jwt_auth)
def api_me(request):
    """Profil de l'utilisateur connecté (Bearer token requis)."""
    return request.user


@auth_router.put("/me", response=UserOut, auth=jwt_auth)
def api_update_me(request, payload: ProfileUpdateIn):
    """Modifier son propre profil."""
    user = request.user
    changed = False
    for field in ["email", "first_name", "last_name", "telephone_mobile"]:
        value = getattr(payload, field, None)
        if value is not None:
            setattr(user, field, value)
            changed = True
    if changed:
        user.save()
    return user


@auth_router.post("/logout", response=MessageOut, auth=jwt_auth)
def api_logout(request):
    """
    Déconnexion — le client doit supprimer ses tokens localement.
    (Le blacklisting des tokens peut être activé plus tard si besoin.)
    """
    return {"success": True, "message": "Déconnecté avec succès"}


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER UTILISATEURS (CRUD)  /api/users/*
# ═══════════════════════════════════════════════════════════════════════════════

users_router = Router(tags=["Utilisateurs"], auth=jwt_auth)


@users_router.get("/", response=List[UserOut])
@paginate(PageNumberPagination, page_size=10)
def api_list_users(request):
    """Liste des utilisateurs. Permissions : view_utilisateur ou superuser."""
    _check_perm(request, "utilisateurs.view_utilisateur")
    return Utilisateur.objects.select_related('porte_entree').prefetch_related('groups').order_by("-date_joined")


@users_router.post("/", response=UserOut)
def api_create_user(request, payload: UserCreateIn):
    """Créer un utilisateur. Permissions : add_utilisateur ou superuser."""
    _check_perm(request, "utilisateurs.add_utilisateur")
    if Utilisateur.objects.filter(username=payload.username).exists():
        raise HttpError(400, "Nom d'utilisateur déjà utilisé")
    if Utilisateur.objects.filter(email=payload.email).exists():
        raise HttpError(400, "Email déjà utilisé")
    user = Utilisateur.objects.create_user(
        username=payload.username,
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    if payload.telephone_mobile:
        user.telephone_mobile = payload.telephone_mobile
    user.statut = payload.statut
    user.is_staff = payload.is_staff
    user.is_superuser = payload.is_superuser
    user.save()
    return user


@users_router.get("/{user_id}", response=UserOut)
def api_get_user(request, user_id: int):
    """Détail d'un utilisateur. Permissions : view_utilisateur, superuser, ou soi-même."""
    if not (request.user.is_superuser or request.user.has_perm("utilisateurs.view_utilisateur") or request.user.id == user_id):
        raise HttpError(403, "Permission refusée")
    return _get_user_or_404(user_id)


@users_router.put("/{user_id}", response=UserOut)
def api_update_user(request, user_id: int, payload: UserUpdateIn):
    """Modifier un utilisateur. Permissions : change_utilisateur, superuser, ou soi-même."""
    if not (request.user.is_superuser or request.user.has_perm("utilisateurs.change_utilisateur") or request.user.id == user_id):
        raise HttpError(403, "Permission refusée")
    user = _get_user_or_404(user_id)

    update_fields = []
    for field in ["username", "email", "first_name", "last_name", "telephone_mobile", "statut", "is_staff", "is_superuser"]:
        value = getattr(payload, field, None)
        if value is not None:
            setattr(user, field, value)
            update_fields.append(field)
    if payload.password:
        user.set_password(payload.password)
        update_fields.append("password")
    if update_fields:
        user.save(update_fields=update_fields)
    return user


@users_router.delete("/{user_id}", response=MessageOut)
def api_delete_user(request, user_id: int):
    """Supprimer un utilisateur. Permissions : delete_utilisateur ou superuser."""
    _check_perm(request, "utilisateurs.delete_utilisateur")
    user = _get_user_or_404(user_id)
    if user == request.user:
        raise HttpError(400, "Vous ne pouvez pas supprimer votre propre compte")
    if user.is_superuser:
        raise HttpError(403, "Impossible de supprimer un super administrateur")
    user.delete()
    return {"success": True, "message": "Utilisateur supprimé avec succès"}
