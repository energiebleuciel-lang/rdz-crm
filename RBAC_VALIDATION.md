# RDZ CRM - RBAC Validation Checklist

## Test Accounts (dev/staging only)
| Email | Password | Role | Entity |
|---|---|---|---|
| `superadmin@test.local` | `RdzTest2026!` | super_admin | ZR7 |
| `admin_zr7@test.local` | `RdzTest2026!` | admin | ZR7 |
| `ops_zr7@test.local` | `RdzTest2026!` | ops | ZR7 |
| `viewer_zr7@test.local` | `RdzTest2026!` | viewer | ZR7 |
| `admin_mdl@test.local` | `RdzTest2026!` | admin | MDL |
| `ops_mdl@test.local` | `RdzTest2026!` | ops | MDL |
| `viewer_mdl@test.local` | `RdzTest2026!` | viewer | MDL |

**Reset/Re-seed:** `cd /app/backend && python scripts/seed_test_users.py`

---

## 1. Entity Isolation

| Test | Login as | Action | Expected |
|---|---|---|---|
| Own entity | ops_zr7 | /admin/commandes | Sees ZR7 commandes only |
| Cross entity | ops_zr7 | API: `?entity=MDL` | 403 Forbidden |
| Own entity | ops_mdl | /admin/commandes | Sees MDL commandes only |
| Cross entity | ops_mdl | API: `?entity=ZR7` | 403 Forbidden |
| Super admin ZR7 | superadmin | Click scope ZR7 | Sees ZR7 data only |
| Super admin MDL | superadmin | Click scope MDL | Sees MDL data only |
| Super admin BOTH | superadmin | Click scope BOTH | Combined ZR7+MDL |

## 2. Menu Visibility

| Menu Item | super_admin | admin | ops | viewer |
|---|---|---|---|---|
| Dashboard | Yes | Yes | Yes | Yes |
| Deliveries | Yes | Yes | Yes | Yes |
| Leads | Yes | Yes | Yes | Yes |
| Clients | Yes | Yes | Yes | Yes |
| Commandes | Yes | Yes | Yes | Yes |
| Departements | Yes | Yes | Yes | Yes |
| Facturation | Yes | Yes | **No** | **No** |
| Activity | Yes | Yes | **No** | **No** |
| Utilisateurs | Yes | **No** | **No** | **No** |
| Settings | Yes | Yes | **No** | **No** |

## 3. Write Permissions

| Action | admin | ops | viewer |
|---|---|---|---|
| Create client | Yes | **No** | **No** |
| Edit client | Yes | **No** | **No** |
| Create commande | Yes | **No** | **No** |
| Edit quota/LB target | Yes | Yes | **No** |
| Activate/pause commande | Yes | Yes | **No** |
| Resend delivery | Yes | Yes | **No** |
| Manage users | **No** | **No** | **No** |

## 4. Scope Switcher

| Login as | Scope Switcher visible? | Entity badge? |
|---|---|---|
| super_admin | **Yes** (ZR7/MDL/BOTH) | No (uses switcher) |
| admin | **No** | Yes (shows entity) |
| ops | **No** | Yes (shows entity) |
| viewer | **No** | Yes (shows entity) |

## 5. LB Monitoring Widget (super_admin only)

| Login as | LB Monitor visible? |
|---|---|
| super_admin | **Yes** (on commandes page) |
| admin | **No** |
| ops | **No** |
| viewer | **No** |
