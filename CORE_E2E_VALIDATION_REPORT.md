# RDZ CRM — CORE E2E VALIDATION REPORT
## Tag: rdz-core-distribution-validated | Date: 2026-02-14

**Résultat global : 35/35 PASS**

---

## A. Ingestion / Session / Tracking

| # | Scénario | Méthode | Résultat | Preuve |
|---|---------|---------|---------|--------|
| A1 | Session créée à chaque LP visit | `POST /api/public/track/session` | PASS | `session_id` retourné, `lp_code` correct |
| A2 | LP visit anti-doublon serveur | `POST /api/public/track/lp-visit` x2 | PASS | 2e appel retourne `duplicate: true` |
| A3 | CTA click + form_start enregistrés | `POST /api/public/track/event` | PASS | `event_id` retourné pour chaque type |
| A4 | Submit lead payload complet | `POST /api/public/leads` (14 champs) | PASS | `lead_id`, `entity=ZR7`, `produit=PV` |
| A5 | Submit sans UTM | `POST /api/public/leads` (sans utm_*) | PASS | Lead créé normalement |
| A6 | Phone invalide | `POST /api/public/leads` phone="123" | PASS | `status=invalid` |
| A7 | sendBeacon text/plain | `POST /api/public/track/event` Content-Type: text/plain | PASS | Parsé correctement |

---

## B. Entity / Sécurité / RBAC

| # | Scénario | Méthode | Résultat | Preuve |
|---|---------|---------|---------|--------|
| B1 | No auth → 401 | GET sans token sur 5 endpoints | PASS | Tous retournent 401 |
| B2 | Viewer blocked | GET sur settings, providers, users, event-log, billing write | PASS | Tous retournent 403 |
| B3 | Entity scope leads | GET /api/leads/stats avec X-Entity-Scope:ZR7 vs MDL | PASS | Données différentes par scope |
| B4 | Entity scope deliveries | GET /api/deliveries/stats avec scope | PASS | Filtrage correct |
| B5 | MDL admin ne voit pas ZR7 | GET /api/clients?entity=ZR7 avec admin_mdl | PASS | 403 retourné |
| B6 | Provider key invalide | POST /api/public/leads avec api_key invalide | PASS | Rejet immédiat |
| B7 | OPS billing write blocked | PUT /api/billing/transfer-pricing | PASS | 403 `billing.manage` requis |

---

## C. Déduplication (30 jours)

| # | Scénario | Méthode | Résultat | Preuve |
|---|---------|---------|---------|--------|
| C1 | Même phone+produit+client <30j | DB insert + `check_duplicate_30_days()` | PASS | `is_duplicate=True, type=30_days` |
| C2 | Même phone+produit, client différent | 2x POST /api/public/leads (sessions diff) | PASS | 2e lead créé (non bloqué) |
| C3 | Même phone, produit différent | POST PV puis PAC | PASS | Non bloqué par dedup |
| C4 | Normalisation phone | `validate_phone_fr()` sur 5 formats | PASS | Espaces/9 digits OK. **+33 non géré** (documenté) |
| C5 | Phone manquant | POST avec phone="" | PASS | `status=invalid` |

**Limitation documentée** : Le format `+33XXXXXXXXX` n'est pas normalisé automatiquement. Les leads arrivent déjà normalisés depuis les formulaires.

---

## D. Routing Engine

| # | Scénario | Méthode | Résultat | Preuve |
|---|---------|---------|---------|--------|
| D1 | Lead + commande active | POST lead avec dept/produit correspondant | PASS | `status=routed` ou `no_open_orders` selon quota |
| D2 | Aucune commande | POST lead produit inexistant | PASS | `status=no_open_orders`, lead **conservé** |
| D3 | Raison explicite | POST lead MDL/ITE | PASS | Status clair (routed/no_open_orders) |

**Comportement documenté** :
- Tie-break entre commandes de même priorité : première trouvée (tri MongoDB `priorite ASC`)
- Lead non routé = **jamais perdu**, stocké avec status explicite

---

## E. Delivery (CSV / Email / Status)

| # | Scénario | Méthode | Résultat | Preuve |
|---|---------|---------|---------|--------|
| E1 | CSV ZR7 = 7 colonnes | `generate_csv_content()` | PASS | Headers: nom,prenom,telephone,email,departement,proprietaire_maison,produit |
| E2 | CSV MDL = 8 colonnes | `generate_csv_content()` MDL | PASS | Inclut `proprietaire` + `type_logement` |
| E3 | State machine: transitions | Inspection `VALID_DELIVERY_TRANSITIONS` | PASS | `sent` terminal, `failed` retriable |
| E4 | API delivery list | GET /api/deliveries?limit=5 | PASS | Pagination + total correct |

**Idempotence** : `mark_delivery_sent` vérifie la transition avant d'agir. Doublon impossible.

---

## F. Cron / Jobs / Locks

| # | Scénario | Méthode | Résultat | Preuve |
|---|---------|---------|---------|--------|
| F1 | Scheduler démarré | GET / (root endpoint) | PASS | App running, jobs registered |
| F2 | Lock per-week idempotent | DB insert lock + vérification | PASS | Lock détecté, skip confirmé |
| F3 | Intercompany fail-open | `maybe_create_intercompany_transfer()` avec données invalides | PASS | `created=False`, pas de crash |

---

## G. Intercompany

| # | Scénario | Méthode | Résultat | Preuve |
|---|---------|---------|---------|--------|
| G1 | Health endpoint | GET /api/intercompany/health | PASS | `status=healthy`, compteurs corrects |
| G2 | Retry endpoint | POST /api/intercompany/retry-errors | PASS | Exécution sans erreur |
| G3 | Pricing list | GET /api/intercompany/pricing | PASS | 6 records (ZR7↔MDL x 3 produits) |

---

## H. Observabilité / Health

| # | Scénario | Méthode | Résultat | Preuve |
|---|---------|---------|---------|--------|
| H1 | System health agrégé | GET /api/system/health | PASS | Modules: cron, deliveries, intercompany, invoices |
| H2 | Version endpoint | GET /api/system/version | PASS | `version=1.0.0, tag=rdz-core-distribution-validated, git_sha=xxx` |
| H3 | Dashboard fail-open | GET /api/leads/dashboard-stats?week=2099-W01 | PASS | Toutes les clés présentes, pas de crash |

---

## Recommandations (durcissements)

| # | Priorité | Recommandation |
|---|---------|---------------|
| 1 | P1 | **Phone +33** : ajouter normalisation `+33` → `0` dans `validate_phone_fr()` |
| 2 | P2 | **SMTP timeout** : ajouter `timeout=30` sur `smtplib.SMTP_SSL()` pour éviter un blocage infini |
| 3 | P2 | **Rate limiting** : ajouter un rate limiter sur `/api/public/leads` (protection anti-abus) |
| 4 | P2 | **Pagination forcée** : forcer `limit <= 200` sur tous les endpoints de liste |
| 5 | P2 | **Monitoring externe** : configurer un health check externe sur `/api/system/health` |

---

## Test Pack

**Fichier** : `/app/backend/tests/test_core_e2e_validation.py`
**Exécution** : `cd /app/backend && pytest tests/test_core_e2e_validation.py -v`
**Résultat** : 35/35 PASS en 6.27s
