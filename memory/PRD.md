# RDZ CRM — Product Requirements Document

## Architecture
Backend: FastAPI:8001 | Frontend: React:3000 | DB: MongoDB | Cron: APScheduler (Europe/Paris)
Version: 1.0.0 | Tag: `rdz-core-distribution-validated`

## Implemented — 100 E2E tests PASS

### Core Distribution Layer
Lead ingestion, routing, delivery state machine, dedup 30j, RBAC 40+ perms, entity isolation, billing, intercompany (fail-open), cron

### Phone Normalization
`normalize_phone_fr()`: +33/0033/33, blocked patterns, `phone_quality` (valid/suspicious/invalid)

### Suspicious Phone Policy
Providers/Inter-CRM: reject | Internal LP: LB replacement (atomic)

### Monitoring Intelligence v2 (2026-02-14)
- **Toxicity Score** (0-100): `(dup_rate*2) + susp_rate + rej_rate - deliv_rate`
- **Trust Score** (0-100): `(valid_rate*0.4) + (deliv_rate*0.4) - (dup_rate*0.1) - (susp_rate*0.1)`
- **Cannibalization Index**: cross-entity duplicate rate + first source distribution
- **Duplicate Offenders by Entity**: against_internal_lp, against_provider, against_other_entity
- **Time Buckets**: <1h, 1-24h, 1-7d, >7d
- **Cross-Source Matrix**: with entity info
- Frontend: 4 tabs (Overview, Sources Intelligence, Doublons, Cannibalisation)

## Backlog
- **(P0)** Accounts / LP / Form registry + UI builder
- **(P1)** Invoice PDF, SMTP timeout
- **(P2)** Rate limiting, audit trail UI
