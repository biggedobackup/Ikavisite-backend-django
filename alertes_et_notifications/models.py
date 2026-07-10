from django.db import models


class Alerte(models.Model):
    TYPE_ALERTE_CHOICES = [
        ('LISTE_NOIRE', 'Liste noire'),
        ('INCIDENT', 'Incident'),
        ('OBJET_OUBLIE', 'Objet oublié'),
    ]
    type = models.CharField(max_length=20, choices=TYPE_ALERTE_CHOICES)
    entite_id = models.PositiveIntegerField(db_column='id_entite')
    message = models.TextField()
    lu = models.BooleanField(default=False)
    lu_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'alertes'
        verbose_name = 'alerte'
        verbose_name_plural = 'alertes'
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.get_type_display()}] {self.message[:60]}'
