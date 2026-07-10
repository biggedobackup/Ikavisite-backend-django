import uuid
from django.conf import settings
from django.db import models


TYPE_INCIDENT_CHOICES = [
    ('INTRUSION', 'Intrusion'),
    ('VOL', 'Vol'),
    ('VIOLENCE', 'Violence / Agression'),
    ('INCENDIE', 'Incendie'),
    ('ALARME', 'Alarme'),
    ('ACCIDENT', 'Accident'),
    ('DOMMAGE', 'Dégât matériel'),
    ('SUSPICION', 'Comportement suspect'),
    ('INFRACTION', 'Infraction'),
    ('AUTRE', 'Autre incident'),
]


class Incident(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    type_incident = models.CharField(max_length=50, choices=TYPE_INCIDENT_CHOICES)
    motif = models.TextField(null=True, blank=True)
    date_incident = models.DateTimeField(null=True, blank=True)
    visite = models.ForeignKey(
        'visites.Visite', on_delete=models.CASCADE,
        db_column='id_visite'
    )
    gravite = models.CharField(max_length=50, default='MOYENNE')
    statut = models.CharField(max_length=50, default='OUVERT')
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    class Meta:
        db_table = 'incidents'
        indexes = [
            models.Index(fields=['statut']),
            models.Index(fields=['date_incident']),
            models.Index(fields=['visite']),
        ]

    def __str__(self):
        return f'{self.type_incident} - {self.visite}'


class DetectionIncident(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    incident = models.ForeignKey(
        Incident, on_delete=models.CASCADE,
        db_column='id_incident'
    )
    date_detection = models.DateTimeField(null=True, blank=True)
    confiance = models.CharField(max_length=50, default='MOYENNE', null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    statut = models.CharField(max_length=50, default='ACTIF')
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )

    class Meta:
        db_table = 'detections_incident'
        verbose_name_plural = 'detections_incident'
        indexes = [
            models.Index(fields=['statut']),
            models.Index(fields=['incident']),
            models.Index(fields=['date_detection']),
        ]

    def __str__(self):
        return f'Détection {self.incident} - {self.date_detection}'
