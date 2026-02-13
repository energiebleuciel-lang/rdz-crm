# RDZ CRM - Product Requirements Document

## OBJECTIF

CRM central **RDZ** : collecte 100% des leads, separation stricte **ZR7** / **MDL**, routing immediat + distribution automatique 09h30 CSV.

## NAMING STRICT (SCHEMA FREEZE)

`phone`, `departement`, `produit`, `nom`, `entity` (ZR7|MDL)
❌ Interdit: telephone, tel, mobile, product, product_type, crm, account, dept

## MODELES

- **Client** : `{id, entity, name, email, delivery_emails, active}`
- **Commande** : `{id, entity, client_id, produit, departements, quota_semaine, lb_percent_max, priorite, active}`
- **Provider** : `{id, name, slug, entity, api_key, active}` - fournisseur externe rattache a UNE entite
- **Lead statuts** : `new` | `routed` | `no_open_orders` | `duplicate` | `hold_source` | `pending_config` | `invalid` | `livre`
- **Settings** : `cross_entity`, `source_gating`, `forms_config`

## REGLES METIER

1. **Commande OPEN** = `active` + `semaine courante` + `delivered < quota`
2. **Doublon 30j** = meme phone + produit + client = bloque, remplacement auto
3. **LB** = non livre > 8 jours, exporte comme lead normal
4. **Provider** = auth par API key -> entity verrouillee, jamais de cross-entity
5. **Cross-entity** = ZR7<->MDL fallback, controle par settings (global + per-entity)
6. **Source gating** = blacklist, lead stocke en hold_source, jamais route
7. **Form mapping** = form_code -> entity + produit via settings.forms_config

## ARCHITECTURE (v4.3)

```
/app/backend/
  config.py, server.py
  models/ (auth, client, commande, delivery, entity, lead, provider, setting)
  routes/ (auth, clients, commandes, providers, public, settings)
  services/ (activity_logger, csv_delivery, daily_delivery, duplicate_detector, routing_engine, settings)
```

## COMPLETED

- Phase 1 : Backend foundation (modeles, routing, delivery 09h30, doublon 30j, CSV ZR7/MDL, SMTP OVH)
- Audit technique (Decembre 2025) : 25+ fichiers legacy supprimes, naming unifie (produit partout), DB nettoyee
- Commande OPEN : active + semaine courante + delivered < quota
- Cross-entity toggle : collection settings, global ON/OFF + per-entity in/out
- Source gating : blacklist dans settings, lead stocke hold_source
- Provider : auth API key (prov_xxx), entity locked, cross-entity interdit, CRUD admin + rotate-key
- **Phase 2 (Decembre 2025)** : Routing immediat dans POST /api/public/leads
  - form_code mapping (settings.forms_config -> entity + produit)
  - Routing engine appele apres insert
  - Delivery record cree quand routed (status=pending_csv pour batch CSV matin)
  - Statuts enrichis: routed, no_open_orders, duplicate, hold_source, pending_config, invalid
  - Tests: 22/22 passes

## NEXT (Phase 3 - UI Admin)

- Interface gestion Clients par entite
- Interface gestion Commandes (CRUD + stats OPEN/CLOSED)
- Interface gestion Providers (CRUD + API keys)
- Interface forms_config (form_code -> entity/produit)
- Page Settings (cross-entity toggle, source gating)
- Dashboard livraison (stats quotidiennes)

## BACKLOG

- Dashboard stats avances (filtres par entite/produit/periode)
- Livraison API (POST en plus du CSV)
- Tracking & audit final
- Feature rejet_client (client rejette un lead livre)
- Facturation inter-entites

## CREDENTIALS

- UI: `energiebleuciel@gmail.com` / `92Ruemarxdormoy`
- SMTP ZR7: `vos-leads@zr7-digital.fr` / `@92Ruemarxdormoy`
- SMTP MDL: `livraisonleads@maisonduleads.fr` / `@92Ruemarxdormoy`
- Provider test: `prov_0vVMbevPVC1yBXXb3cPKySmiB_iP4nW1cjTjIOQ54is` (ZR7)

## API ENDPOINTS

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/auth/login | Non | Connexion |
| GET | /api/auth/me | Oui | Info user |
| GET/POST/PUT/DELETE | /api/clients | Oui | CRUD clients |
| GET/POST/PUT/DELETE | /api/commandes | Oui | CRUD commandes |
| GET/POST/PUT/DELETE | /api/providers | Admin | CRUD providers |
| POST | /api/providers/{id}/rotate-key | Admin | Regenerer API key |
| GET | /api/settings | Oui | Liste settings |
| GET/PUT | /api/settings/cross-entity | Admin | Toggle cross-entity |
| GET/PUT | /api/settings/source-gating | Admin | Source gating |
| GET/PUT | /api/settings/forms-config | Admin | Form -> entity/produit mapping |
| POST | /api/settings/forms-config/{code} | Admin | Config single form |
| POST | /api/public/leads | Non/Key | Soumettre lead + routing immediat |
| POST | /api/public/track/session | Non | Creer session |
| POST | /api/public/track/lp-visit | Non | Tracking LP |
| POST | /api/public/track/event | Non | Tracking event |

## KEY FILES

- `/app/backend/server.py` - FastAPI app, routes, indexes, scheduler 09h30
- `/app/backend/services/routing_engine.py` - is_commande_open(), find_open_commandes(), route_lead(entity_locked), _try_cross_entity()
- `/app/backend/services/daily_delivery.py` - run_daily_delivery(), mark_leads_as_lb(), process_commande_delivery()
- `/app/backend/services/duplicate_detector.py` - check_duplicate_30_days() (supports old+new format), check_double_submit()
- `/app/backend/services/csv_delivery.py` - generate_csv_content() (ZR7: 7 cols, MDL: 8 cols), send_csv_email()
- `/app/backend/services/settings.py` - get/upsert settings, is_cross_entity_allowed(), is_source_allowed(), get_form_config()
- `/app/backend/routes/public.py` - submit_lead avec routing immediat + provider auth + source gating
- `/app/backend/routes/providers.py` - CRUD providers + rotate-key
- `/app/backend/routes/settings.py` - Admin settings endpoints + forms-config
