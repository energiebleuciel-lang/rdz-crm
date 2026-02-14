# ARCHITECTURE OVERVIEW — RDZ CRM v1.0.0
> Un dev doit comprendre le systeme en 10 minutes avec ce fichier.

---

## MODULES

### Backend (`/app/backend/`)

| Dossier | Fichiers | Role |
|---------|----------|------|
| `server.py` | Entrypoint | App FastAPI, indexes DB, cron APScheduler |
| `config.py` | Config | DB connection, helpers (hash, token, phone normalization) |
| `models/` | 7 fichiers | Pydantic: lead, delivery, client, commande, provider, auth, entity |
| `routes/` | 15 fichiers | API endpoints (auth, public, clients, commandes, deliveries, leads, billing, monitoring, settings, providers, invoices, intercompany, departements, event_log, system_health) |
| `services/` | 11 fichiers | Logique metier (routing, dedup, delivery state machine, daily delivery cron, CSV email, overlap guard, LB replacement, intercompany, permissions, settings, event/activity logger) |
| `scripts/` | 2 fichiers | seed_test_users, migrate_normalize_phones |
| `tests/` | 35+ fichiers | pytest (E2E, unit, simulation) |

### Frontend (`/app/frontend/src/`)

| Dossier | Role |
|---------|------|
| `App.jsx` | Router principal, routes protegees |
| `pages/` | 25 pages (Dashboard, Leads, Clients, Commandes, Deliveries, Billing, Monitoring, Settings, Users, etc.) |
| `components/` | Layout, WeekNav, AdminLayout, UI components |
| `hooks/` | useAuth, useApi, useCRM, useEntityScope |

### Cron (APScheduler, in-process)

| Job | Quand | Quoi |
|-----|-------|------|
| `daily_delivery` | 09h30 Europe/Paris, tous les jours | Traite pending_csv, marque LB, livre par entity |
| `intercompany_invoices` | Lundi 08h00 Europe/Paris | Genere factures intercompany semaine N-1 |

---

## FLOW E2E — 10 ETAPES

```
1. LP VISIT
   POST /api/public/track/session → cree visitor_session + cookie _rdz_vid
   POST /api/public/track/lp-visit → log tracking event

2. FORM SUBMIT
   POST /api/public/leads
   Body: { phone, nom, departement, session_id, form_code, ... }

3. PHONE NORMALIZATION
   normalize_phone_fr(phone) → format 0XXXXXXXXX
   Qualite: valid | suspicious | invalid
   Provider/interCRM + suspicious → REJECT immediat

4. ANTI DOUBLE-SUBMIT
   Meme session + meme phone < 5 sec → retourne lead existant

5. ENTITY + PRODUIT RESOLUTION
   Provider api_key → entity = provider.entity (verrouillee)
   Sinon → form_code → settings.forms_config → entity + produit
   Sinon → body direct

6. DEDUP 30 JOURS
   Meme phone + meme produit + meme client + < 30 jours → skip ce client
   (le lead peut aller vers un AUTRE client)

7. ROUTING
   Cherche commandes OPEN: active + quota_restant + dept_match + client_livrable
   Priorite: 1 (haute) → 10 (basse)
   Si aucune → cross-entity fallback (si autorise + entity non verrouilee)

8. OVERLAP GUARD (optionnel, fail-open)
   Client partage entre ZR7/MDL + delivery cross-entity < 30j?
   → Cherche alternative non-partagee (max 10 candidats, timeout 500ms)
   → Sinon: livre quand meme (fallback)

9. LB REPLACEMENT (optionnel, fail-open)
   Phone suspect + source internal_lp?
   → Cherche LB compatible (reservation atomique)
   → Sinon: livre le suspect tel quel

10. DELIVERY
    Cree delivery (status=pending_csv) + lead (status=routed)
    → Cron 09h30: genere CSV, envoie email SMTP OVH
    → State machine: pending_csv → [ready_to_send] → sending → sent
    → Lead: routed → livre (UNIQUEMENT via state machine)
```

---

## FAIL-OPEN & KILL SWITCHES

| Module | Comportement en cas d'erreur | Kill switch |
|--------|------------------------------|-------------|
| **Overlap Guard** | Exception/timeout → livre normalement | `settings.overlap_guard.enabled` (DB) |
| **LB Replacement** | Pas de LB dispo → livre le suspect | Aucun (toujours actif si conditions remplies) |
| **Intercompany** | Erreur → log + record status=error, delivery OK | Aucun (fire-and-forget) |
| **Dashboard widgets** | Widget crash → `_errors[]` partiel, autres widgets OK | Aucun |
| **Monitoring** | Widget crash → `_errors[]` partiel | Aucun |
| **Calendar gating** | Jour OFF → deliveries restent pending_csv (pas failed) | `settings.delivery_calendar` (DB) |
| **Source gating** | Source bloquee → lead cree avec status=hold_source | `settings.source_gating.blocked_sources` (DB) |
| **Cross-entity** | Bloque → lead stocke, pas de fallback | `settings.cross_entity.per_entity.out_enabled` (DB) |

---

## ENDPOINTS CLES

### Public (pas d'auth)

| Method | Path | Role |
|--------|------|------|
| POST | `/api/public/track/session` | Cree session visiteur |
| POST | `/api/public/track/lp-visit` | Log visite LP |
| POST | `/api/public/track/event` | Log event generique |
| POST | `/api/public/leads` | **Soumettre un lead** (ingestion principale) |
| GET | `/api/system/version` | Version, tag, git SHA |

### Admin (auth requise — token Bearer)

| Method | Path | Permission | Role |
|--------|------|-----------|------|
| POST | `/api/auth/login` | - | Login |
| GET | `/api/auth/me` | - | User courant |
| GET | `/api/leads/list` | leads.view | Liste leads filtree |
| GET | `/api/leads/dashboard-stats` | leads.view | KPIs cockpit |
| GET | `/api/clients?entity=ZR7` | clients.view | Liste clients |
| GET | `/api/commandes?entity=ZR7` | commandes.view | Liste commandes |
| GET | `/api/deliveries` | deliveries.view | Liste deliveries |
| POST | `/api/deliveries/{id}/send` | admin | Envoyer manuellement |
| POST | `/api/deliveries/{id}/reject-leads` | admin | Rejet client |
| GET | `/api/monitoring/intelligence` | dashboard.view | Dashboard strategique |
| GET | `/api/system/health` | dashboard.view | Sante systeme |
| GET | `/api/billing/week` | billing.view | Dashboard facturation |
| POST | `/api/billing/week/{wk}/build-ledger` | billing.manage | Construire ledger |
| GET | `/api/settings` | settings.access | Tous les settings |
| GET | `/api/providers` | providers.access | Liste providers |

### Provider (auth par API key)

| Method | Path | Auth |
|--------|------|------|
| POST | `/api/public/leads` | `api_key: prov_xxx` dans body ou header `Authorization: Bearer prov_xxx` |
