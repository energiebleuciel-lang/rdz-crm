# RDZ CRM — Architecture Complète & Handover

> **Date** : Février 2026  
> **Flux unique** : `Lead → RDZ (toujours sauvegardé) → account.crm_routing → send_to_crm`

---

## 1. Lancement local

```bash
# Backend (FastAPI + MongoDB)
cd /app/backend
pip install -r requirements.txt
# Créer .env avec :
#   MONGO_URL=mongodb://localhost:27017
#   DB_NAME=rdz_crm
#   BACKEND_URL=http://localhost:8001
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Frontend (React + Tailwind)
cd /app/frontend
yarn install
# Créer .env avec :
#   REACT_APP_BACKEND_URL=http://localhost:8001
yarn start   # port 3000
```

**Supervisor (production)** :
```bash
sudo supervisorctl restart backend
sudo supervisorctl restart frontend
```

---

## 2. Structure du projet (fichiers ACTIFS uniquement)

```
/app/
├── backend/
│   ├── .env                          # MONGO_URL, DB_NAME, BACKEND_URL
│   ├── server.py                     # Point d'entrée FastAPI, lifespan, CORS, routes
│   ├── config.py                     # DB connection, helpers (hash, now_iso, validate_phone)
│   ├── models.py                     # Pydantic: Account, LP, Form, Lead, CRMProductConfig
│   ├── requirements.txt
│   │
│   ├── routes/
│   │   ├── public.py                 # CRITIQUE: submit_lead, sessions, tracking (pas d'auth)
│   │   ├── accounts.py               # CRUD comptes + crm_routing (avec sécurité API key)
│   │   ├── auth.py                   # Login, sessions, get_current_user
│   │   ├── lps.py                    # CRUD Landing Pages (création auto du Form lié)
│   │   ├── forms.py                  # CRUD Formulaires + brief endpoint + reset stats
│   │   ├── leads.py                  # CRUD Leads + force-send + retry + stats
│   │   ├── crms.py                   # CRUD CRMs externes (ZR7, MDL)
│   │   ├── monitoring.py             # Stats succès par CRM/produit/compte + retry batch
│   │   ├── stats.py                  # Stats par département, timeline
│   │   ├── queue.py                  # File d'attente retry automatique
│   │   ├── billing.py               # Facturation
│   │   ├── media.py                  # Upload logos
│   │   ├── quality_mappings.py       # Mapping utm_campaign → quality_tier
│   │   ├── config.py                 # Endpoint config (CRMs list)
│   │   └── verification.py           # Rapports de vérification
│   │
│   ├── services/
│   │   ├── lead_sender.py            # CRITIQUE: send_to_crm() — unique point d'envoi CRM
│   │   ├── duplicate_detector.py     # Anti double-clic (5s)
│   │   ├── brief_generator.py        # Génération scripts LP/Form (Mode A/B)
│   │   ├── nightly_verification.py   # Job 3h UTC: vérifie et retente les leads
│   │   ├── activity_logger.py        # Journal d'activité
│   │   └── billing.py               # Calcul facturation
│   │
│   └── tests/
│       └── test_account_centric_routing.py  # 10 tests routing (ACTIF)
│
├── frontend/
│   ├── .env                          # REACT_APP_BACKEND_URL
│   ├── package.json
│   └── src/
│       ├── App.jsx                   # Routes React
│       ├── index.js / index.css
│       ├── components/
│       │   ├── Layout.jsx            # Sidebar + CRM selector
│       │   ├── UI.jsx                # Card, Modal, Button, Badge, Input, Select, etc.
│       │   └── RedistributionKeys.jsx
│       ├── hooks/
│       │   ├── useAuth.js            # Auth context + authFetch
│       │   ├── useApi.js             # API base URL
│       │   └── useCRM.js             # CRM context (ZR7/MDL selector)
│       └── pages/
│           ├── Dashboard.jsx         # KPI + queue + leads récents
│           ├── Accounts.jsx          # Comptes + UI routing CRM (PV/PAC/ITE)
│           ├── LandingPages.jsx      # LP + création duo LP+Form
│           ├── Forms.jsx             # Formulaires + briefs + reset stats
│           ├── Leads.jsx             # Liste leads + édition + force-send
│           ├── Monitoring.jsx        # Taux succès + alertes + retry + dictionnaire
│           ├── Login.jsx
│           ├── Departements.jsx
│           ├── Billing.jsx
│           ├── Settings.jsx
│           ├── UsersPage.jsx
│           ├── Media.jsx
│           └── QualityMappings.jsx
│
├── memory/
│   └── PRD.md                        # Product Requirements Document
│
└── ARCHITECTURE.md                   # CE FICHIER
```

### Fichiers MORTS (plus importés, à supprimer) :
```
backend/routes/commandes.py           # Distribution V2 — supprimé du server.py
backend/routes/sub_accounts.py        # Jamais intégré
backend/services/lead_replacement.py  # Système LB — désactivé
backend/services/lead_redistributor.py # Redistribution — désactivé
backend/core_locked.py                # Documentation legacy
backend/schema_locked.py              # Documentation legacy
backend_old/                          # Ancien backend complet — à supprimer
frontend_old/                         # Ancien frontend complet — à supprimer
frontend/src/pages/Commandes.jsx      # Page commandes — retirée du routing
frontend/src/components/RedistributionKeys.jsx  # Legacy
```

---

## 3. Endpoints critiques

### Public (pas d'auth — appelés par les scripts LP/Form)

| Méthode | Endpoint | Rôle |
|---------|----------|------|
| `POST` | `/api/public/track/session` | Créer/réutiliser une session visiteur (anti-doublon 30min) |
| `POST` | `/api/public/track/lp-visit` | Tracker visite LP avec UTM complet (sendBeacon) |
| `POST` | `/api/public/track/event` | Tracker events: `cta_click`, `form_start` (sendBeacon) |
| `POST` | `/api/public/leads` | **SOUMISSION LEAD** — routing + envoi CRM |
| `GET`  | `/api/forms/public/{form_code}` | Config publique d'un formulaire |

### Admin (auth requise)

| Méthode | Endpoint | Rôle |
|---------|----------|------|
| `POST` | `/api/auth/login` | Login → token |
| `GET/POST/PUT/DELETE` | `/api/accounts` | CRUD comptes + crm_routing |
| `GET/POST/PUT/DELETE` | `/api/lps` | CRUD Landing Pages (crée auto le Form) |
| `GET/POST/PUT/DELETE` | `/api/forms` | CRUD Formulaires |
| `GET` | `/api/forms/brief/{form_id}` | Génère le brief (scripts LP + Form) |
| `GET/PUT/DELETE` | `/api/leads` | CRUD Leads |
| `POST` | `/api/leads/{id}/force-send` | Forcer envoi vers un CRM |
| `POST` | `/api/leads/{id}/retry` | Retenter envoi |
| `GET` | `/api/monitoring/stats` | Taux succès par CRM/produit/compte (24h, 7j) + alertes |
| `POST` | `/api/monitoring/retry` | Relancer batch les leads en échec |
| `GET` | `/api/crms` | Liste CRMs (ZR7, MDL) |
| `POST` | `/api/queue/process` | Traiter la file d'attente manuellement |

---

## 4. Où sont stockés les identifiants clés

| Champ | Collection(s) | Défini à | Rôle |
|-------|--------------|----------|------|
| `account_id` | `accounts`, `forms`, `leads`, `lps` | Création du compte | Lie tout à un compte propriétaire |
| `lp_code` | `lps`, `leads`, `visitor_sessions`, `tracking` | Création LP (auto: `LP-001`) | Identifie la Landing Page |
| `form_code` | `forms`, `leads`, `visitor_sessions`, `tracking` | Création Form (auto: `PV-001`) | Identifie le formulaire |
| `liaison_code` | `leads`, `tracking` | Runtime: `{lp_code}_{form_code}` | Lie LP ↔ Form pour attribution |
| `session_id` | `visitor_sessions`, `leads`, `tracking` | Création session (UUID) | Session visiteur unique |
| `product_type` | `forms`, `leads`, `accounts.crm_routing` | Création Form: `PV`/`PAC`/`ITE` | Type de produit |
| `routing_source` | `leads` | Runtime: submit_lead | D'où vient la config CRM: `account_routing`, `form_override`, `none` |
| `target_crm` | `leads`, `forms` (override), `accounts.crm_routing` | Routing account-centric | CRM destination: `zr7` ou `mdl` |

---

## 5. Flow exact : LP → CRM

```
                    VISITEUR
                       │
    ┌──────────────────▼──────────────────┐
    │           LANDING PAGE              │
    │  Script LP injecté (brief)          │
    │                                     │
    │  1. POST /track/session             │
    │     → session_id + visitor_id       │
    │                                     │
    │  2. POST /track/lp-visit            │
    │     → UTM, referrer, gclid, fbclid  │
    │                                     │
    │  3. Clic CTA                        │
    │     POST /track/event (cta_click)   │
    │     → Redirige vers Form            │
    └──────────────────┬──────────────────┘
                       │ ?session=...&lp=...&liaison=...&utm_campaign=...
    ┌──────────────────▼──────────────────┐
    │           FORMULAIRE                │
    │  Script Form injecté (brief)        │
    │                                     │
    │  4. Premier champ touché            │
    │     POST /track/event (form_start)  │
    │                                     │
    │  5. Soumission formulaire           │
    │     POST /api/public/leads          │
    │     {session_id, form_code, phone,  │
    │      nom, prenom, email, dept, ...} │
    └──────────────────┬──────────────────┘
                       │
    ┌──────────────────▼──────────────────┐
    │        BACKEND: submit_lead         │
    │                                     │
    │  6. Valider phone + champs          │
    │  7. Anti double-clic (5s)           │
    │  8. Récupérer form → account_id     │
    │  9. ROUTING ACCOUNT-CENTRIC:        │
    │     a) form.target_crm (override?)  │
    │     b) account.crm_routing[product] │
    │     → target_crm + api_key          │
    │ 10. Créer lead dans RDZ (TOUJOURS)  │
    │ 11. Envoyer au CRM si config OK     │
    └──────────────────┬──────────────────┘
                       │
    ┌──────────────────▼──────────────────┐
    │      send_to_crm(lead, url, key)    │
    │                                     │
    │  POST {api_url}/lead/api/create_lead│
    │  Headers: Authorization: {api_key}  │
    │  Body: {phone, nom, prenom, email,  │
    │         register_date, civilite,    │
    │         custom_fields: {dept, ...}} │
    │                                     │
    │  → 201 = success                    │
    │  → 200 + "doublon" = duplicate      │
    │  → 403 = auth_error                 │
    │  → 400 = validation_error           │
    │  → 5xx = server_error → queue       │
    └─────────────────────────────────────┘
```

---

## 6. Routing Account-Centric (détail)

```python
# Chaque account a un champ crm_routing :
{
  "PV":  {"target_crm": "zr7", "api_key": "uuid-...", "delivery_mode": "api"},
  "PAC": {"target_crm": "mdl", "api_key": "uuid-...", "delivery_mode": "api"},
  "ITE": {"target_crm": "zr7", "api_key": "uuid-...", "delivery_mode": "api"}
}

# Hiérarchie de résolution dans submit_lead :
# 1. form.target_crm + form.crm_api_key → override (si les 2 renseignés + whitelist zr7/mdl)
# 2. account.crm_routing[product_type] → défaut
# 3. Aucun → status=no_crm, lead conservé dans RDZ

# Sécurité API keys :
# - Jamais supprimable une fois configurée (rotation uniquement)
# - Whitelist target_crm : {zr7, mdl}
# - Validation product_type : {PV, PAC, ITE}
```

---

## 7. Templates scripts LP/Form

**Générés par** : `services/brief_generator.py`
**Endpoint** : `GET /api/forms/brief/{form_id}?mode=separate&selected_product=PV`

### Mode A (separate) : LP et Form sur pages différentes
- **Script LP** : session init + lp-visit tracking + CTA click tracking + URL params injection
- **Script Form** : session recovery + form_start tracking + submit lead + GTM conversion + redirection

### Mode B (integrated) : Form intégré dans la LP
- **Script unique** : session + lp-visit + form_start + submit + conversion + redirection

### Versioning
- **Une seule version active** (pas de V1/V2 en parallèle)
- Le brief est **régénéré à chaque appel** — pas de cache, toujours la dernière config
- Variables injectées : `BACKEND_URL`, `form_code`, `lp_code`, `liaison_code`, `redirect_url`, `gtm_conversion`

---

## 8. Schéma DB (MongoDB)

### Collection `accounts`
```json
{
  "id": "uuid",
  "name": "AZ",
  "crm_id": "uuid-du-crm",
  "crm_routing": {
    "PV":  {"target_crm": "zr7", "api_key": "...", "delivery_mode": "api"},
    "PAC": {"target_crm": "zr7", "api_key": "...", "delivery_mode": "api"},
    "ITE": {"target_crm": "zr7", "api_key": "...", "delivery_mode": "api"}
  },
  "logo_main_url": "", "logo_secondary_url": "", "logo_mini_url": "",
  "primary_color": "#3B82F6", "secondary_color": "#1E40AF",
  "redirect_url_pv": "", "redirect_url_pac": "", "redirect_url_ite": "",
  "gtm_head": "", "gtm_body": "", "gtm_conversion": "",
  "cgu_text": "", "privacy_policy_text": "", "legal_mentions_text": "",
  "created_at": "iso", "created_by": "user-id"
}
```

### Collection `lps`
```json
{
  "id": "uuid", "code": "LP-001",
  "account_id": "uuid",
  "name": "Ma LP Solaire", "url": "https://...",
  "product_type": "PV",
  "form_id": "uuid-du-form",
  "form_mode": "redirect", "source_type": "native",
  "status": "active", "created_at": "iso"
}
```

### Collection `forms`
```json
{
  "id": "uuid", "code": "PV-001",
  "account_id": "uuid", "lp_id": "uuid",
  "name": "Form PV", "url": "https://...",
  "product_type": "PV",
  "target_crm": "",      // Override optionnel (vide = utilise account.crm_routing)
  "crm_api_key": "",     // Override optionnel
  "tracking_type": "redirect", "redirect_url": "/merci",
  "status": "active", "created_at": "iso"
}
```

### Collection `leads`
```json
{
  "id": "uuid", "session_id": "uuid",
  "form_id": "uuid", "form_code": "PV-001",
  "account_id": "uuid", "product_type": "PV",
  "phone": "0612345678", "nom": "Doe", "prenom": "John",
  "email": "john@example.com", "civilite": "M.",
  "departement": "75", "ville": "", "adresse": "",
  "type_logement": "maison", "statut_occupant": "proprietaire",
  "surface_habitable": "", "annee_construction": "",
  "type_chauffage": "", "facture_electricite": "", "facture_chauffage": "",
  "type_projet": "", "delai_projet": "", "budget": "",
  "lp_code": "LP-001", "liaison_code": "LP-001_PV-001",
  "utm_source": "", "utm_medium": "", "utm_campaign": "",
  "quality_tier": null,
  "origin_crm": "zr7",
  "target_crm": "zr7",
  "routing_reason": "account_routing_zr7",
  "routing_source": "account_routing",    // account_routing | form_override | none
  "distribution_reason": "account_routing_zr7",
  "api_status": "success",               // success|failed|no_crm|orphan|...
  "sent_to_crm": true,
  "sent_at": "2026-02-13T12:53:19Z",
  "retry_count": 0,
  "phone_invalid": false, "missing_nom": false, "missing_dept": false,
  "form_not_found": false, "is_double_submit": false,
  "register_date": 1739448799,
  "created_at": "2026-02-13T12:53:19Z"
}
```

### Collection `crms`
```json
{
  "id": "uuid", "slug": "zr7", "name": "ZR7 Digital",
  "api_url": "https://app.zr7-digital.fr/lead/api/create_lead/"
}
```

### Collection `visitor_sessions`
```json
{
  "id": "uuid", "visitor_id": "uuid",
  "lp_code": "LP-001", "form_code": "PV-001", "liaison_code": "LP-001_PV-001",
  "utm_source": "", "utm_medium": "", "utm_campaign": "",
  "gclid": "", "fbclid": "",
  "ip": "", "referrer": "", "user_agent": "",
  "status": "converted", "lead_id": "uuid",
  "created_at": "iso"
}
```

### Collection `tracking`
```json
{
  "id": "uuid", "session_id": "uuid", "visitor_id": "uuid",
  "event": "lp_visit",      // lp_visit | cta_click | form_start
  "lp_code": "LP-001", "form_code": "PV-001",
  "account_id": "uuid", "lp_id": "uuid", "form_id": "uuid",
  "utm_source": "", "utm_medium": "", "utm_campaign": "",
  "created_at": "iso"
}
```

---

## 9. Comptes production configurés

| Compte | CRM | PV → | PAC → | ITE → |
|--------|-----|------|-------|-------|
| AZ | ZR7 | zr7 | zr7 | zr7 |
| ZR7 | ZR7 | zr7 | zr7 | zr7 |
| MDL | MDL | mdl | mdl | mdl |
| AUDIT GREEN | MDL | mdl | mdl | mdl |
| OBJECTIF ACADEMIE | MDL | mdl | mdl | mdl |
| SPOOT | MDL | mdl | mdl | mdl |

---

## 10. Preuves E2E (6/6 success)

```
[ROUTING_RESULT] lead_id=aab04cf6 account_id=7cf7cc61(AZ)  product=PV  target=zr7 status=success
[ROUTING_RESULT] lead_id=1c6d1ff9 account_id=7cf7cc61(AZ)  product=PAC target=zr7 status=success
[ROUTING_RESULT] lead_id=fa97a99c account_id=7cf7cc61(AZ)  product=ITE target=zr7 status=success
[ROUTING_RESULT] lead_id=3a730752 account_id=7b4eab12(MDL) product=PV  target=mdl status=success
[ROUTING_RESULT] lead_id=9c9e0a87 account_id=7b4eab12(MDL) product=PAC target=mdl status=success
[ROUTING_RESULT] lead_id=b3cbe5fa account_id=7b4eab12(MDL) product=ITE target=mdl status=success
```

Exemple lead en DB (`sent_to_crm=True`) :
```json
{
  "id": "aab04cf6-9a09-4374-b8f1-7d5b637c73fb",
  "product_type": "PV",
  "account_id": "7cf7cc61-4078-4d42-b175-b9cb849ff547",
  "routing_source": "account_routing",
  "routing_reason": "account_routing_zr7",
  "target_crm": "zr7",
  "api_status": "success",
  "sent_to_crm": true,
  "sent_at": "2026-02-13T12:53:19.656967+00:00"
}
```

---

## 11. Credentials

- **UI Admin** : `energiebleuciel@gmail.com` / `92Ruemarxdormoy`
- **ZR7 API** : `https://app.zr7-digital.fr/lead/api/create_lead/`
- **MDL API** : `https://maison-du-lead.com/lead/api/create_lead/`

---

## 12. Scheduler (APScheduler)

| Heure | Job | Fichier |
|-------|-----|---------|
| 3h UTC | Vérification nocturne + retry leads | `services/nightly_verification.py` |
| Toutes les 5 min | Traitement file d'attente | `services/lead_sender.py:process_queue` |
