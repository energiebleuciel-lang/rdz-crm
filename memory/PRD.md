# RDZ CRM - Product Requirements Document

## OBJECTIF GLOBAL

Construire un CRM central unique **RDZ** qui :
- Recupere 100% des leads
- Ne perd jamais aucun lead
- Stocke tout avant toute distribution
- Separe strictement **ZR7** et **MDL**
- Distribue automatiquement selon commandes
- Livre automatiquement chaque matin **09h30 Europe/Paris**
- Envoi automatique CSV par email
- **Zero manipulation humaine**

---

## ARCHITECTURE MULTI-TENANT

### Entites
- **ZR7** - ZR7 Digital
- **MDL** - Maison du Lead

### Regle fondamentale
TOUS les leads passent par RDZ avant toute distribution.

### Separation stricte
Chaque entite possede ses propres :
- Clients (acheteurs de leads)
- Commandes (ordres d'achat)
- Prix, Emails SMTP, Stats

Champ `entity` obligatoire partout.

---

## NAMING STRICT

- `phone` (jamais telephone)
- `departement` (jamais code_postal)
- `produit` (jamais product_type)
- `nom` (jamais name pour un lead)
- `entity` (ZR7 ou MDL)

---

## MODELES DE DONNEES

### Client
`{id, entity, name, email, delivery_emails, default_prix_lead, active}`

### Commande
`{id, entity, client_id, produit, departements, quota_semaine, prix_lead, lb_percent_max, priorite, active}`

### Lead Statuts
| Statut | Description |
|--------|-------------|
| `new` | Nouveau, pas encore traite |
| `non_livre` | Non livre |
| `livre` | Livre a un client |
| `doublon` | Doublon 30 jours |
| `rejet_client` | Rejete par le client |
| `lb` | Lead Backlog (>8 jours) |

---

## REGLES METIER

1. Lead TOUJOURS insere si telephone present
2. Doublon 30j: meme phone + produit + client = bloque, remplace automatiquement
3. LB: non livre > 8 jours, exporte comme lead normal
4. CSV: ZR7 (7 cols), MDL (8 cols)
5. Livraison 09h30 Europe/Paris

---

## ARCHITECTURE CODE (v4.0 POST-AUDIT)

```
/app/backend/
  config.py
  server.py
  models/ (auth, client, commande, delivery, entity, lead)
  routes/ (auth, clients, commandes, public)
  services/ (activity_logger, csv_delivery, daily_delivery, duplicate_detector, routing_engine)
```

---

## COMPLETED

### Phase 1 - Backend Foundation (Fevrier 2026)
- Modeles multi-tenant, routing, delivery 09h30, doublon 30j, CSV, SMTP

### Audit Technique (Decembre 2025)
- 25+ fichiers legacy supprimes
- Naming unifie (produit partout)
- DB nettoyee (indexes, collections, champs)
- Zero code mort, zero fallback
- Lint 0 erreurs

---

## NEXT

### Phase 2 - Pipeline Public (P0)
- Connecter /api/public/leads au routing engine
- Determiner entity/produit automatiquement

### Phase 3 - UI Admin (P1)
- Gestion Clients + Commandes par entite
- Dashboard livraison

### Phase 4 - Dashboard (P2)
- Stats quotidiennes, filtres

### Backlog
- Livraison API, Tracking final, rejet_client

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
| POST | /api/public/leads | Non | Soumettre lead |
| POST | /api/public/track/session | Non | Session tracking |
| POST | /api/public/track/lp-visit | Non | LP visit |
| POST | /api/public/track/event | Non | Event tracking |
