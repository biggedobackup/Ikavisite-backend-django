from datetime import timedelta, datetime, time
from io import StringIO

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db.models import Q
from django.utils import timezone

from visites.models import Visite


class Command(BaseCommand):
    help = 'Passe les visites dépassées en EXCEDE, puis en TERMINE_SYSTEME après 5h'

    def handle(self, *args, **options):
        now = timezone.now()
        today = now.date()
        stats = {'excede': 0, 'termine_systeme': 0}

        # ── 1. EN_COURS → EXCEDE (heure de fin dépassée) ────────────────
        exc_ids = []
        for v in Visite.objects.filter(
            statut='EN_COURS'
        ).select_related('type_visite').iterator():

            fin_prevue = None

            # Priorité à la date/heure départ prévue
            if v.date_depart_prevue and v.heure_depart_prevue:
                fin_prevue = datetime.combine(v.date_depart_prevue, v.heure_depart_prevue)
                fin_prevue = timezone.make_aware(fin_prevue, timezone.get_current_timezone())

            # Sinon, arrivée + durée max du type de visite
            elif (v.type_visite and v.type_visite.duree_max_minutes
                  and v.heure_arrivee and v.date_visite):
                base = v.date_visite
                if isinstance(base, datetime):
                    base = base.replace(hour=v.heure_arrivee.hour,
                                        minute=v.heure_arrivee.minute,
                                        second=0)
                else:
                    base = datetime.combine(base, v.heure_arrivee)
                if not timezone.is_aware(base):
                    base = timezone.make_aware(base, timezone.get_current_timezone())
                fin_prevue = base + timedelta(minutes=v.type_visite.duree_max_minutes)

            if fin_prevue and now > fin_prevue:
                exc_ids.append(v.pk)

        if exc_ids:
            updated = Visite.objects.filter(pk__in=exc_ids, statut='EN_COURS').update(
                statut='EXCEDE',
                updated_at=now,
            )
            stats['excede'] = updated

        # ── 2. EXCEDE → TERMINE_SYSTEME (si 5h en statut EXCEDE) ────────
        term_ids = []
        obs_suffix = '\nVisite terminée automatiquement par le système après 5h en statut EXCEDE'

        for v in Visite.objects.filter(statut='EXCEDE').iterator():
            # updated_at = moment du dernier changement de statut
            if v.updated_at and now > v.updated_at + timedelta(hours=5):
                term_ids.append(v.pk)

        if term_ids:
            count = 0
            for v in Visite.objects.filter(pk__in=term_ids).iterator():
                v.observations = (v.observations + obs_suffix) if v.observations else obs_suffix.lstrip()
                v.statut = 'TERMINE_SYSTEME'
                v.date_depart = today
                v.heure_depart = now.time()
                v.updated_at = now
                v.save(update_fields=[
                    'statut', 'observations', 'date_depart',
                    'heure_depart', 'updated_at',
                ])
                count += 1
            stats['termine_systeme'] = count

        self.stdout.write(self.style.SUCCESS(
            f'EN_COURS → EXCEDE : {stats["excede"]} | '
            f'EXCEDE → TERMINE_SYSTEME (5h) : {stats["termine_systeme"]}'
        ))
