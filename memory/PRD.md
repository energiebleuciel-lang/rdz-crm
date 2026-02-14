# RDZ CRM — Product Requirements Document

## Original Problem Statement
Build a comprehensive CRM application named "RDZ" to manage leads, orders, and deliveries between two business entities: **ZR7** and **MDL**. The system includes dynamic LB targeting, permission-based RBAC with entity scoping, billing/invoicing, intercompany transfers, and production-ready cron jobs.

## Core Architecture
- **Backend**: FastAPI (Python) on port 8001
- **Frontend**: React with Tailwind CSS on port 3000
- **Database**: MongoDB (via Motor async driver)
- **Scheduler**: APScheduler (async, Europe/Paris timezone)
- **Version**: 1.0.0 | Tag: `rdz-core-distribution-validated`

## What's Been Implemented

### Core Distribution Layer (VALIDATED — 35/35 E2E tests PASS)
- Lead ingestion (public API + provider auth + tracking)
- Routing engine (priority, quota, departement, duplicate 30-day rule, cross-entity fallback)
- Delivery state machine (strict transitions, CSV email via OVH SMTP)
- Deduplication (30-day per-client, double-submit protection)
- Granular RBAC (40+ permission keys, 4 role presets)
- Entity isolation (ZR7/MDL strict scoping, super_admin scope switcher)
- Billing engine (weekly, prepaid, credits, ledger)
- Intercompany transfers (fail-open, health check, retry)
- Production cron (APScheduler, Europe/Paris, DB locks)
- System health monitoring (`/api/system/health`, `/api/system/version`)

### Production Audit (2026-02-14)
- 12 issues found and fixed (entity scope, permissions, fail-open dashboard, indexes)
- Full E2E validation: 35 scenarios across 8 categories
- Release policy established

## Freeze Artifacts
- `/app/CORE_E2E_VALIDATION_REPORT.md` — Full E2E proof
- `/app/RELEASE_POLICY.md` — Deployment rules
- `/app/AUDIT_REPORT_PRODUCTION.md` — Audit details
- `/app/indexes_v1.json` — DB index dump (70 indexes)
- `/app/backend/tests/test_core_e2e_validation.py` — 35-test suite

## Prioritized Backlog

### P0 - Next Phase
- **Accounts / LP / Form registry + UI builder** (user's next priority)

### P1
- Phone +33 normalization
- Invoice PDF generation
- SMTP timeout hardening

### P2
- Rate limiting on public endpoints
- Audit trail UI
- Monitoring externe

## Test Accounts
All use password: `RdzTest2026!`
- superadmin@test.local (super_admin, ZR7)
- admin_zr7@test.local / ops_zr7@test.local / viewer_zr7@test.local
- admin_mdl@test.local / ops_mdl@test.local / viewer_mdl@test.local
