import uuid
from django.conf import settings
from django.db import models


class ObjetOublie(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    code = models.CharField(max_length=50, unique=True, null=True, blank=True)
    nom_objet = models.CharField(max_length=255)
    categorie = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    date_trouve = models.DateTimeField(null=True, blank=True)
    lieu_trouve = models.CharField(max_length=255, null=True, blank=True)
    visite = models.ForeignKey(
        'visites.Visite', on_delete=models.SET_NULL,
        null=True, blank=True, db_column='id_visite'
    )
    visiteur = models.ForeignKey(
        'visites.Visiteur', on_delete=models.SET_NULL,
        null=True, blank=True, db_column='id_visiteur', related_name='objets_oublies'
    )
    departement = models.ForeignKey(
        'entreprise.Departement', on_delete=models.SET_NULL,
        null=True, blank=True, db_column='id_departement'
    )
    date_remise = models.DateTimeField(null=True, blank=True)
    signature = models.TextField(null=True, blank=True)
    photo_objet = models.TextField(null=True, blank=True)
    personne_recupere = models.CharField(max_length=255, null=True, blank=True)
    statut = models.CharField(max_length=50, default='NON_RESTITUÉ')
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
        db_table = 'objets_oublies'
        verbose_name_plural = 'objets_oublies'
        indexes = [
            models.Index(fields=['statut']),
            models.Index(fields=['date_trouve']),
            models.Index(fields=['categorie']),
            models.Index(fields=['visite']),
            models.Index(fields=['visiteur']),
            models.Index(fields=['departement']),
        ]

    def __str__(self):
        return self.nom_objet


class DetectionObjetOublie(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    objet_oublie = models.ForeignKey(
        ObjetOublie, on_delete=models.CASCADE,
        db_column='id_objet_oublie'
    )
    porte_entree = models.ForeignKey(
        'entreprise.PorteEntree', on_delete=models.CASCADE,
        db_column='id_porte_entree'
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
        db_table = 'detections_objets_oublies'
        verbose_name_plural = 'detections_objets_oublies'
        indexes = [
            models.Index(fields=['statut']),
            models.Index(fields=['porte_entree']),
            models.Index(fields=['objet_oublie']),
            models.Index(fields=['date_detection']),
        ]

    def __str__(self):
        return f'Détection {self.objet_oublie} - {self.date_detection}'
