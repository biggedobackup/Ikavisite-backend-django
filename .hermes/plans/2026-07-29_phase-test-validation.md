# Plan de Tests — IkaVisite (Phase de Validation Fonctionnelle)

> **Objectif :** Valider systématiquement toutes les fonctionnalités construites, dans l'ordre de dépendance logique. Chaque test validé = une coche.

**Méthode :** Test réel navigateur (pas de tests unitaires abstraits). On crée, on modifie, on supprime, on vérifie les résultats visibles.

**Prérequis :** Service `testikavisite` actif, utilisateur admin connecté, NGINX opérationnel.

---

## PHASE 0 — Fondations (30 min)

### 0.1 Service & Accès
- [ ] `systemctl status testikavisite` → active
- [ ] Accès navigateur `https://ikavisite.siralink.bf` → page login
- [ ] Connexion Super Admin → sidebar complète visible
- [ ] Connexion Agent (rôle restreint) → sidebar limitée

### 0.2 Permissions & Rôles
- [ ] Super Admin : toutes les sections visibles dans la sidebar
- [ ] Super Admin : pas d'erreur 500 sur aucune page
- [ ] Super Admin : peut créer/modifier/supprimer dans toutes les sections
- [ ] Agent standard : sections restreintes masquées
- [ ] Tentative d'accès direct URL sans permission → 403 (pas 500)

### 0.3 Fichiers & Permissions
- [ ] `find /var/www/ikavisite -name "*.py" -not -path "*/venv/*" -user root` → aucun résultat (tout appartient à adminika)
- [ ] `python manage.py check` → 0 erreur

---

## PHASE 1 — Config & Paramétrage (20 min)

### 1.1 Types d'incident
- [ ] Navigation : Incidents > Types d'incident → liste paginée
- [ ] Ajouter : formulaire (Nom, Gravité défaut, Description, Actif)
- [ ] Pas de champ "Ordre" (supprimé)
- [ ] Doublon nom → message erreur
- [ ] Modifier : valeurs pré-remplies, sauvegarde OK
- [ ] Supprimer → confirmation → redirection liste
- [ ] Badge couleur gravité (FAIBLE=vert, GRAVE=rouge, etc.)

### 1.2 Créneaux (Planning)
- [ ] Navigation : Paramétrage > Créneaux → 7 jours affichés
- [ ] Toggle jour ACTIF/INACTIF → sauvegarde via fetch()
- [ ] Ajout créneau horaire → modal, sélection heures
- [ ] Suppression créneau → suppression immédiate
- [ ] Jour INACTIF → opacité réduite, pas d'ajout possible

---

## PHASE 2 — Visiteurs & Visites (40 min)

### 2.1 Visiteurs (CRUD)
- [ ] Liste visiteurs : pagination, recherche par nom/NIP
- [ ] Ajouter visiteur : formulaire complet, validation champs obligatoires
- [ ] NIP unique → doublon refusé
- [ ] Modifier : pré-remplissage, sauvegarde
- [ ] Détail visiteur : infos + historique visites + bouton "Signaler incident"

### 2.2 Visites — Ajout
- [ ] Navigation : Visites > Ajouter
- [ ] **Pas de champ "Porte d'entrée"** visible (retiré)
- [ ] **Pas de champ "Signature d'entrée"** visible (retiré)
- [ ] Recherche visiteur par nom/NIP → sélection
- [ ] Département visible, auto-fill depuis personnel
- [ ] **Personnel visité :**
  - [ ] Heures NORMALES (dans créneaux) → champ masqué (sans astérisque rouge)
  - [ ] Heures HORS NORMES (hors créneaux/jour inactif) → champ visible + astérisque rouge obligatoire
- [ ] Création visite → redirection avec détection (si applicable)

### 2.3 Visites — Détection à l'accueil
- [ ] Visiteur avec **Liste Noire ACTIVE** → 🔴 BLOCAGE, visite non créée, message rouge
- [ ] Visiteur avec **flag_avertissement=True** → 🟠 AVERTISSEMENT orange, visite créée
- [ ] Visiteur avec **incidents passés** (FAIBLE/MOYENNE) → 🟠 AVERTISSEMENT, visite créée
- [ ] Visiteur sans historique → ✅ visite créée normalement

### 2.4 Visites — Listes
- [ ] Liste principale : pagination, filtres, colonnes (visiteur, date, heure, statut, département)
- [ ] Onglet "En cours" : EN_COURS + EXCEDE
- [ ] Onglet "Excédées" : EXCEDE uniquement
- [ ] Onglet "Terminées" : TERMINE + SORTIE_SYSTEME
- [ ] Colonne Département : priorité directe, puis indirecte via personnel

### 2.5 Visites — Terminer
- [ ] Bouton "Terminer" sur visite EN_COURS/EXCEDE
- [ ] Modal sortie : canvas signature présent
- [ ] Possibilité de signaler un incident pendant la sortie
- [ ] Validation → visite passe à TERMINE, date/heure sortie enregistrée

### 2.6 Visites — Sortie Système (23:59)
- [ ] Vérifier présence du script `cloture_visites_systeme.py`
- [ ] Vérifier cron Hermes actif : `cronjob(action='list')`
- [ ] Test manuel : `python manage.py cloture_visites_systeme`
  - [ ] Visites EN_COURS → SORTIE_SYSTEME
  - [ ] Visites EXCEDE → SORTIE_SYSTEME
  - [ ] Motif = "Clôture automatique système"
  - [ ] Heure départ = 23:59:00
- [ ] Aucun statut TERMINE_SYSTEME créé

---

## PHASE 3 — Incidents (30 min)

### 3.1 Ajout incident
- [ ] Recherche personne par nom/prénom/NIP → sélection
- [ ] Badge personne sélectionnée visible + bouton "Changer"
- [ ] Type incident (select depuis TypeIncident) → gravité auto-remplie
- [ ] Formulaire : Titre, Description, Date/Heure, Gravité, Agent rapporteur
- [ ] Soumission → sauvegarde OK

### 3.2 Règles automatiques
- [ ] **GRAVE/CRITIQUE** :
  - [ ] Incident créé → entrée ListeNoire automatique créée
  - [ ] ListeNoire : statut = ACTIF
  - [ ] NIP correctement lié à la personne
- [ ] **FAIBLE/MOYENNE** :
  - [ ] Incident créé → `flag_avertissement` = True sur le Visiteur
  - [ ] PAS de ListeNoire créée

### 3.3 Liste incidents
- [ ] Pagination, recherche
- [ ] Colonnes : Titre, Personne, Type, Gravité, Statut, Date
- [ ] Badge couleur par gravité
- [ ] Bouton "Signaler incident" sur liste visiteurs → pré-remplit personne

### 3.4 Détail incident
- [ ] Infos complètes (titre, description, type, gravité, personne, date)
- [ ] Historique des modifications (HistoriqueAction) visible
- [ ] Visite associée (si depuis une visite) → lien cliquable

### 3.5 Requalification (Phase 4a)
- [ ] Modifier gravité d'un incident → justification obligatoire
- [ ] Passer GRAVE → FAIBLE → ListeNoire associée désactivée (sur demande)
- [ ] Passer FAIBLE → GRAVE → ListeNoire créée automatiquement
- [ ] CLASSE_SANS_SUITE → justification, ListeNoire désactivée
- [ ] Toute modification → HistoriqueAction créée (qui, quand, ancienne valeur, nouvelle valeur)

---

## PHASE 4 — Liste Noire (20 min)

### 4.1 Liste Noire
- [ ] Navigation : Sécurité > Liste noire
- [ ] Colonnes : Nom, Prénom, NIP, Statut, Date début
- [ ] Filtres, pagination
- [ ] Badge ACTIF/INACTIF

### 4.2 Ajout manuel
- [ ] Formulaire simplifié : **Nom** (obligatoire), **Prénom** (obligatoire), NIP (optionnel), N° pièce (optionnel)
- [ ] Pas de champ "Type de liste noire" (auto-assigné)
- [ ] Soumission → sauvegarde OK

### 4.3 Vérification chaînage
- [ ] Créer incident GRAVE → ListeNoire auto-créée avec bon NIP
- [ ] Vérifier que la détection d'accueil bloque ce visiteur ensuite

---

## PHASE 5 — Export & Rapports (15 min)

### 5.1 Exports
- [ ] Visites : Export Excel → colonnes correctes, données complètes
- [ ] Visites : Export PDF → mise en page correcte
- [ ] Incidents : Export Excel
- [ ] Liste Noire : Export Excel
- [ ] Visiteurs : Export Excel

### 5.2 Dashboard
- [ ] Page d'accueil : stats visites du jour, en cours, excédées
- [ ] Chiffres cohérents avec les listes

---

## PHASE 6 — Régressions Rapides (15 min)

### 6.1 Scénarios bout-en-bout
- [ ] Scénario complet : Créer visiteur → Créer visite → Détection OK → Terminer visite
- [ ] Scénario incident : Créer incident GRAVE → ListeNoire auto → Tenter nouvelle visite → Bloqué
- [ ] Scénario vigilance : Créer incident FAIBLE → flag avertissement → Nouvelle visite → Avertissement orange
- [ ] Scénario 23:59 : Créer 3 visites EN_COURS → lancer cloture_visites_systeme → toutes SORTIE_SYSTEME

### 6.2 Mobile Responsive
- [ ] Toutes les pages à ≤640px → pas de scroll horizontal
- [ ] Sidebar mobile → toggle fonctionnel
- [ ] Tableaux → scroll horizontal intégré

### 6.3 Erreurs
- [ ] Page inexistante → 404 propre (pas 500)
- [ ] Accès non autorisé → 403
- [ ] Aucune page ne rend d'erreur 500 en navigation normale

---

## Ordre d'exécution recommandé

```
0.x → 1.x → 2.1 → 2.2 → 2.3 → 2.4 → 2.5 → 2.6
                                          ↓
               3.x ← 1.1 ─────────────────┘
                ↓
               4.x
                ↓
               5.x → 6.x
```

**Priorité bugs critiques :** 0.2 (Super Admin), 2.6 (clôture 23:59), 3.2 (règles auto)

---

> **Livrable :** Pour chaque phase, un rapport concis : ✅ OK / ❌ X échecs avec captures d'écran.
