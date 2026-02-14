# RDZ CRM — Product Requirements Document

## Original Problem Statement
Build a comprehensive CRM "RDZ" managing leads, orders, and deliveries between ZR7 and MDL entities.

## Core Architecture
- **Backend**: FastAPI on port 8001 | **Frontend**: React on port 3000 | **DB**: MongoDB | **Cron**: APScheduler (Europe/Paris)
- **Version**: 1.0.0 | Tag: `rdz-core-distribution-validated`

## What's Been Implemented

### Core Distribution Layer (VALIDATED — 81 E2E tests PASS)
- Lead ingestion with phone normalization pipeline
- Routing engine with LB replacement for suspicious leads
- Delivery state machine, deduplication (30-day per-client)
- Granular RBAC (40+ permissions), entity isolation (ZR7/MDL)
- Billing engine, intercompany transfers (fail-open), cron jobs

### Phone Normalization (2026-02-14)
- `normalize_phone_fr()`: +33/0033/33 prefix, 9-digit mobile, blocked patterns
- `phone_quality` field: valid/suspicious/invalid
- Migration: 3243 leads processed

### Suspicious Phone Policy (2026-02-14)
- **Providers/Inter-CRM**: suspicious → rejected immediately, no lead created
- **Internal LP**: suspicious → accepted, LB replacement attempted before delivery
- `try_lb_replacement()`: atomic reservation (findOneAndUpdate), dedup-checked
- Fields: `was_replaced`, `replacement_source`, `replacement_lead_id`, `lead_source_type`
- 10 dedicated tests + 71 regression = 81/81 PASS

## Files Modified (Suspicious Policy)
- `backend/routes/public.py`: rejection gate + LB replacement hook
- `backend/services/lb_replacement.py`: NEW — atomic LB selection
- `backend/tests/test_suspicious_policy.py`: NEW — 10 E2E tests

## Modules NOT touched
routing_engine, duplicate_detector, delivery_state_machine, RBAC, entity scoping

## Prioritized Backlog
- **(P0)** Accounts / LP / Form registry + UI builder
- **(P1)** Invoice PDF, SMTP timeout
- **(P2)** Rate limiting, audit trail UI

## Test Accounts
Password: `RdzTest2026!` — superadmin/admin_zr7/ops_zr7/viewer_zr7/admin_mdl/ops_mdl/viewer_mdl @test.local
