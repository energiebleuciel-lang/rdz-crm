# EnerSolar CRM - Gestion de Leads Solaires

## Problème Original
CRM multi-tenant pour centraliser et redistribuer les leads solaires (PAC, PV, ITE) vers ZR7 Digital et Maison du Lead.

## URL Production
- **API Backend**: https://rdz-group-ltd.online
- **Preview**: https://crm-lead-routing.preview.emergentagent.com

## Fonctionnalités Implémentées

### ✅ Facturation Inter-CRM & Vérification Nocturne (09/02/2026)
- **Page Facturation** (`/billing`): Vue complète des leads cross-CRM
  - Statistiques par période (7 jours, 30 jours)
  - Balances par CRM (à recevoir vs à payer)
  - Transactions détaillées
  - Détail des leads cross-CRM
- **API `/api/billing/cross-crm`**: Calcul automatique des montants
  - Si ZR7 envoie un lead à MDL → MDL doit payer ZR7
  - Prix basé sur `prix_unitaire` des commandes
- **Vérification Nocturne (3h UTC)**: Tâche planifiée APScheduler
  - Vérifie tous les leads des 24 dernières heures
  - Relance automatique des leads échoués (sauf doublons CRM)
  - Génère un rapport de réconciliation
  - API `/api/verification/run` pour exécution manuelle
  - API `/api/verification/status` pour statut

### ✅ Système de Commandes & Routage Cross-CRM
- Routage intelligent des leads basé sur les commandes actives
- Fallback cross-CRM si le CRM principal n'a pas de commande active
- Configurable par formulaire (`allow_cross_crm`)

### ✅ Gestion des Utilisateurs & Permissions
- CRUD complet des utilisateurs
- Rôles: Admin, Editor, Viewer
- Permissions par section

### ✅ Dashboard Départements
- Statistiques par département, produit, source
- Filtres avancés par période et CRM

### ✅ Gestion des Leads Rejetés
- Affichage des raisons d'échec
- Bouton "Relancer" pour les leads échoués

### ✅ Journal d'Activité
- Suivi des actions utilisateurs

### ✅ Autres Fonctionnalités
- Endpoint Public pour Récupérer les Formulaires
- Départements France Métropolitaine (01-95)
- Champs de Récupération de Lead Étendus
- Scripts LP/Form Synchronisés
- Navigation par CRM
- Configuration GTM dans les Comptes
- Configuration Redirection dans les Formulaires

## Architecture Technique

### Backend (V2 - Modulaire)
```
/app/backend/
├── server.py              # Point d'entrée FastAPI + APScheduler
├── config.py              # Configuration, DB, helpers
├── models.py              # Modèles Pydantic
├── routes/
│   ├── auth.py            # Login, sessions, users, permissions
│   ├── accounts.py        # Comptes clients
│   ├── crms.py            # CRMs externes (ZR7, MDL)
│   ├── lps.py             # Landing Pages
│   ├── forms.py           # Formulaires + endpoints publics
│   ├── leads.py           # API v1 + gestion leads
│   ├── tracking.py        # Events LP/Form
│   ├── queue.py           # File d'attente
│   ├── commandes.py       # Gestion des commandes de leads
│   ├── stats.py           # Statistiques par département
│   ├── billing.py         # Facturation inter-CRM
│   └── verification.py    # Vérification nocturne
└── services/
    ├── brief_generator.py      # Génération scripts
    ├── lead_sender.py          # Envoi CRM externe
    ├── activity_logger.py      # Journal d'activité
    ├── billing.py              # Calcul facturation
    └── nightly_verification.py # Vérification nocturne
```

### Frontend (V2 - Modulaire)
```
/app/frontend/src/
├── App.jsx             # Routes principales
├── pages/
│   ├── Dashboard.jsx
│   ├── Accounts.jsx
│   ├── LandingPages.jsx
│   ├── Forms.jsx
│   ├── Leads.jsx
│   ├── Departements.jsx
│   ├── Commandes.jsx
│   ├── Billing.jsx     # Facturation inter-CRM
│   ├── UsersPage.jsx
│   └── Settings.jsx
├── components/
│   ├── Layout.jsx
│   └── UI.jsx
└── hooks/
    ├── useAuth.js
    ├── useApi.js
    └── useCRM.js
```

### Collections MongoDB
- `users`, `sessions` - Auth
- `accounts` - Comptes clients
- `crms` - CRMs externes
- `lps` - Landing Pages
- `forms` - Formulaires
- `leads` - Leads reçus
- `tracking` - Events de tracking
- `lead_queue` - File d'attente
- `commandes` - Commandes de leads
- `activity_logs` - Journal d'activité
- `billing_history` - Historique facturation
- `lead_prices` - Prix des leads
- `verification_reports` - Rapports de vérification nocturne
- `system_config` - Config (API key globale)

## Endpoints API Clés

### Facturation & Vérification
- `GET /api/billing/cross-crm` - Facturation inter-CRM
- `GET /api/billing/cross-crm/summary` - Résumé facturation
- `GET /api/verification/status` - Statut vérification nocturne
- `POST /api/verification/run` - Lancer vérification manuellement
- `GET /api/verification/reports` - Liste des rapports

### Publics (sans auth)
- `GET /api/forms/public/{form_code}` - Récupérer config form
- `GET /api/forms/public/by-lp/{lp_code}` - Forms liés à une LP
- `GET /api/forms/config/departements` - Liste départements FR

### API v1 (Token auth)
- `POST /api/v1/leads` - Soumettre un lead

### Authentifiés (Bearer token)
- `GET /api/forms` - Liste formulaires
- `GET /api/forms/brief/{form_id}` - Brief développeur
- `GET /api/leads` - Liste leads
- `POST /api/leads/{lead_id}/retry` - Relancer un lead

## Credentials Test
- **Email**: energiebleuciel@gmail.com
- **Password**: 92Ruemarxdormoy
- **ZR7 API Key (PV)**: 342b6515-7424-43a6-b5c9-142385fc6ef1
- **MDL API Key (PV)**: 00f4e557-4903-47c6-87db-e3d41460ce45

## Backlog

### P0 - Critique
- [x] URL RDZ pour récupérer les forms (endpoint public)
- [x] Champs de récupération de lead complets
- [x] Départements France métropolitaine (01-95)
- [x] Scripts LP/Form synchronisés
- [x] Facturation Inter-CRM & Prix des leads
- [x] Vérification nocturne (rollback 3h du matin)
- [ ] **Déploiement sur Hostinger** (en attente validation utilisateur)

### P1 - Important
- [ ] Support complet GTM & Redirect tracking
- [ ] Sous-comptes (Sub-accounts)
- [ ] Sources de diffusion
- [ ] Configuration Types de produits

### P2 - Nice to have
- [ ] Bibliothèque d'images
- [ ] Alertes système
- [ ] Mode Campagne A/B Testing

### Technique
- [ ] Vérification SendGrid (dépend action utilisateur)

## Déploiement
- **Preview**: https://crm-lead-routing.preview.emergentagent.com
- **Production**: https://rdz-group-ltd.online (Hostinger VPS - à déployer)
