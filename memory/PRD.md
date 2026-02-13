# RDZ CRM - Product Requirements Document

## OBJECTIF GLOBAL

CRM central unique **RDZ** :
- Recupere 100% des leads, zero perte
- Separation stricte **ZR7** / **MDL** (multi-tenant)
- Distribution automatique selon commandes OPEN
- Livraison quotidienne 09h30 Europe/Paris (CSV email)
- Zero manipulation humaine

---

## NAMING STRICT

`phone`, `departement`, `produit`, `nom`, `entity` (ZR7|MDL)

---

## MODELES

### Client
`{id, entity, name, email, delivery_emails, default_prix_lead, active}`

### Commande
`{id, entity, client_id, produit, departements, quota_semaine, prix_lead, lb_percent_max, priorite, active}`

### Lead Statuts
`new` | `non_livre` | `livre` | `doublon` | `rejet_client` | `lb` | `hold_source`

### Settings (collection `settings`, key-based)
- `cross_entity`: toggle global + per-entity in/out
- `source_gating`: blacklist de sources

---

## REGLES METIER

### Commande OPEN
OPEN = `active=true` AND `semaine courante` AND `delivered_this_week < quota_semaine`
- Quota 0 = illimite (toujours OPEN)
- Commande remplie = CLOSED, ne recoit plus de leads

### Cross-entity fallback
- ZR7->MDL ou MDL->ZR7 si aucune commande OPEN dans l'entite principale
- Controle par settings: global ON/OFF + per-entity in/out
- Log `no_open_orders` si fallback impossible

### Source gating
- Blacklist de sources dans settings
- Source bloquee: lead stocke avec `status=hold_source`, jamais route
- Uniquement si lead minimal valide (phone+departement+nom)

### Doublon 30 jours
Meme phone + produit + client = bloque, remplacement automatique

### LB (Lead Backlog)
Non livre > 8 jours, exporte comme lead normal

---

## ARCHITECTURE (v4.1)

```
/app/backend/
  config.py
  server.py
  models/ (auth, client, commande, delivery, entity, lead)
  routes/ (auth, clients, commandes, public, settings)
  services/ (activity_logger, csv_delivery, daily_delivery, duplicate_detector, routing_engine, settings)
```

---

## COMPLETED

### Phase 1 - Backend Foundation (Fevrier 2026)
- Modeles multi-tenant, routing, delivery 09h30, doublon 30j, CSV, SMTP

### Audit Technique (Decembre 2025)
- 25+ fichiers legacy supprimes, naming unifie, DB nettoyee

### Features Routing (Decembre 2025)
- Commande OPEN (active + semaine + quota)
- Cross-entity toggle (global + per-entity in/out)
- Source gating (blacklist, hold_source)
- Settings admin endpoints avec audit (updated_at/by)

---

## NEXT

### Phase 2 - Pipeline Public (P0)
- Connecter /api/public/leads au routing engine automatiquement
- Determiner entity/produit depuis la config formulaire

### Phase 3 - UI Admin (P1)
- Gestion Clients + Commandes par entite
- Dashboard livraison + settings UI

### Backlog
- Dashboard stats, Livraison API, Tracking final, rejet_client

---

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
| GET | /api/settings | Oui | Liste settings |
| GET/PUT | /api/settings/cross-entity | Admin | Toggle cross-entity |
| GET/PUT | /api/settings/source-gating | Admin | Source gating |
| POST | /api/public/leads | Non | Soumettre lead |
| POST | /api/public/track/session | Non | Session tracking |
| POST | /api/public/track/lp-visit | Non | LP visit |
| POST | /api/public/track/event | Non | Event tracking |
