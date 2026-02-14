# DEPLOYMENT RUNBOOK — RDZ CRM v1.0.0

## 1. VARIABLES D'ENVIRONNEMENT

### 1.1 Backend (`/app/backend/.env`)

| Variable | Obligatoire | Description | Exemple |
|----------|-------------|-------------|---------|
| `MONGO_URL` | OUI | URI MongoDB | `mongodb://localhost:27017` |
| `DB_NAME` | OUI | Nom base de donnees | `rdz_production` |
| `BACKEND_URL` | OUI | URL publique du backend | `https://rdz-group-ltd.online` |
| `ZR7_SMTP_PASSWORD` | OUI | Password SMTP ZR7 (OVH) | `***` |
| `MDL_SMTP_PASSWORD` | OUI | Password SMTP MDL (OVH) | `***` |
| `ZR7_API_URL` | NON | API CRM ZR7 (legacy) | `https://app.zr7-digital.fr/...` |
| `ZR7_API_KEY` | NON | Cle API ZR7 (legacy) | - |
| `MDL_API_URL` | NON | API CRM MDL (legacy) | `https://maison-du-lead.com/...` |
| `MDL_API_KEY` | NON | Cle API MDL (legacy) | - |

### 1.2 Frontend (`/app/frontend/.env`)

| Variable | Obligatoire | Description |
|----------|-------------|-------------|
| `REACT_APP_BACKEND_URL` | OUI | URL publique (prefixe /api pour le backend) |
| `WDS_SOCKET_PORT` | NON | Port WebSocket (dev only) |

### 1.3 ATTENTION: Variables critiques

- `MONGO_URL` et `DB_NAME` ont des defaults dans le code (`mongodb://localhost:27017`, `test_database`). **En production, TOUJOURS verifier qu'elles pointent vers la bonne DB.**
- `BACKEND_URL` n'a PAS de default — l'app crash si absent (correct).

---

## 2. CRON JOBS

| Job | Schedule | Timezone | Description |
|-----|----------|----------|-------------|
| `daily_delivery` | 09h30 | Europe/Paris | Traite pending_csv + marque LB + livraison quotidienne |
| `intercompany_invoices` | Lundi 08h00 | Europe/Paris | Genere factures intercompany semaine precedente |

### 2.1 Anti double-run
- `daily_delivery`: Pas de lock explicite, mais idempotent via state machine (delivery sent = terminal).
- `intercompany_invoices`: Lock via `cron_logs` collection (per-week_key, status running/success).

### 2.2 SMTP Config (hardcode)
```
ZR7: ssl0.ovh.net:465 | vos-leads@zr7-digital.fr
MDL: ssl0.ovh.net:465 | livraisonleads@maisonduleads.fr
```

---

## 3. HEALTH CHECKS

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /` | Public | Status basique (name, version, status) |
| `GET /api/system/version` | Public | Version, tag, git SHA, build date |
| `GET /api/system/health` | Auth (dashboard.view) | Health agrege (cron, deliveries, transfers, invoices) |

### 3.1 Monitoring recommande
- `/api/system/version` — poll chaque 30s, alerte si indisponible
- `/api/system/health` — poll chaque 5min, alerte si `status != "healthy"`
- Surveiller `delivery_reports` — alerte si aucun rapport depuis >26h (cron skip)

---

## 4. ROLLBACK

### 4.1 Strategie
- **Emergent Platform:** Utiliser la fonctionnalite "Rollback" integree (gratuit, restaure un checkpoint precedent).
- **Git:** `git log` pour identifier le commit cible, puis rollback via la plateforme.

### 4.2 Rollback DB
- Les modifications DB sont additives (ajout de champs, pas de suppression). Un rollback code ne casse pas les donnees existantes.
- **Exception:** Si une migration destructive est effectuee (ex: suppression de champs), un backup DB est requis AVANT.

### 4.3 Commandes utiles
```bash
# Voir les dernieres modifications
git log --oneline -20

# Verifier l'etat du service
sudo supervisorctl status

# Logs backend (erreurs)
tail -n 100 /var/log/supervisor/backend.err.log

# Logs backend (stdout)
tail -n 100 /var/log/supervisor/backend.out.log

# Restart services (si .env modifie)
sudo supervisorctl restart backend
sudo supervisorctl restart frontend
```

---

## 5. CHECKLIST PRE-DEPLOIEMENT

### 5.1 Avant chaque deploiement
- [ ] Tous les tests E2E passent (`cd /app/backend && python -m pytest tests/ -v`)
- [ ] Aucun finding critique non resolu
- [ ] Variables .env correctes pour l'environnement cible
- [ ] CORS configure correctement (pas `*` en prod)
- [ ] DB indexes confirmes (`/api/system/health`)
- [ ] Cron schedule verifie (Europe/Paris)
- [ ] SMTP credentials testes (envoi test)

### 5.2 Apres deploiement
- [ ] `GET /api/system/version` retourne la bonne version
- [ ] `GET /api/system/health` retourne `status: healthy`
- [ ] Login utilisateur fonctionne
- [ ] Dashboard charge correctement
- [ ] Soumission test de lead via `/api/public/leads`
- [ ] Verifier que le lead apparait dans la liste admin

### 5.3 Pour les changements core (geles)
- [ ] TOUT ce qui precede
- [ ] 114 tests E2E passent sans exception
- [ ] Review code par un second dev
- [ ] Tag git avant deploiement
- [ ] Plan de rollback documente

---

## 6. RISQUES "CA MARCHE EN LOCAL MAIS PAS EN PROD"

| Risque | Description | Mitigation |
|--------|-------------|------------|
| DB default | `test_database` au lieu de la DB prod | Verifier `DB_NAME` dans .env + logs startup |
| SMTP timeout | OVH SMTP lent/indisponible | Ajouter timeout SMTP (actuellement manquant) |
| Timezone | APScheduler en Europe/Paris, serveur en UTC | Le code utilise `pytz.timezone("Europe/Paris")` explicitement |
| CORS | `*` en dev, domaines specifiques en prod | Modifier `allow_origins` dans `server.py` |
| Cookie secure | `_rdz_vid` cookie sans `secure=True` | Ajouter `secure=True` en HTTPS |
| Indexes | Crees au demarrage, bloquent si conflits | Verifier `background=True` sur tous les indexes |
| Memory | APScheduler in-process, pas de worker separe | Surveiller RAM du process backend |
| File system | `backend/static/media/` pour uploads | Verifier persistence du volume en prod |

---

## 7. ARCHITECTURE DEPLOIEMENT EMERGENT

```
[Internet]
    |
    v
[Kubernetes Ingress]
    |
    +-- /api/* --> Backend (port 8001)
    +-- /*     --> Frontend (port 3000)
    |
[MongoDB] (localhost:27017 dans le pod)
```

- Frontend et Backend dans le meme pod
- MongoDB dans le meme pod (pas de cluster externe)
- Hot reload actif (redemarrage auto sur changement de fichier)
- Supervisor gere les processus (backend, frontend, mongodb)
