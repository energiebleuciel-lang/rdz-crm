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
- Prepayment with auto-blocking, immutable billing_ledger, billing_records

### Week Navigation Standardization (Feb 2026)
- WeekNavStandard on ALL admin pages

### Interfacturation MDL <-> ZR7 (Feb 2026)
- entity_transfer_pricing, interfacturation_records

### Vue Récapitulative Mensuelle (Feb 2026)
- Onglets Semaine | Mois dans /admin/facturation

### LB Target Dynamique (Feb 14, 2026)
- `lb_target_pct` (float 0-1) replaces `lb_percent_max`
- Dynamic Fresh/LB mix: `lb_needed = ceil(target * (delivered + 1)) - lb_delivered`
- `lb_shortfall` event logging, `is_lb` on deliveries
- 8/8 unit tests + 11/11 API tests pass

### RBAC + Entity Isolation (Feb 14, 2026)
- **Granular permissions** (25 keys) as source of truth, roles as presets
- **Roles:** super_admin, admin, ops, viewer
- **Entity isolation:** strict server-side enforcement on ALL endpoints
  - Non-super_admin: forced to user.entity, 403 on cross-entity access
  - super_admin: entity scope switcher (ZR7/MDL/BOTH)
- **Backend:** `require_permission(key)` FastAPI dependency on every endpoint
  - `validate_entity_access(user, entity)` on all entity-scoped endpoints
  - deliveries, leads, commandes, clients, billing all protected
- **Frontend:** useAuth with `hasPermission()`, `entityScope`, `setEntityScope()`
  - Menu items auto-hide based on permissions
  - Entity Scope Switcher visible only for super_admin
- **User Management:** /admin/users page (super_admin only)
  - Create/edit users with role preset + manual permission override
  - Permission checkbox grid organized by groups
- **Migration:** energiebleuciel@gmail.com → super_admin, all permissions true
- **Testing:** 20/21 backend tests pass, 100% frontend tests pass
  - Security fixes applied for deliveries + leads entity isolation

## Permission Keys (25)
dashboard.view, leads.view, leads.edit_status, leads.add_note, leads.delete,
clients.view, clients.create, clients.edit, clients.delete,
commandes.view, commandes.create, commandes.edit_quota, commandes.edit_lb_target, commandes.activate_pause, commandes.delete,
deliveries.view, deliveries.resend,
billing.view, billing.manage,
departements.view, activity.view,
settings.access, providers.access, users.manage, monitoring.lb.view

## Key DB Collections
clients, commandes, leads, deliveries, products, client_pricing, client_product_pricing,
prepayment_balances, billing_credits, billing_ledger, billing_records,
entity_transfer_pricing, interfacturation_records, event_log, users, sessions

## Backlog
### P1: LB Monitoring widget (super_admin only, gated by monitoring.lb.view)
### P1: Configure transfer pricing via admin UI
### P2: Permissions audit trail
