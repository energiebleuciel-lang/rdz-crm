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
**6 livrables:**
- `ARCHITECTURE_OVERVIEW.md` — Modules, flow E2E 10 etapes, fail-open, endpoints
- `NAMING_SCHEMA_STANDARD.md` — Collections, champs, conventions, mapping API<>DB
- `TEST_MATRIX.md` — Matrice 80+ scenarios, chaos checklist, commandes replay
- `DEPLOYMENT_RUNBOOK.md` — Env vars, cron, health, rollback, checklist 5min
- `AUDIT_REPORT_FINAL.md` — Risques P0/P1/P2, fixes, reco
- `AUDIT_ADDENDUM_POINTS_SENSIBLES.md` — 8 points sensibles: risque, preuve, tests, rollback

**6 fixes appliques:** fail-fast DB, LeadStatus enum, LB 30j, $or fix, provider_id index, SMTP timeout

## Backlog
- **(P0) Accounts / LP / Form registry + UI builder** — prochaine phase
- **(P0) Migration bcrypt** — avant prod
- **(P0) CORS restrictif** — avant prod
- **(P1) Rate limiting (slowapi)** — endpoints publics
- **(P1) Lock cron daily_delivery** — comme intercompany
- **(P1) Invoice PDF generation**
- **(P1) SMTP host/port dans .env**
- **(P2) N+1 queries clients/providers**
- **(P2) Unifier champs delivery dupliques**
- **(P2) Audit trail UI**
