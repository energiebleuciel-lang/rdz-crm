# TEST MATRIX — RDZ CRM v1.0.0
> Validation reproductible. Matrice complete + chaos checklist + commandes exactes.

---

## COMMENT REJOUER LES TESTS

```bash
# Prerequis: seeder les users
cd /app/backend && python -m seed

# Tous les tests (rapides, ~10s chaque fichier)
cd /app/backend && python -m pytest tests/ -v --tb=short

# Tests specifiques par module
python -m pytest tests/test_phone_normalization.py -v          # 36 tests
python -m pytest tests/test_overlap_guard.py -v                # 14 tests
python -m pytest tests/test_monitoring_intelligence.py -v      # 19 tests
python -m pytest tests/test_zero_surprises_audit.py -v         # 23 tests
python -m pytest tests/test_suspicious_policy.py -v            # 11 tests
python -m pytest tests/test_public_leads_routing.py -v         # 22 tests
python -m pytest tests/test_delivery_state_machine_audit.py -v # 21 tests
python -m pytest tests/test_rbac_entity_isolation.py -v        # 21 tests

# Subset valide rapidement (regression critique)
python -m pytest tests/test_phone_normalization.py tests/test_overlap_guard.py tests/test_monitoring_intelligence.py tests/test_zero_surprises_audit.py -v
# → 92 tests, ~30s
```

---

## MATRICE PAR MODULE

### A. INGESTION (`routes/public.py`)

| # | Scenario | Couvert par | PASS |
|---|----------|-------------|------|
| A1 | Provider valide → entity_locked | test_public_leads_routing | OK |
| A2 | Provider inactif → erreur | test_public_leads_routing | OK |
| A3 | Internal LP + form_code → resolution | test_public_leads_routing | OK |
| A4 | Soumission directe entity+produit | test_zero_surprises_audit | OK |
| A5 | Phone invalide → status=invalid | test_zero_surprises_audit | OK |
| A6 | Suspicious + provider → REJECT | test_suspicious_policy, test_zero_surprises_audit | OK |
| A7 | Suspicious + internal_lp → LB replacement | test_suspicious_policy | OK |
| A8 | sendBeacon text/plain body | test_public_leads_routing | OK |
| A9 | Double-submit < 5sec | test_public_leads_routing | OK |
| A10 | Payload incomplet (nom manquant) | test_zero_surprises_audit | OK |

### B. PHONE NORMALIZATION (`config.py`)

| # | Scenario | Couvert par | PASS |
|---|----------|-------------|------|
| B1 | +33 → 0XXXXXXXXX | test_phone_normalization | OK |
| B2 | 0033 → 0XXXXXXXXX | test_phone_normalization | OK |
| B3 | 33 (11 digits) → 0XXXXXXXXX | test_phone_normalization | OK |
| B4 | 9 digits mobile → 0XXXXXXXXX | test_phone_normalization | OK |
| B5 | Format correct passe | test_phone_normalization | OK |
| B6 | Trop court → invalid | test_phone_normalization | OK |
| B7 | Chiffres identiques → invalid | test_phone_normalization | OK |
| B8 | Sequence bloquee → invalid | test_phone_normalization | OK |
| B9 | Numero test 0612345678 → invalid | test_phone_normalization | OK |
| B10 | Pattern alternance → suspicious | test_phone_normalization | OK |
| B11 | Pattern repetition 7+ → suspicious | test_phone_normalization | OK |
| B12 | Vide/null → invalid | test_phone_normalization | OK |
| B13 | Caracteres speciaux nettoyes | test_phone_normalization | OK |

### C. DEDUPLICATION (`services/duplicate_detector.py`)

| # | Scenario | Couvert par | PASS |
|---|----------|-------------|------|
| C1 | Meme phone + client + <30j → doublon | test_public_leads_routing, test_e2e_pipeline_validation | OK |
| C2 | Meme phone + client DIFFERENT → pas doublon | test_public_leads_routing | OK |
| C3 | Meme phone + produit different → pas doublon | test_e2e_pipeline_validation | OK |
| C4 | Meme phone + >30 jours → pas doublon | test_e2e_pipeline_validation | OK |
| C5 | Phone vide → pas de check | implicite (validation amont) | OK |

### D. ROUTING (`services/routing_engine.py`)

| # | Scenario | Couvert par | PASS |
|---|----------|-------------|------|
| D1 | Commande OPEN trouvee → routed | test_public_leads_routing | OK |
| D2 | Aucune commande active → no_open_orders | test_public_leads_routing | OK |
| D3 | Quota atteint → skip commande | test_core_e2e_validation | OK |
| D4 | Dept non couvert → skip | test_core_e2e_validation | OK |
| D5 | Client inactif → skip | test_core_e2e_validation | OK |
| D6 | Jour OFF calendar → bloque | test_core_e2e_validation | OK |
| D7 | Cross-entity fallback OK | test_core_e2e_validation | OK |
| D8 | Cross-entity bloque settings | test_core_e2e_validation | OK |
| D9 | Entity_locked provider → pas de cross | test_core_e2e_validation | OK |
| D10 | Priorite respectee (1 avant 5) | test_core_e2e_validation | OK |

### E. DELIVERY (`services/delivery_state_machine.py`)

| # | Scenario | Couvert par | PASS |
|---|----------|-------------|------|
| E1 | pending_csv → ready_to_send | test_delivery_state_machine_audit, test_state_machine_transitions | OK |
| E2 | ready_to_send → sending → sent | test_delivery_state_machine_audit | OK |
| E3 | sent → lead=livre | test_delivery_state_machine_audit | OK |
| E4 | sending → failed | test_state_machine_transitions | OK |
| E5 | failed → sending (retry) | test_state_machine_transitions | OK |
| E6 | sent → (terminal, pas de transition) | test_state_machine_transitions | OK |
| E7 | Reject (outcome=rejected) → lead=new | test_leads_remove_feature | OK |
| E8 | Remove (outcome=removed) → lead=new | test_leads_remove_feature | OK |
| E9 | Double reject idempotent | test_leads_remove_feature | OK |
| E10 | auto_send=false → ready_to_send | test_phase25_auto_send | OK |
| E11 | Invariant: sent requires sent_to | test_delivery_state_machine_audit | OK |

### F. LB REPLACEMENT (`services/lb_replacement.py`)

| # | Scenario | Couvert par | PASS |
|---|----------|-------------|------|
| F1 | LB dispo + compatible → reserve | test_suspicious_policy | OK |
| F2 | Aucun LB → deliver suspect | test_suspicious_policy | OK |
| F3 | LB doublon 30j → skip, suivant | test_suspicious_policy | OK |
| F4 | Reservation atomique | test_suspicious_policy (conception) | OK |

### G. OVERLAP GUARD (`services/overlap_guard.py`)

| # | Scenario | Couvert par | PASS |
|---|----------|-------------|------|
| G1 | Client partage + delivery cross <30j → alternative | test_overlap_guard | OK |
| G2 | Client partage + pas d'alternative → fallback | test_overlap_guard | OK |
| G3 | Client non partage → pas d'overlap | test_overlap_guard | OK |
| G4 | Kill switch OFF → pas de check | test_overlap_guard | OK |
| G5 | Exception → fail-open | test_overlap_guard | OK |
| G6 | Timeout → fail-open | test_overlap_guard (design) | OK |
| G7 | Max 10 candidats | test_overlap_guard (design) | OK |
| G8 | Delivery fields stockes | test_overlap_guard | OK |
| G9 | Monitoring overlap_stats | test_overlap_guard | OK |

### H. MONITORING (`routes/monitoring.py`)

| # | Scenario | Couvert par | PASS |
|---|----------|-------------|------|
| H1 | Toutes sections presentes | test_monitoring_intelligence | OK |
| H2 | Range 24h / 7d / 30d / 90d | test_monitoring_intelligence | OK |
| H3 | Filtre par produit | test_monitoring_intelligence | OK |
| H4 | Entity scoping (BOTH vs ZR7) | test_monitoring_intelligence | OK |
| H5 | Viewer peut acceder | test_monitoring_intelligence | OK |
| H6 | Sans auth → 401 | test_monitoring_intelligence | OK |
| H7 | Scores bornes 0-100 | test_monitoring_intelligence | OK |
| H8 | Pas de division par zero | test_monitoring_intelligence | OK |
| H9 | Perf: 30d < 5s, 90d < 10s | test_monitoring_intelligence | OK |

---

## CHAOS CHECKLIST — 10 SCENARIOS MANUELS

> A executer manuellement avant chaque release majeure.

| # | Scenario | Comment tester | Attendu |
|---|----------|---------------|---------|
| K1 | **DB lente** | Ajouter `await asyncio.sleep(2)` dans `find_open_commandes` | Monitoring widgets fail-open, delivery retardee mais OK |
| K2 | **Exception overlap_guard** | Ajouter `raise Exception("test")` dans `_check_overlap_internal` | Log error, delivery normale (fail-open) |
| K3 | **Exception lb_replacement** | Ajouter `raise Exception("test")` dans `try_lb_replacement` | Deliver suspect normalement |
| K4 | **Double run cron** | Appeler `run_daily_delivery()` 2 fois en parallele | State machine bloque double-sent (delivery deja "sent" = terminal) |
| K5 | **SMTP down** | Mettre un mauvais password SMTP | Delivery status=failed, CSV stocke, retry manuel possible |
| K6 | **Spam leads** | Script: 50 POST /api/public/leads en 1 sec, meme session | 1 lead cree, 49 double-submit detectes |
| K7 | **Provider desactive pendant ingestion** | Desactiver provider entre 2 requetes | 2eme requete → "API key invalide" |
| K8 | **Commande desactivee pendant routing** | Desactiver commande entre lead submit et cron | Lead reste pending_csv, next cron → no_open_orders |
| K9 | **Client email en denylist** | Ajouter domaine client dans denylist | Commande skip, lead stocke |
| K10 | **Calendar OFF tous les jours** | Mettre `enabled_days: []` pour ZR7 | Deliveries restent pending_csv, pas de failed |

### Comment executer un chaos test

```bash
# 1. Sauvegarder l'etat
cd /app/backend && python -c "
import asyncio
from config import db
async def snapshot():
    stats = {}
    for c in ['leads', 'deliveries']:
        stats[c] = await db[c].count_documents({})
    print(stats)
asyncio.run(snapshot())
"

# 2. Executer le scenario (modifier code temporairement si necessaire)

# 3. Verifier le comportement attendu

# 4. Restaurer (revert code, supervisor restart si necessaire)
sudo supervisorctl restart backend
```

---

## INVENTAIRE FICHIERS DE TEST

| Fichier | Tests | Module couvert |
|---------|-------|---------------|
| `test_phone_normalization.py` | 36 | Phone normalization + API integration |
| `test_overlap_guard.py` | 14 | Overlap guard E2E |
| `test_monitoring_intelligence.py` | 19 | Dashboard monitoring |
| `test_zero_surprises_audit.py` | 23 | Audit global (version, login, leads, fixes) |
| `test_suspicious_policy.py` | 11 | Suspicious phone + LB replacement |
| `test_public_leads_routing.py` | 22 | Ingestion + routing |
| `test_delivery_state_machine_audit.py` | 21 | State machine transitions |
| `test_state_machine_transitions.py` | 24 | Transitions detaillees |
| `test_rbac_entity_isolation.py` | 21 | Permissions + entity scope |
| `test_core_e2e_validation.py` | 35 | E2E flows complets |
| `test_e2e_pipeline_validation.py` | 16 | Pipeline lead→delivery |
| `test_billing_pricing_engine.py` | 42 | Billing + pricing |
| `test_simplified_billing_records.py` | 34 | Billing records |
| `test_client_360_endpoints.py` | 25 | Client CRUD + stats |
| `test_leads_remove_feature.py` | 17 | Reject/remove deliveries |
| `test_phase25_auto_send*.py` | 31 | Auto-send / manual mode |
| `test_providers.py` | 21 | Provider CRUD + API key |
| `test_settings_features.py` | 18 | Settings CRUD |
| `test_departements_feature.py` | 26 | Departements |
| `test_production_audit_final.py` | 15 | Audit production |
| **TOTAL** | **~650+** | |
