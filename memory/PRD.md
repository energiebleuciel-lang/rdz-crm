# RDZ CRM - Product Requirements Document

## 🎯 OBJECTIF GLOBAL

Construire un CRM central unique **RDZ** qui :
- Récupère 100% des leads
- Ne perd jamais aucun lead
- Stocke tout avant toute distribution
- Sépare strictement **ZR7** et **MDL**
- Distribue automatiquement selon commandes
- Livre automatiquement chaque matin **09h30 Europe/Paris**
- Envoi automatique CSV par email et/ou API
- **Zéro manipulation humaine**

---

## 🏗️ ARCHITECTURE MULTI-TENANT

### Entités (Entity)
- **ZR7** - ZR7 Digital
- **MDL** - Maison du Lead

### Règle fondamentale
TOUS les leads passent par RDZ avant toute distribution.
**Interdit** : insertion directe vers ZR7 ou MDL

### Séparation stricte
Chaque entité possède ses propres :
- Clients (acheteurs de leads)
- Commandes (ordres d'achat)
- Prix
- Emails SMTP
- Stats
- Facturation

⚠️ **AUCUN mélange de données** - Champ `entity` obligatoire partout

---

## 📊 MODÈLES DE DONNÉES

### Client (Acheteur de leads)
```json
{
  "id": "uuid",
  "entity": "ZR7|MDL",  // OBLIGATOIRE
  "name": "Installateur XYZ",
  "email": "contact@xyz.fr",
  "delivery_emails": [],
  "api_endpoint": "",
  "default_prix_lead": 25.0,
  "remise_percent": 0,
  "active": true
}
```

### Commande (Ordre d'achat)
```json
{
  "id": "uuid",
  "entity": "ZR7|MDL",  // OBLIGATOIRE
  "client_id": "xxx",
  "product_type": "PV|PAC|ITE",
  "departements": ["75", "92", "93"],
  "quota_semaine": 50,
  "prix_lead": 25.0,
  "lb_percent_max": 20,  // % LB autorisé
  "priorite": 5,  // 1=haute, 10=basse
  "auto_renew": true,
  "active": true
}
```

### Lead (Statuts)
| Statut | Description |
|--------|-------------|
| `new` | Nouveau lead, pas encore traité |
| `non_livre` | Non livré (pas de commande, etc.) |
| `livre` | Livré avec succès à un client |
| `doublon` | Doublon 30 jours (non envoyé mais stocké) |
| `rejet_client` | Rejeté par le client après livraison |
| `lb` | Lead Backlog (>8 jours sans livraison) |

---

## ⚙️ RÈGLES MÉTIER

### Règle d'insertion (CRITIQUE)
Un lead est **TOUJOURS inséré** si téléphone présent.
Même si doublon, même si non livré, même sans commande, même rejeté.

### Règle Doublon 30 jours
**Doublon** si :
- Même téléphone
- Même produit
- Déjà livré **au même client**
- Dans les 30 derniers jours

**Comportement** :
- ❌ NE PAS envoyer
- ✅ Rester en base avec `status = doublon`
- ✅ Logger : client déjà livré + date livraison précédente

### Règle LB (Lead Backlog)
- Lead non livré depuis **> 8 jours** → devient LB automatiquement
- LB peut être redistribué
- LB ne doit jamais retourner au même client (sauf si aucune disponibilité)

**⚠️ RÈGLE EXPORT LB** : Un lead LB doit être exporté comme un lead **NORMAL** :
- Aucune mention "LB" dans le CSV
- Le champ `produit` = produit de la **commande** (pas l'original du lead)

---

## 📤 FORMAT CSV (OBLIGATOIRE)

**7 colonnes exactes, dans cet ordre** :

| # | Colonne | Description |
|---|---------|-------------|
| 1 | nom | Nom du lead |
| 2 | prenom | Prénom du lead |
| 3 | telephone | Numéro de téléphone |
| 4 | email | Email |
| 5 | departement | Code département |
| 6 | proprietaire_maison | **Toujours TRUE** |
| 7 | produit | **Produit de la commande** |

**Interdits** : lead_id, date, source, type, raison, LB, statut

---

## ⏰ LIVRAISON AUTOMATIQUE

### CRON : 09h30 Europe/Paris (tous les jours)
Actions :
1. Marquer les vieux leads (>8j) comme LB
2. Récupérer les leads `new`/`non_livre`
3. Router vers commandes actives (priorité + quota)
4. Éviter doublons 30 jours
5. Compléter avec LB si autorisé
6. Générer CSV
7. Envoyer par email
8. Mettre à jour la base

### SMTP Configuration
| Entity | Email | Host | Port |
|--------|-------|------|------|
| ZR7 | livraison@zr7-digital.fr | ssl0.ovh.net | 465 SSL |
| MDL | livraisonleads@maisonduleads.fr | ssl0.ovh.net | 465 SSL |

---

## ✅ PHASE 1 COMPLÉTÉE (Février 2026)

### Nouveaux modèles implémentés
- `/app/backend/models/entity.py` - EntityType (ZR7/MDL)
- `/app/backend/models/client.py` - ClientCreate/Update/Response
- `/app/backend/models/commande.py` - CommandeCreate/Update/Response
- `/app/backend/models/lead.py` - LeadStatus, LeadDocument
- `/app/backend/models/delivery.py` - DeliveryBatch, DeliveryStats

### Nouveaux services implémentés
- `/app/backend/services/duplicate_detector_v2.py` - Règle 30 jours
- `/app/backend/services/routing_engine.py` - Moteur de routing
- `/app/backend/services/csv_delivery.py` - Génération et envoi CSV
- `/app/backend/services/daily_delivery.py` - Scheduler 09h30

### Nouvelles routes API
- `GET/POST /api/clients` - CRUD clients (entity obligatoire)
- `GET/POST /api/commandes` - CRUD commandes
- `GET /api/commandes/departements` - Liste départements métro
- `GET /api/commandes/products` - Liste produits (PV/PAC/ITE)

### Scheduler configuré
- Livraison quotidienne: 09h30 Europe/Paris
- Vérification nocturne: 03h00 UTC
- Queue processing: 5 minutes

---

## 🔜 PHASES SUIVANTES

### Phase 2 - Intégration Pipeline Public
- Modifier `routes/public.py` pour ajouter le champ `entity` aux leads
- Connecter submit_lead au nouveau routing engine
- Tests E2E complets du flux

### Phase 3 - UI Admin
- Interface gestion Clients par entité
- Interface gestion Commandes
- Dashboard de livraison

### Phase 4 - Production
- Tests E2E avec vrais envois CSV
- Validation SMTP
- Monitoring et alertes

---

## 🔐 CREDENTIALS TEST

- **UI Login** : `energiebleuciel@gmail.com` / `92Ruemarxdormoy`
- **SMTP ZR7/MDL** : `@92Ruemarxdormoy`

## URLs CRM
- **ZR7** : `https://app.zr7-digital.fr/lead/api/create_lead/`
- **MDL** : `https://maison-du-lead.com/lead/api/create_lead/`
