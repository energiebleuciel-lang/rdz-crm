# RDZ CRM - Product Requirements Document

## Original Problem Statement
Build a central CRM named "RDZ" with strict entity separation (ZR7/MDL). The project includes:
- Lead collection, order management, and automated delivery
- Admin UI with full visibility and control over all backend systems
- Industrial piloting by department and product
- Pricing & billing engine for client pricing, weekly billing, and financial tracking

## Architecture
- **Backend:** FastAPI + MongoDB (multi-tenant ZR7/MDL)
- **Frontend:** React + Shadcn/UI, dark theme
- **Key Services:** OVH SMTP for CSV delivery, APScheduler for daily jobs

## Core Entities
- **Clients:** Entity-separated, delivery config, CRM ratings
- **Commandes:** Weekly quotas per product/department
- **Leads:** Collected, routed, delivered
- **Deliveries:** CSV-based, state machine lifecycle
- **Billing:** Simplified financial tracking (billing_records, not invoices)

## Implemented Features

### Phase 1-2: Backend Foundation
- Lead collection, order management, automated delivery
- Delivery state machine for data integrity
- Multi-tenant routing engine

### Phase 3: Admin UI
- Dashboard cockpit, entity pages, event log
- Client 360 view with CRM, performance, pricing tabs

### Departements Piloting
- `/admin/departements` page with filters, data grid, drawer
- Backend endpoints: GET /api/departements/overview, /api/departements/{dept}/detail

### Pricing & Billing Engine
- Client product pricing, discounts, TVA, billing modes (WEEKLY_INVOICE/PREPAID)
- Prepayment with auto-blocking via routing engine
- Immutable billing_ledger for auditable tracking
- billing_records for external accounting tool

### Week Navigation Standardization (Feb 2026)
- WeekNavStandard component deployed on ALL admin pages
- Pages with WeekNav: Dashboard, Commandes, Deliveries, Leads, Activity, Departements, Facturation
- Display format: "Semaine du DD/MM/YYYY au DD/MM/YYYY"
- week_key (YYYY-W##) is internal only, never shown in UI
- Backend APIs accept optional `week` query parameter on: dashboard-stats, commandes, deliveries, leads/list, event-log
- Client Detail OffersTab uses WeekNav for week selection, weekKeyToShort for display
- Departements chart X axis uses weekKeyToShort format

## Backlog

### P1 - Next
- Simple Permissions: admin/ops/viewer role-based access control

### P2 - Future
- No additional features specified yet
