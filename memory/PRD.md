# RDZ CRM - Product Requirements Document

## Original Problem Statement
Central CRM "RDZ" with strict entity separation (ZR7/MDL). Full lead management, RBAC, billing, and intercompany transfers.

## Architecture
- **Backend:** FastAPI + MongoDB (multi-tenant ZR7/MDL)
- **Frontend:** React + Shadcn/UI, dark theme
- **Auth:** JWT, 27 granular permission keys, 4 roles
- **Crons:** Livraison 09h30 + Intercompany lundi 08h00

## Key Features

### Core: Lead ingestion, routing engine, delivery state machine, LB Target
### RBAC: 27 permissions, entity isolation, scope switcher, user management
### Billing v1: Invoice CRUD, TTC auto-computation, overdue dashboard

### Intercompany System (Feb 14, 2026)
- **lead_owner_entity**: Immutable field on lead ingestion
- **routing_mode**: "normal" | "fallback_no_orders" on delivery + lead + transfer
- **Trigger**: delivery becomes billable (sent+accepted) AND owner != target
- **Anti-double**: UNIQUE(delivery_id) — delivery-based model
- **Pricing**: intercompany_pricing collection, inline editable in UI
- **Weekly invoice generation**: Idempotent, groups by (from→to) direction
- **Cron**: Monday 08:00 Europe/Paris, auto-generates from pending transfers
- **Frontend**: "Intercompany" tab in Factures page with:
  - Filters: week_key, direction (ZR7→MDL / MDL→ZR7)
  - Table: invoice_number, week, direction, transfers count, total HT, status
  - Detail modal: line items + individual transfer details (delivery_id, lead_id, product, price, routing_mode, date)
  - Pricing admin panel with inline editing
  - "Générer factures" button for manual trigger
- **Separation**: Intercompany invoices excluded from client overdue dashboard

## Collections
leads (lead_owner_entity), deliveries (routing_mode, outcome, accepted_at),
invoices (type: external|intercompany), intercompany_transfers, intercompany_pricing,
clients, commandes, users, sessions, event_log

## Backlog
### P2: Invoice PDF generation, permissions audit trail
