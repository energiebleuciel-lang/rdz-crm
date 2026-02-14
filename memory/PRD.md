# RDZ CRM - Product Requirements Document

## Original Problem Statement
Central CRM "RDZ" with strict entity separation (ZR7/MDL). Full lead management pipeline with automated delivery, RBAC, billing, and intercompany transfers.

## Architecture
- **Backend:** FastAPI + MongoDB (multi-tenant ZR7/MDL)
- **Frontend:** React + Shadcn/UI, dark theme
- **Auth:** JWT, 27 granular permission keys, 4 roles
- **Entity Isolation:** X-Entity-Scope header, strict server-side enforcement

## Key Features Implemented

### Core: Lead ingestion, routing engine, delivery state machine, OVH SMTP, APScheduler
### LB Target: Dynamic Fresh/LB mix (`lb_target_pct`), LB Monitor widget
### RBAC: 27 permissions, entity isolation on ALL endpoints, scope switcher, user management
### Billing v1: Invoice CRUD, TTC auto-computation, overdue dashboard
### Entity Scope Audit: Fixed all pages to respect scope switcher

### Intercompany Lead Transfers (Feb 14, 2026)
- **`lead_owner_entity`**: Immutable field set at lead ingestion
- **Trigger**: When delivery becomes billable (status=sent, outcome=accepted) AND owner != target
- **Anti-double**: Unique index on (lead_id, from_entity, to_entity)
- **Pricing**: `intercompany_pricing` collection with per-product rates
- **Transfers**: `intercompany_transfers` with snapshot pricing, week_key, status lifecycle
- **Invoice generation**: `POST /api/intercompany/generate-invoices` aggregates by (from→to) direction
- **Separation**: Intercompany invoices (type=intercompany) excluded from overdue dashboard
- **Event logging**: intercompany_transfer events in event_log + lead timeline
- **Permissions**: `intercompany.view`, `intercompany.manage`

## Collections
clients, commandes, leads (with lead_owner_entity), deliveries (with outcome, accepted_at),
invoices (with type: external|intercompany), intercompany_transfers, intercompany_pricing,
billing_ledger, billing_records, event_log, users, sessions

## Test Accounts
Reset: `cd /app/backend && python scripts/seed_test_users.py`

## Backlog
### P1: Intercompany tab in frontend invoices page
### P2: Invoice PDF generation, cron for weekly invoice generation
