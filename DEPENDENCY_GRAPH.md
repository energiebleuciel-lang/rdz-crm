# DEPENDENCY GRAPH — RDZ CRM v1.0.0

## 1. GRAPHE DES DEPENDANCES MODULES

```
server.py (entrypoint)
  |
  +-- config.py (DB, helpers, normalize_phone_fr)
  |     |
  |     +-- motor (MongoDB async)
  |     +-- dotenv (.env loading)
  |
  +-- routes/
  |     |
  |     +-- auth.py
  |     |     +-- config.py (db, hash_password, generate_token)
  |     |     +-- services/permissions.py
  |     |     +-- services/activity_logger.py
  |     |
  |     +-- public.py  *** POINT D'ENTREE LEADS ***
  |     |     +-- config.py (db, normalize_phone_fr)
  |     |     +-- services/routing_engine.py
  |     |     |     +-- services/duplicate_detector.py
  |     |     |     +-- services/settings.py
  |     |     +-- services/settings.py
  |     |     +-- services/overlap_guard.py (lazy import, fail-open)
  |     |     +-- services/lb_replacement.py (lazy import, fail-open)
  |     |
  |     +-- clients.py
  |     |     +-- config.py
  |     |     +-- routes/auth.py (get_current_user)
  |     |     +-- services/permissions.py
  |     |     +-- services/routing_engine.py (get_week_start)
  |     |     +-- services/settings.py
  |     |     +-- models/client.py
  |     |
  |     +-- commandes.py
  |     |     +-- services/routing_engine.py
  |     |     +-- services/permissions.py
  |     |
  |     +-- deliveries.py
  |     |     +-- services/delivery_state_machine.py
  |     |     +-- services/csv_delivery.py
  |     |     +-- services/settings.py
  |     |     +-- services/permissions.py
  |     |
  |     +-- leads.py
  |     |     +-- services/permissions.py
  |     |     +-- services/settings.py
  |     |     +-- services/routing_engine.py
  |     |
  |     +-- billing.py
  |     |     +-- services/permissions.py
  |     |     +-- services/event_logger.py
  |     |
  |     +-- monitoring.py (READ-ONLY)
  |     |     +-- services/permissions.py
  |     |     +-- services/overlap_guard.py (compute_client_group_key)
  |     |
  |     +-- providers.py
  |     +-- settings.py
  |     +-- invoices.py
  |     +-- intercompany.py
  |     +-- departements.py
  |     +-- event_log.py
  |     +-- system_health.py
  |
  +-- services/
        |
        +-- routing_engine.py
        |     +-- services/duplicate_detector.py
        |     +-- services/settings.py (delivery calendar)
        |
        +-- delivery_state_machine.py
        |     +-- services/intercompany.py (maybe_create_intercompany_transfer)
        |
        +-- daily_delivery.py (CRON)
        |     +-- services/duplicate_detector.py
        |     +-- services/routing_engine.py
        |     +-- services/csv_delivery.py
        |     +-- services/delivery_state_machine.py
        |     +-- services/settings.py
        |     +-- services/event_logger.py
        |
        +-- csv_delivery.py
        |     +-- smtplib (OVH SMTP)
        |
        +-- duplicate_detector.py (STANDALONE)
        |
        +-- overlap_guard.py
        |     +-- services/routing_engine.py (find_open_commandes)
        |     +-- services/duplicate_detector.py
        |
        +-- lb_replacement.py
        |     +-- services/duplicate_detector.py
        |
        +-- intercompany.py
        |     +-- services/event_logger.py
        |
        +-- permissions.py (STANDALONE)
        +-- settings.py (STANDALONE)
        +-- event_logger.py (STANDALONE)
        +-- activity_logger.py (STANDALONE)
```

## 2. BLAST RADIUS

### 2.1 Modifications a haut risque (BLAST RADIUS LARGE)

| Module | Blast Radius | Modules impactes |
|--------|-------------|-------------------|
| `config.py` | MAXIMUM | TOUT le systeme (DB connection, helpers) |
| `routes/auth.py` | TRES HAUT | Tous les endpoints proteges, login, sessions |
| `services/permissions.py` | TRES HAUT | Tous les endpoints admin |
| `services/routing_engine.py` | HAUT | Ingestion leads, delivery quotidienne, overlap guard |
| `services/delivery_state_machine.py` | HAUT | Envoi deliveries, billing (livre = billable) |
| `services/duplicate_detector.py` | HAUT | Routing, LB replacement, overlap guard |

### 2.2 Modifications a risque moyen

| Module | Blast Radius | Modules impactes |
|--------|-------------|-------------------|
| `routes/public.py` | MOYEN | Ingestion leads seulement |
| `services/daily_delivery.py` | MOYEN | Cron quotidien, impact sur livraisons |
| `services/csv_delivery.py` | MOYEN | Format CSV, envoi SMTP |
| `services/settings.py` | MOYEN | Calendar, cross-entity, source gating |

### 2.3 Modifications a faible risque (ISOLE)

| Module | Blast Radius | Impact |
|--------|-------------|--------|
| `routes/monitoring.py` | MINIMAL | Dashboard monitoring (read-only) |
| `routes/billing.py` | MINIMAL | Facturation (pas de lien avec delivery flow) |
| `services/overlap_guard.py` | MINIMAL | Fail-open, kill switch |
| `services/lb_replacement.py` | MINIMAL | Fail-open, remplacement optionnel |
| `services/intercompany.py` | MINIMAL | Fail-open, best-effort |
| `services/event_logger.py` | MINIMAL | Logging non-bloquant |

## 3. DEPENDANCES PYTHON (requirements.txt)

| Package | Usage | Critique |
|---------|-------|----------|
| `fastapi` | Framework API | OUI |
| `uvicorn` | Serveur ASGI | OUI |
| `motor` | MongoDB async driver | OUI |
| `pymongo` | MongoDB sync (pour motor) | OUI |
| `pydantic` | Validation donnees | OUI |
| `python-dotenv` | Chargement .env | OUI |
| `apscheduler` | Scheduler cron | OUI |
| `pytz` | Timezone Europe/Paris | OUI |
| `python-multipart` | File uploads | MOYEN |

## 4. DEPENDANCES FRONTEND (package.json)

| Package | Usage | Critique |
|---------|-------|----------|
| `react` / `react-dom` | Framework UI | OUI |
| `react-router-dom` | Routing | OUI |
| `tailwindcss` | CSS framework | OUI |
| `lucide-react` | Icons | FAIBLE |
| `@radix-ui/*` | Composants Shadcn | MOYEN |
| `sonner` | Toasts | FAIBLE |
| `craco` | Build config override | MOYEN |
