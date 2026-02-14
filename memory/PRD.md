# RDZ CRM - Product Requirements Document

## Original Problem Statement
Build a central CRM named "RDZ" with strict entity separation (ZR7/MDL). The project includes:
- Lead collection, order management, and automated delivery
- Admin UI with full visibility and control
- Industrial piloting by department and product
- Pricing & billing engine with weekly billing and financial tracking
- Interfacturation interne MDL <-> ZR7
- Dynamic LB Target per commande
- RBAC + Entity Isolation (granular permissions + role presets)
- LB Monitoring widget (super_admin only)
- Billing v1: Invoices + Overdue Dashboard

## Architecture
- **Backend:** FastAPI + MongoDB (multi-tenant ZR7/MDL)
- **Frontend:** React + Shadcn/UI, dark theme
- **Key Services:** OVH SMTP for CSV delivery, APScheduler for daily jobs
- **Auth:** JWT sessions, granular permission-based RBAC with role presets

## Implemented Features

### Core: Lead collection, order management, automated delivery, delivery state machine, multi-tenant routing engine

### Admin UI: Dashboard cockpit, entity pages, event log, client 360 view

### Pricing & Billing Engine: Client product pricing, discounts, TVA, billing modes

### LB Target Dynamique (Feb 14, 2026)
- `lb_target_pct` (float 0-1), dynamic Fresh/LB mix formula, `lb_shortfall` event logging

### RBAC + Entity Isolation (Feb 14, 2026)
- 25 granular permission keys, 4 roles (super_admin/admin/ops/viewer)
- Strict server-side entity enforcement on ALL endpoints
- Entity Scope Switcher (super_admin), User Management page
- BOTH scope write safety: writes disabled, "Lecture seule (BOTH)" badge

### LB Monitoring Widget (Feb 14, 2026)
- Backend uses X-Entity-Scope header (no query param)
- Collapsible card grid, gated by monitoring.lb.view

### Billing v1: Invoices + Overdue Dashboard (Feb 14, 2026)
- **Client model:** Added `vat_rate` (0 or 20%), `payment_terms_days` (default 30)
- **Invoice model:** `amount_ht`, `vat_rate`, `amount_ttc` (computed), `invoice_number`, `status` (draft/sent/paid/overdue), `issued_at`, `due_at`, `paid_at`
- **Invoice CRUD:** Create, send (draft→sent), mark-paid (sent/overdue→paid)
- **Overdue auto-detection:** sent invoices past due_at auto-marked overdue
- **Overdue Dashboard:** Per-client totals, grand total TTC, days overdue indicator
- **Frontend:** /admin/invoices with list view (status filters, overdue banner) + overdue tab (KPI cards + detail table)
- **Entity-scoped:** Uses X-Entity-Scope header, respects RBAC

## Test Accounts (dev/staging)
| Email | Role | Entity | Password |
|---|---|---|---|
| superadmin@test.local | super_admin | ZR7 | RdzTest2026! |
| admin_zr7/mdl@test.local | admin | ZR7/MDL | RdzTest2026! |
| ops_zr7/mdl@test.local | ops | ZR7/MDL | RdzTest2026! |
| viewer_zr7/mdl@test.local | viewer | ZR7/MDL | RdzTest2026! |

Reset: `cd /app/backend && python scripts/seed_test_users.py`

## Backlog
### P1: Configure transfer pricing via admin UI
### P2: Invoice PDF generation, Email invoice sending, Permissions audit trail
