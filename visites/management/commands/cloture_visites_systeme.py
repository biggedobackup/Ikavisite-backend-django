"""
IKAVISITE — Commande de clôture automatique quotidienne des visites.

S'exécute tous les jours à 23:59:00.
Ferme toutes les visites encore ouvertes (EN_COURS, EXCEDE)
en les passant à SORTIE_SYSTEME avec motif de sortie automatique.
"""
from datetime import time
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from visites.models import Visite


class Command(BaseCommand):
    help = 'Clôture systématique des visites ouvertes (23h59, statut → SORTIE_SYSTEME)'

    def handle(self, *args, **options):
        now = timezone.now()
        today = now.date()
        closing_time = time(23, 59, 0)
        motif = "Clôture automatique système"
        count = 0

        qs = Visite.objects.filter(
            Q(statut='EN_COURS') | Q(statut='EXCEDE')
        ).iterator()

        for v in qs:
            v.statut = 'SORTIE_SYSTEME'
            v.date_depart = today
            v.heure_depart = closing_time
            v.motif = motif
            v.updated_at = now
            v.save(update_fields=[
                'statut', 'date_depart', 'heure_depart',
                'motif', 'updated_at',
            ])
            count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Clôture système — {count} visite(s) fermée(s) → SORTIE_SYSTEME'
        ))
