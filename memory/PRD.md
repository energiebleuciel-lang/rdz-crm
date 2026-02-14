# RDZ CRM — Product Requirements Document

## Original Problem Statement
Build a comprehensive CRM application named "RDZ" to manage leads, orders, and deliveries between two business entities: **ZR7** and **MDL**.

## Core Architecture
- **Backend**: FastAPI (Python) on port 8001
- **Frontend**: React with Tailwind CSS on port 3000
- **Database**: MongoDB (via Motor async driver)
- **Scheduler**: APScheduler (async, Europe/Paris timezone)
- **Version**: 1.0.0 | Tag: `rdz-core-distribution-validated`

## What's Been Implemented

### Core Distribution Layer (VALIDATED — 71 E2E tests PASS)
- Lead ingestion with **phone normalization pipeline** (public API + provider auth)
- Routing engine (priority, quota, departement, duplicate 30-day, cross-entity fallback)
- Delivery state machine (strict transitions, CSV email via OVH SMTP)
- Deduplication (30-day per-client, double-submit protection)
- Granular RBAC (40+ permission keys, 4 role presets)
- Entity isolation (ZR7/MDL, super_admin scope switcher)
- Billing engine (weekly, prepaid, credits, ledger)
- Intercompany transfers (fail-open, health check, retry)
- Production cron (APScheduler, Europe/Paris, DB locks)
- System health monitoring (`/api/system/health`, `/api/system/version`)

### Phone Normalization (2026-02-14)
- **Function**: `normalize_phone_fr()` in `config.py`
- **Pipeline**: strip non-digits → +33/0033/33 prefix → 9-digit mobile → validate 10 digits starts with 0
- **Blocked**: 10 identical digits, sequential (0123456789, 1234567890, etc.), test number 0612345678
- **Quality**: `phone_quality` field on leads (valid/suspicious/invalid)
- **Suspicious patterns**: alternating (0606060606), 7+ same digit — accepted but flagged
- **Migration**: 3243 leads processed, 0 modified, 59 suspicious flagged, 56 invalid tagged
- **36 tests**: normalization + quality + API integration all PASS

## Freeze Artifacts
- `/app/backend/tests/test_core_e2e_validation.py` — 35 tests (A→H)
- `/app/backend/tests/test_phone_normalization.py` — 36 tests
- `/app/CORE_E2E_VALIDATION_REPORT.md`, `/app/RELEASE_POLICY.md`
- `/app/indexes_v1.json` — 70 indexes

## Prioritized Backlog

### P0 - Next Phase
- **Accounts / LP / Form registry + UI builder**

### P1
- Invoice PDF generation
- SMTP timeout hardening (timeout=30)

### P2
- Rate limiting on public endpoints
- Audit trail UI
- External monitoring

## Test Accounts
All use password: `RdzTest2026!`
- superadmin@test.local (super_admin, ZR7)
- admin_zr7/ops_zr7/viewer_zr7 @test.local (ZR7)
- admin_mdl/ops_mdl/viewer_mdl @test.local (MDL)
