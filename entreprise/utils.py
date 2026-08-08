"""
IKAVISITE — Utilitaires métier.

Fonctions de détermination du mode de visite (HEURES_NORMALES / HORS_NORMES)
et validation du champ 'Personne visitée'.
"""
from datetime import date, time, datetime
from entreprise.models import CreneauSemaine

MODE_HEURES_NORMALES = "HEURES_NORMALES"
MODE_HORS_NORMES = "HORS_NORMES"


def _parse_time(val):
    """Convertit une valeur time/heure en objet time."""
    if isinstance(val, time):
        return val
    if isinstance(val, str):
        # Format HH:MM ou HH:MM:SS
        parts = val.strip().split(':')
        return time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
    if isinstance(val, datetime):
        return val.time()
    return val


def determine_visit_mode(dt, heure):
    """
    Détermine si une visite est en HEURES_NORMALES ou HORS_NORMES.

    Règles :
    - Utiliser le planning hebdo (CreneauSemaine) :
      - Vérifier si l'heure tombe dans un créneau ACTIF du jour correspondant
      - Si oui → HEURES_NORMALES, sinon → HORS_NORMES
    """
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt).date() if 'T' in dt else date.fromisoformat(dt)
    if not isinstance(heure, time):
        heure = _parse_time(heure)

    # Planning hebdomadaire
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
