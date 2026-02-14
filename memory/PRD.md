# RDZ CRM - Product Requirements Document

## Original Problem Statement
Build a central CRM named "RDZ" with strict entity separation (ZR7/MDL). The project includes:
- Lead collection, order management, and automated delivery
- Admin UI with full visibility and control
- Industrial piloting by department and product
- Pricing & billing engine with weekly billing and financial tracking
- Interfacturation interne MDL <-> ZR7
- Vue récapitulative mensuelle
- Dynamic LB Target per commande
- RBAC + Entity Isolation (granular permissions + role presets)
- LB Monitoring widget (super_admin only)

## Architecture
- **Backend:** FastAPI + MongoDB (multi-tenant ZR7/MDL)
- **Frontend:** React + Shadcn/UI, dark theme
- **Key Services:** OVH SMTP for CSV delivery, APScheduler for daily jobs
- **Auth:** JWT sessions, granular permission-based RBAC with role presets

## Implemented Features

### Core: Lead collection, order management, automated delivery, delivery state machine, multi-tenant routing engine

### Admin UI: Dashboard cockpit, entity pages, event log, client 360 view

### Departements Piloting: /admin/departements with filters, data grid, drawer

### Pricing & Billing Engine
- Client product pricing, discounts, TVA, billing modes (WEEKLY_INVOICE/PREPAID)

### Week Navigation Standardization (Feb 2026)

### Interfacturation MDL <-> ZR7 (Feb 2026)

### Vue Récapitulative Mensuelle (Feb 2026)

### LB Target Dynamique (Feb 14, 2026)
- `lb_target_pct` (float 0-1) replaces `lb_percent_max`
- Dynamic Fresh/LB mix: `lb_needed = ceil(target * (delivered + 1)) - lb_delivered`
- `lb_shortfall` event logging, `is_lb` on deliveries

### RBAC + Entity Isolation (Feb 14, 2026)
- **25 granular permission keys** as source of truth, roles as presets
- **Roles:** super_admin, admin, ops, viewer
- **Entity isolation:** strict server-side enforcement on ALL endpoints
- **Entity Scope Switcher** (super_admin only) in sidebar
- **User Management Page** at /admin/users with permission checkbox grid
- **Test accounts:** 7 accounts seeded via `scripts/seed_test_users.py`

### LB Monitoring Widget (Feb 14, 2026)
- Backend: `GET /api/commandes/lb-monitor?entity=ZR7` — returns lb_target vs actual per commande
- Frontend: Collapsible card grid on commandes page showing target/actual/status
- Gated by `monitoring.lb.view` permission (super_admin only)
- Shows: client name, produit, actual %, target %, LB/units count, progress bar, status (on_target/over/under)

## Permission Keys (25)
dashboard.view, leads.view, leads.edit_status, leads.add_note, leads.delete,
clients.view, clients.create, clients.edit, clients.delete,
commandes.view, commandes.create, commandes.edit_quota, commandes.edit_lb_target, commandes.activate_pause, commandes.delete,
deliveries.view, deliveries.resend,
billing.view, billing.manage,
departements.view, activity.view,
settings.access, providers.access, users.manage, monitoring.lb.view

## Test Accounts (dev/staging)
| Email | Role | Entity | Password |
|---|---|---|---|
| superadmin@test.local | super_admin | ZR7 | RdzTest2026! |
| admin_zr7@test.local | admin | ZR7 | RdzTest2026! |
| ops_zr7@test.local | ops | ZR7 | RdzTest2026! |
| viewer_zr7@test.local | viewer | ZR7 | RdzTest2026! |
| admin_mdl@test.local | admin | MDL | RdzTest2026! |
| ops_mdl@test.local | ops | MDL | RdzTest2026! |
| viewer_mdl@test.local | viewer | MDL | RdzTest2026! |

Reset: `cd /app/backend && python scripts/seed_test_users.py`

## Backlog
### P1: Configure transfer pricing via admin UI
### P2: Permissions audit trail, Export des données de facturation
