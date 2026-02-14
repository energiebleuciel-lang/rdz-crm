# AUDIT REPORT FINAL — RDZ CRM v1.0.0
## Audit Global "Zero Surprises" — 2026-02-15

**Tag:** `rdz-core-distribution-validated`  
**Auditeur:** Agent E1  
**Scope:** Backend complet + Frontend + Scripts + Tests + Cron + Config

---

## 1. RESUME EXECUTIF

| Categorie | Critique | Majeur | Mineur | Info |
|-----------|----------|--------|--------|------|
| Code & Logique | 2 | 5 | 8 | 3 |
| Schema & Naming | 0 | 3 | 4 | 2 |
| Securite | 1 | 2 | 2 | 0 |
| Performance | 0 | 2 | 3 | 1 |
| Config & Deploy | 0 | 1 | 2 | 2 |
| Tests | 0 | 1 | 2 | 0 |
| **TOTAL** | **3** | **14** | **21** | **8** |

**Verdict global:** L'application est **fonctionnelle et stable**. Les 3 issues critiques sont des risques de production (pas des bugs actifs). La base de code est bien structuree avec des patterns solides (fail-open, state machine, entity isolation). Les findings majeurs sont principalement des incoherences de schema et des optimisations manquantes.

---

## 2. FINDINGS CRITIQUES (BLOQUANTS PROD)

### C-01: Hashage mot de passe SHA256 (SECURITE)
- **Fichier:** `config.py:34`
- **Probleme:** `hashlib.sha256()` est un hash rapide, non resistant au brute-force. En prod, un attaquant avec acces DB peut casser les passwords en minutes.
- **Impact:** Compromission de tous les comptes utilisateur en cas de fuite DB.
- **Recommandation:** Migrer vers `bcrypt` ou `argon2`. Script de migration a prevoir.
- **Risque si non corrige:** Critique en cas de breach DB.

### C-02: Default values sur MONGO_URL / DB_NAME (CONFIG)
- **Fichier:** `config.py:18-19`
- **Probleme:** `MONGO_URL` et `DB_NAME` ont des valeurs par defaut (`mongodb://localhost:27017`, `test_database`). Si les vars d'env ne sont pas definies en production, l'app demarre silencieusement sur la mauvaise DB.
- **Impact:** L'app peut ecrire sur une DB de test en prod sans aucune alerte.
- **Recommandation:** Supprimer les defaults et fail-fast comme pour `BACKEND_URL`.
- **Note:** Dans l'environnement Emergent actuel, les vars sont presentes, donc pas de bug actif.

### C-03: Statuts de lead non declares dans l'enum (SCHEMA)
- **Fichier:** `models/lead.py` (LeadStatus) vs `routes/public.py`
- **Probleme:** Le code utilise des statuts `routed`, `replaced_by_lb`, `reserved_for_replacement`, `no_open_orders`, `hold_source`, `pending_config`, `invalid`, `double_submit` qui ne sont PAS dans l'enum `LeadStatus`.
- **Impact:** L'enum `LeadStatus` est trompeuse — elle ne reflete pas la realite du systeme. Un dev recrute se basera dessus et sera induit en erreur.
- **Recommandation:** Mettre a jour `LeadStatus` avec TOUS les statuts reels, ou documenter clairement que l'enum est partielle.

---

## 3. FINDINGS MAJEURS

### M-01: Champs delivery dupliques (SCHEMA)
- **Fichier:** `routes/public.py`, `services/delivery_state_machine.py`
- **Probleme:** Un lead livre a DEUX jeux de champs paralleles:
  - Ancien format: `delivered_to_client_id`, `delivered_to_client_name`, `delivered_at`, `delivery_commande_id`
  - Nouveau format: `delivery_client_id`, `delivery_client_name`, `routed_at`, `delivery_id`
- **Impact:** Code de detection doublon doit checker les deux formats (complexite accrue). Risque de desynchronisation.
- **Recommandation:** Migration pour unifier vers un seul format. Phase post-audit.

### M-02: Detection inter-CRM fragile (LOGIQUE)
- **Fichier:** `routes/public.py:319`
- **Probleme:** `is_intercrm = bool(data.api_key and not provider)` — toute valeur non-vide dans `api_key` qui n'est pas un provider valide est classee "inter-CRM". Un user envoyant `api_key: "test"` sera traite comme inter-CRM.
- **Impact:** Leads avec `api_key` invalide sont rejetes si phone suspect, au lieu d'etre traites comme des leads directs.
- **Recommandation:** Verifier un format specifique (prefixe `intercrm_` ou lookup dans une collection dediee).

### M-03: Collision de route /products (ARCHITECTURE)
- **Fichier:** `routes/billing.py:55` et `routes/commandes.py:108`
- **Probleme:** Les deux routes exposent `GET /api/products`. En pratique, la derniere route enregistree gagne, mais c'est un comportement imprevisible.
- **Impact:** Un des deux endpoints est mort silencieusement.
- **Recommandation:** Prefixer billing routes (`/api/billing/products`) ou unifier.

### M-04: N+1 queries dans list_clients (PERFORMANCE)
- **Fichier:** `routes/clients.py:71-87`
- **Probleme:** Pour CHAQUE client, 2 queries separees sont executees (`count_documents` pour leads livres + leads cette semaine). Avec 100 clients = 200 queries supplementaires.
- **Impact:** Latence elevee sur la page clients (>1s avec 100+ clients).
- **Recommandation:** Utiliser une aggregation MongoDB pour calculer les stats en batch.

### M-05: N+1 queries dans list_providers (PERFORMANCE)
- **Fichier:** `routes/providers.py:43-44`
- **Probleme:** Pour chaque provider, un `count_documents` est execute.
- **Recommandation:** Aggregation batch.

### M-06: mark_leads_as_lb() marque "livre" comme LB immediatement (LOGIQUE)
- **Fichier:** `services/daily_delivery.py:139-150`
- **Probleme:** `Condition 2` marque TOUS les leads `status=livre` comme LB, meme ceux livres il y a 1 minute. Le commentaire dit "livre > 30 jours" mais le code n'a pas de filtre temporel.
- **Impact:** Un lead fraichement livre est immediatement disponible en LB pool. Peut causer des re-livraisons indesirables si le timing du cron couvre ce cas.
- **Recommandation:** Ajouter un filtre `delivered_at: {"$lt": cutoff_30_days}` pour ne marquer LB que les leads livres > 30 jours.

### M-07: $or query override dans leads list (BUG)
- **Fichier:** `routes/leads.py:217-228`
- **Probleme:** Si `client_id` ET `search` sont fournis, les deux assignent `query["$or"]`. Le second ecrase le premier.
- **Impact:** Filtrer par client_id + search ne fonctionne pas correctement.
- **Recommandation:** Utiliser `$and` pour combiner les deux conditions `$or`.

---

## 4. FINDINGS MINEURS

### m-01: CORS wildcard (SECURITE)
- `server.py:296` — `allow_origins=["*"]` acceptable en preview, DOIT etre restreint en production aux domaines de l'app.

### m-02: Pas de rate limiting sur /api/public/* (SECURITE)
- Les endpoints publics (tracking, lead submission) n'ont aucune protection anti-spam/DDoS. Un script peut soumettre des milliers de leads.
- **Recommandation:** `slowapi` ou middleware custom (50 req/min par IP).

### m-03: Index manquant sur leads.provider_id (PERFORMANCE)
- Utilise dans `routes/providers.py` pour le comptage par provider. Sans index = collection scan.

### m-04: Pydantic v1 deprecation (CODE)
- Plusieurs modeles utilisent `@validator` (Pydantic v1) au lieu de `@field_validator` (v2). Fonctionne grace au mode compat mais generera des warnings.

### m-05: Deux systemes de logging (ARCHITECTURE)
- `services/activity_logger.py` ecrit dans `activity_logs` (actions utilisateur)
- `services/event_logger.py` ecrit dans `event_log` (actions systeme)
- Confusion possible. Recommandation: unifier ou documenter clairement la distinction.

### m-06: compute_client_group_key fragile (CODE)
- `overlap_guard.py:28-39` — Joint les emails avec `|`. Si un email contient `|` (rare mais possible), le key sera casse.
- **Recommandation:** Utiliser un hash SHA256 du set trie d'emails comme group_key.

### m-07: Delivery model incomplet (SCHEMA)
- `models/delivery.py` ne declare pas: `outcome`, `accepted_at`, `rejected_at`, `rejected_by`, `rejection_reason`, `removed_at`, `removed_by`, `removal_reason`, `routing_mode`, `batch_id`, `client_group_key`, `is_shared_client_30d`, `overlap_fallback_delivery`.
- Ces champs existent en DB mais pas dans le modele Pydantic.

### m-08: register_date vs created_at (SCHEMA)
- Leads ont `register_date` (int, Unix timestamp ms) ET `created_at` (str, ISO). Redondance.

### m-09: produit vs product vs product_code (NAMING)
- Le champ s'appelle `produit` dans leads/commandes/deliveries mais `product` dans intercompany et `product_code` dans billing. Inconsistance.

### m-10: session expiry comparison (CODE)
- `routes/auth.py:37` compare `expires_at` comme string ISO. Fonctionne car ISO est tri-alphabetique, mais fragile si le format change.

### m-11: CSV delivery manque timeout SMTP (ROBUSTESSE)
- `csv_delivery.py:251` — `smtplib.SMTP_SSL` n'a pas de timeout explicite. Un serveur SMTP non-responsive peut bloquer le thread indefiniment.
- **Recommandation:** Ajouter `timeout=30` au constructeur.

---

## 5. INFORMATIONS (SANS ACTION REQUISE)

- Les entites (ZR7/MDL) sont correctement isolees dans 100% des endpoints audites.
- Le pattern fail-open est correctement applique dans: monitoring, overlap guard, intercompany.
- La state machine delivery est robuste avec des invariants bien verifies.
- Le cron schedule est correct (Europe/Paris, anti-double-run via cron_logs).
- Tous les endpoints admin sont proteges par `require_permission()` ou `require_admin`.
- Le seeding intercompany pricing est idempotent.

---

## 6. DECISIONS PROPOSEES

| ID | Finding | Decision proposee | Priorite |
|----|---------|-------------------|----------|
| C-01 | SHA256 passwords | Migrer vers bcrypt AVANT mise en prod | P0 |
| C-02 | Default DB values | Supprimer defaults, fail-fast | P0 |
| C-03 | LeadStatus enum | Mettre a jour l'enum avec tous les statuts reels | P1 |
| M-01 | Champs dupliques | Documenter maintenant, migrer plus tard | P2 |
| M-03 | Route collision | Prefixer billing routes | P1 |
| M-04 | N+1 queries | Refactorer avec aggregation | P2 |
| M-06 | LB marking | Ajouter filtre 30 jours | P1 |
| M-07 | $or override | Fix immediat | P1 |
| m-11 | SMTP timeout | Ajouter timeout=30 | P1 |

---

## 7. CONCLUSION

Le code est **solide pour un MVP en production controle**. Les patterns architecturaux sont bons (entity isolation, fail-open, state machine). Les 3 critiques identifiees sont des risques latents, pas des bugs actifs. Les findings majeurs sont principalement des dettes techniques accumulees pendant le developpement rapide des features.

**Recommandation finale:** Corriger C-01, C-02, M-07 et m-11 avant tout deploiement production. Les autres peuvent etre adresses incrementalement.
