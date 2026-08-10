import uuid
from django.conf import settings
from django.db import models


GRAVITE_CHOICES = [
    ('FAIBLE', 'Faible'),
    ('MOYENNE', 'Moyenne'),
    ('GRAVE', 'Grave'),
    ('CRITIQUE', 'Critique'),
]

STATUT_INCIDENT_CHOICES = [
    ('OUVERT', 'Ouvert'),
    ('RESOLU', 'Résolu'),
    ('CLASSE_SANS_SUITE', 'Classé sans suite'),
]


class TypeIncident(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    gravite_defaut = models.CharField(
        max_length=20, choices=GRAVITE_CHOICES, default='MOYENNE'
    )
    actif = models.BooleanField(default=True)
    ordre = models.IntegerField(default=0)

    class Meta:
        db_table = 'types_incident'
        ordering = ['ordre', 'nom']
        verbose_name = "Type d'incident"
        verbose_name_plural = "Types d'incident"

    def __str__(self):
        return self.nom


class Incident(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    type_incident = models.ForeignKey(
        TypeIncident, on_delete=models.PROTECT,
        db_column='id_type_incident'
    )
    titre = models.CharField(max_length=255)
    motif = models.TextField(null=True, blank=True)
    date_incident = models.DateTimeField(null=True, blank=True)
    visite = models.ForeignKey(
        'visites.Visite', on_delete=models.SET_NULL,
        null=True, blank=True, db_column='id_visite'
    )
    personne = models.ForeignKey(
        'visites.Visiteur', on_delete=models.SET_NULL,
        null=True, blank=True, db_column='id_personne'
    )
    gravite = models.CharField(max_length=50, choices=GRAVITE_CHOICES, default='MOYENNE')
    statut = models.CharField(max_length=50, choices=STATUT_INCIDENT_CHOICES, default='OUVERT')
    justification = models.TextField(null=True, blank=True)
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
            models.Index(fields=['personne']),
        ]

    def __str__(self):
        return f'{self.type_incident} — {self.titre or self.motif or "(sans titre)"}'


DECISION_CHOICES = [
    ('REFUSE_SYSTEME', 'Refusé (système — Liste Noire)'),
    ('REFUSE_AGENT', 'Refusé (agent)'),
    ('AUTORISE', 'Autorisé (agent)'),
]


class DetectionDecision(models.Model):
    """Trace chaque décision prise lors d'une détection (BLOCK/WARN)."""
    visiteur_nom = models.CharField(max_length=255)
    visiteur_prenom = models.CharField(max_length=255)
    visiteur_nip = models.CharField(max_length=100, null=True, blank=True)
    visiteur_piece = models.CharField(max_length=100, null=True, blank=True)
    decision = models.CharField(max_length=50, choices=DECISION_CHOICES)
    type_detection = models.CharField(max_length=50)
    detail_detection = models.TextField()
    visite = models.ForeignKey(
        'visites.Visite', on_delete=models.SET_NULL,
        null=True, blank=True, db_column='id_visite'
    )
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'detection_decisions'
        ordering = ['-created_at']
        verbose_name = "Décision de détection"
        verbose_name_plural = "Décisions de détection"

    def __str__(self):
        return f'{self.get_decision_display()} — {self.visiteur_prenom} {self.visiteur_nom} ({self.type_detection})'
