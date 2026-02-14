# RDZ CRM — Product Requirements Document

## Original Problem Statement
CRM "RDZ" managing leads, orders, deliveries between ZR7 and MDL entities.

## Architecture
Backend: FastAPI:8001 | Frontend: React:3000 | DB: MongoDB | Cron: APScheduler (Europe/Paris)
Version: 1.0.0 | Tag: `rdz-core-distribution-validated`

## Implemented — 95 E2E tests PASS

### Core Distribution Layer
- Lead ingestion, routing engine, delivery state machine, deduplication 30j
- RBAC (40+ permissions), entity isolation (ZR7/MDL), super_admin scope switcher
- Billing engine, intercompany transfers (fail-open), cron jobs

### Phone Normalization
- `normalize_phone_fr()`: +33/0033/33, blocked patterns, `phone_quality` field

### Suspicious Phone Policy
- Providers/Inter-CRM: reject suspicious | Internal LP: LB replacement
- `try_lb_replacement()`: atomic reservation, dedup-checked

### Monitoring Intelligence Layer (2026-02-14)
- **Backend**: `GET /api/monitoring/intelligence?range=24h|7d|30d|90d&product=PV`
  - Phone quality by source (with trend vs previous period)
  - Duplicate rate by source + cross-source conflict matrix + delay buckets
  - Rejection stats by source/reason
  - LB replacement efficiency
  - Core KPIs: deliverability rate, clean rate, economic yield
- **Frontend**: Full dashboard with 7 KPI cards, 4 widgets, source ranking table
- **Entity scoping**: strict via X-Entity-Scope, tested
- **Fail-open**: per-widget isolation
- **Performance**: <5s for 30d, <10s for 90d
- **Indexes added**: phone_quality, lead_source_type, source

## Prioritized Backlog
- **(P0)** Accounts / LP / Form registry + UI builder
- **(P1)** Invoice PDF, SMTP timeout
- **(P2)** Rate limiting, audit trail UI

## Test Accounts
Password: `RdzTest2026!` — superadmin/admin_zr7/ops_zr7/viewer_zr7/admin_mdl/ops_mdl/viewer_mdl @test.local
