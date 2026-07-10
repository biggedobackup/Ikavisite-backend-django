import uuid
from django.conf import settings
from django.db import models
from core.compress_image import CompressedImageField


class ParametreEntreprise(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    nom_entreprise = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    logo = CompressedImageField(upload_to='logos/', null=True, blank=True)
    email = models.CharField(max_length=255, null=True, blank=True)
    telephone = models.CharField(max_length=30, null=True, blank=True)
    site_web = models.CharField(max_length=255, null=True, blank=True)
    pays = models.CharField(max_length=100, null=True, blank=True)
    ville = models.CharField(max_length=100, null=True, blank=True)
    adresse = models.TextField(null=True, blank=True)
    secteur_activite = models.CharField(max_length=255, null=True, blank=True)
    duree_moyenne_visites = models.PositiveIntegerField(null=True, blank=True)
    nombre_employes = models.PositiveIntegerField(null=True, blank=True)
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
        db_table = 'parametres_entreprise'
        verbose_name_plural = 'parametres_entreprise'
        indexes = [
            models.Index(fields=['statut']),
        ]

    def __str__(self):
        return self.nom_entreprise


class PorteEntree(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    titre = models.CharField(max_length=255, unique=True)
    emplacement = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
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
        db_table = 'portes_entree'
        indexes = [
            models.Index(fields=['titre']),
            models.Index(fields=['statut']),
        ]

    def __str__(self):
        return self.titre


class Departement(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    nom = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)
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
        db_table = 'departements'
        indexes = [
            models.Index(fields=['nom']),
            models.Index(fields=['statut']),
        ]

    def __str__(self):
        return self.nom


class Personnel(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    nom = models.CharField(max_length=255)
    prenom = models.CharField(max_length=255)
    fonction = models.CharField(max_length=255, null=True, blank=True)
    email = models.CharField(max_length=255, null=True, blank=True)
    telephone = models.CharField(max_length=50, null=True, blank=True)
    departement = models.ForeignKey(
        Departement, on_delete=models.SET_NULL,
        null=True, blank=True, db_column='id_departement'
    )
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
        db_table = 'personnel'
        verbose_name_plural = 'personnel'
        indexes = [
            models.Index(fields=['nom']),
            models.Index(fields=['prenom']),
            models.Index(fields=['statut']),
            models.Index(fields=['departement']),
        ]

    def __str__(self):
        return f'{self.nom} {self.prenom}'


class CreneauSemaine(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    jour_semaine = models.CharField(max_length=50)
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
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
        db_table = 'creneaux_semaine'
        verbose_name_plural = 'creneaux_semaine'
        indexes = [
            models.Index(fields=['jour_semaine']),
            models.Index(fields=['statut']),
        ]

    def __str__(self):
        return f'{self.jour_semaine} {self.heure_debut}-{self.heure_fin}'
