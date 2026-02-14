# DEPLOYMENT RUNBOOK — RDZ CRM v1.0.0
> Zero surprise en prod. Checklist 5 minutes.

---

## ENV VARS

### Backend (`/app/backend/.env`)

| Variable | Obligatoire | Valeur prod | Note |
|----------|-------------|-------------|------|
| `MONGO_URL` | **OUI** | `mongodb://...` | FAIL-FAST si absent |
| `DB_NAME` | **OUI** | `rdz_production` | FAIL-FAST si absent |
| `BACKEND_URL` | **OUI** | `https://rdz-group-ltd.online` | FAIL-FAST si absent |
| `ZR7_SMTP_PASSWORD` | **OUI** | `***` | Pour envoi CSV email ZR7 |
| `MDL_SMTP_PASSWORD` | **OUI** | `***` | Pour envoi CSV email MDL |
| `ZR7_API_URL` | non | URL CRM | Legacy, non utilise |
| `MDL_API_URL` | non | URL CRM | Legacy, non utilise |

### Frontend (`/app/frontend/.env`)

| Variable | Obligatoire | Valeur prod |
|----------|-------------|-------------|
| `REACT_APP_BACKEND_URL` | **OUI** | `https://rdz-group-ltd.online` |

### SMTP Config (hardcode dans `csv_delivery.py`)

```
ZR7 → ssl0.ovh.net:465 | vos-leads@zr7-digital.fr
MDL → ssl0.ovh.net:465 | livraisonleads@maisonduleads.fr
Timeout: 30 secondes
```

---

## CRON

| Job | Schedule | TZ | Idempotent | Anti-double-run |
|-----|----------|-----|-----------|----------------|
| daily_delivery | **09h30** | Europe/Paris | OUI (state machine: sent=terminal) | Non explicite, mais idempotent |
| intercompany_invoices | **Lundi 08h00** | Europe/Paris | OUI | Lock via `cron_logs` collection (per week_key) |

**Technologie:** APScheduler AsyncIO (in-process, meme PID que FastAPI).

---

## HEALTH ENDPOINTS

| Endpoint | Auth | Quoi verifier | Alerte si |
|----------|------|---------------|-----------|
| `GET /` | - | `{"status": "running"}` | Absent ou erreur |
| `GET /api/system/version` | - | `version`, `tag`, `git_sha` | SHA ne correspond pas au deploy |
| `GET /api/system/health` | Token (dashboard.view) | `status: "healthy"` | status = "degraded" ou "error" |

### Sous-modules health

| Module | Check | Alerte |
|--------|-------|--------|
| `cron` | Dernier run, failed_crons_7d | failed_crons_7d > 0 |
| `deliveries` | failed count, pending_csv count | failed > 10 |
| `intercompany` | error_transfers count | error_transfers > 0 |
| `invoices` | overdue count | overdue > 0 |

---

## ROLLBACK

### Option 1: Emergent Platform (recommande)
1. Aller dans le chat → "Rollback" → selectionner le checkpoint precedent
2. Gratuit, instantane

### Option 2: Manuel
```bash
# Voir les commits recents
git log --oneline -20

# NE PAS faire git reset (casse Emergent)
# Utiliser rollback plateforme
```

### Rollback DB
- Les modifications DB sont **additives** (ajout de champs, pas de suppression)
- Un rollback code ne casse pas les donnees existantes
- **Exception:** migration destructive → backup MongoDB AVANT

---

## CHECKLIST AVANT RELEASE (5 minutes)

### Etape 1: Tests (2 min)
```bash
cd /app/backend
python -m seed  # si DB vierge
python -m pytest tests/test_phone_normalization.py tests/test_overlap_guard.py tests/test_monitoring_intelligence.py tests/test_zero_surprises_audit.py -v
# Attendu: 92/92 PASS
```

### Etape 2: Services (30s)
```bash
sudo supervisorctl status
# Attendu: backend RUNNING, frontend RUNNING, mongodb RUNNING
```

### Etape 3: API (30s)
```bash
API_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2)
curl -s "$API_URL/api/system/version" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'v{d[\"version\"]} tag={d[\"tag\"]} sha={d[\"git_sha\"]}')"
# Attendu: v1.0.0 tag=rdz-core-distribution-validated sha=xxx
```

### Etape 4: Login (30s)
```bash
API_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2)
curl -s -X POST "$API_URL/api/auth/login" -H "Content-Type: application/json" -d '{"email":"superadmin@test.local","password":"RdzTest2026!"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Login OK: {d[\"user\"][\"email\"]} role={d[\"user\"][\"role\"]}')"
```

### Etape 5: Health (30s)
```bash
TOKEN=$(curl -s -X POST "$API_URL/api/auth/login" -H "Content-Type: application/json" -d '{"email":"superadmin@test.local","password":"RdzTest2026!"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
curl -s "$API_URL/api/system/health" -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Status: {d[\"status\"]}')"
# Attendu: Status: healthy
```

### Si un test echoue: NE PAS DEPLOYER.

---

## RISQUES "LOCAL OK / PROD KO"

| Risque | Symptome | Mitigation |
|--------|----------|------------|
| DB mal configuree | Donnees manquantes, erreurs 500 | Verifier logs: `[CONFIG] Using database: xxx` |
| SMTP timeout | Deliveries en "failed" | Timeout 30s ajoute. Surveiller failed count. |
| Timezone cron | Livraisons a la mauvaise heure | APScheduler configure avec `pytz.timezone("Europe/Paris")` |
| CORS | Frontend ne peut pas appeler backend | Modifier `allow_origins` dans `server.py` pour le domaine prod |
| Cookie insecure | `_rdz_vid` sans `secure=True` | Ajouter `secure=True` en production HTTPS |
| Indexes | Conflit si index existant avec schema different | Tous les indexes sont `background=True` |

---

## LOGS

```bash
# Backend stdout
tail -f /var/log/supervisor/backend.out.log

# Backend errors
tail -f /var/log/supervisor/backend.err.log

# Chercher des erreurs specifiques
grep "CRITICAL\|ERROR\|FAILED" /var/log/supervisor/backend.err.log | tail -20

# Chercher un lead specifique
grep "lead_id_prefix" /var/log/supervisor/backend.err.log
```
