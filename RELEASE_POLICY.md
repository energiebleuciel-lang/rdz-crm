# RDZ CRM — RELEASE POLICY
## Version: 1.0 | Date: 2026-02-14

---

## 1. Version Unique + Identifiant Visible

- **Tag de référence** : `rdz-core-distribution-validated`
- **Version** : `1.0.0`
- **Endpoint** : `GET /api/system/version` retourne `{ version, tag, git_sha, build_date, env }`
- **Frontend** : Version affichée dans le footer de la sidebar admin (`vX.Y.Z (sha)`)

---

## 2. Déploiement Verrouillé

| Règle | Détail |
|-------|--------|
| Source autorisée | Uniquement depuis `main` + tag validé |
| Branche non taggée | Déploiement interdit en prod |
| Lockfiles | `yarn.lock` (frontend) + `requirements.txt` (backend) versionnés |
| Reproductibilité | Mêmes dépendances, même résultat |

---

## 3. Base de Données : Migrations & Compatibilité

| Règle | Détail |
|-------|--------|
| Schéma | Toute modification = migration versionnée |
| Index dump | `indexes_v1.json` versionné à la racine |
| Rollback plan | Obligatoire pour chaque migration |
| Changement manuel | **INTERDIT** en prod |
| Index creation | Idempotent (`create_index` + `background=True`) |

---

## 4. Environnements

| Env | Rôle | Version |
|-----|------|---------|
| **dev** | Développement, expérimentation | Toute branche |
| **staging** | Miroir de prod, validation | Même version que prod (tag) |
| **prod** | Production | Uniquement depuis tag validé |

---

## 5. Règle d'Or — Modules Protégés

Après freeze, si une modification touche l'un des modules ci-dessous, le merge est **REFUSÉ** sans :

1. Suite de tests E2E complète (`test_core_e2e_validation.py` — 35 tests)
2. Revue manuelle des changements
3. Validation explicite du responsable

### Modules Protégés

| Module | Fichiers |
|--------|---------|
| **Routing** | `services/routing_engine.py` |
| **Duplicate Detection** | `services/duplicate_detector.py` |
| **Delivery State Machine** | `services/delivery_state_machine.py` |
| **Daily Delivery** | `services/daily_delivery.py` |
| **Auth / RBAC** | `routes/auth.py`, `services/permissions.py` |
| **Entity Scoping** | Tout usage de `get_entity_scope_from_request`, `build_entity_filter` |
| **Cron Jobs** | `server.py` (scheduler), `services/intercompany.py` |
| **Public Ingestion** | `routes/public.py` |

### Procédure de Validation

```
1. git checkout -b fix/my-change
2. Modifier le code
3. cd /app/backend && pytest tests/test_core_e2e_validation.py -v
4. Si 35/35 PASS → OK pour merge
5. Si FAIL → corriger AVANT merge
6. Après merge → re-tag si applicable
```

---

## 6. Artifacts de Freeze

| Artifact | Chemin | Description |
|----------|--------|-------------|
| Index dump | `/app/indexes_v1.json` | 70 indexes, 26 collections |
| E2E test suite | `/app/backend/tests/test_core_e2e_validation.py` | 35 tests (A→H) |
| Audit report | `/app/AUDIT_REPORT_PRODUCTION.md` | Full audit + blast radius |
| Validation report | `/app/CORE_E2E_VALIDATION_REPORT.md` | E2E proof |
| Release policy | `/app/RELEASE_POLICY.md` | Ce document |
