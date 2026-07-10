import uuid
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from core.compress_image import CompressedImageField


class Utilisateur(AbstractUser):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    telephone_mobile = models.CharField(max_length=30, null=True, blank=True)
    photo_profil = CompressedImageField(upload_to='profils/', null=True, blank=True)
    porte_entree = models.ForeignKey(
        'entreprise.PorteEntree', on_delete=models.SET_NULL,
        null=True, blank=True, db_column='id_porte_entree'
    )
    statut = models.CharField(max_length=50, default='ACTIF')
    email = models.EmailField(unique=True)

    class Meta:
        db_table = 'utilisateurs'
        verbose_name = 'utilisateur'
        verbose_name_plural = 'utilisateurs'
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['statut']),
            models.Index(fields=['porte_entree']),
        ]

    def __str__(self):
        return self.get_full_name() or self.username


class HistoriqueAction(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, db_column='id_utilisateur'
    )
    action = models.CharField(max_length=100)
    entite = models.CharField(max_length=100)
    entite_id = models.PositiveIntegerField(null=True, blank=True)
    details = models.TextField(null=True, blank=True)
    ip_address = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    class Meta:
        db_table = 'historiques_actions'
        verbose_name_plural = 'historiques_actions'
        indexes = [
            models.Index(fields=['utilisateur']),
            models.Index(fields=['action']),
            models.Index(fields=['entite']),
            models.Index(fields=['entite_id']),
            models.Index(fields=['created_at']),
        ]

    @classmethod
    def log(cls, request, action, entite, entite_id=None, details=None):
        cls.objects.create(
            utilisateur=request.user if request.user.is_authenticated else None,
            action=action,
            entite=entite,
            entite_id=entite_id,
            details=details,
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

    def __str__(self):
        return f'{self.action} - {self.entite} ({self.created_at})'
