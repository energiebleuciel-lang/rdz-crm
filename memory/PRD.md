# CRM Multi-tenant - Gestion de Leads Solaires

## Problème Original
Créer un CRM multi-tenant pour la gestion de leads solaires. Le système centralise toutes les informations (logos, images, codes GTM, textes légaux) au niveau du Compte, génère des briefs textuels pour les développeurs, et route les leads vers les CRM destination (ZR7 Digital ou Maison du Lead).

## Architecture Technique

### Stack
- **Frontend**: React 18 avec Tailwind CSS, React Router
- **Backend**: FastAPI (Python)
- **Base de données**: MongoDB
- **Authentification**: JWT

### Flux des Leads
```
[Formulaire Web]
     ↓ (Lead soumis via /api/submit-lead)
[CE CRM] → Stocke le lead
     ↓ (Si phone valide + crm_api_key configurée)
[ZR7 ou MDL] → Envoi instantané via leur API
     ↓ (Job nocturne à 03h00)
[Retry des leads échoués] → POST /api/leads/retry-failed
```

### Structure des Données
```
CRM (MDL ou ZR7)
  └── Compte (plusieurs par CRM)
        ├── Logos (principal, secondaire, petit, favicon)
        ├── Bibliothèque d'images (bannières, produits)
        ├── Codes GTM (pixel, conversion, CTA)
        ├── URLs de redirection nommées
        ├── Textes légaux
        ├── Types de produits
        ├── Landing Pages (avec code HTML)
        └── Formulaires (avec clé API CRM + code HTML)
              ├── crm_api_key (clé ZR7/MDL fournie)
              └── internal_api_key (auto-générée)
```

## APIs CRM Destination
- **ZR7 Digital**: `POST https://app.zr7-digital.fr/lead/api/create_lead/`
- **Maison du Lead**: `POST https://app.maisonsdulead.fr/lead/api/create_lead/`
- **Format**: JSON avec Header `Authorization: <token>`
- **Champs requis**: `phone`, `register_date`
- **Champs optionnels**: `nom`, `prenom`, `email`, `custom_fields`

## Fonctionnalités Implémentées

### Phase 1-5 (Complétées - voir historique)

### Phase 6 - Gestion Utilisateurs Avancée (Complété - 08/02/2026)
- [x] Ajout champ `allowed_accounts` aux utilisateurs
- [x] Interface de sélection des comptes autorisés par utilisateur
- [x] Modal de modification utilisateur avec multi-sélection de comptes

### Phase 7 - Intégration CRM & Lead Routing (Complété - 08/02/2026)
- [x] **Clé API CRM par formulaire** : Chaque formulaire stocke sa `crm_api_key` (ZR7/MDL)
- [x] **Clé API interne auto-générée** : `internal_api_key` UUID générée à la création
- [x] **Envoi instantané des leads** : Si phone valide + config présente → envoi immédiat vers ZR7/MDL
- [x] **Job nocturne retry** : `POST /api/leads/retry-failed?hours=24` pour réessayer les leads échoués
- [x] **Bibliothèque d'images au niveau Compte** : Onglet "Images" pour stocker bannières, produits, etc.
- [x] **Interface formulaire mise à jour** : Section "Intégration CRM (ZR7/MDL)" avec champ clé API
- [x] **Duplication formulaire** : Requiert nouvelle `crm_api_key`, génère nouvelle `internal_api_key`

## API Endpoints Principaux

### Leads
- `POST /api/submit-lead` - Soumet un lead (envoi instantané si config OK)
- `POST /api/leads/retry/{lead_id}` - Réessayer un lead spécifique
- `POST /api/leads/retry-failed?hours=24` - Job nocturne retry des leads échoués
- `DELETE /api/leads/{id}` - Supprimer un lead
- `POST /api/leads/bulk-delete` - Supprimer plusieurs leads

### Formulaires
- `POST /api/forms` - Créer (génère `internal_api_key`)
- `PUT /api/forms/{id}` - Modifier
- `POST /api/forms/{id}/duplicate?new_code=X&new_name=Y&new_crm_api_key=Z` - Dupliquer

### Comptes
- `POST /api/accounts` - Créer (avec `images: [{name, url}]`)
- `PUT /api/accounts/{id}` - Modifier (bibliothèque images incluse)

### Brief Generator
- `POST /api/generate-brief/lp` - Générer brief LP
- `POST /api/generate-brief/form` - Générer brief formulaire

## Credentials de Test
- **Email**: energiebleuciel@gmail.com
- **Password**: 92Ruemarxdormoy

## Tests Effectués
- `/app/test_reports/iteration_1.json` - Tests filtrage CRM (26/26 PASS)
- `/app/test_reports/iteration_2.json` - Tests nouvelles fonctionnalités (32/32 PASS)
- `/app/test_reports/iteration_3.json` - Tests refactoring compte/leads (14/14 PASS)
- `/app/test_reports/iteration_4.json` - Tests intégration CRM (17/17 PASS, 100%)

## Backlog

### P0 - Sécurité (PRIORITAIRE)
- [ ] **Backend filtrage par allowed_accounts** : Les endpoints ne filtrent pas encore les données selon les permissions utilisateur

### P1 - Améliorations
- [ ] Générateur de LP HTML avec style officiel
- [ ] Générateur de Formulaires HTML avec GTM intégré
- [ ] Mise à jour Guide d'utilisation

### P2 - Technique
- [ ] Refactoring Frontend (App.js > 4000 lignes)
- [ ] Refactoring Backend (server.py vers modules)
- [ ] Graphiques visuels dans Dashboard Comparatif
