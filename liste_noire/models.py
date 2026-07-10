import uuid
from django.conf import settings
from django.db import models


class TypeListeNoire(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    nom = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    niveau_risque = models.CharField(max_length=50, default='FAIBLE', null=True, blank=True)
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
        db_table = 'types_liste_noire'
        indexes = [
            models.Index(fields=['nom']),
            models.Index(fields=['statut']),
        ]

    def __str__(self):
        return self.nom


class ListeNoire(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    type_liste_noire = models.ForeignKey(
        TypeListeNoire, on_delete=models.CASCADE,
        db_column='id_type_liste_noire'
    )
    nom = models.CharField(max_length=255)
    prenom = models.CharField(max_length=255)
    motif = models.TextField(null=True, blank=True)
    piece_identite = models.CharField(max_length=100, null=True, blank=True)
    numero_piece = models.CharField(max_length=100, null=True, blank=True)
    numero_nip = models.CharField(max_length=100, null=True, blank=True)
    date_debut = models.DateTimeField(null=True, blank=True)
    date_fin = models.DateTimeField(null=True, blank=True)
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
        db_table = 'listes_noire'
        verbose_name_plural = 'listes_noire'
        indexes = [
            models.Index(fields=['nom']),
            models.Index(fields=['prenom']),
            models.Index(fields=['statut']),
            models.Index(fields=['type_liste_noire']),
        ]

    def __str__(self):
        return f'{self.nom} {self.prenom}'


class DetectionListeNoire(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    liste_noire = models.ForeignKey(
        ListeNoire, on_delete=models.CASCADE,
        db_column='id_liste_noire'
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
        db_table = 'detections_liste_noire'
        verbose_name_plural = 'detections_liste_noire'
        indexes = [
            models.Index(fields=['statut']),
            models.Index(fields=['porte_entree']),
            models.Index(fields=['liste_noire']),
            models.Index(fields=['date_detection']),
        ]

    def __str__(self):
        return f'Détection {self.liste_noire} - {self.date_detection}'
