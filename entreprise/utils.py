"""
IKAVISITE — Utilitaires métier.

Fonctions de détermination du mode de visite (HEURES_NORMALES / HORS_NORMES)
et validation du champ 'Personne visitée'.
"""
from datetime import date, time, datetime
from entreprise.models import CreneauSemaine, ExceptionJour

MODE_HEURES_NORMALES = "HEURES_NORMALES"
MODE_HORS_NORMES = "HORS_NORMES"


def _parse_time(val):
    """Convertit une valeur time/heure en objet time."""
    if isinstance(val, time):
        return val
    if isinstance(val, str):
        parts = val.strip().split(':')
        return time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
    if isinstance(val, datetime):
        return val.time()
    return val


def determine_visit_mode(dt, heure):
    """
    Détermine si une visite est en HEURES_NORMALES ou HORS_NORMES.

    Priorité :
    1. ExceptionJour (date spécifique) → surcharge tout
       - Si chômé → HORS_NORMES
       - Si travaillé → vérifier créneaux de l'exception
    2. CreneauSemaine (planning hebdomadaire)
    """
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt).date() if 'T' in dt else date.fromisoformat(dt)
    if not isinstance(heure, time):
        heure = _parse_time(heure)

    # 1. Vérifier les exceptions (prioritaires)
    try:
        exc = ExceptionJour.objects.get(date=dt, statut='ACTIF')
        if exc.est_chome:
            return MODE_HORS_NORMES
        # Jour d'exception travaillé → utiliser ses créneaux
        slots = exc.creneaux.all().order_by('heure_debut')
        for slot in slots:
            if slot.heure_debut <= heure <= slot.heure_fin:
                return MODE_HEURES_NORMALES
        return MODE_HORS_NORMES
    except ExceptionJour.DoesNotExist:
        pass

    # 2. Planning hebdomadaire
    jour_map = {
        0: 'LUNDI', 1: 'MARDI', 2: 'MERCREDI', 3: 'JEUDI',
        4: 'VENDREDI', 5: 'SAMEDI', 6: 'DIMANCHE',
    }
    jour_str = jour_map.get(dt.weekday(), '')
    if not jour_str:
        return MODE_HORS_NORMES

    slots = CreneauSemaine.objects.filter(
        jour_semaine=jour_str,
        statut='ACTIF'
    ).order_by('heure_debut')
    for slot in slots:
        if slot.heure_debut <= heure <= slot.heure_fin:
            return MODE_HEURES_NORMALES
    return MODE_HORS_NORMES
