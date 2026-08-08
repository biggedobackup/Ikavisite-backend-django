from datetime import timedelta, datetime, time
from io import StringIO

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db.models import Q
from django.utils import timezone

from visites.models import Visite


class Command(BaseCommand):
    help = 'Passe les visites EN_COURS → EXCEDE quand l heure de fin est dépassée'

    def handle(self, *args, **options):
        now = timezone.now()
        stats = {'excede': 0}

        # ── EN_COURS → EXCEDE (heure de fin dépassée) ────────────────────
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

        self.stdout.write(self.style.SUCCESS(
            f'EN_COURS → EXCEDE : {stats["excede"]}'
        ))
