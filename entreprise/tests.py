"""
Tests pour les créneaux de semaine et exceptions jour.
"""
from django.test import TestCase
from datetime import date, time
from unittest.mock import patch, Mock

from entreprise.utils import (
    determine_visit_mode,
    MODE_HEURES_NORMALES,
    MODE_HORS_NORMES,
)
from entreprise.models import (
    CreneauSemaine,
    ParametreEntreprise,
)


class DetermineVisitModeTest(TestCase):
    """Tests unitaires pour la fonction determine_visit_mode()."""

    @classmethod
    def setUpTestData(cls):
        # Créer une entreprise par défaut
        cls.ent = ParametreEntreprise.objects.create(
            nom_entreprise="Test",
            statut="ACTIF",
        )

    def test_1_sans_creneaux_journee_inactive(self):
        """Jour sans aucun créneau → journée INACTIVE → Hors-Normes 24h."""
        d = date(2026, 7, 22)  # Mercredi (3)
        # Pas de créneau ce jour → INACTIF → Hors-Normes
        self.assertEqual(
            determine_visit_mode(d, time(10, 0)),
            MODE_HORS_NORMES,
        )
        self.assertEqual(
            determine_visit_mode(d, time(23, 59)),
            MODE_HORS_NORMES,
        )

    def test_2_creneaux_actifs_heures_normales(self):
        """Créneau trouvé → Heures Normales."""
        d = date(2026, 7, 23)  # Jeudi (4)
        CreneauSemaine.objects.create(
            jour_semaine='JEUDI',
            heure_debut=time(8, 0),
            heure_fin=time(12, 0),
            statut='ACTIF',
        )
        self.assertEqual(
            determine_visit_mode(d, time(9, 0)),
            MODE_HEURES_NORMALES,
        )

    def test_3_creneaux_actifs_hors_creneaux(self):
        """Créneau existe mais en dehors → Hors-Normes."""
        d = date(2026, 7, 24)  # Vendredi (5)
        CreneauSemaine.objects.create(
            jour_semaine='VENDREDI',
            heure_debut=time(8, 0),
            heure_fin=time(12, 0),
            statut='ACTIF',
        )
        self.assertEqual(
            determine_visit_mode(d, time(14, 0)),
            MODE_HORS_NORMES,
        )
