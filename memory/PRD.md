# RDZ CRM — Product Requirements Document

## Architecture
Backend: FastAPI:8001 | Frontend: React:3000 | DB: MongoDB | Cron: APScheduler (Europe/Paris)
Version: 1.0.1 | Tag: `rdz-core-distribution-validated`

## Implemented — 92 tests regression suite PASS

### Core Distribution Layer
Lead ingestion, routing, delivery state machine, dedup 30j, RBAC 40+ perms, entity isolation, billing, intercompany (fail-open), cron

### Phone Normalization
`normalize_phone_fr()`: +33/0033/33, blocked patterns, `phone_quality` (valid/suspicious/invalid)

### Suspicious Phone Policy
Providers/Inter-CRM: reject | Internal LP: LB replacement (atomic)

### Monitoring Intelligence v2
Toxicity/Trust scores, cannibalization index, cross-source matrix, time buckets, overlap stats

### Client Overlap Guard
Fail-open, kill switch, 30d window, alternative routing, max 10 candidates, 500ms timeout

### Audit Global Zero Surprises (2026-02-15)
**5 livrables:**
- `/app/ARCHITECTURE_OVERVIEW.md` — Modules, flow E2E 10 etapes, fail-open, endpoints
- `/app/NAMING_SCHEMA_STANDARD.md` — Collections, champs, conventions, mapping API↔DB
- `/app/TEST_MATRIX.md` — Matrice scenarios A-H, chaos checklist, commandes replay
- `/app/DEPLOYMENT_RUNBOOK.md` — Env vars, cron, health, rollback, checklist 5min
- `/app/AUDIT_REPORT_FINAL.md` — Risques P0/P1/P2, fixes appliques, reco
- `/app/RELEASE_POLICY.md` — Politique freeze, procedure merge/rollback

**6 fixes appliques:**
- FIX-1: MONGO_URL/DB_NAME fail-fast
- FIX-2: LeadStatus enum complet (14 statuts)
- FIX-3: LB marking filtre 30j pour leads livres
- FIX-4: Fix $or override leads list (client_id + search)
- FIX-5: Index leads.provider_id
- FIX-6: SMTP timeout=30s

## Backlog
- **(P0) Accounts / LP / Form registry + UI builder** — prochaine phase
- **(P0) C-01: Migration bcrypt** — avant mise en prod
- **(P0) CORS restrictif** — avant mise en prod
- **(P1) Invoice PDF generation**
- **(P1) Prefixer billing routes** (collision /products)
- **(P1) Detection inter-CRM** (format validation)
- **(P2) Rate limiting endpoints publics**
- **(P2) N+1 queries clients/providers**
- **(P2) Unifier champs delivery dupliques**
- **(P2) Audit trail UI**
