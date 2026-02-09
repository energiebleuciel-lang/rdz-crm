# EnerSolar CRM - Gestion de Leads Solaires

## Problème Original
CRM multi-tenant pour centraliser et redistribuer les leads solaires (PAC, PV, ITE) vers ZR7 Digital et Maison du Lead.

## URL Production
- **API Backend**: https://rdz-group-ltd.online
- **Preview**: https://leadsolar-2.preview.emergentagent.com

## Fonctionnalités Implémentées

### ✅ Endpoint Public pour Récupérer les Formulaires (09/02/2026)
- **GET /api/forms/public/{form_code}**: Récupérer un formulaire par son code sans authentification
- **GET /api/forms/public/by-lp/{lp_code}**: Récupérer les formulaires liés à une LP
- Retourne: infos form, LP liée, compte (logos, couleurs)

### ✅ Endpoint Départements France Métropolitaine (09/02/2026)
- **GET /api/forms/config/departements**: Liste des 96 départements (01-95 + 2A, 2B)
- Format: `{"code": "75", "nom": "Paris"}`

### ✅ Champs de Récupération de Lead Étendus (09/02/2026)
Nouveaux champs disponibles dans l'API v1/leads:
- **Identité**: phone (obligatoire), nom, prenom, civilite, email
- **Localisation**: code_postal, departement, ville, adresse
- **Logement**: type_logement, statut_occupant, surface_habitable, annee_construction, type_chauffage
- **Énergie**: facture_electricite, facture_chauffage
- **Projet**: type_projet, delai_projet, budget
- **Tracking**: lp_code, liaison_code, source, utm_source, utm_medium, utm_campaign
- **Consentement**: rgpd_consent, newsletter

### ✅ Scripts LP/Form Synchronisés (09/02/2026)
- Scripts générés dans le Brief avec code de liaison automatique
- Format: `{LP_CODE}_{FORM_CODE}`
- UTM tracking transmis de LP vers Form
- URL de production: https://rdz-group-ltd.online

### ✅ Configuration GTM dans les Comptes (09/02/2026)
- Champs GTM HEAD, BODY et Conversion
- Type de tracking par défaut configurable
- Options: Redirection, GTM, Les deux

### ✅ Configuration Redirection dans les Formulaires (09/02/2026)
- Option "Que faire après la soumission du lead ?"
- Choix: Redirection, GTM, Les deux, Rien (le form gère)
- URL de redirection configurable

## Architecture Technique

### Backend (V2 - Modulaire)
```
/app/backend/
├── server.py           # Point d'entrée FastAPI
├── config.py           # Configuration, DB, helpers
├── models.py           # Modèles Pydantic
├── routes/
│   ├── auth.py         # Login, sessions, API key
│   ├── accounts.py     # Comptes clients
│   ├── crms.py         # CRMs externes (ZR7, MDL)
│   ├── lps.py          # Landing Pages
│   ├── forms.py        # Formulaires + endpoints publics
│   ├── leads.py        # API v1 + gestion leads
│   ├── tracking.py     # Events LP/Form
│   └── queue.py        # File d'attente
└── services/
    ├── brief_generator.py  # Génération scripts
    └── lead_sender.py      # Envoi CRM externe
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
│   └── Settings.jsx
├── components/
│   ├── Layout.jsx
│   └── UI.jsx
└── hooks/
    ├── useAuth.js
    └── useApi.js
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
- `system_config` - Config (API key globale)

## Endpoints API Clés

### Publics (sans auth)
- `GET /api/forms/public/{form_code}` - Récupérer config form
- `GET /api/forms/public/by-lp/{lp_code}` - Forms liés à une LP
- `GET /api/forms/config/departements` - Liste départements FR
- `POST /api/track/lp-visit` - Track visite LP
- `POST /api/track/cta-click` - Track clic CTA
- `POST /api/track/form-start` - Track début form

### API v1 (Token auth)
- `POST /api/v1/leads` - Soumettre un lead

### Authentifiés (Bearer token)
- `GET /api/forms` - Liste formulaires
- `GET /api/forms/brief/{form_id}` - Brief développeur
- `GET /api/leads` - Liste leads
- `GET /api/auth/api-key` - Récupérer clé API globale

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
- [ ] Facturation Inter-CRM & Prix des leads

### P1 - Important
- [ ] Support complet GTM & Redirect tracking
- [ ] Sous-comptes (Sub-accounts)
- [ ] Sources de diffusion
- [ ] Configuration Types de produits

### P2 - Nice to have
- [ ] Bibliothèque d'images
- [ ] Logs d'activité
- [ ] Alertes système
- [ ] Mode Campagne A/B Testing

### Technique
- [ ] Vérification SendGrid (dépend action utilisateur)

## Déploiement
- **Preview**: https://leadsolar-2.preview.emergentagent.com
- **Production**: https://rdz-group-ltd.online (Hostinger VPS - à déployer)
