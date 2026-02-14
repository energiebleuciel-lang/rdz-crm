# AUDIT REPORT FINAL — RDZ CRM v1.0.0
> Resume des risques + recommandations. Pas un roman.

**Date:** 2026-02-15 | **Tag:** `rdz-core-distribution-validated` | **Scope:** Backend + Frontend + Cron + Config

---

## RISQUES IDENTIFIES

### P0 — Corriger avant prod

| ID | Module | Risque | Impact |
|----|--------|--------|--------|
| P0-1 | `config.py:34` | **Hashage SHA256 pour passwords** | Comptes compromis si fuite DB. Migrer vers bcrypt. |
| P0-2 | `server.py:296` | **CORS `allow_origins=["*"]`** | Requetes cross-origin non controlees en prod. Restreindre au domaine. |

### P1 — Corriger rapidement

| ID | Module | Risque | Impact |
|----|--------|--------|--------|
| P1-1 | `routes/public.py:319` | **Detection inter-CRM fragile** | `api_key: "test"` (non-provider) classe comme inter-CRM → reject si suspect. Ajouter validation format. |
| P1-2 | `routes/billing.py:55` + `routes/commandes.py:108` | **Collision route GET /products** | Deux endpoints identiques. Derniere route gagne silencieusement. Prefixer billing. |
| P1-3 | `models/delivery.py` | **Modele Pydantic incomplet** | 15+ champs en DB absents du modele (outcome, rejected_at, routing_mode, overlap fields...). Trompeur pour un dev. |
| P1-4 | leads schema | **Champs delivery dupliques** | `delivered_to_client_id` (ancien) + `delivery_client_id` (nouveau). Code dedup doit checker les deux. |

### P2 — Backlog

| ID | Module | Risque |
|----|--------|--------|
| P2-1 | Public endpoints | Pas de rate limiting (spam leads) |
| P2-2 | `routes/clients.py:71` | N+1 queries (2 queries par client dans la liste) |
| P2-3 | `routes/providers.py:43` | N+1 queries (1 query par provider) |
| P2-4 | `services/activity_logger.py` + `services/event_logger.py` | Deux systemes de logging (collections differentes) |
| P2-5 | `public.py:158` | Cookie `_rdz_vid` sans `secure=True` |
| P2-6 | Pydantic | `@validator` (v1) au lieu de `@field_validator` (v2) dans plusieurs modeles |

---

## DEJA CORRIGE (dans cette session)

| ID | Fix | Fichier |
|----|-----|---------|
| FIX-1 | MONGO_URL/DB_NAME fail-fast (plus de defaults silencieux) | `config.py` |
| FIX-2 | LeadStatus enum complet (14 statuts reels) | `models/lead.py` |
| FIX-3 | LB marking: filtre 30j pour leads livres (evite LB immediat) | `services/daily_delivery.py` |
| FIX-4 | Fix `$or` override quand client_id + search combines | `routes/leads.py` |
| FIX-5 | Index `leads.provider_id` ajoute | `server.py` |
| FIX-6 | SMTP timeout=30s | `services/csv_delivery.py` |

---

## CE QUI EST SOLIDE

- **Entity isolation:** 100% des endpoints audites filtrent par entity
- **State machine:** Invariants delivery sent/livre respectes, terminal states proteges
- **Fail-open:** overlap_guard, intercompany, monitoring — aucun module secondaire ne bloque la delivery
- **Dedup 30j:** Correct, dual-format supporte (ancien + nouveau)
- **Phone normalization:** Robuste, 36 tests unitaires
- **RBAC:** 40+ permissions granulaires, 4 role presets, super_admin scope BOTH
- **Cron:** Timezone Europe/Paris correcte, intercompany avec anti-double-run

---

## RECOMMANDATIONS

1. **Avant production:** Corriger P0-1 (bcrypt) et P0-2 (CORS) obligatoirement
2. **Sprint suivant:** P1-1 (inter-CRM) et P1-2 (collision routes) — rapides a corriger
3. **Phase Accounts/LP/Forms:** Peut demarrer des que P0 resolus. Les P1/P2 n'impactent pas cette phase.
4. **Tests:** 650+ tests existants, 92 dans la suite rapide de regression. Coverage OK sauf billing (C).
