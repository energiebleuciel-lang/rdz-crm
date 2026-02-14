# RDZ CRM — Product Requirements Document

## Architecture
Backend: FastAPI:8001 | Frontend: React:3000 | DB: MongoDB | Cron: APScheduler (Europe/Paris)
Version: 1.0.0 | Tag: `rdz-core-distribution-validated`

## Implemented — 114 E2E tests PASS

### Core Distribution Layer
Lead ingestion, routing, delivery state machine, dedup 30j, RBAC 40+ perms, entity isolation, billing, intercompany (fail-open), cron

### Phone Normalization
`normalize_phone_fr()`: +33/0033/33, blocked patterns, `phone_quality` (valid/suspicious/invalid)

### Suspicious Phone Policy
Providers/Inter-CRM: reject | Internal LP: LB replacement (atomic)

### Monitoring Intelligence v2
Toxicity/Trust scores, cannibalization index, cross-source matrix, time buckets, overlap stats

### Client Overlap Guard (2026-02-14)
- **Service**: `services/overlap_guard.py` — soft protection fail-open
- **Detection**: shared client = same delivery email across ZR7/MDL, active if cross-entity delivery in 30d window
- **Routing hook**: if overlap active → try alternative non-shared commande (max 10 candidates, 500ms timeout)
- **Fallback**: no alternative → deliver normally + `overlap_fallback_delivery=true`
- **Kill switch**: `overlap_guard` setting (enabled/disabled)
- **Delivery fields**: `client_group_key`, `is_shared_client_30d`, `overlap_fallback_delivery`
- **Index**: `(client_group_key, entity, created_at)` on deliveries
- **Monitoring**: shared_clients_count/rate, overlap_deliveries_count/rate, fallback_rate
- **14 tests**: group key, detection, kill switch, delivery fields, monitoring, regression

## Modules NOT touched
routing_engine.py, duplicate_detector.py, delivery_state_machine.py, RBAC, entity scoping

## Backlog
- **(P0)** Accounts / LP / Form registry + UI builder
- **(P1)** Invoice PDF, SMTP timeout
- **(P2)** Rate limiting, audit trail UI
