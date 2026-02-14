# RDZ CRM — Product Requirements Document

## Architecture
Backend: FastAPI:8001 | Frontend: React:3000 | DB: MongoDB | Cron: APScheduler (Europe/Paris)
Version: 1.0.1 | Tag: `rdz-core-distribution-validated`

## Implemented — 92+ tests PASS (69 unit + 23 audit)

### Core Distribution Layer
Lead ingestion, routing, delivery state machine, dedup 30j, RBAC 40+ perms, entity isolation, billing, intercompany (fail-open), cron

### Phone Normalization
`normalize_phone_fr()`: +33/0033/33, blocked patterns, `phone_quality` (valid/suspicious/invalid)

### Suspicious Phone Policy
Providers/Inter-CRM: reject | Internal LP: LB replacement (atomic)

### Monitoring Intelligence v2
Toxicity/Trust scores, cannibalization index, cross-source matrix, time buckets, overlap stats

### Client Overlap Guard (2026-02-14)
- **Service**: `services/overlap_guard.py` — soft protection fail-open
- **Detection**: shared client = same delivery email across ZR7/MDL, active if cross-entity delivery in 30d window
- **Routing hook**: if overlap active -> try alternative non-shared commande (max 10 candidates, 500ms timeout)
- **Fallback**: no alternative -> deliver normally + `overlap_fallback_delivery=true`
- **Kill switch**: `overlap_guard` setting (enabled/disabled)

### Audit Global Zero Surprises (2026-02-15)
- **6 livrables produits:** AUDIT_REPORT_FINAL.md, ARCHITECTURE_OVERVIEW.md, NAMING_SCHEMA_STANDARD.md, TEST_MATRIX.md, DEPLOYMENT_RUNBOOK.md, DEPENDENCY_GRAPH.md
- **Findings:** 3 critiques, 14 majeurs, 21 mineurs, 8 info
- **6 fixes appliques:**
  - C-02: MONGO_URL/DB_NAME fail-fast (plus de defaults)
  - C-03: LeadStatus enum complet (14 statuts)
  - M-06: LB marking filtre 30j pour leads livres
  - M-07: Fix $or override dans leads list (client_id + search)
  - m-03: Index leads.provider_id ajoute
  - m-11: SMTP timeout=30s ajoute
- **RELEASE_POLICY.md mis a jour**

## Modules NOT touched
routing_engine.py, duplicate_detector.py, delivery_state_machine.py (core freeze maintenu)

## Backlog
- **(P0) Accounts / LP / Form registry + UI builder** (prochaine phase)
- **(P0) C-01: Migration bcrypt** (avant mise en prod)
- **(P1) Invoice PDF generation**
- **(P1) Unifier champs delivery dupliques (M-01)** delivered_to_client_id vs delivery_client_id
- **(P1) Prefixer billing routes (M-03)** collision /products
- **(P2) Rate limiting endpoints publics (m-02)**
- **(P2) N+1 queries clients/providers (M-04, M-05)**
- **(P2) Audit trail UI**
- **(P2) CORS restrictif en production (m-01)**
