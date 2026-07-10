# Skill CRUD Django Template

Génère un CRUD complet Django (vues, URLs, templates) pour un modèle existant.

## Étapes

1. **Modèle** — Vérifier que le modèle existe dans `entreprise/models.py` (ou l'app cible) avec les champs `titre`/`nom`, `description`, `statut`, `created_at`, `updated_at`, `created_by`, `updated_by`, `deleted_at`

2. **Dossier templates** — Créer `templates/<entity>/` avec 4 fichiers :
   - `liste.html` — tableau avec recherche/filtre statut, pagination (10/page), actions (détail/modifier/supprimer)
   - `ajouter.html` — formulaire de création
   - `detail.html` — fiche d'information avec champs en grille
   - `modiifer.html` — formulaire d'édition (nom du fichier avec la faute intentionnelle `modiifer` pour respecter la convention existante)

3. **Vues** — Créer ou compléter `<app>/views.py` avec 5 fonctions :
   - `liste_<entity>` (GET) — queryset filtré par `deleted_at__isnull=True`, recherche `Q()`, filtre statut, **Paginator(queryset, 10)**, `page_obj` passé au contexte
   - `ajouter_<entity>` (GET/POST) — validation, création, message "Ajout effectué avec succès"
   - `detail_<entity>` (GET) — get_object_or_404 avec `select_related('created_by', 'updated_by')`
   - `modifier_<entity>` (GET/POST) — validation, mise à jour, message "Modification effectuée avec succès"
   - `supprimer_<entity>` (GET/POST) — soft-delete via `deleted_at`, message "Suppression effectuée avec succès"

4. **URLs** — Créer `<app>/urls.py` avec les 5 routes nommées :
   - `''` → `liste_<entity>` (name: `liste_<entity>`)
   - `'ajouter/'` → `ajouter_<entity>` (name: `ajouter_<entity>`)
   - `'detail/<int:pk>/'` → `detail_<entity>` (name: `detail_<entity>`)
   - `'modifier/<int:pk>/'` → `modifier_<entity>` (name: `modifier_<entity>`)
   - `'supprimer/<int:pk>/'` → `supprimer_<entity>` (name: `supprimer_<entity>`)

5. **core/urls.py** — Ajouter `path('<entity>/', include('<app>.<subdir>.urls'))` (ou directement depuis l'app)

6. **sidebar.html** — Remplacer le lien `/admin/...` par `{% url 'liste_<entity>' %}` avec `active` conditionnelle

7. **Export PDF & Excel** — Ajouter 2 vues d'export :
   - `export_pdf_<entity>` — utilise `reportlab`, génère un tableau stylé, téléchargement direct
   - `export_excel_<entity>` — utilise `openpyxl`, en-tête stylé, téléchargement direct
   - URLs : `export/pdf/` et `export/excel/` (à placer avant les routes avec paramètres)
   - Template : lier les boutons avec `{% url '...' %}` dans le bloc `pe-actions`

8. **Notifications** — Les messages utilisent déjà le système toast dans `base.html` (auto-dismiss 4s). Les vues doivent utiliser `messages.success(request, 'Ajout/Modification/Suppression effectué avec succès.')`

## Ordre des champs dans le détail

Les champs métier (nom, emplacement, description) doivent précéder les champs d'audit (créé/modifié par/le). La Description passe en 2e position après le nom/identité.

## Convention de nommage

| Élément | Format | Exemple |
|---------|--------|---------|
| App | `snake_case` | `entreprise` |
| Dossier templates | `kebab-case/` | `portes-entree/` |
| Prefix CSS | `3 lettres` | `pe-`, `dep-`, `pers-` |
| Nom route | `snake_case` | `liste_portes_entree` |
| URL | `kebab-case` | `portes-entree/` |
| Template block | `extra_css` + `name>` | `{% block extra_css %}<style>.pe-*{}</style>{% endblock %}` |

## Structure templates type

```html
{% extends "base.html" %}
{% load static %}
{% block title %}Titre - IKAVISITE{% endblock %}
{% block extra_css %}
<style>
.prefix-label{font-size:.8125rem;font-weight:700;color:#6b7280}
.prefix-input{width:100%;border-radius:.75rem;border:1px solid #e2e8f0;padding:.75rem 1rem;font-size:.875rem;font-weight:600;color:#0f172a;outline:none}
.prefix-input:focus{border-color:var(--primary);box-shadow:0 0 0 4px #e8f3fc}
.prefix-btn{display:inline-flex;align-items:center;gap:.5rem;border-radius:.75rem;padding:.75rem 1.5rem;font-size:.875rem;font-weight:700;border:none;cursor:pointer;transition:background .15s}
.prefix-btn-primary{background:var(--primary);color:#fff}
.prefix-btn-primary:hover{background:var(--primary-hover)}
.prefix-btn-ghost{background:#fff;color:#374151;border:1px solid #e2e8f0}
.prefix-btn-ghost:hover{background:#f8fafc}
.prefix-card{border-radius:1.5rem;border:1px solid #f1f5f9;background:#fff;padding:1.5rem;box-shadow:0 1px 3px rgba(15,23,42,.04)}
.prefix-pagination{display:flex;align-items:center;justify-content:space-between;gap:1rem;padding:1rem 1.25rem;border-top:1px solid #f1f5f9;flex-wrap:wrap}
.prefix-pagination-info{font-size:.8125rem;font-weight:600;color:#64748b}
.prefix-pagination-steps{display:flex;align-items:center;gap:.25rem}
.prefix-page-btn{display:inline-flex;align-items:center;justify-content:center;min-width:2.25rem;height:2.25rem;border-radius:.5rem;border:1px solid #e2e8f0;background:#fff;color:#475569;font-size:.8125rem;font-weight:700;cursor:pointer;text-decoration:none;transition:background .15s,border-color .15s,color .15s}
.prefix-page-btn:hover{background:#f1f5f9;border-color:#cbd5e1}
.prefix-page-btn.active{background:var(--primary);border-color:var(--primary);color:#fff}
</style>
{% endblock %}
{% block content %}
...
{% endblock %}
```

## Palette / Design tokens

| Token | Valeur | Usage |
|-------|--------|-------|
| `--primary` | `#1270b8` | Boutons, liens, badges actifs |
| `--primary-hover` | `#0f5d99` | Hover des boutons primaires |
| `--primary-light` | `#e8f3fc` | Fond tableau, badges, cartes |
| `--secondary` | `#e51b35` | Bouton danger, badge inactif |
| `--secondary-light` | `#fdecee` | Fond danger |
| border | `#e2e8f0` / `#f1f5f9` | Bordures |
| text | `#0f172a` (titre), `#475569` (corps), `#64748b` (label) | Typographie |
