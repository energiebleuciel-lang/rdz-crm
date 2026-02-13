# 🔒 RDZ CRM - OFFICIAL SCHEMA FREEZE
> **Date**: December 2025  
> **Status**: IMMUTABLE - NO MODIFICATIONS ALLOWED

## Core Identity Fields
| Field | Type | Notes |
|-------|------|-------|
| `id` | string (uuid) | Primary key |
| `phone` | string | ✅ ONLY this (never telephone/tel/mobile) |
| `nom` | string | |
| `prenom` | string | |
| `email` | string | |

## Classification Fields
| Field | Type | Values |
|-------|------|--------|
| `entity` | string | `ZR7` \| `MDL` |
| `produit` | string | `PV` \| `PAC` \| `ITE` |
| `departement` | string | 2 digits (01-95, 2A, 2B, 971-976) |
| `status` | string | `new` \| `delivered` \| `hold_source` \| `duplicate` \| `invalid` |
| `entity_locked` | boolean | Provider leads only |

## Tracking Fields
| Field | Type |
|-------|------|
| `session_id` | string |
| `lp_code` | string |
| `form_code` | string |
| `liaison_code` | string |
| `source` | string |
| `utm_source` | string |
| `utm_medium` | string |
| `utm_campaign` | string |

## Provider Fields
| Field | Type |
|-------|------|
| `provider_id` | string |
| `provider_slug` | string |

## Date Fields
| Field | Type | Notes |
|-------|------|-------|
| `register_date` | timestamp | Unix timestamp |
| `created_at` | string | ISO datetime |

## Extra Data
| Field | Type |
|-------|------|
| `custom_fields` | object |

---

## ❌ FORBIDDEN NAMES - NEVER USE
```
telephone, tel, mobile, numero
product, product_type
crm, account
dept, department
```

## ✅ ENFORCEMENT CHECKLIST
- [x] Backend models
- [x] Backend routes
- [x] Backend services
- [x] Routing engine
- [x] CSV exports (uses `telephone` for French clients - ALLOWED in export only)
- [ ] Frontend (Phase 3 - to be rebuilt)
- [ ] Tracking scripts (Phase 9)

## Notes
- `telephone` is allowed ONLY in CSV export headers (French business requirement)
- Internal field must ALWAYS be `phone`
- `produit` is the official term (not `product` or `product_type`)
- `departement` is official (not `dept` or `department`)
