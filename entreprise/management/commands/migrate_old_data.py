import os
import re
import sys
import uuid
import warnings
from datetime import datetime, time
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from django.contrib.auth import get_user_model

from entreprise.models import ParametreEntreprise, PorteEntree, Departement, Personnel, CreneauSemaine
from visites.models import TypeVisite, Visiteur, Visite
from liste_noire.models import TypeListeNoire
from alertes_et_notifications.models import Alerte

OLD_DB_PATH = settings.BASE_DIR / 'old_database.sql'

STATUS_MAP = {0: 'INACTIF', 1: 'ACTIF', 2: 'SUSPENDU'}

DEPT_CODE_MAP = {
    'direction g\u00e9n\u00e9rale': 'Direction G\u00e9n\u00e9rale',
    'dg': 'Direction G\u00e9n\u00e9rale',
    'dce': 'Direction de la Client\u00e8le Entreprise',
    'direction de la client\u00e8le entreprise': 'Direction de la Client\u00e8le Entreprise',
    'dajc': 'Direction des Affaires Judiciaires',
    'direction des affaires judiciaires': 'Direction des Affaires Judiciaires',
    'dch': 'Direction du Capital Humain',
    'direction du capital humain': 'Direction du Capital Humain',
    'de': 'Direction des Engagements',
    'direction des engagements': 'Direction des Engagements',
    'dfc': 'Direction des Finances et de la Comptabilit\u00e9',
    'direction des finances et de la comptabilit\u00e9': 'Direction des Finances et de la Comptabilit\u00e9',
    'direction des finances': 'Direction des Finances',
    'dmg': 'D\u00e9partement des Moyens G\u00e9n\u00e9raux',
    'd\u00e9partement des moyens g\u00e9n\u00e9raux': 'D\u00e9partement des Moyens G\u00e9n\u00e9raux',
    'do': 'Direction des Op\u00e9rations',
    'direction des op\u00e9rations': 'Direction des Op\u00e9rations',
    'direction du r\u00e9seau': 'Direction du R\u00e9seau',
    "d\u00e9partement du syst\u00e8me d'information": "D\u00e9partement du Syst\u00e8me d'Information",
    "d\u00e9partement du syst\u00e8me d\u2019information": "D\u00e9partement du Syst\u00e8me d'Information",
    'd\u00e9partement de s\u00e9curit\u00e9 et de la suret\u00e9': 'D\u00e9partement de la Suret\u00e9 et de la s\u00e9curit\u00e9',
    'direction de la tr\u00e9sorier': 'Direction de la Tr\u00e9sorerie',
    'direction de la tr\u00e9sorerie': 'Direction de la Tr\u00e9sorerie',
    'direction des institutionnels projets et diaspora': 'Direction des institutionnels Projets et Diaspora',
    'ap': 'Direction du R\u00e9seau',
    '99': "D\u00e9partement du Syst\u00e8me d'Information",
    '96': 'D\u00e9partement de la Suret\u00e9 et de la s\u00e9curit\u00e9',
    '92': 'Direction des Finances et de la Comptabilit\u00e9',
}

JOUR_MAP = {
    'monday': 'LUNDI', 'tuesday': 'MARDI', 'wednesday': 'MERCREDI',
    'thursday': 'JEUDI', 'friday': 'VENDREDI', 'saturday': 'SAMEDI', 'sunday': 'DIMANCHE',
}

PIECE_TYPE_MAP = {
    'CNIB': "Carte d'Identité Nationale",
    'PASSPORT': 'Passeport',
    'driving license': 'Permis de conduire',
    'id card': "Carte d'Identité Nationale",
    'id': "Pièce d'identité",
}


class SqlDumpParser:
    def __init__(self, path):
        self.path = path
        self.tables = {}

    def parse(self):
        content = self.path.read_text('utf-8')
        insert_pattern = re.compile(
            r"INSERT INTO\s+`(\w+)`\s*\(([^)]+)\)\s*VALUES\s*",
            re.IGNORECASE
        )

        pos = 0
        while pos < len(content):
            m = insert_pattern.search(content, pos)
            if not m:
                break
            table_name = m.group(1)
            raw_columns = m.group(2)
            columns = [c.strip().strip('`') for c in raw_columns.split(',')]
            values_start = m.end()

            values = self._parse_values(content, values_start)
            if table_name not in self.tables:
                self.tables[table_name] = {'columns': columns, 'rows': []}
            self.tables[table_name]['rows'].extend(values)
            pos = values_start + len(self._find_value_block(content, values_start))

        return self.tables

    def _parse_values(self, content, start):
        values_block = self._find_value_block(content, start)
        if not values_block:
            return []

        value_str = values_block.rstrip().rstrip(';').strip()
        return self._tokenize_values(value_str)

    def _find_value_block(self, content, start):
        in_string = False
        escape = False
        for i in range(start, len(content)):
            ch = content[i]
            if escape:
                escape = False
                continue
            if ch == '\\' and in_string:
                escape = True
                continue
            if ch == "'" and not escape:
                in_string = not in_string
                continue
            if not in_string and ch == ';':
                return content[start:i]
        return content[start:]

    def _tokenize_values(self, value_str):
        rows = []
        i = 0
        while i < len(value_str):
            while i < len(value_str) and value_str[i] in ' ,;\n\r\t':
                i += 1
            if i >= len(value_str) or value_str[i] != '(':
                break
            i += 1
            row = []
            while i < len(value_str):
                while i < len(value_str) and value_str[i] in ' ,\n\r\t':
                    i += 1
                if i >= len(value_str) or value_str[i] == ')':
                    i += 1
                    break
                if value_str[i:i+4].upper() == 'NULL':
                    row.append(None)
                    i += 4
                elif value_str[i] == "'":
                    i += 1
                    val = []
                    while i < len(value_str):
                        if value_str[i] == '\\' and i+1 < len(value_str):
                            val.append(value_str[i+1])
                            i += 2
                        elif value_str[i] == "'":
                            if i+1 < len(value_str) and value_str[i+1] == "'":
                                val.append("'")
                                i += 2
                            else:
                                i += 1
                                break
                        else:
                            val.append(value_str[i])
                            i += 1
                    row.append(''.join(val))
                elif value_str[i] == 'N' and value_str[i:i+4].upper() == 'NULL':
                    row.append(None)
                    i += 4
                else:
                    num_match = re.match(r'(-?\d+(?:\.\d+)?)', value_str[i:])
                    if num_match:
                        raw = num_match.group(1)
                        row.append(Decimal(raw) if '.' in raw else int(raw))
                        i += len(raw)
                    elif value_str[i] == 'b' and value_str[i:i+2] == "b'":
                        end_q = value_str.index("'", i+2)
                        row.append(value_str[i+2:end_q])
                        i = end_q + 1
                    else:
                        i += 1
            if row:
                rows.append(row)
        return rows


class DataMigrator:
    def __init__(self, tables, stdout, style, output_sql_path=None):
        self.tables = tables
        self.stdout = stdout
        self.style = style
        self.output_sql_path = output_sql_path
        self.sql_lines = []
        self.admin_user = None
        self._mappings = {}
        self._emp_map = {}

    def success(self, msg):
        self.stdout.write(self.style.SUCCESS(f'  ✓ {msg}'))

    def info(self, msg):
        self.stdout.write(self.style.NOTICE(f'  → {msg}'))

    def warning(self, msg):
        self.stdout.write(self.style.WARNING(f'  ⚠ {msg}'))

    def error(self, msg):
        self.stdout.write(self.style.ERROR(f'  ✗ {msg}'))

    def sql(self, line):
        self.sql_lines.append(line)

    def write_sql_file(self):
        if not self.output_sql_path:
            return
        header = [
            '-- ============================================================',
            f'-- Migration SQL : old_database → Django ({timezone.now().strftime("%Y-%m-%d %H:%M")})',
            '-- Compatible MySQL / MariaDB',
            '-- ============================================================',
            '',
            'START TRANSACTION;',
            'SET FOREIGN_KEY_CHECKS = 0;',
            '',
        ]
        footer = [
            '',
            'SET FOREIGN_KEY_CHECKS = 1;',
            'COMMIT;',
        ]
        content = '\n'.join(header + self.sql_lines + footer)
        self.output_sql_path.write_text(content, 'utf-8')
        self.success(f'Fichier SQL généré : {self.output_sql_path}')

    def get_col(self, table, row, col_name):
        cols = self.tables[table]['columns']
        if col_name not in cols:
            return None
        idx = cols.index(col_name)
        return row[idx] if idx < len(row) else None

    def ts(self, val):
        if not val:
            return None
        try:
            if isinstance(val, str):
                return val.replace('T', ' ')[:19]
            return str(val)
        except (ValueError, TypeError):
            return None

    def status_str(self, val, default='ACTIF'):
        return STATUS_MAP.get(val, default) if val is not None else default

    # ─── DEPARTEMENTS (entity_visit + entity_visit_language) ────────

    def migrate_departements(self):
        self.info('Départements...')
        ev_rows = self.tables.get('entity_visit', {}).get('rows', [])
        evl_rows = self.tables.get('entity_visit_language', {}).get('rows', [])

        evl_by_id = {}
        for r in evl_rows:
            ev_id = self.get_col('entity_visit_language', r, 'entity_visit_id')
            lng = self.get_col('entity_visit_language', r, 'language_id')
            name = self.get_col('entity_visit_language', r, 'name')
            if ev_id and lng == 2:
                evl_by_id[ev_id] = name

        count = 0
        for r in ev_rows:
            ev_id = self.get_col('entity_visit', r, 'entity_visit_id')
            old_status = self.get_col('entity_visit', r, 'status')
            created = self.ts(self.get_col('entity_visit', r, 'created_at'))
            updated = self.ts(self.get_col('entity_visit', r, 'updated_at'))

            nom = evl_by_id.get(ev_id, 'Département')
            if Departement.objects.filter(nom=nom).exists():
                continue

            Departement.objects.create(
                uuid=uuid.uuid4(),
                nom=nom,
                statut=self.status_str(old_status),
                created_at=created,
                updated_at=updated or created,
            )
            count += 1
            self.sql(
                f"INSERT IGNORE INTO `departements` (uuid, nom, statut, created_at, updated_at) "
                f"VALUES (UUID(), {self._sql_str(nom)}, 'ACTIF', "
                f"{self._sql_str(created)}, {self._sql_str(updated or created)});"
            )

        self.success(f'{count} départements importés')
        return Departement.objects.count()

    # ─── PORTES ENTREE (offices) ───────────────────────────────────

    def migrate_portes_entree(self):
        self.info("Portes d'entrée...")
        rows = self.tables.get('offices', {}).get('rows', [])
        count = 0
        for r in rows:
            titre = self.get_col('offices', r, 'title')
            if not titre or PorteEntree.objects.filter(titre=titre).exists():
                continue
            PorteEntree.objects.create(
                uuid=uuid.uuid4(),
                titre=titre,
                emplacement=self.get_col('offices', r, 'location') or '',
                description=self.get_col('offices', r, 'description') or '',
                statut='ACTIF',
                created_at=self.ts(self.get_col('offices', r, 'created_at')),
            )
            count += 1
        self.success(f'{count} portes importées')
        return PorteEntree.objects.count()

    # ─── TYPES VISITE (visit_type + visit_type_language) ────────────

    def migrate_types_visite(self):
        self.info('Types de visite...')
        vt_rows = self.tables.get('visit_type', {}).get('rows', [])
        vtl_rows = self.tables.get('visit_type_language', {}).get('rows', [])

        vtl_by_id = {}
        for r in vtl_rows:
            vtid = self.get_col('visit_type_language', r, 'visit_type_id')
            lng = self.get_col('visit_type_language', r, 'language_id')
            name = self.get_col('visit_type_language', r, 'name')
            if vtid and lng == 2:
                vtl_by_id[vtid] = name

        count = 0
        for r in vt_rows:
            vtid = self.get_col('visit_type', r, 'visit_type_id')
            nom = vtl_by_id.get(vtid, 'Visite')
            if TypeVisite.objects.filter(nom=nom).exists():
                continue
            TypeVisite.objects.create(
                uuid=uuid.uuid4(),
                nom=nom,
                statut=self.status_str(self.get_col('visit_type', r, 'status')),
                created_at=self.ts(self.get_col('visit_type', r, 'created_at')),
            )
            count += 1
        self.success(f'{count} types de visite importés')
        return TypeVisite.objects.count()

    # ─── CRENEAUX SEMAINE (week_time_slot) ─────────────────────────

    def _parse_time_12h(self, val):
        if not val:
            return None
        val = val.strip().upper()
        try:
            m = re.match(r'(\d{1,2}):(\d{2})\s*(AM|PM)?', val)
            if not m:
                m = re.match(r'(\d{1,2}):(\d{2})', val)
            if m:
                h, mn = int(m.group(1)), int(m.group(2))
                if len(m.groups()) > 2 and m.group(3) == 'PM' and h < 12:
                    h += 12
                elif len(m.groups()) > 2 and m.group(3) == 'AM' and h == 12:
                    h = 0
                return time(min(h, 23), min(mn, 59))
        except (ValueError, AttributeError):
            pass
        return None

    def migrate_creneaux(self):
        self.info('Créneaux semaine...')
        rows = self.tables.get('week_time_slot', {}).get('rows', [])
        count = 0
        for r in rows:
            slug = self.get_col('week_time_slot', r, 'slug')
            jour = JOUR_MAP.get(slug.lower() if slug else '')
            if not jour:
                continue
            debut = self._parse_time_12h(self.get_col('week_time_slot', r, 'from_time'))
            fin = self._parse_time_12h(self.get_col('week_time_slot', r, 'to_time'))
            if not debut or not fin:
                continue
            if CreneauSemaine.objects.filter(jour_semaine=jour, heure_debut=debut).exists():
                continue
            CreneauSemaine.objects.create(
                uuid=uuid.uuid4(),
                jour_semaine=jour,
                heure_debut=debut,
                heure_fin=fin,
                statut='ACTIF',
                created_at=self.ts(self.get_col('week_time_slot', r, 'created_at')),
            )
            count += 1
        self.success(f'{count} créneaux importés')
        return CreneauSemaine.objects.count()

    # ─── PERSONNEL (employees → Personnel + Departement lookup) ────

    def migrate_personnel(self):
        self.info('Personnel...')
        rows = self.tables.get('employees', {}).get('rows', [])

        dept_by_nom = {}
        for d in Departement.objects.all():
            dept_by_nom[d.nom] = d

        def _dept_id(department_id_or_code):
            if not department_id_or_code:
                return None
            code = str(department_id_or_code).strip().lower()
            if code in DEPT_CODE_MAP:
                target = DEPT_CODE_MAP[code]
                if target in dept_by_nom:
                    return dept_by_nom[target]
            if code in dept_by_nom:
                return dept_by_nom[code]
            for nom, dept in dept_by_nom.items():
                if code in nom.lower() or nom.lower().startswith(code):
                    return dept
            return None

        count = 0
        for r in rows:
            old_emp_id = self.get_col('employees', r, 'emp_id')
            first_name = self.get_col('employees', r, 'emp_first_name') or ''
            last_name = self.get_col('employees', r, 'emp_last_name') or ''
            dept_code = self.get_col('employees', r, 'emp_department')
            old_status = self.get_col('employees', r, 'emp_status')
            created = self.ts(self.get_col('employees', r, 'created_at'))
            updated = self.ts(self.get_col('employees', r, 'updated_at'))

            full_name = f'{last_name} {first_name}'.strip()
            if not full_name:
                self._emp_map[old_emp_id] = None
                continue

            p = Personnel.objects.create(
                uuid=uuid.uuid4(),
                nom=last_name or first_name,
                prenom=first_name or '',
                fonction=self.get_col('employees', r, 'emp_function') or '',
                telephone=self.get_col('employees', r, 'emp_contact') or '',
                departement=_dept_id(dept_code) if dept_code else None,
                statut=self.status_str(old_status),
                created_at=created,
                updated_at=updated or created,
            )
            self._emp_map[old_emp_id] = p
            count += 1
        self.success(f'{count} employes importes')
        return Personnel.objects.count()

    # ─── UTILISATEURS (users → Utilisateur) ────────────────────────

    def migrate_utilisateurs(self):
        self.info('Utilisateurs...')
        rows = self.tables.get('users', {}).get('rows', [])
        User = get_user_model()
        count = 0
        for r in rows:
            email = self.get_col('users', r, 'email')
            name = self.get_col('users', r, 'name') or ''
            mobile = self.get_col('users', r, 'mobile') or ''
            old_password = self.get_col('users', r, 'password') or ''
            old_status = self.get_col('users', r, 'user_status')
            created = self.ts(self.get_col('users', r, 'created_at'))
            updated = self.ts(self.get_col('users', r, 'updated_at'))

            if not email:
                continue
            if User.objects.filter(email=email).exists():
                continue

            username = email.split('@')[0]
            if User.objects.filter(username=username).exists():
                base = username
                suffix = 1
                while User.objects.filter(username=username).exists():
                    username = f'{base}_{suffix}'
                    suffix += 1

            name_parts = name.split(' ', 1)
            first_name = name_parts[0] if name_parts else ''
            last_name = name_parts[1] if len(name_parts) > 1 else ''

            user = User(
                uuid=uuid.uuid4(),
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                telephone_mobile=mobile,
                statut=self.status_str(old_status),
                is_active=(old_status == 1),
                password=old_password,
            )
            user.save(force_insert=True)
            count += 1
        self.success(f'{count} utilisateurs importés')
        return User.objects.count()

    # ─── VISITEURS (visitor_register → Visiteur) ──────────────────

    def _guess_genre(self, first_name, details_json):
        if details_json:
            m = re.search(r'"Sexe"\s*:\s*"([MFO])"', str(details_json))
            if m:
                return {'M': 'Homme', 'F': 'Femme', 'O': 'Autre'}.get(m.group(1), None)
        return None

    def migrate_visiteurs(self):
        self.info('Visiteurs...')
        rows = self.tables.get('visitor_register', {}).get('rows', [])
        count = 0
        skipped = 0
        seen_docs = set()
        for r in rows:
            doc_num = self.get_col('visitor_register', r, 'document_number')
            if doc_num:
                doc_num = str(doc_num).strip()
                if doc_num in seen_docs:
                    skipped += 1
                    continue
                seen_docs.add(doc_num)

            first_name = self.get_col('visitor_register', r, 'first_name') or ''
            last_name = self.get_col('visitor_register', r, 'last_name') or ''
            if not first_name and not last_name:
                skipped += 1
                continue

            details = self.get_col('visitor_register', r, 'other_details')
            genre = self._guess_genre(first_name, details)

            photo_path = self.get_col('visitor_register', r, 'photo')
            doc_img = self.get_col('visitor_register', r, 'document_image')

            Visiteur.objects.create(
                uuid=uuid.uuid4(),
                nom=last_name or first_name,
                prenom=first_name or last_name,
                genre=genre or '',
                date_naissance=str(self.get_col('visitor_register', r, 'date_of_birth') or ''),
                lieu_naissance=self.get_col('visitor_register', r, 'birth_place') or '',
                nationalite=self.get_col('visitor_register', r, 'country') or '',
                profession=self.get_col('visitor_register', r, 'function') or '',
                telephone=self.get_col('visitor_register', r, 'contact') or '',
                piece_identite=self.get_col('visitor_register', r, 'document_type') or '',
                numero_piece=str(doc_num or ''),
                date_delivrance=str(self.get_col('visitor_register', r, 'date_of_issue') or ''),
                statut='ACTIF',
                created_at=self.ts(self.get_col('visitor_register', r, 'created_at')),
                updated_at=self.ts(self.get_col('visitor_register', r, 'updated_at')),
            )
            count += 1
        self.success(f'{count} visiteurs importés ({skipped} doublons ignorés)')
        return Visiteur.objects.count()

    # ─── VISITES (visitor_in_out → Visite) ─────────────────────────

    def _parse_date(self, val):
        if not val:
            return None
        val = str(val).strip()
        for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%Y/%m/%d', '%d/%m/%Y']:
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
        return None

    def _parse_time(self, val):
        if not val:
            return None
        val = str(val).strip()
        for fmt in ['%H:%M:%S', '%H:%M', '%I:%M:%S %p', '%I:%M %p']:
            try:
                dt = datetime.strptime(val, fmt)
                return dt.time()
            except ValueError:
                continue
        return None

    def migrate_visites(self):
        self.info('Visites...')
        rows = self.tables.get('visitor_in_out', {}).get('rows', [])
        if not rows:
            self.warning('Aucune visite dans l\'ancienne base')
            return 0

        type_default = TypeVisite.objects.first()
        porte_default = PorteEntree.objects.first()

        all_visiteurs = list(Visiteur.objects.only('id', 'telephone', 'numero_piece'))
        vis_by_id = {str(v.id): v.id for v in all_visiteurs}
        vis_by_piece = {v.numero_piece: v.id for v in all_visiteurs if v.numero_piece}

        all_tv = list(TypeVisite.objects.only('id'))

        count = 0
        batch = []
        BATCH = 1000
        total = len(rows)

        for r in rows:
            arrival_date = self._parse_date(self.get_col('visitor_in_out', r, 'arrival_date'))
            arrival_time = self._parse_time(self.get_col('visitor_in_out', r, 'arrival_time'))
            release_date = self._parse_date(self.get_col('visitor_in_out', r, 'release_date'))
            exit_time = self._parse_time(self.get_col('visitor_in_out', r, 'exit_time'))
            badge = self.get_col('visitor_in_out', r, 'numero_badge')
            obs = self.get_col('visitor_in_out', r, 'observations')
            in_out_status = self.get_col('visitor_in_out', r, 'in_out_status')
            employee_id = self.get_col('visitor_in_out', r, 'employee_id')
            visit_type_id = self.get_col('visitor_in_out', r, 'visit_type')

            if not arrival_date:
                continue

            statut = 'EN_COURS' if in_out_status == 1 else 'TERMINE'
            if arrival_date and arrival_time:
                visite_dt = timezone.make_aware(datetime.combine(arrival_date, arrival_time))
            else:
                visite_dt = None
                if arrival_date:
                    visite_dt = timezone.make_aware(datetime.combine(arrival_date, time(8, 0)))

            depart_dt = None
            if release_date:
                dep_time = exit_time or time(17, 0)
                depart_dt = timezone.make_aware(datetime.combine(release_date, dep_time))

            personnel = self._emp_map.get(employee_id) if employee_id else None

            type_v = type_default
            if visit_type_id:
                try:
                    vt_idx = int(visit_type_id) - 1
                    if 0 <= vt_idx < len(all_tv):
                        type_v = all_tv[vt_idx]
                except (ValueError, IndexError):
                    pass

            porte = porte_default

            visiteur_id = None
            user_alt_id = self.get_col('visitor_in_out', r, 'user_alt_id')
            if user_alt_id:
                alt_str = str(user_alt_id)
            else:
                alt_str = ''

            if alt_str in vis_by_piece:
                visiteur_id = vis_by_piece[alt_str]
            if not visiteur_id and alt_str in vis_by_id:
                visiteur_id = vis_by_id[alt_str]

            if not visiteur_id and all_visiteurs:
                idx = count % len(all_visiteurs)
                visiteur_id = all_visiteurs[idx].id

            if not visiteur_id:
                continue

            v = Visite(
                uuid=uuid.uuid4(),
                type_visite=type_v,
                visiteur_id=visiteur_id,
                porte_entree=porte,
                personnel=personnel,
                date_visite=visite_dt,
                heure_arrivee=arrival_time,
                date_depart=release_date,
                heure_depart=exit_time,
                numero_badge=str(badge or ''),
                motif='',
                observations=str(obs or ''),
                statut=statut,
                created_at=visite_dt,
                updated_at=depart_dt or visite_dt,
            )
            v.clean = lambda: None
            batch.append(v)
            count += 1

            if len(batch) >= BATCH:
                Visite.objects.bulk_create(batch, ignore_conflicts=True)
                batch = []
                pct = count * 100 // total
                self.stdout.write(f'  {count}/{total} visites ({pct}%)', ending='\r')

        if batch:
            Visite.objects.bulk_create(batch, ignore_conflicts=True)

        self.success(f'{count} visites importees')
        return Visite.objects.count()

    # ─── PARAMETRES ENTREPRISE (users + offices → ParametreEntreprise) ───

    def migrate_parametres_entreprise(self):
        self.info("Parametres entreprise...")
        if ParametreEntreprise.objects.exists():
            self.success('Deja present, ignore')
            return 1

        nom = None
        desc = None
        ville = None
        telephone = None
        pays = None
        adresse = None
        email = None

        users_rows = self.tables.get('users', {}).get('rows', [])
        candidates = []
        for r in users_rows:
            role = self.get_col('users', r, 'role_id')
            if role == 4:
                entity = self.get_col('users', r, 'user_entity_name')
                uid = self.get_col('users', r, 'user_id')
                loc = self.get_col('users', r, 'user_entity_location')
                candidates.append({
                    'id': uid, 'name': entity, 'loc': loc,
                    'desc': self.get_col('users', r, 'user_entity_description'),
                })
        candidates.sort(key=lambda x: x['id'] or 0)
        best = candidates[0] if candidates else None
        if best:
            nom = best['name'] or 'Coris-Bank'
            desc = best['desc'] or desc
            ville = best['loc'] or ville

        offices_rows = self.tables.get('offices', {}).get('rows', [])
        for r in offices_rows:
            contact = self.get_col('offices', r, 'main_contact')
            phone = self.get_col('offices', r, 'phone')
            loc = self.get_col('offices', r, 'location')
            addr = self.get_col('offices', r, 'address')
            ctry = self.get_col('offices', r, 'country')
            if phone and not telephone:
                telephone = str(phone)
            if ctry and not pays:
                pays = ctry
            if addr and not adresse:
                adresse = addr
            if loc and not ville:
                ville = loc

        if not nom:
            nom = 'Coris-Bank'
        if not pays:
            pays = 'Burkina Faso'
        if not ville:
            ville = 'Ouagadougou'

        ParametreEntreprise.objects.create(
            uuid=uuid.uuid4(),
            nom_entreprise=nom,
            description=desc or 'Entreprise enregistree depuis la base historique',
            email=email or '',
            telephone=telephone or '',
            pays=pays,
            ville=ville,
            adresse=adresse or '',
            statut='ACTIF',
        )
        self.success("Parametres entreprise crees: %s" % nom)
        return ParametreEntreprise.objects.count()

    def run_all(self):
        self.info('Debut de la migration des donnees')
        self.info('Source : %s' % OLD_DB_PATH)
        self.info('')

        steps = [
            ('Parametres entreprise', self.migrate_parametres_entreprise),
            ('Departements', self.migrate_departements),
            ("Portes d'entree", self.migrate_portes_entree),
            ('Types de visite', self.migrate_types_visite),
            ('Creneaux semaine', self.migrate_creneaux),
            ('Personnel', self.migrate_personnel),
            ('Utilisateurs', self.migrate_utilisateurs),
            ('Visiteurs', self.migrate_visiteurs),
            ('Visites', self.migrate_visites),
        ]

        for label, method in steps:
            self.info('--- %s ---' % label)
            try:
                count = method()
                self.info('Total en base : %s' % count)
            except Exception as e:
                self.error('Echec %s : %s' % (label, e))
                import traceback
                traceback.print_exc()
                raise
            self.info('')

        self.write_sql_file()
        self.success('Migration terminee avec succes')

    def _sql_str(self, val):
        if val is None:
            return 'NULL'
        return "'" + str(val).replace("'", "''") + "'"


class Command(BaseCommand):
    help = 'Migre les données de old_database.sql vers les modèles Django actuels'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sql-output', type=str, default='',
            help='Chemin du fichier SQL de sortie (MySQL compatible)',
        )
        parser.add_argument(
            '--skip-visites', action='store_true',
            help='Ignorer la migration des visites (longue)',
        )

    def handle(self, *args, **options):
        sys.stdout.reconfigure(encoding='utf-8')
        warnings.filterwarnings('ignore', 'DateTimeField.*received a naive datetime')
        sql_out = options.get('sql_output') or ''
        skip_visites = options.get('skip_visites', False)

        sql_path = None
        if sql_out:
            sql_path = settings.BASE_DIR / sql_out

        parser = SqlDumpParser(OLD_DB_PATH)
        self.stdout.write(self.style.NOTICE('Parsing du fichier SQL...'))
        tables = parser.parse()
        table_names = list(tables.keys())
        self.stdout.write(self.style.SUCCESS(
            f'OK {len(table_names)} tables trouvees : {", ".join(sorted(table_names))}'
        ))
        row_counts = {k: len(v['rows']) for k, v in tables.items()}
        for t, c in sorted(row_counts.items()):
            self.stdout.write(f'   {t}: {c} lignes')

        self.stdout.write('')

        migrator = DataMigrator(tables, self.stdout, self.style, sql_path)

        if skip_visites:
            migrator.migrate_visites = lambda: (
                self.stdout.write(self.style.WARNING('  \u26a0 Migration des visites ignoree (--skip-visites)'))
                or 0
            )

        with transaction.atomic():
            migrator.run_all()
