# ARCHITECTURE OVERVIEW — RDZ CRM v1.0.0

## 1. VUE D'ENSEMBLE

```
+------------------+     +------------------+     +------------------+
|                  |     |                  |     |                  |
|   React SPA      +---->+   FastAPI        +---->+   MongoDB        |
|   (Port 3000)    |     |   (Port 8001)    |     |   (Port 27017)   |
|                  |     |                  |     |                  |
+------------------+     +-------+----------+     +------------------+
                                 |
                          +------+------+
                          |             |
                    +-----+-----+ +----+------+
                    | APScheduler| | OVH SMTP  |
                    | (in-proc)  | | (SSL 465) |
                    +-----+------+ +----+------+
                          |              |
                   09h30 daily     CSV delivery
                   Lun 08h00       emails
                   intercompany
```

## 2. COMPOSANTS

### 2.1 Frontend (React SPA)
- **Framework:** React 18 + TailwindCSS + Shadcn/UI
- **Routing:** React Router v6
- **State:** Hooks (useAuth, useApi, useCRM, useEntityScope)
- **Build:** CRACO (CRA override)
- **URL config:** `REACT_APP_BACKEND_URL` (env)

### 2.2 Backend (FastAPI)
- **Framework:** FastAPI + Uvicorn
- **Auth:** Token-based (SHA256 hash, sessions en DB, 7j TTL)
- **RBAC:** 40+ permissions granulaires, 4 roles presets
- **Scheduler:** APScheduler AsyncIO (in-process)

### 2.3 Base de donnees (MongoDB)
- **Driver:** Motor (async)
- **Collections:** 42 (voir Section 5)
- **Indexes:** 60+ (crees au demarrage)

### 2.4 Services externes
- **OVH SMTP:** `ssl0.ovh.net:465` (ZR7 + MDL)
- **Aucune autre dependance externe**

---

## 3. FLOW END-TO-END (E2E)

### 3.1 Flux Principal: LP Visit -> Lead -> Delivery

```
[Visiteur]
    |
    v
POST /api/public/track/session
    |  -> Cree visitor_session
    |  -> Set cookie _rdz_vid
    v
POST /api/public/track/lp-visit
    |  -> Log tracking event
    |  -> Anti-doublon 1 par session
    v
POST /api/public/leads
    |
    |  === PIPELINE INGESTION ===
    |
    |  1. PROVIDER AUTH
    |     api_key present?
    |     +-- prov_xxx -> lookup providers -> entity_locked
    |     +-- autre    -> is_intercrm = true
    |     +-- absent   -> direct / LP
    |
    |  2. PHONE NORMALIZATION
    |     normalize_phone_fr(phone)
    |     -> status: valid | invalid
    |     -> quality: valid | suspicious | invalid
    |     -> format: 0XXXXXXXXX
    |
    |  3. SUSPICIOUS PHONE POLICY
    |     provider/intercrm + suspicious?
    |     +-- OUI -> REJECT (HTTP 200, error)
    |     +-- NON -> continue
    |
    |  4. ANTI DOUBLE-SUBMIT
    |     same session + phone < 5sec?
    |     +-- OUI -> return existing lead_id
    |     +-- NON -> continue
    |
    |  5. ENTITY + PRODUIT RESOLUTION
    |     provider?    -> entity = provider.entity
    |     form_code?   -> lookup settings.forms_config
    |     body direct? -> entity + produit from body
    |
    |  6. SOURCE GATING
    |     source in blocked_sources?
    |     +-- OUI -> status = hold_source
    |     +-- NON -> continue
    |
    |  7. LEAD CREATION
    |     -> INSERT leads
    |     -> status = new | invalid | hold_source | pending_config
    |
    |  8. ROUTING IMMEDIAT (si eligible)
    |     route_lead(entity, produit, dept, phone)
    |     |
    |     |  a. Calendar gating
    |     |     -> jour OFF? -> no_open_orders
    |     |
    |     |  b. find_open_commandes(entity)
    |     |     -> active + quota_restant + dept_match
    |     |     -> client_actif + deliverable + prepaid_check
    |     |     -> LB target check (si is_lb)
    |     |
    |     |  c. Doublon 30 jours par client
    |     |     -> phone + produit + client_id + 30j
    |     |
    |     |  d. Cross-entity fallback
    |     |     -> si no_open_orders + !entity_locked
    |     |     -> check settings + other entity commandes
    |     |
    |     +-- SUCCESS: client_id + commande_id
    |     +-- FAIL: no_open_orders | duplicate
    |
    |  9. OVERLAP GUARD (si routed + guard_enabled)
    |     check_overlap_and_find_alternative()
    |     -> shared client? -> cross-entity delivery 30d?
    |     -> alternative non-shared commande?
    |     +-- OUI -> switch routing target
    |     +-- NON -> fallback delivery (fail-open)
    |
    | 10. LB REPLACEMENT (si suspicious + internal_lp)
    |     try_lb_replacement()
    |     -> find compatible LB (atomic reserve)
    |     +-- OUI -> deliver LB instead, mark original replaced
    |     +-- NON -> deliver suspicious normally
    |
    | 11. DELIVERY CREATION
    |     -> INSERT deliveries (status=pending_csv)
    |     -> UPDATE lead (status=routed)
    |
    v
[Delivery pending_csv]
```

### 3.2 Flux Quotidien: Cron 09h30

```
run_daily_delivery()
    |
    |  1. process_pending_csv_deliveries()
    |     -> Pour chaque delivery pending_csv:
    |        a. Calendar gating (skip si jour OFF)
    |        b. Client deliverable check
    |        c. auto_send_enabled?
    |           +-- OUI: send CSV email -> mark sent/livre
    |           +-- NON: mark ready_to_send (CSV genere)
    |
    |  2. mark_leads_as_lb()
    |     -> new/non_livre > 8 jours -> LB
    |     -> livre (any age) -> LB
    |
    |  3. process_entity_deliveries("ZR7")
    |  4. process_entity_deliveries("MDL")
    |     -> Pour chaque entity:
    |        a. Get fresh_leads + lb_leads
    |        b. Get active_commandes
    |        c. Pour chaque commande:
    |           - LB target dynamic mix
    |           - 3 passes: fresh -> LB new -> LB recycled
    |           - Doublon check per lead/client
    |        d. deliver_leads_to_client() via state_machine
    |
    |  5. Save delivery_report
    v
[Report saved]
```

### 3.3 Flux Intercompany

```
delivery_state_machine.mark_delivery_sent()
    |
    +-> maybe_create_intercompany_transfer()
        |  lead.lead_owner_entity != target_entity?
        |  +-- OUI -> create transfer record (pending)
        |  +-- NON -> no transfer needed
        |
        +-> Cron Monday 08h00:
            generate_weekly_invoices_internal()
            -> Aggregate transfers by week
            -> Create interfacturation_records
```

---

## 4. FRONTIERES: CORE vs EXTENSIONS

```
+================================================================+
|                      CORE (GELE / FREEZE)                      |
|                                                                |
|  routing_engine.py    duplicate_detector.py                    |
|  delivery_state_machine.py    daily_delivery.py                |
|  auth.py (login/session)    permissions.py                     |
|  entity isolation    RBAC enforcement                          |
|                                                                |
|  REGLE: Aucune modification sans E2E test pass (114 tests)     |
+================================================================+

+---------------------------+  +-----------------------------+
|   EXTENSION: Data Quality |  |   EXTENSION: Monitoring     |
|                           |  |                             |
| normalize_phone_fr()      |  | monitoring.py (READ-ONLY)   |
| lb_replacement.py         |  | system_health.py            |
| overlap_guard.py          |  | AdminMonitoringIntelligence |
|                           |  |                             |
| REGLE: Fail-open,         |  | REGLE: Fail-open per-widget|
| jamais bloquer delivery   |  | Jamais modifier les donnees |
+---------------------------+  +-----------------------------+

+---------------------------+  +-----------------------------+
| EXTENSION: Billing        |  | EXTENSION: Tracking         |
|                           |  |                             |
| billing.py                |  | public.py (track/*)         |
| invoices.py               |  | visitor_sessions            |
| intercompany.py           |  | tracking events             |
|                           |  |                             |
| REGLE: Calcul seulement,  |  | REGLE: Fire-and-forget,    |
| ne bloque jamais delivery |  | jamais bloquer ingestion    |
+---------------------------+  +-----------------------------+
```

---

## 5. COLLECTIONS MONGODB (42)

| Collection | Description | Indexes |
|------------|-------------|---------|
| `users` | Comptes utilisateurs | email (unique) |
| `sessions` | Sessions auth (token, TTL 7j) | token, expires_at |
| `leads` | Leads (3392 docs) | 16 indexes (phone, entity, produit, status, routing composite, LB, monitoring, double-submit) |
| `clients` | Clients acheteurs | entity, (entity+email unique) |
| `commandes` | Commandes hebdo | entity, (entity+client+produit+active) |
| `deliveries` | Livraisons individuelles | 11 indexes (entity, status, client, lead, commande, overlap) |
| `delivery_batches` | Batches CSV historiques | entity, sent_at |
| `delivery_reports` | Rapports cron quotidiens | run_at |
| `providers` | Fournisseurs externes | slug (unique), api_key (unique), entity |
| `settings` | Config dynamique (cross-entity, source gating, calendar, forms, denylist, overlap_guard) | key |
| `tracking` | Events LP/Form | session_id, lp_code, form_code |
| `visitor_sessions` | Sessions visiteurs | id (unique), visitor_id, lp_code, status |
| `event_log` | Audit trail systeme | created_at, action, entity |
| `activity_logs` | Audit trail utilisateur | created_at |
| `products` | Catalogue produits | code (unique) |
| `client_pricing` | Prix global par client | client_id (unique) |
| `client_product_pricing` | Prix par client/produit | (client_id+product_code unique) |
| `billing_credits` | Offres/credits | (client_id+week_key) |
| `billing_ledger` | Ledger immutable par semaine | week_key, (week_key+client_id+product_code) |
| `billing_records` | Records facturation | (week_key+client_id+product_code+order_id), status |
| `prepayment_balances` | Soldes prepaid | (client_id+product_code unique) |
| `invoices` | Factures | entity, status, client_id, type |
| `entity_transfer_pricing` | Prix transfert interentite | (from+to+product unique) |
| `intercompany_pricing` | Prix intercompany (legacy) | (from+to+product unique) |
| `intercompany_transfers` | Transferts interco | delivery_id (unique), week_key |
| `interfacturation_records` | Records interfacturation | (week_key+from+to) |
| `cron_logs` | Logs execution cron | (job+week_key) |
| `client_activity` | Timeline client CRM | client_id |
| `system_config` | Config systeme (API key) | type |

---

## 6. POINTS DE DECISION

| Point | Acteur | Regle |
|-------|--------|-------|
| Entity routing | Provider API key | Verouille par provider.entity |
| Cross-entity fallback | Settings | cross_entity_enabled + per_entity.out/in |
| Calendar gating | Settings | enabled_days + disabled_dates par entity |
| Doublon 30j | Routing engine | phone + produit + client_id + 30 jours |
| LB classification | Cron daily | age >= 8j OU deja livre |
| Quota check | Routing engine | delivered_this_week < quota_semaine |
| Client deliverable | Client model | Au moins 1 email valide OU API endpoint |
| Source gating | Settings | Blacklist mode |
| Suspicious policy | Public.py | Provider/interCRM -> reject; LP -> LB replace |
| Overlap guard | Settings | Kill switch + 30d window + alternative search |
| Billing: billable | State machine | delivery.status=sent AND outcome=accepted |
| Prepaid block | Routing engine | billing_mode=PREPAID AND units_remaining <= 0 |
| RBAC | Permissions service | 40+ granular permission keys, 4 role presets |
| Entity isolation | Permissions | Non-super_admin forces user.entity, super_admin uses X-Entity-Scope |
