# ADDENDUM AUDIT — Points Sensibles
> Pour chaque point : risque, preuve code, tests existants, plan de correction + rollback.

---

## 1. AUTH / BCRYPT

**Risque:** Les passwords sont hashes en SHA256 (`config.py:38`). Un attaquant avec un dump DB casse tous les comptes en minutes (hashrate SHA256 : ~10 milliards/s sur GPU).

**Preuve:**
```python
# config.py:38
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()
```
Aucun salt, aucun cost factor. `hash_password("RdzTest2026!")` produit toujours le meme hash.

**Tests existants:**
- `test_zero_surprises_audit.py::TestAuthentication` — teste login/logout, mais ne valide pas la force du hash.
- Aucun test ne verifie qu'un hash est resistant au brute-force.

**Plan de correction:**
1. `pip install bcrypt`
2. Modifier `hash_password()` → `bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()`
3. Modifier check dans `routes/auth.py:80` → `bcrypt.checkpw()`
4. Script migration: re-hasher les 19 users existants (seeder + users reels)
5. Rollback: revert `config.py` + `auth.py` + relancer le seed. Les sessions actives sont invalides mais le login re-fonctionne avec l'ancien hash.

---

## 2. CORS

**Risque:** `allow_origins=["*"]` autorise n'importe quel domaine a appeler l'API. Un site malveillant peut forger des requetes au nom d'un user connecte (le cookie session est transmis car `allow_credentials=True`).

**Preuve:**
```python
# server.py:297-301
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,  # ← combinaison dangereuse avec "*"
    allow_methods=["*"],
    allow_headers=["*"],
)
```
Note : FastAPI/Starlette refuse en realite `credentials=True` avec `origins=["*"]` et renvoie `Access-Control-Allow-Origin: *` sans le header `Credentials`. Le vrai risque est donc limite aux requetes sans cookie (API key provider), mais le signal est mauvais.

**Tests existants:**
- Aucun test CORS.

**Plan de correction:**
1. Remplacer `["*"]` par la liste exacte des domaines : `["https://rdz-group-ltd.online", "https://overlap-monitor.preview.emergentagent.com"]`
2. Garder `allow_credentials=True` (necessaire pour le cookie `_rdz_vid`)
3. Tester via curl avec `Origin: https://evil.com` — doit retourner 403 ou pas de header `Access-Control-Allow-Origin`
4. Rollback: remettre `["*"]`. Aucun impact DB.

---

## 3. ENDPOINTS PUBLICS — ANTI-ABUSE

**Risque:** Les 4 endpoints publics n'ont aucun rate limiting :
- `POST /api/public/track/session`
- `POST /api/public/track/lp-visit`
- `POST /api/public/track/event`
- `POST /api/public/leads`

Un script peut soumettre 10k leads/min, polluer la DB, et saturer le SMTP.

**Preuve:**
```python
# routes/public.py — aucune trace de rate limit, slowapi, ou throttle
# Seule protection : anti double-submit (meme session + phone < 5s)
```
Le double-submit est contourne en changeant le `session_id` a chaque requete.

**Tests existants:**
- `test_public_leads_routing.py` — teste le flow normal, pas le spam.
- Aucun test de charge.

**Plan de correction:**
1. `pip install slowapi`
2. Ajouter au `server.py` :
```python
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
```
3. Decorer les 4 endpoints publics : `@limiter.limit("30/minute")`
4. Le rate limit est par IP (X-Forwarded-For en prod derriere ingress).
5. Rollback: retirer le decorateur. Aucun impact DB ni logique.

---

## 4. CONCURRENCE / IDEMPOTENCE CRON

**Risque:** Le cron `daily_delivery` n'a pas de lock explicite. Si APScheduler trigger 2 fois (bug, restart rapide), les memes leads peuvent etre traites en parallele.

**Preuve:**
```python
# daily_delivery.py:1025 — run_daily_delivery()
# Aucun lock, aucun findOneAndUpdate sur un "cron_runs" collection
# Seule protection : state machine (delivery.status="sent" est terminal)
```
La state machine protege contre le double-sent (un lead deja `livre` ne sera pas re-livre). Mais le double-run peut creer 2 deliveries pour le meme lead si les deux runs passent le routing avant que l'autre ne committe.

En revanche, `intercompany_invoices` (server.py:240-244) **a** un lock via `cron_logs` :
```python
lock = await db.cron_logs.find_one(
    {"job": "intercompany_invoices", "week_key": wk, "status": {"$in": ["running", "success"]}}
)
if lock: return  # skip
```

**Tests existants:**
- `test_delivery_state_machine_audit.py` — verifie que `sent` est terminal.
- Aucun test de concurrence reelle (2 runs paralleles).

**Plan de correction:**
1. Ajouter un lock similaire a `intercompany_invoices` pour `daily_delivery` :
```python
lock = await db.cron_logs.find_one(
    {"job": "daily_delivery", "date": today, "status": {"$in": ["running", "success"]}}
)
if lock: return
await db.cron_logs.insert_one({"job": "daily_delivery", "date": today, "status": "running", ...})
```
2. En fin de run : `status: "success"` avec `duration_seconds`.
3. APScheduler `max_instances=1` (deja implicite avec `replace_existing=True`, mais l'expliciter).
4. Rollback: retirer le lock. Worst case = double-run, mais state machine protege le double-sent.

---

## 5. LB REPLACEMENT + OVERLAP GUARD

### 5a. LB Replacement — Reservation atomique

**Risque:** Si 2 leads suspects arrivent en meme temps pour la meme commande, les 2 peuvent cibler le meme LB avant que le premier `findOneAndUpdate` ne committe.

**Preuve:**
```python
# lb_replacement.py:81-95
reserved = await db.leads.find_one_and_update(
    {"id": cand_id, "status": {"$in": ["lb", "new", "no_open_orders"]}},
    {"$set": {"status": "reserved_for_replacement", ...}},
    return_document=False,
)
```
`findOneAndUpdate` est atomique au niveau MongoDB. Le 2eme appel trouvera `status="reserved_for_replacement"` et le filtre `status: $in [lb, new, no_open_orders]` echouera → `reserved = None` → passe au candidat suivant. **Protection correcte.**

**Tests existants:**
- `test_suspicious_policy.py` — teste reservation + fallback.
- Pas de test de concurrence reelle (mais le mecanisme MongoDB est atomique par design).

### 5b. Overlap Guard — Timeout + fail-open

**Risque:** Le timeout 500ms peut etre depasse si MongoDB est lent (aggregation sur `clients` + `deliveries`). En cas de timeout, la delivery est faite normalement (fail-open).

**Preuve:**
```python
# overlap_guard.py:73-86
return await asyncio.wait_for(
    _check_overlap_internal(...),
    timeout=0.5,  # 500ms
)
# TimeoutError → _no_overlap_result("")
# Exception → _no_overlap_result("")
```
**Verification:** Le fail-open est correct. `_no_overlap_result` retourne `{"is_shared": False, "fallback": False}` — la delivery se fait normalement sans annotation overlap.

**Tests existants:**
- `test_overlap_guard.py::TestOverlapDetection::test_guard_failopen_on_error` — verifie fail-open.
- `test_overlap_guard.py::TestNoRegression::test_perf_30d_ok` — verifie que le check < 500ms sur 30j de data.

**Plan de correction (si necessaire):**
- Le design actuel est correct. Si le timeout est depasse en prod, surveiller via les logs `[OVERLAP] Timeout` et augmenter le timeout ou ajouter un index si necessaire.
- Rollback: kill switch → `settings.overlap_guard.enabled = false` en DB. Effet immediat, 0 code change.

---

## 6. PERF MONITORING (AGGREGATIONS)

**Risque:** L'endpoint `/api/monitoring/intelligence` execute des aggregations lourdes (group by phone, lookups individuels pour doublons, cross-source matrix). Sur 90 jours de data, ca peut depasser 10s.

**Preuve:**
```python
# monitoring.py:160 — 500 leads doublons avec lookup individuel
dup_leads = await db.leads.find({...}).limit(500).to_list(500)
for dl in dup_leads:
    orig = await db.leads.find_one({...})  # ← N+1 query pattern

# monitoring.py:229 — 300 leads pour time buckets avec lookups
dup_leads_for_buckets = await db.leads.find({...}).limit(300).to_list(300)
for dl in dup_leads_for_buckets:
    orig = await db.leads.find_one({...})  # ← N+1 encore
```
Avec 3392 leads actuels, ca passe (<5s sur 30d, <10s sur 90d — teste). Mais a 50k leads, les lookups N+1 sur 500 items vont exploser.

**Tests existants:**
- `test_monitoring_intelligence.py::TestPerformance::test_30d_under_5s` — PASS
- `test_monitoring_intelligence.py::TestPerformance::test_90d_under_10s` — PASS

**Plan de correction:**
1. **Court terme (acceptable):** Les `limit(500)` et `limit(300)` bornent le N+1. Meme a 50k leads, on ne scan que 500 doublons.
2. **Moyen terme:** Remplacer les boucles N+1 par des aggregations `$lookup` cote MongoDB.
3. **Surveillance:** Si `test_90d_under_10s` commence a fail, refactorer.
4. Rollback: monitoring est READ-ONLY et fail-open. Un widget lent ne bloque jamais rien.

---

## 7. LOGS / DONNEES SENSIBLES

**Risque:** Les logs backend pourraient contenir des donnees personnelles (phone, email, nom).

**Preuve:**
```python
# routes/public.py:631-632
f"[LEAD_CREATED] id={lead_id} phone=***{phone[-4:] if len(phone) >= 4 else phone} "

# routes/public.py:323
f"[SUSPICIOUS_REJECTED] phone=***{phone[-4:]} source={source_label} "

# services/duplicate_detector.py:87
f"[DOUBLE_SUBMIT] ... phone={phone[-4:]}"
```
**Verdict: OK.** Le phone est masque partout dans les logs (seuls les 4 derniers chiffres). Le nom, prenom, email ne sont **jamais** logges.

**Donnees en DB non masquees:**
- Collection `leads` : phone complet en clair (necessaire pour dedup + delivery CSV).
- Collection `deliveries` : `csv_content` contient le CSV complet (nom, prenom, phone, email, dept).
- Pas de chiffrement at-rest cote MongoDB.

**Tests existants:**
- Aucun test specifique anti-leak dans les logs.

**Plan de correction:**
1. **Logs: OK** — deja masques.
2. **DB at-rest:** Activer le chiffrement MongoDB si disponible (hors scope Emergent preview). Sinon, accepter le risque avec un acces DB restreint.
3. **csv_content en DB:** Acceptable car necessaire pour le retry/download. Purger les csv_content > 90 jours si besoin.
4. Rollback: N/A (pas de changement code).

---

## 8. CONFIG / DEPLOY

**Risque:** Mauvaise config = l'app demarre sur la mauvaise DB, envoie des emails au mauvais endroit, ou expose des endpoints sans protection.

**Preuve (fixes deja appliques):**
```python
# config.py:18-21 — CORRIGE dans cette session
MONGO_URL = os.environ.get('MONGO_URL')
if not MONGO_URL:
    raise ValueError("MONGO_URL environment variable is required")
DB_NAME = os.environ.get('DB_NAME')
if not DB_NAME:
    raise ValueError("DB_NAME environment variable is required")
```

**Risques restants:**
| Config | Fichier | Risque | Statut |
|--------|---------|--------|--------|
| `MONGO_URL` | config.py | DB mauvaise | CORRIGE (fail-fast) |
| `DB_NAME` | config.py | DB mauvaise | CORRIGE (fail-fast) |
| `BACKEND_URL` | config.py | Tracking URLs cassees | OK (fail-fast) |
| `ZR7_SMTP_PASSWORD` | csv_delivery.py | Envoi echoue → delivery failed | OK (erreur catchee, retry possible) |
| `MDL_SMTP_PASSWORD` | csv_delivery.py | Idem | OK |
| SMTP host/port | csv_delivery.py:200-213 | **Hardcode** `ssl0.ovh.net:465` | RISQUE si changement OVH |
| CORS origins | server.py:299 | Cross-origin non controle | A CORRIGER (P0-2) |
| Cookie `_rdz_vid` | public.py:158 | Pas de `secure=True` | MINEUR (tracking seulement) |
| Cron timezone | server.py:22+224 | Mauvaise heure | OK (explicite `Europe/Paris`) |

**Tests existants:**
- `test_zero_surprises_audit.py::TestBugFixVerification::test_c02_config_fail_fast` — PASS

**Plan de correction:**
1. SMTP host/port → Extraire dans .env (`ZR7_SMTP_HOST`, `ZR7_SMTP_PORT`) pour permettre un changement sans code.
2. CORS → Voir section 2.
3. Cookie secure → Ajouter `secure=True` quand `BACKEND_URL` commence par `https`.
4. Rollback: chaque config est independante. Revert le .env suffit.

---

## RESUME

| Point | Severite | Etat actuel | Action requise |
|-------|----------|-------------|---------------|
| Auth/bcrypt | **P0** | SHA256 | Migration bcrypt avant prod |
| CORS | **P0** | `*` | Restreindre aux domaines |
| Anti-abuse | **P1** | Aucun rate limit | Ajouter slowapi |
| Cron idempotence | **P1** | Pas de lock daily_delivery | Ajouter lock type intercompany |
| LB atomique | **OK** | findOneAndUpdate | Correct par design |
| Overlap fail-open | **OK** | timeout 500ms | Correct, kill switch dispo |
| Perf monitoring | **OK (borne)** | N+1 limite a 500 | Surveiller, refactorer si lent |
| Logs sensibles | **OK** | Phone masque 4 derniers | Correct |
| Config deploy | **OK (corrige)** | Fail-fast | SMTP host a externaliser |
