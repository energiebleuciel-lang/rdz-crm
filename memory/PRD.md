# RDZ CRM - Product Requirements Document

## OBJECTIF

CRM central **RDZ** : collecte 100% des leads, separation stricte **ZR7** / **MDL**, distribution automatique 09h30.

## NAMING STRICT

`phone`, `departement`, `produit`, `nom`, `entity` (ZR7|MDL)

## MODELES

- **Client** : `{id, entity, name, email, delivery_emails, active}`
- **Commande** : `{id, entity, client_id, produit, departements, quota_semaine, lb_percent_max, priorite, active}`
- **Provider** : `{id, name, slug, entity, api_key, active}` - fournisseur externe rattache a UNE entite
- **Lead statuts** : `new` | `non_livre` | `livre` | `doublon` | `rejet_client` | `lb` | `hold_source`
- **Settings** : `cross_entity` (toggle global + per-entity in/out), `source_gating` (blacklist)

## REGLES METIER

1. **Commande OPEN** = `active` + `semaine courante` + `delivered < quota`
2. **Doublon 30j** = meme phone + produit + client = bloque, remplacement auto
3. **LB** = non livre > 8 jours, exporte comme lead normal
4. **Provider** = auth par API key -> entity verrouillee, jamais de cross-entity
5. **Cross-entity** = ZR7<->MDL fallback, controle par settings (global + per-entity)
6. **Source gating** = blacklist, lead stocke en hold_source, jamais route

## ARCHITECTURE (v4.2)

```
/app/backend/
  config.py, server.py
  models/ (auth, client, commande, delivery, entity, lead, provider)
  routes/ (auth, clients, commandes, providers, public, settings)
  services/ (activity_logger, csv_delivery, daily_delivery, duplicate_detector, routing_engine, settings)
```

## COMPLETED

- Phase 1 : Backend foundation (modeles, routing, delivery 09h30, doublon 30j, CSV ZR7/MDL, SMTP OVH)
- Audit technique (Decembre 2025) : 25+ fichiers legacy supprimes, naming unifie (produit partout), DB nettoyee (indexes, collections, champs), zero code mort
- Commande OPEN : active + semaine courante + delivered < quota. Cross-entity fallback uniquement si commande OPEN compatible
- Cross-entity toggle : collection settings, global ON/OFF + per-entity in/out (ZR7.in, ZR7.out, MDL.in, MDL.out)
- Source gating : blacklist dans settings, lead stocke hold_source, jamais route
- Provider : auth API key (prov_xxx), entity locked, cross-entity interdit, CRUD admin + rotate-key
- Tests: 59/59 passes (audit 20/20 + settings 18/18 + providers 21/21)

## NEXT (Phase 2 - Pipeline Public)

- Connecter POST /api/public/leads au routing engine
- Determiner entity/produit automatiquement (depuis provider ou config formulaire)
- Tests E2E du flux complet : LP -> Form -> RDZ -> Routing -> CSV -> Email

## UPCOMING (Phase 3 - UI Admin)

- Interface gestion Clients par entite
- Interface gestion Commandes (CRUD + stats OPEN/CLOSED)
- Interface gestion Providers (CRUD + API keys)
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
| POST | /api/public/leads | Non/Key | Soumettre lead |
| POST | /api/public/track/session | Non | Creer session |
| POST | /api/public/track/lp-visit | Non | Tracking LP |
| POST | /api/public/track/event | Non | Tracking event |

## KEY FILES

- `/app/backend/server.py` - FastAPI app, routes, indexes, scheduler 09h30
- `/app/backend/services/routing_engine.py` - is_commande_open(), find_open_commandes(), route_lead(entity_locked), _try_cross_entity()
- `/app/backend/services/daily_delivery.py` - run_daily_delivery(), mark_leads_as_lb(), process_commande_delivery()
- `/app/backend/services/duplicate_detector.py` - check_duplicate_30_days(), check_double_submit()
- `/app/backend/services/csv_delivery.py` - generate_csv_content() (ZR7: 7 cols, MDL: 8 cols), send_csv_email()
- `/app/backend/services/settings.py` - get/upsert settings, is_cross_entity_allowed(), is_source_allowed()
- `/app/backend/routes/public.py` - submit_lead avec provider auth + source gating
- `/app/backend/routes/providers.py` - CRUD providers + rotate-key
- `/app/backend/routes/settings.py` - Admin settings endpoints
- `/app/backend/routes/clients.py` - CRUD clients par entity
- `/app/backend/routes/commandes.py` - CRUD commandes par entity
