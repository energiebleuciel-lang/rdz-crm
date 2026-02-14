# RDZ CRM — Product Requirements Document

## Original Problem Statement
Build a comprehensive CRM application named "RDZ" to manage leads, orders, and deliveries between two business entities: **ZR7** and **MDL**. The system includes dynamic LB targeting, permission-based RBAC with entity scoping, billing/invoicing, intercompany transfers, and production-ready cron jobs.

## Core Architecture
- **Backend**: FastAPI (Python) on port 8001
- **Frontend**: React with Tailwind CSS on port 3000
- **Database**: MongoDB (via Motor async driver)
- **Scheduler**: APScheduler (async, Europe/Paris timezone)

## What's Been Implemented

### Phase 1: Core CRM
- Lead ingestion (public API + provider auth)
- Routing engine (priority, quota, departement, duplicate 30-day rule)
- Delivery state machine (strict transitions, CSV email)
- Client CRUD with deliverability checks
- Commande CRUD with quota management

### Phase 2: Advanced Features
- Dynamic LB Target (lb_target_pct per commande)
- Cross-entity fallback routing (ZR7 ↔ MDL)
- Calendar gating (delivery days per entity)
- Source gating (blacklist)
- Prepayment balance system

### Phase 3: RBAC & Entity Scoping
- Granular permission system (40+ permission keys)
- Role presets: super_admin, admin, ops, viewer
- Entity isolation (ZR7/MDL strict scoping)
- Super_admin scope switcher (ZR7/MDL/BOTH)
- Write blocking in BOTH scope

### Phase 4: Billing & Invoicing
- External client invoices (draft → sent → paid → overdue)
- Overdue dashboard with per-client aggregation
- Billing ledger + records (weekly snapshot)
- Client pricing engine (per-product, discounts, VAT)

### Phase 5: Intercompany
- Delivery-based transfer tracking
- Intercompany pricing management
- Weekly invoice generation (cron)
- Fail-open architecture (never blocks deliveries)
- Health check + retry endpoints

### Phase 6: Production Audit (2026-02-14)
- **12 issues found and fixed:**
  - 4 entity scope fixes (leads, deliveries endpoints)
  - 6 permission guard fixes (settings, providers, billing, departements)
  - 1 fail-open dashboard (per-widget isolation)
  - 1 new system health endpoint
  - DB indexes added (deliveries: 9, invoices: 5, event_log: 3)
- **15/15 audit tests passed**
- Comprehensive audit report at `/app/AUDIT_REPORT_PRODUCTION.md`

## Prioritized Backlog

### P1 - Next
- Invoice PDF generation (client + intercompany)
- Comprehensive audit trail UI

### P2 - Future
- Full CRUD interface for intercompany pricing
- UI/UX improvements
- Export capabilities (CSV/PDF for reports)

## Test Accounts
All use password: `RdzTest2026!`
- superadmin@test.local (super_admin, ZR7)
- admin_zr7@test.local (admin, ZR7)
- ops_zr7@test.local (ops, ZR7)
- viewer_zr7@test.local (viewer, ZR7)
- admin_mdl@test.local (admin, MDL)
- ops_mdl@test.local (ops, MDL)
- viewer_mdl@test.local (viewer, MDL)
