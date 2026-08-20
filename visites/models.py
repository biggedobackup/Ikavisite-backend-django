import uuid
import datetime
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from core.compress_image import CompressedImageField

GENRE_CHOICES = [
    ('Homme', 'Homme'),
    ('Femme', 'Femme'),
]


def _parse_date(val):
    """Convertit une date string (YYYY-MM-DD ou DD/MM/YYYY) en date Python, ou None."""
    if not val:
        return None
    val = str(val).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
        try:
            return datetime.datetime.strptime(val, fmt).date()
        except (ValueError, TypeError):
            continue
    return None


class TypeVisite(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    nom = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    duree_max_minutes = models.IntegerField(null=True, blank=True)
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
        db_table = 'types_visite'
        indexes = [
            models.Index(fields=['nom']),
            models.Index(fields=['statut']),
        ]

    def __str__(self):
        return self.nom


class Visiteur(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    nom = models.CharField(max_length=255)
    prenom = models.CharField(max_length=255)
    genre = models.CharField(max_length=50, choices=GENRE_CHOICES, null=True, blank=True)
    date_naissance = models.CharField(max_length=20, null=True, blank=True)
    lieu_naissance = models.CharField(max_length=255, null=True, blank=True)
    nationalite = models.CharField(max_length=100, null=True, blank=True)
    profession = models.CharField(max_length=255, null=True, blank=True)
    adresse = models.TextField(null=True, blank=True)
    email = models.CharField(max_length=255, null=True, blank=True)
    telephone = models.CharField(max_length=50, null=True, blank=True)
    piece_identite = models.CharField(max_length=100, null=True, blank=True)
    numero_piece = models.CharField(max_length=100, null=True, blank=True)
    numero_nip = models.CharField(max_length=100, null=True, blank=True)
    pays_delivrance = models.CharField(max_length=100, null=True, blank=True)
    date_delivrance = models.CharField(max_length=20, null=True, blank=True)
    photo = CompressedImageField(upload_to='visiteurs/', null=True, blank=True)
    document_recto = CompressedImageField(upload_to='visiteurs/', null=True, blank=True)
    document_verso = CompressedImageField(upload_to='visiteurs/', null=True, blank=True)
    statut = models.CharField(max_length=50, default='ACTIF')
    flag_avertissement = models.BooleanField(default=False)
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
        db_table = 'visiteurs'
        indexes = [
            models.Index(fields=['nom']),
            models.Index(fields=['prenom']),
            models.Index(fields=['statut']),
            models.Index(fields=['nationalite']),
            models.Index(fields=['numero_piece']),
            models.Index(fields=['numero_nip']),
            models.Index(fields=['created_at']),
        ]

    @classmethod
    def chercher_ou_creer(cls, data, files=None):
        numero_piece = data.get('numero_piece')
        numero_nip = data.get('numero_nip')
        piece_identite = data.get('piece_identite', '')

        instance = None
        if numero_piece:
            instance = cls.objects.filter(numero_piece__iexact=numero_piece).first()
            # Chercher aussi via DocumentIdentite
            if not instance:
                doc = DocumentIdentite.objects.filter(
                    numero_document__iexact=numero_piece, statut='ACTIF'
                ).select_related('visiteur').first()
                if doc:
                    instance = doc.visiteur
        if not instance and numero_nip:
            instance = cls.objects.filter(numero_nip__iexact=numero_nip).first()
            # Chercher aussi via DocumentIdentite (NIP utilisé comme numéro de document)
            if not instance:
                doc = DocumentIdentite.objects.filter(
                    numero_document__iexact=numero_nip, statut='ACTIF'
                ).select_related('visiteur').first()
                if doc:
                    instance = doc.visiteur

        if instance:
            # ═══ Visiteur existant : archiver l'ancien document puis mettre à jour ═══
            # Sauvegarder l'ancien document dans DocumentIdentite s'il n'y est pas déjà
            if instance.piece_identite and instance.numero_piece:
                if not DocumentIdentite.objects.filter(
                    visiteur=instance,
                    type_document__iexact=instance.piece_identite,
                    numero_document__iexact=instance.numero_piece,
                ).exists():
                    DocumentIdentite.objects.create(
                        visiteur=instance,
                        type_document=instance.piece_identite,
                        numero_document=instance.numero_piece,
                        pays_emetteur=data.get('pays_delivrance') or None,
                        date_delivrance=_parse_date(data.get('date_delivrance')),
                        statut='ACTIF',
                    )

            # Mettre à jour les champs d'identité
            for attr, val in data.items():
                if attr in ('piece_identite', 'numero_piece', 'numero_nip', 'nom', 'prenom',
                            'telephone', 'email', 'adresse', 'nationalite',
                            'date_naissance', 'lieu_naissance', 'profession',
                            'genre', 'pays_delivrance', 'date_delivrance'):
                    if val:
                        setattr(instance, attr, val)
            if files:
                for fld in ('photo', 'document_recto', 'document_verso'):
                    if fld in files:
                        setattr(instance, fld, files[fld])

            instance.save()

            # ═══ Ajouter le nouveau document dans DocumentIdentite ═══
            if numero_piece and piece_identite:
                if not DocumentIdentite.objects.filter(
                    visiteur=instance,
                    type_document__iexact=piece_identite,
                    numero_document__iexact=numero_piece,
                ).exists():
                    DocumentIdentite.objects.create(
                        visiteur=instance,
                        type_document=piece_identite,
                        numero_document=numero_piece,
                        pays_emetteur=data.get('pays_delivrance') or None,
                        date_delivrance=_parse_date(data.get('date_delivrance')),
                        statut='ACTIF',
                    )
        else:
            instance = cls.objects.create(**data, **(files or {}))
            # ═══ Nouveau visiteur : créer aussi le DocumentIdentite initial ═══
            if numero_piece and piece_identite:
                DocumentIdentite.objects.create(
                    visiteur=instance,
                    type_document=piece_identite,
                    numero_document=numero_piece,
                    pays_emetteur=data.get('pays_delivrance') or None,
                    date_delivrance=_parse_date(data.get('date_delivrance')),
                    statut='ACTIF',
                )

        return instance

    @property
    def nb_visites(self):
        return self.visite_set.count()

    def __str__(self):
        return f'{self.nom} {self.prenom}'


TYPE_DOCUMENT_CHOICES = [
    ('CNI', 'CNI'),
    ('PASSEPORT', 'Passeport'),
    ('PERMIS', 'Permis de conduire'),
    ('CARTE_CONSULAIRE', 'Carte consulaire'),
    ('CARTE_SEJOUR', 'Carte de séjour'),
    ('CARTE_ETUDIANT', 'Carte étudiant'),
    ('AUTRE', 'Autre'),
]

STATUT_DOCUMENT_CHOICES = [
    ('ACTIF', 'Actif'),
    ('EXPIRE', 'Expiré'),
    ('PERDU', 'Perdu'),
    ('VOLE', 'Volé'),
]


class DocumentIdentite(models.Model):
    """Documents d'identité liés à un visiteur — un visiteur peut avoir N documents."""
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    visiteur = models.ForeignKey(
        Visiteur, on_delete=models.CASCADE,
        related_name='documents', db_column='id_visiteur'
    )
    type_document = models.CharField(max_length=50, choices=TYPE_DOCUMENT_CHOICES)
    numero_document = models.CharField(max_length=100)
    pays_emetteur = models.CharField(max_length=100, null=True, blank=True)
    date_delivrance = models.DateField(null=True, blank=True)
    date_expiration = models.DateField(null=True, blank=True)
    recto = CompressedImageField(upload_to='documents/', null=True, blank=True)
    verso = CompressedImageField(upload_to='documents/', null=True, blank=True)
    commentaire = models.TextField(null=True, blank=True)
    statut = models.CharField(max_length=50, choices=STATUT_DOCUMENT_CHOICES, default='ACTIF')
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
        db_table = 'documents_identite'
        verbose_name = "Document d'identité"
        verbose_name_plural = "Documents d'identité"
        indexes = [
            models.Index(fields=['numero_document']),
            models.Index(fields=['type_document']),
            models.Index(fields=['visiteur']),
            models.Index(fields=['statut']),
            models.Index(fields=['date_expiration']),
        ]
        # Contrainte d'unicité par type + numéro (un même numéro de CNI ne peut pas exister 2x)
        constraints = [
            models.UniqueConstraint(
                fields=['type_document', 'numero_document'],
                name='uq_document_type_numero'
            ),
        ]

    def __str__(self):
        return f'{self.get_type_document_display()} — {self.numero_document} ({self.visiteur})'


class Visite(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    type_visite = models.ForeignKey(
        TypeVisite, on_delete=models.CASCADE,
        db_column='id_type_visite'
    )
    visiteur = models.ForeignKey(
        Visiteur, on_delete=models.CASCADE,
        db_column='id_visiteur'
    )
    genre = models.CharField(max_length=50, choices=GENRE_CHOICES, null=True, blank=True)
    piece_identite = models.CharField(max_length=50, null=True, blank=True,
        help_text='Type de document présenté lors de cette visite')
    numero_piece = models.CharField(max_length=100, null=True, blank=True,
        help_text='Numéro de document présenté lors de cette visite')
    porte_entree = models.ForeignKey(
        'entreprise.PorteEntree', on_delete=models.CASCADE,
        null=True, blank=True, db_column='id_porte_entree'
    )
    personnel = models.ForeignKey(
        'entreprise.Personnel', on_delete=models.SET_NULL,
        null=True, blank=True, db_column='id_employe'
    )
    departement = models.ForeignKey(
        'entreprise.Departement', on_delete=models.SET_NULL,
        null=True, blank=True, db_column='id_departement'
    )
    date_visite = models.DateTimeField(null=True, blank=True)
    heure_arrivee = models.TimeField(null=True, blank=True)
    date_depart_prevue = models.DateField(null=True, blank=True)
    heure_depart_prevue = models.TimeField(null=True, blank=True)
    date_depart = models.DateField(null=True, blank=True)
    date_expiration = models.DateField(null=True, blank=True)
    heure_depart = models.TimeField(null=True, blank=True)
    numero_badge = models.CharField(max_length=100, null=True, blank=True)
    motif = models.TextField(null=True, blank=True)
    observations = models.TextField(null=True, blank=True)
    signature_entree = CompressedImageField(upload_to='signatures_entree/', null=True, blank=True)
    signature_sortie = CompressedImageField(upload_to='signatures_sortie/', null=True, blank=True)
    statut = models.CharField(max_length=50, default='EN_COURS')
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

    def clean(self):
        errs = {}
        if self.porte_entree_id and self.porte_entree.statut != 'ACTIF':
            errs['porte_entree'] = 'Cette porte d\'entrée est inactive'
        if self.personnel_id:
            if self.personnel.statut != 'ACTIF':
                errs['personnel'] = 'Ce personnel est inactif'
            elif self.personnel.departement_id and self.personnel.departement.statut != 'ACTIF':
                errs['personnel'] = 'Le département de ce personnel est inactif'
        if errs:
            raise ValidationError(errs)

    @property
    def visit_mode(self):
        """
        Détermine le mode de la visite : MODE_HEURES_NORMALES ou MODE_HORS_NORMES.
        Appelle determine_visit_mode() du module entreprise.
        """
        from entreprise.utils import determine_visit_mode
        if self.date_visite and self.heure_arrivee:
            return determine_visit_mode(self.date_visite, self.heure_arrivee)
        return None

    @property
    def personnel_required(self):
        """True si le champ 'Personne visitée' est obligatoire pour cette visite."""
        from entreprise.utils import MODE_HORS_NORMES
        return self.visit_mode == MODE_HORS_NORMES

    class Meta:
        db_table = 'visites'
        permissions = [
            # Statistiques du tableau de bord
            ('view_stat_total_visits', 'Voir le total des visites'),
            ('view_stat_today_visits', 'Voir les visites du jour'),
            ('view_stat_en_cours', 'Voir les visites en cours'),
            ('view_stat_termine', 'Voir les visites terminées'),
            ('view_stat_termine_aujourdhui', 'Voir les visites terminées du jour'),
            ('view_stat_excede', 'Voir les visites excédées'),
            ('view_stat_visiteurs', 'Voir le total des visiteurs'),
            ('view_stat_utilisateurs', 'Voir le total des utilisateurs'),
            ('view_stat_departements', 'Voir le total des départements'),
            ('view_stat_portes', "Voir le total des portes d'entrée"),
            ('view_stat_incidents', 'Voir le total des incidents'),
            ('view_stat_objets', 'Voir le total des objets oubliés'),
            ('view_stat_personnes_liste_noire', 'Voir les personnes en liste noire'),
            ('view_stat_detections_liste_noire', 'Voir les détections liste noire'),
            # Graphiques du tableau de bord
            ('view_chart_departments', 'Voir le graphique par département'),
            ('view_chart_weekday', 'Voir le graphique par jour de la semaine'),
            ('view_chart_entry_points', "Voir le graphique par point d'entrée"),
            ('view_chart_incidents', 'Voir le flux des incidents'),
            ('view_chart_visit_types', 'Voir la répartition des types de visite'),
        ]
        indexes = [
            models.Index(fields=['statut']),
            models.Index(fields=['date_visite']),
            models.Index(fields=['statut', 'date_visite'], name='visites_statut_date_idx'),
            models.Index(fields=['type_visite']),
            models.Index(fields=['visiteur']),
            models.Index(fields=['porte_entree']),
            models.Index(fields=['personnel']),
        ]

    @property
    def duree_max_minutes(self):
        return self.type_visite.duree_max_minutes or 60

    @property
    def heure_arrivee_dt(self):
        if not self.heure_arrivee or not self.date_visite:
            return None
        base = self.date_visite
        return base.replace(hour=self.heure_arrivee.hour, minute=self.heure_arrivee.minute, second=0, microsecond=0)

    @property
    def heure_fin_prevue_dt(self):
        if self.heure_depart_prevue and self.date_visite:
            base = self.date_visite
            return base.replace(hour=self.heure_depart_prevue.hour, minute=self.heure_depart_prevue.minute, second=0, microsecond=0)
        if self.heure_arrivee_dt:
            return self.heure_arrivee_dt + datetime.timedelta(minutes=self.duree_max_minutes)
        return None

    @property
    def est_excedee(self):
        if self.statut != 'EN_COURS':
            return False
        fin = self.heure_fin_prevue_dt
        if not fin:
            return False
        return timezone.now() > fin

    def save(self, *args, **kwargs):
        if self.statut == 'EN_COURS' and self.heure_fin_prevue_dt and timezone.now() > self.heure_fin_prevue_dt:
            self.statut = 'EXCEDE'
        if not kwargs.pop('skip_validation', False):
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.visiteur} - {self.date_visite}'


class VisiteEnCours(Visite):
    class Meta:
        proxy = True
        verbose_name = 'Visite en cours'
        verbose_name_plural = 'Visites en cours'

    def save(self, *args, **kwargs):
        self.statut = 'EN_COURS'
        kwargs['skip_validation'] = True
        super().save(*args, **kwargs)


class VisiteTerminee(Visite):
    class Meta:
        proxy = True
        verbose_name = 'Visite terminée'
        verbose_name_plural = 'Visites terminées'

    def save(self, *args, **kwargs):
        self.statut = 'TERMINE'
        kwargs['skip_validation'] = True
        super().save(*args, **kwargs)


class VisiteExcedee(Visite):
    class Meta:
        proxy = True
        verbose_name = 'Visite excédée'
        verbose_name_plural = 'Visites excédées'

    def save(self, *args, **kwargs):
        self.statut = 'EXCEDE'
        kwargs['skip_validation'] = True
        super().save(*args, **kwargs)
