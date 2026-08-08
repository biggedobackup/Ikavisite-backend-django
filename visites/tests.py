"""
Tests pour les visites — validation créneaux et exceptions.
"""
from django.test import TestCase
from django.contrib.auth.models import User, Group, Permission
from datetime import date, time
from django.utils import timezone

from visites.models import Visite, TypeVisite, Visiteur
from entreprise.models import (
    ParametreEntreprise,
    PorteEntree,
    Personnel,
    Departement,
    CreneauSemaine,
)


class VisiteCleanValidationTest(TestCase):
    """La validation clean doit permettre les visites même Hors-Normes."""

    @classmethod
    def setUpTestData(cls):
        cls.ent = ParametreEntreprise.objects.create(nom_entreprise="Test", statut="ACTIF")
        cls.dep = Departement.objects.create(nom="IT", statut="ACTIF")
        cls.personnel = Personnel.objects.create(nom="Dupont", prenom="Jean", departement=cls.dep, statut="ACTIF")
        cls.porte = PorteEntree.objects.create(titre="Entrée principale", statut="ACTIF")
        cls.type_visite = TypeVisite.objects.create(nom="Visite simple", statut="ACTIF", duree_max_minutes=60)
        cls.visiteur = Visiteur.objects.create(nom="Martin", prenom="Test")

    def test_visite_sans_personnel_hors_normes(self):
        """Une visite Hors-Normes sans personnel doit pouvoir être créée."""
        v = Visite(
            visiteur=self.visiteur,
            type_visite=self.type_visite,
            porte_entree=self.porte,
            date_visite=timezone.now(),
            heure_arrivee=timezone.now().time(),
            statut='EN_COURS',
        )
        # Ne doit pas lever d'erreur
        v.full_clean()
        v.save()

    def test_visite_avec_personnel_heures_normales(self):
        """Une visite aux Heures Normales avec personnel OK."""
        v = Visite(
            visiteur=self.visiteur,
            type_visite=self.type_visite,
            porte_entree=self.porte,
            personnel=self.personnel,
            date_visite=timezone.now(),
            heure_arrivee=timezone.now().time(),
            statut='EN_COURS',
        )
        v.full_clean()
        v.save()
