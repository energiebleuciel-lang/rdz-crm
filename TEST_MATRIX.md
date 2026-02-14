# TEST MATRIX — RDZ CRM v1.0.0
## Matrice de scenarios exhaustive

---

## 1. INGESTION (POST /api/public/leads)

### A. Sources d'ingestion

| # | Scenario | Input | Expected | Status |
|---|----------|-------|----------|--------|
| A1 | Provider source valide | `api_key: prov_xxx` (actif) | entity_locked, lead cree | PASS |
| A2 | Provider source inactif | `api_key: prov_xxx` (inactif) | error: "API key invalide" | PASS |
| A3 | Internal LP avec form_code | `form_code: "form1"` + settings config | entity/produit resolus | PASS |
| A4 | Soumission directe (entity+produit dans body) | `entity: "ZR7", produit: "PV"` | lead cree avec ces valeurs | PASS |
| A5 | Inter-CRM (api_key non-provider) | `api_key: "intercrm_xxx"` | Traite comme inter-CRM | RISK (M-02) |
| A6 | Aucune auth, aucun form_code | Payload minimal | status=pending_config | PASS |
| A7 | sendBeacon content-type text/plain | Form data via beacon | Parsing OK | PASS |

### B. Phone normalization

| # | Scenario | Input | Expected | Status |
|---|----------|-------|----------|--------|
| B1 | Format +33 | `+33612345678` | `0612345678`, valid | PASS |
| B2 | Format 0033 | `0033612345678` | `0612345678`, valid | PASS |
| B3 | Format 33 (11 chiffres) | `33612345678` | `0612345678`, valid | PASS |
| B4 | Format 9 chiffres mobile | `612345678` | `0612345678`, valid | PASS |
| B5 | Format correct 10 chiffres | `0612345678` | `0612345678`, valid | PASS |
| B6 | Trop court (7 chiffres) | `0612345` | invalid | PASS |
| B7 | Trop long (12 chiffres) | `061234567890` | invalid | PASS |
| B8 | Chiffres identiques | `0000000000` | invalid (blocked) | PASS |
| B9 | Sequence ascendante | `0123456789` | invalid (blocked) | PASS |
| B10 | Numero test bloque | `0612345678` | invalid (blocked) | PASS |
| B11 | Pattern suspect (alternance) | `0606060606` | valid, suspicious | PASS |
| B12 | Pattern suspect (repetition 7+) | `0611111111` | valid, suspicious | PASS |
| B13 | Caracteres non-numeriques | `06 12 34 56 78` | `0612345678`, valid | PASS |
| B14 | Vide | `""` | invalid | PASS |
| B15 | Null/undefined | null | invalid | PASS |

### C. Suspicious phone policy

| # | Scenario | Input | Expected | Status |
|---|----------|-------|----------|--------|
| C1 | Provider + suspicious | Provider api_key + phone suspect | REJECT (200 + error) | PASS |
| C2 | Inter-CRM + suspicious | Non-provider api_key + phone suspect | REJECT | PASS |
| C3 | Internal LP + suspicious | No api_key + phone suspect | ACCEPT + LB replacement attempt | PASS |
| C4 | Provider + valid | Provider api_key + phone valide | ACCEPT normally | PASS |
| C5 | Direct + suspicious | No api_key, no form + phone suspect | ACCEPT normally | PASS |

### D. Payloads incomplets

| # | Scenario | Input | Expected | Status |
|---|----------|-------|----------|--------|
| D1 | Phone manquant | Tout sauf phone | Pydantic 422 error | PASS |
| D2 | Nom manquant | Tout sauf nom | lead_minimal_valid=false, status=invalid | PASS |
| D3 | Departement manquant | Tout sauf dept | lead_minimal_valid=false, status=invalid | PASS |
| D4 | Entity manquante (pas provider) | Pas d'entity ni form_code | status=pending_config | PASS |
| D5 | Departement invalide (1 char) | `dept: "7"` | Tronque a 2 chars, valide si possible | PASS |

---

## 2. DEDUPLICATION

| # | Scenario | Input | Expected | Status |
|---|----------|-------|----------|--------|
| E1 | Double-submit (<5 sec) | Meme session + phone en <5s | Retourne lead_id existant | PASS |
| E2 | Meme phone, meme client, <30j | Phone deja livre au client | Doublon detecte, skip client | PASS |
| E3 | Meme phone, client DIFFERENT | Phone deja livre a un autre client | PAS doublon, livrable | PASS |
| E4 | Meme phone, produit different | Phone deja livre pour PV, soumis PAC | PAS doublon | PASS |
| E5 | Meme phone, >30 jours | Phone livre il y a 35 jours | PAS doublon (fenetre expiree) | PASS |
| E6 | Phone missing | `phone: ""` | Pas de check doublon | PASS |

---

## 3. ROUTING

| # | Scenario | Expected | Status |
|---|----------|----------|--------|
| F1 | Commande active + quota dispo + dept match | Routing OK | PASS |
| F2 | Aucune commande active | status=no_open_orders | PASS |
| F3 | Quota atteint | Commande skip, cherche suivante | PASS |
| F4 | Dept non couvert | Skip commande | PASS |
| F5 | Client inactif | Skip commande | PASS |
| F6 | Client non-deliverable (email en denylist) | Skip commande | PASS |
| F7 | Jour OFF (calendar gating) | no_open_orders (delivery_day_disabled) | PASS |
| F8 | Cross-entity fallback autorise | Route vers autre entity | PASS |
| F9 | Cross-entity bloque (settings) | no_open_orders | PASS |
| F10 | Cross-entity + entity_locked (provider) | no_open_orders_entity_locked | PASS |
| F11 | Toutes commandes = doublon 30j | all_commandes_duplicate | PASS |
| F12 | Prepaid client balance = 0 | Skip commande | PASS |
| F13 | Multi-entity BOTH | Route dans les 2 entities | PASS |
| F14 | Priorite commande respectee | Commande priorite 1 avant priorite 5 | PASS |

---

## 4. DELIVERY

| # | Scenario | Expected | Status |
|---|----------|----------|--------|
| G1 | pending_csv -> ready_to_send | CSV genere, lead reste routed | PASS |
| G2 | ready_to_send -> sending -> sent | Email envoye, lead=livre | PASS |
| G3 | sending -> failed | Error stockee, retry possible | PASS |
| G4 | failed -> sending (retry) | Transition autorisee | PASS |
| G5 | sent -> (rien) | Terminal, pas de transition | PASS |
| G6 | Reject delivery (sent -> outcome=rejected) | Lead remis a new, re-routable | PASS |
| G7 | Remove delivery (sent -> outcome=removed) | Lead remis a new | PASS |
| G8 | Double reject (idempotent) | Pas d'erreur, retour OK | PASS |
| G9 | CSV format ZR7 (7 colonnes) | Colonnes correctes | PASS |
| G10 | CSV format MDL (8 colonnes) | Colonnes correctes | PASS |
| G11 | auto_send_enabled=false | ready_to_send (pas d'envoi) | PASS |
| G12 | Batch send (groupement par client) | Un email par client | PASS |

---

## 5. LB REPLACEMENT

| # | Scenario | Expected | Status |
|---|----------|----------|--------|
| H1 | LB disponible + compatible | LB reserve, original replaced_by_lb | PASS |
| H2 | Aucun LB disponible | Deliver suspicious normally | PASS |
| H3 | LB = doublon 30j pour ce client | Skip, chercher suivant | PASS |
| H4 | Reservation atomique (concurrent) | Un seul gagne, l'autre fallback | PASS |
| H5 | LB respecte departement commande | Filtre departement actif | PASS |
| H6 | Pas de remplacement pour "direct" source | Deliver normally | PASS |

---

## 6. OVERLAP GUARD

| # | Scenario | Expected | Status |
|---|----------|----------|--------|
| I1 | Client partage, delivery cross-entity <30j | Alternative trouvee -> switch | PASS |
| I2 | Client partage, pas d'alternative | Fallback delivery (fail-open) | PASS |
| I3 | Client non partage | Pas d'overlap detecte | PASS |
| I4 | Kill switch OFF | Pas de check, baseline identique | PASS |
| I5 | Exception dans overlap_guard | Fail-open, delivery normale | PASS |
| I6 | Timeout (>500ms) | Fail-open, delivery normale | PASS |
| I7 | Max 10 candidates | Arret apres 10 alternatives | PASS |

---

## 7. MONITORING

| # | Scenario | Expected | Status |
|---|----------|----------|--------|
| J1 | Widget phone_quality | Aggregation par source/quality | PASS |
| J2 | Widget duplicate_by_source | Taux doublon par source | PASS |
| J3 | Widget cross_matrix | Conflits source A/B | PASS |
| J4 | Widget cannibalization index | Cross-entity duplicate rate | PASS |
| J5 | Widget source_scores (toxicity/trust) | Scores 0-100 | PASS |
| J6 | Widget overlap_stats | Shared clients count/rate | PASS |
| J7 | Widget fail-open (un widget crash) | Autres widgets OK, _errors partial | PASS |
| J8 | Range 24h / 7d / 30d / 90d | Cutoff correct | PASS |

---

## 8. CHAOS TESTS (SCENARIOS EXTREMES)

| # | Scenario | Expected | Status |
|---|----------|----------|--------|
| K1 | DB lente (query timeout) | Monitoring fail-open, delivery retry | DESIGN |
| K2 | Exception dans overlap_guard | Fail-open, log error, delivery OK | PASS |
| K3 | Exception dans lb_replacement | Deliver suspicious normally | PASS |
| K4 | Double run cron | State machine bloque double-sent | PASS |
| K5 | SMTP down | Delivery failed, CSV stocke, retry | PASS |
| K6 | 100 leads meme phone en 1s | Double-submit detecte, 1 seul cree | DESIGN |
| K7 | Provider envoie 10k leads/min | Pas de rate limiting (RISK m-02) | RISK |
| K8 | Intercompany pricing manquant | Warning log, price=0, transfer cree | PASS |

---

## 9. COVERAGE PAR MODULE

| Module | Tests unitaires | Tests E2E | Scenarios chaos | Score |
|--------|----------------|-----------|-----------------|-------|
| Phone normalization | 15 | 3 | 0 | A |
| Ingestion (public.py) | 0 | 12 | 2 | B+ |
| Routing engine | 0 | 14 | 1 | B+ |
| Duplicate detector | 0 | 6 | 0 | B |
| Delivery state machine | 0 | 12 | 2 | B+ |
| LB replacement | 6 | 4 | 1 | B+ |
| Overlap guard | 14 | 2 | 2 | A |
| Monitoring | 8 | 0 | 1 | B |
| Billing | 0 | 4 | 0 | C |
| Auth / RBAC | 0 | 8 | 0 | B |
| Settings | 0 | 4 | 0 | B- |
| Intercompany | 0 | 2 | 1 | C+ |

**Note:** Les tests existants sont principalement dans:
- `test_phone_normalization.py` (phone validation)
- `test_overlap_guard.py` (14 tests)
- `test_monitoring_intelligence.py` (8 tests)
- `test_core_e2e_validation.py` (114 tests comprehensive)

### Legende Status
- **PASS**: Scenario teste et valide
- **RISK**: Scenario identifie comme risque (voir audit report)
- **DESIGN**: Scenario a tester via chaos engineering
