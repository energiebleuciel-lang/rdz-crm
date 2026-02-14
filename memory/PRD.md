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

## Architecture
- **Backend:** FastAPI + MongoDB (multi-tenant ZR7/MDL)
- **Frontend:** React + Shadcn/UI, dark theme
- **Key Services:** OVH SMTP for CSV delivery, APScheduler for daily jobs

## Implemented Features

### Core: Lead collection, order management, automated delivery, delivery state machine, multi-tenant routing engine

### Admin UI: Dashboard cockpit, entity pages, event log, client 360 view (CRM, performance, pricing, offers tabs)

### Departements Piloting: /admin/departements with filters, data grid, drawer

### Pricing & Billing Engine
- Client product pricing, discounts, TVA, billing modes (WEEKLY_INVOICE/PREPAID)
- Prepayment with auto-blocking, immutable billing_ledger, billing_records

### Week Navigation Standardization (Feb 2026)
- WeekNavStandard on ALL admin pages, format "Semaine du DD/MM/YYYY au DD/MM/YYYY"

### Leads vs LB Display (Feb 2026)
- 8 KPI cards (Units, Leads, LB, Billable, Non-billable, CA HT, CA TTC, Leads prod.)
- Separate Leads/LB columns in weekly invoice + prepaid tables

### Client Creation (Feb 2026)
- Create modal in /admin/clients and /admin/facturation

### Interfacturation MDL <-> ZR7 (Feb 2026)
- entity_transfer_pricing (6 seed items), source_entity/billing_entity on ledger
- Interfacturation records, section in facturation page

### Vue Récapitulative Mensuelle (Feb 2026)
- Onglets Semaine | Mois dans /admin/facturation
- GET /api/billing/month-summary?month=YYYY-MM endpoint
- Agrège billing_records de toutes les semaines chevauchant le mois calendaire
- KPIs mensuels (8 cards dont TVA), tableau récap par client+produit avec colonne Sem.
- Section interfacturation interne mensuelle agrégée
- MonthNavStandard component avec noms de mois en français

### LB Target Dynamique (Feb 14, 2026)
- **New field `lb_target_pct`** (float 0-1) replaces `lb_percent_max` on commandes
- Dynamic Fresh/LB mix per commande: `lb_needed = ceil(target * (delivered + 1)) - lb_delivered`
- Counts only `delivery.status=sent AND outcome=accepted` (rejects/removed excluded)
- `lb_shortfall` event logged when LB needed but unavailable
- `is_lb` field added to delivery records for efficient querying
- Frontend: "LB Target" column in commandes table, create/edit modals, detail page
- All existing commandes migrated from lb_percent_max to lb_target_pct
- Backend: `get_accepted_stats_for_lb_target()`, `compute_lb_needed()` in routing_engine
- Backend: `process_commande_delivery()` rewritten with dynamic targeting in daily_delivery
- 8/8 unit tests pass, 11/11 API tests pass, 100% frontend tests pass

## Key DB Collections
clients, commandes, leads, deliveries, products, client_pricing, client_product_pricing,
prepayment_balances, billing_credits, billing_ledger, billing_records,
entity_transfer_pricing, interfacturation_records, event_log

## Key DB Schema Changes
- **commandes**: Added `lb_target_pct: float` (0-1), `lb_percent_max` deprecated
- **deliveries**: Added `is_lb: bool` on new records
- **event_log**: New action `lb_shortfall` with details (week_key, target_pct, current_pct, lb_needed, available_lb)

## Backlog
### P1: Simple Permissions (admin/ops/viewer), Configure transfer pricing via admin UI
### P2: No additional features specified
