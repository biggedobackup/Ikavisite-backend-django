from django.db.models.signals import post_save, post_delete
from django.core.cache import cache


def _clear_cache(pattern_or_key: str):
    try:
        if '*' in pattern_or_key:
            cache.delete_pattern(pattern_or_key)
        else:
            cache.delete(pattern_or_key)
    except Exception:
        pass


def invalidate_dashboard_cache(**kwargs):
    _clear_cache('dashboard_data_*')


def invalidate_references_cache(**kwargs):
    _clear_cache('entreprise_references')


def invalidate_types_cache(**kwargs):
    _clear_cache('types_visite_list')


def invalidate_portes_cache(**kwargs):
    _clear_cache('portes_entree_list')


def invalidate_departements_cache(**kwargs):
    _clear_cache('departements_list')


def invalidate_personnel_cache(**kwargs):
    _clear_cache('personnel_list')


def connect_signals():
    from visites.models import Visite, TypeVisite, Visiteur
    from incidents.models import Incident
    from liste_noire.models import ListeNoire, DetectionListeNoire
    from objets_oublies.models import ObjetOublie
    from entreprise.models import PorteEntree, Departement, Personnel, ParametreEntreprise

    for model_cls in [Visite, Visiteur, Incident, ListeNoire]:
        post_save.connect(invalidate_dashboard_cache, sender=model_cls, weak=False)
        post_delete.connect(invalidate_dashboard_cache, sender=model_cls, weak=False)

    for model_cls, handler in [
        (ParametreEntreprise, invalidate_references_cache),
        (TypeVisite, invalidate_types_cache),
        (PorteEntree, invalidate_portes_cache),
        (Departement, invalidate_departements_cache),
        (Personnel, invalidate_personnel_cache),
    ]:
        post_save.connect(handler, sender=model_cls, weak=False)
        post_delete.connect(handler, sender=model_cls, weak=False)
