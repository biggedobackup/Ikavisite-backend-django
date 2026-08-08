from django.db import migrations, models
import django.db.models.deletion

GRAVITE_CHOICES = [
    ('FAIBLE', 'Faible'),
    ('MOYENNE', 'Moyenne'),
    ('GRAVE', 'Grave'),
    ('CRITIQUE', 'Critique'),
]

OLD_CHOICES = [
    ('INTRUSION', 'Intrusion', 'GRAVE'),
    ('VOL', 'Vol', 'GRAVE'),
    ('VIOLENCE', 'Violence / Agression', 'CRITIQUE'),
    ('INCENDIE', 'Incendie', 'CRITIQUE'),
    ('ALARME', 'Alarme', 'MOYENNE'),
    ('ACCIDENT', 'Accident', 'MOYENNE'),
    ('DOMMAGE', 'Dégât matériel', 'MOYENNE'),
    ('SUSPICION', 'Comportement suspect', 'FAIBLE'),
    ('INFRACTION', 'Infraction', 'GRAVE'),
    ('AUTRE', 'Autre incident', 'MOYENNE'),
]


def create_type_incidents_and_migrate(apps, schema_editor):
    TypeIncident = apps.get_model('incidents', 'TypeIncident')
    Incident = apps.get_model('incidents', 'Incident')

    code_to_obj = {}
    for idx, (code, label, gravite) in enumerate(OLD_CHOICES):
        obj, _ = TypeIncident.objects.get_or_create(
            nom=label,
            defaults={
                'description': f'Ancien code : {code}',
                'gravite_defaut': gravite,
                'ordre': idx,
            },
        )
        code_to_obj[code] = obj

    for inc in Incident.objects.iterator():
        old_val = getattr(inc, 'type_incident_old_char', None)
        if old_val and old_val in code_to_obj:
            inc.type_incident = code_to_obj[old_val]
        else:
            inc.type_incident = code_to_obj.get('AUTRE')
        inc.save(update_fields=['type_incident'])


def reverse_migration(apps, schema_editor):
    TypeIncident = apps.get_model('incidents', 'TypeIncident')
    Incident = apps.get_model('incidents', 'Incident')
    # Reverse: set type_incident_old_char from FK nom
    for inc in Incident.objects.iterator():
        if inc.type_incident:
            inc.type_incident_old_char = inc.type_incident.nom
            inc.save(update_fields=['type_incident_old_char'])
    TypeIncident.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('incidents', '0003_incident_justification_incident_personne_and_more'),
    ]

    operations = [
        # 1. Create TypeIncident model
        migrations.CreateModel(
            name='TypeIncident',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('gravite_defaut', models.CharField(choices=GRAVITE_CHOICES, default='MOYENNE', max_length=20)),
                ('actif', models.BooleanField(default=True)),
                ('ordre', models.IntegerField(default=0)),
            ],
            options={
                'verbose_name': "Type d'incident",
                'verbose_name_plural': "Types d'incident",
                'db_table': 'types_incident',
                'ordering': ['ordre', 'nom'],
            },
        ),
        # 2. Rename old CharField to temporary name (saves existing data)
        migrations.RenameField(
            model_name='incident',
            old_name='type_incident',
            new_name='type_incident_old_char',
        ),
        # 3. Add new FK field (nullable initially)
        migrations.AddField(
            model_name='incident',
            name='type_incident',
            field=models.ForeignKey(
                null=True, blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                to='incidents.typeincident',
                db_column='id_type_incident',
            ),
        ),
        # 4. Data migration: populate TypeIncident + link existing incidents
        migrations.RunPython(
            create_type_incidents_and_migrate,
            reverse_migration,
        ),
        # 5. Remove old CharField
        migrations.RemoveField(
            model_name='incident',
            name='type_incident_old_char',
        ),
        # 6. Make FK non-nullable
        migrations.AlterField(
            model_name='incident',
            name='type_incident',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to='incidents.typeincident',
                db_column='id_type_incident',
            ),
        ),
    ]
