# CRM Multi-tenant - Gestion de Leads Solaires

## Problème Original
Créer un CRM multi-tenant pour la gestion de leads solaires. Le système centralise toutes les informations (logos, images, codes GTM, textes légaux) au niveau du Compte, génère des briefs textuels pour les développeurs, et route les leads vers les CRM destination (ZR7 Digital ou Maison du Lead).

## Architecture Technique

### Stack
- **Frontend**: React 18 avec Tailwind CSS, React Router
- **Backend**: FastAPI (Python)
- **Base de données**: MongoDB
- **Authentification**: JWT

### Flux des Leads avec Routage Intelligent
```
[Formulaire Web]
     ↓ (Lead soumis via /api/submit-lead avec form_code)
[CE CRM] → Stocke le lead
     ↓ (Routage intelligent OPTIONNEL)
[Vérification des commandes]
  → Si commandes configurées:
    → CRM origine a commande pour ce département/produit? → Envoi vers origine
    → Sinon, autre CRM a commande? → Reroutage vers autre CRM
    → Aucun CRM n'a commande? → Fallback vers origine
  → Si pas de commandes: → Envoi direct vers CRM origine
     ↓
[ZR7 ou MDL] → Via leur API avec crm_api_key
     ↓
[Facturation Inter-CRM] → Si reroutage, montants calculés selon prix configurés
```

## APIs CRM Destination
- **ZR7 Digital**: `POST https://app.zr7-digital.fr/lead/api/create_lead/`
- **Maison du Lead**: `POST https://app.maisonsdulead.fr/lead/api/create_lead/`
- **Format**: JSON avec Header `Authorization: <token>`

## API Ce CRM - Envoi des Leads

### Endpoint
```
POST /api/submit-lead
Content-Type: application/json
```

### Body (JSON)
```json
{
  "form_code": "VOTRE-CODE-FORM",
  "phone": "0612345678",
  "nom": "Dupont",
  "prenom": "Jean",
  "civilite": "M.",
  "email": "email@example.com",
  "departement": "75",
  "code_postal": "75001",
  "superficie_logement": "120",
  "chauffage_actuel": "Gaz",
  "type_logement": "Maison",
  "statut_occupant": "Propriétaire",
  "facture_electricite": "150"
}
```

## Fonctionnalités Implémentées

### Phase 9 - Facturation Inter-CRM (Complété - 08/02/2026)
- [x] **Dashboard de facturation** (`/billing`) : Statistiques par CRM, leads routés, montants à facturer
- [x] **Configuration des prix par lead** : Prix PAC/PV/ITE en euros par CRM
- [x] **Filtres par type de produit** : Boutons Tous/PV/PAC/ITE sur page Formulaires
- [x] **Archivage automatique** : Endpoint `/api/leads/archive?months=3` + bouton dans UI
- [x] **Routage intelligent** : Reroutage basé sur commandes (départements/produits) par CRM

### Phase 8 - Finalisation (Complété)
- [x] Clé API interne visible avec bouton copier
- [x] Brief Generator avec Notice API auto-incluse
- [x] Suppression réservée aux Admins
- [x] Leads réservés aux Admins
- [x] Guide d'utilisation complet
- [x] Tous les champs ZR7/MDL supportés

## Nouveaux Endpoints (Phase 9)

### Facturation
```
GET /api/billing/dashboard?date_from=X&date_to=Y
```
Retourne:
- `crm_stats[]` : Par CRM → leads_originated, leads_received, leads_rerouted_out/in, amount_to_invoice/pay, net_balance
- `transfers[]` : Détail des transferts inter-CRM avec montants

### Archivage
```
POST /api/leads/archive?months=3  (Admin only)
GET /api/leads/archived?limit=100&date_from=X&date_to=Y  (Admin only)
```

### Configuration CRM avec Prix
```
PUT /api/crms/{crm_id}
Body: { "commandes": {...}, "lead_prices": {"PAC": 25, "PV": 20, "ITE": 30} }
```

## Rôles Utilisateurs

| Rôle | Accès | Peut supprimer | Accès Leads | Accès Facturation |
|------|-------|----------------|-------------|-------------------|
| Admin | Complet | ✅ | ✅ | ✅ |
| Éditeur | Créer/Modifier | ❌ | ❌ | ❌ |
| Lecteur | Consultation | ❌ | ❌ | ❌ |

## Credentials de Test
- **Email**: energiebleuciel@gmail.com
- **Password**: 92Ruemarxdormoy

## Backlog

### P0 - Sécurité
- [ ] **Backend filtrage par allowed_accounts** : Filtrer données selon permissions utilisateur

### P1 - Améliorations
- [ ] Générateur de LP HTML avec style officiel
- [ ] Générateur de Formulaires HTML avec GTM intégré
- [ ] Graphiques visuels sur dashboard de facturation

### P2 - Technique
- [ ] Refactoring Frontend (App.js > 4500 lignes)
- [ ] Refactoring Backend (server.py vers modules)

## Schéma DB Mis à Jour

### Collection `crms`
```json
{
  "id": "uuid",
  "name": "Maison du Lead",
  "slug": "mdl",
  "api_url": "https://...",
  "commandes": {"PAC": ["75", "92"], "PV": ["13"], "ITE": []},
  "lead_prices": {"PAC": 25.0, "PV": 20.0, "ITE": 30.0}
}
```

### Collection `leads` (champs ajoutés)
```json
{
  "origin_crm_id": "uuid",
  "target_crm_id": "uuid",
  "routing_reason": "direct_to_origin | rerouted_to_zr7 | no_order_fallback_origin",
  "product_type": "PAC | PV | ITE"
}
```

### Collection `leads_archived`
Même structure que `leads` + `archived_at`
