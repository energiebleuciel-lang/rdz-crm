# RDZ CRM - Product Requirements Document

## Original Problem Statement
Build a central CRM named "RDZ" with strict entity separation (ZR7/MDL). Features include lead management, order management, automated delivery, billing, RBAC, and entity isolation.

## Architecture
- **Backend:** FastAPI + MongoDB (multi-tenant ZR7/MDL)
- **Frontend:** React + Shadcn/UI, dark theme
- **Auth:** JWT sessions, granular permission-based RBAC (25 keys, 4 roles)
- **Entity Isolation:** X-Entity-Scope header (super_admin), forced user.entity (others)

## Implemented Features

### Core Systems
- Lead collection, order management, automated delivery (OVH SMTP, APScheduler)
- Delivery state machine, multi-tenant routing engine
- Admin UI: Dashboard cockpit, entity pages, event log, client 360 view
- Departements piloting, week navigation standardization

### LB Target Dynamique (Feb 14, 2026)
- `lb_target_pct` (float 0-1) with dynamic Fresh/LB mix formula
- LB Monitoring widget (super_admin only, gated by monitoring.lb.view)

### RBAC + Entity Isolation (Feb 14, 2026)
- 25 granular permission keys, 4 roles (super_admin/admin/ops/viewer)
- Strict server-side enforcement on ALL endpoints
- BOTH scope write safety (disabled writes, "Lecture seule" badge)

### Billing v1: Invoices + Overdue Dashboard (Feb 14, 2026)
- Invoice CRUD with TTC auto-computation from client vat_rate
- Status lifecycle: draft → sent → paid/overdue
- Overdue dashboard with per-client totals

### Entity Scope Audit & Fix (Feb 14, 2026)
**Root cause:** Frontend pages hardcoded ['ZR7','MDL'] instead of using entityScope
**Fix applied to ALL pages:**
- AdminDashboard: refetches on entityScope change, backend applies entity_filter
- AdminClients: uses entityScope for entity list
- AdminLeads: uses entityScope as effective entity filter
- AdminDeliveries: uses entityScope for entity + client loading
- AdminCommandes: uses entityScope via getEntitiesToLoad
- AdminInvoices: uses entityScope for client loading + refetch
- AdminDepartements: uses entityScope for client loading
**Backend:** dashboard-stats endpoint now reads X-Entity-Scope header and applies filter to ALL aggregations
**Verified:** ZR7=1597 leads, MDL=973 leads, BOTH=2653 — numbers change correctly
**Tests:** 16/16 backend + 100% frontend scope audit passed

## Test Accounts
| Email | Role | Entity | Password |
|---|---|---|---|
| superadmin@test.local | super_admin | ZR7 | RdzTest2026! |
| admin/ops/viewer_zr7@test.local | admin/ops/viewer | ZR7 | RdzTest2026! |
| admin/ops/viewer_mdl@test.local | admin/ops/viewer | MDL | RdzTest2026! |

Reset: `cd /app/backend && python scripts/seed_test_users.py`

## Backlog
### P1: Configure transfer pricing via admin UI
### P2: Invoice PDF generation, Permissions audit trail
