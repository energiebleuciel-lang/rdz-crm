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

- Phase 1 : Backend foundation (modeles, routing, delivery, doublon, CSV, SMTP)
- Audit technique : 25+ fichiers supprimes, naming unifie, DB nettoyee
- Commande OPEN + Cross-entity toggle + Source gating
- **Provider** : auth API key, entity locked, no cross-entity

## NEXT

- **Phase 2** : Connecter /api/public/leads au routing engine (entity/produit auto)
- **Phase 3** : UI Admin (Clients, Commandes, Providers, Settings, Dashboard)

## BACKLOG

- Dashboard stats, Livraison API, Tracking final, rejet_client

## CREDENTIALS

- UI: `energiebleuciel@gmail.com` / `92Ruemarxdormoy`
- SMTP: `@92Ruemarxdormoy`

## API ENDPOINTS

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/auth/login | Non | Connexion |
| GET | /api/auth/me | Oui | Info user |
| GET/POST | /api/clients | Oui | CRUD clients |
| GET/POST | /api/commandes | Oui | CRUD commandes |
| GET/POST | /api/providers | Admin | CRUD providers |
| POST | /api/providers/{id}/rotate-key | Admin | Regenerer API key |
| GET | /api/settings | Oui | Liste settings |
| GET/PUT | /api/settings/cross-entity | Admin | Toggle cross-entity |
| GET/PUT | /api/settings/source-gating | Admin | Source gating |
| POST | /api/public/leads | Non/Key | Soumettre lead |
| POST | /api/public/track/* | Non | Tracking |
