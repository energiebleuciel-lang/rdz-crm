# RDZ CRM - Product Requirements Document

## Original Problem Statement
Build a central CRM named "RDZ" with strict entity separation (ZR7/MDL). The project includes:
- Lead collection, order management, and automated delivery
- Admin UI with full visibility and control over all backend systems
- Industrial piloting by department and product
- Pricing & billing engine for client pricing, weekly billing, and financial tracking
- Interfacturation interne MDL <-> ZR7

## Architecture
- **Backend:** FastAPI + MongoDB (multi-tenant ZR7/MDL)
- **Frontend:** React + Shadcn/UI, dark theme
- **Key Services:** OVH SMTP for CSV delivery, APScheduler for daily jobs

## Implemented Features

### Phase 1-2: Backend Foundation
- Lead collection, order management, automated delivery
- Delivery state machine, multi-tenant routing engine

### Phase 3: Admin UI
- Dashboard cockpit, entity pages, event log, client 360 view

### Departements Piloting
- /admin/departements page with filters, data grid, drawer

### Pricing & Billing Engine
- Client product pricing, discounts, TVA, billing modes (WEEKLY_INVOICE/PREPAID)
- Prepayment with auto-blocking, immutable billing_ledger
- billing_records for external accounting tool

### Week Navigation Standardization (Feb 2026)
- WeekNavStandard on ALL admin pages (Dashboard, Commandes, Deliveries, Leads, Activity, Departements, Facturation)
- Format: "Semaine du DD/MM/YYYY au DD/MM/YYYY", week_key internal only

### Leads vs LB Display (Feb 2026)
- KPI cards: Units total, Leads total, LB total, Units billable (with LB breakdown)
- Weekly invoice table: separate Units, Leads, LB columns
- Prepaid section: separate Leads/LB columns
- UnitsDisplay component: "total (LB: X)" format
- Backend summary includes total_leads, total_lb, billable_leads, billable_lb

### Client Creation (Feb 2026)
- "+ Ajouter" button on /admin/clients with create modal (Entity, Name, Email, Phone, Delivery emails)
- "+ Client" button on /admin/facturation with create modal (Entity, Billing mode, Name, Email, Delivery emails, TVA toggle)
- Auto-creates client pricing with default TVA rate

### Interfacturation MDL <-> ZR7 (Feb 2026)
- `entity_transfer_pricing` collection: from_entity, to_entity, product_code, unit_price_ht, active
- Seeded with 6 items (PV/PAC/ITE x MDL->ZR7, ZR7->MDL) at unit_price_ht=0
- `source_entity` (lead.entity) and `billing_entity` (client.entity) added to ledger entries and billing_records
- Build-ledger aggregates cross-entity transfers into `interfacturation_records`
- New section "Interfacturation interne" on /admin/facturation
- Columns: Direction (entity badges), Produit, Units, Leads, LB, Prix int. HT, Total HT, N facture, Statut
- Inline edit for invoice number and status (invoiced/paid)
- TVA interne = 0% (intra-groupe)
- CRUD endpoints: GET/PUT /api/billing/transfer-pricing, GET/PUT /api/billing/interfacturation

## Key DB Collections
- `clients`, `commandes`, `leads`, `deliveries`
- `products`, `client_pricing`, `client_product_pricing`
- `prepayment_balances`, `billing_credits`
- `billing_ledger`, `billing_records`
- `entity_transfer_pricing` (NEW)
- `interfacturation_records` (NEW)
- `event_log`

## Backlog

### P1 - Next
- Simple Permissions: admin/ops/viewer role-based access control
- Configure transfer pricing values via admin UI

### P2 - Future
- No additional features specified
