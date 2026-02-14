# RELEASE POLICY — RDZ CRM v1.0.0
## Politique de release et freeze — Mise a jour 2026-02-15

---

## 1. VERSION STABLE

| Attribut | Valeur |
|----------|--------|
| Version | 1.0.0 |
| Tag | `rdz-core-distribution-validated` |
| Date freeze | 2026-02-14 |
| Tests de regression | 69+ tests (phone, overlap, monitoring) + 114 E2E |

---

## 2. MODULES GELES (CORE)

Les modules suivants sont **GELES**. Toute modification requiert:
1. Justification ecrite
2. Review code
3. Suite E2E complete PASS (114+ tests)
4. Tag git AVANT deploiement

| Module | Fichier | Raison |
|--------|---------|--------|
| Routing engine | `services/routing_engine.py` | Logique metier critique |
| Duplicate detector | `services/duplicate_detector.py` | Regle 30 jours |
| Delivery state machine | `services/delivery_state_machine.py` | Invariants sent/livre |
| Daily delivery (cron) | `services/daily_delivery.py` | Livraison quotidienne |
| Auth & sessions | `routes/auth.py` | Securite |
| Permissions | `services/permissions.py` | RBAC |
| Entity isolation | Pattern transverse | Multi-tenant |

---

## 3. MODULES EXTENSIBLES

Ces modules peuvent etre modifies avec des tests unitaires seulement:

| Module | Fichier | Regle |
|--------|---------|-------|
| Monitoring (READ-ONLY) | `routes/monitoring.py` | Fail-open per-widget |
| Overlap guard | `services/overlap_guard.py` | Kill switch + fail-open |
| LB replacement | `services/lb_replacement.py` | Fail-open |
| Intercompany | `services/intercompany.py` | Fail-open |
| Billing | `routes/billing.py` | Pas de lien avec delivery flow |
| Settings | `routes/settings.py` | Admin only |

---

## 4. PROCEDURE DE MERGE

### 4.1 Pour modules geles
1. Branch feature depuis `main`
2. Developper + tests unitaires
3. Run `python -m pytest tests/ -v` — TOUT doit passer
4. Review code par second dev
5. `git tag v1.0.X-pre-merge` AVANT merge
6. Merge + deploy
7. Verifier `/api/system/version` + `/api/system/health`
8. `git tag v1.0.X` si OK

### 4.2 Pour modules extensibles
1. Developper + tests specifiques
2. Run tests du module concerne
3. Smoke test: `/api/system/health`
4. Deploy

---

## 5. PROCEDURE DE ROLLBACK

1. **Emergent Platform:** Utiliser la fonctionnalite "Rollback" (restaure un checkpoint)
2. **Verifier:** `/api/system/version` retourne la version attendue
3. **Verifier:** `/api/system/health` retourne `status: healthy`
4. **Si rollback DB necessaire:** Restaurer le backup MongoDB pre-merge

---

## 6. BLOCAGE DEPLOIEMENT

Le deploiement est **INTERDIT** si:
- Un test E2E echoue
- Un finding critique (C-xx) n'est pas resolu
- Le tag git n'est pas cree
- La variable `CORE_VERSION` dans `system_health.py` n'est pas mise a jour

---

## 7. AUDIT TRAIL

| Date | Version | Action | Findings |
|------|---------|--------|----------|
| 2026-02-14 | 1.0.0 | Core freeze + validation | 114 E2E pass |
| 2026-02-15 | 1.0.0 | Audit global zero surprises | 3C + 14M + 21m identifies |
| 2026-02-15 | 1.0.1 | Fixes: C-02 (defaults), C-03 (enum), M-07 ($or), m-11 (SMTP timeout), m-03 (index), M-06 (LB 30j) | 6 fixes appliquees |
