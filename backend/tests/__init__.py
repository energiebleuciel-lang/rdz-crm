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
- Prix
- Emails SMTP
- Stats

Champ `entity` obligatoire partout.

---

## MODELES DE DONNEES

### Naming strict
- `phone` (jamais telephone)
- `departement` (jamais code_postal)
- `produit` (jamais product_type)
- `nom` (jamais name pour un lead)
- `entity` (ZR7 ou MDL)

### Client (Acheteur de leads)
```json
{
  "id": "uuid",
  "entity": "ZR7|MDL",
  "name": "Installateur XYZ",
  "email": "contact@xyz.fr",
  "delivery_emails": [],
  "default_prix_lead": 25.0,
  "active": true
}
```

### Commande (Ordre d'achat)
```json
{
  "id": "uuid",
  "entity": "ZR7|MDL",
  "client_id": "xxx",
  "produit": "PV|PAC|ITE",
  "departements": ["75", "92"],
  "quota_semaine": 50,
  "prix_lead": 25.0,
  "lb_percent_max": 20,
  "priorite": 5,
  "active": true
}
```

### Lead (Statuts)
| Statut | Description |
|--------|-------------|
| `new` | Nouveau lead, pas encore traite |
| `non_livre` | Non livre (pas de commande) |
| `livre` | Livre avec succes a un client |
| `doublon` | Doublon 30 jours |
| `rejet_client` | Rejete par le client |
| `lb` | Lead Backlog (>8 jours sans livraison) |

---

## REGLES METIER

### Regle d'insertion
Un lead est TOUJOURS insere si telephone present.

### Regle Doublon 30 jours
Doublon si : meme telephone + meme produit + deja livre au MEME client + dans les 30 derniers jours.
- NE PAS envoyer
- Rester en base avec status=doublon
- Remplacement automatique par le lead suivant compatible

### Regle LB (Lead Backlog)
- Lead non livre depuis > 8 jours -> LB
- LB peut etre redistribue
- LB ne doit jamais retourner au meme client (sauf si aucune disponibilite)
- Un lead LB est exporte comme un lead NORMAL (aucune mention LB dans le CSV)

---

## FORMAT CSV

### ZR7 (7 colonnes)
nom, prenom, telephone, email, departement, proprietaire_maison(=oui), produit

### MDL (8 colonnes)
nom, prenom, telephone, email, departement, proprietaire(=oui), type_logement(=maison), produit

---

## LIVRAISON AUTOMATIQUE

### CRON : 09h30 Europe/Paris
1. Marquer vieux leads (>8j) comme LB
2. Recuperer leads new/non_livre
3. Router vers commandes actives (priorite + quota)
4. Eviter doublons 30 jours
5. Completer avec LB si autorise
6. Generer CSV
7. Envoyer par email
8. Mettre a jour la base

### SMTP
| Entity | Email | Host | Port |
|--------|-------|------|------|
| ZR7 | vos-leads@zr7-digital.fr | ssl0.ovh.net | 465 SSL |
| MDL | livraisonleads@maisonduleads.fr | ssl0.ovh.net | 465 SSL |

---

## ARCHITECTURE CODE (POST-AUDIT v4.0)

```
/app/backend/
  config.py              # DB, helpers, validation telephone
  server.py              # FastAPI app, CORS, scheduler, indexes
  models/
    __init__.py          # Exports tous les modeles
    auth.py              # Auth & utilisateurs
    client.py            # Client (acheteur de leads)
    commande.py          # Commande (ordre d'achat)
    delivery.py          # Delivery batch
    entity.py            # Entity config (ZR7/MDL)
    lead.py              # Lead (source unique)
  routes/
    auth.py              # Login, logout, users CRUD
    clients.py           # CRUD clients par entity
    commandes.py         # CRUD commandes par entity
    public.py            # Tracking + soumission leads
  services/
    activity_logger.py   # Journal d'activite
    csv_delivery.py      # Generation et envoi CSV
    daily_delivery.py    # Scheduler livraison 09h30
    duplicate_detector.py # Doublon 30 jours + anti double-submit
    routing_engine.py    # Moteur de routing leads
```

---

## PHASE 1 COMPLETEE (Fevrier 2026)

- Modeles multi-tenant (ZR7/MDL)
- Moteur de routing base sur commandes
- Livraison quotidienne 09h30 Paris (APScheduler)
- Regle doublon 30 jours + remplacement automatique
- CSV differencies (ZR7: 7 cols, MDL: 8 cols)
- Envoi SMTP par entite
- CRUD Clients + Commandes

## AUDIT TECHNIQUE COMPLETE (Decembre 2025)

- Suppression de 25+ fichiers legacy
- Rename product_type -> produit partout
- Nettoyage base de donnees (indexes, collections, champs)
- Zero code mort, zero fallback, zero logique parallele
- Une seule source de verite pour chaque concept
- Lint 0 erreurs

---

## PHASES SUIVANTES

### Phase 2 - Integration Pipeline Public (P0)
- Connecter POST /api/public/leads au routing engine
- Determiner entity/produit automatiquement
- Tests E2E complets du flux

### Phase 3 - UI Admin (P1)
- Interface gestion Clients par entite
- Interface gestion Commandes
- Dashboard de livraison

### Phase 4 - Dashboard (P2)
- Stats quotidiennes
- Filtres par entite, produit, periode

### Backlog
- Livraison API (POST en plus du CSV)
- Tracking & audit final
- Feature rejet_client

---

## CREDENTIALS

- **UI Login** : `energiebleuciel@gmail.com` / `92Ruemarxdormoy`
- **SMTP ZR7/MDL** : `@92Ruemarxdormoy`

## API ENDPOINTS

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/auth/login | Non | Connexion |
| GET | /api/auth/me | Oui | Info utilisateur |
| GET | /api/clients?entity=X | Oui | Liste clients |
| POST | /api/clients | Oui | Creer client |
| GET | /api/commandes?entity=X | Oui | Liste commandes |
| POST | /api/commandes | Oui | Creer commande |
| GET | /api/commandes/departements | Oui | Liste depts |
| GET | /api/commandes/products | Oui | Liste produits |
| POST | /api/public/leads | Non | Soumettre lead |
| POST | /api/public/track/session | Non | Creer session |
| POST | /api/public/track/lp-visit | Non | Tracking LP |
| POST | /api/public/track/event | Non | Tracking event |
