# EnerSolar CRM - Gestion de Leads Solaires

## Problème Original
CRM multi-tenant pour centraliser et redistribuer les leads solaires (PAC, PV, ITE) vers ZR7 Digital et Maison du Lead, avec routage intelligent et facturation inter-CRM.

## Architecture Technique

### Stack
- **Frontend**: React 18 + Tailwind CSS + React Router
- **Backend**: FastAPI (Python)
- **Base de données**: MongoDB
- **Authentification**: JWT

### Flux des Leads
```
[Formulaire Web] → POST /api/submit-lead
     ↓
[Anti-doublon] → Même téléphone + même produit/jour ?
     ↓ (non)
[Routage intelligent] → Si commandes configurées + formulaire non exclu
     → CRM origine a commande ? → Envoi vers origine
     → Sinon, autre CRM a commande ? → Reroutage
     → Aucun ? → Fallback vers origine
     ↓
[ZR7 ou MDL] → Via API externe
     ↓
[Facturation] → Si reroutage, montants calculés
```

## Fonctionnalités Implémentées

### Phase 10 - Finalisation (08/02/2026)
- [x] **Marquage facturation** : Bouton "Marquer ce mois comme facturé" avec historique
- [x] **Exclusion routage** : Checkbox par formulaire pour éviter reroutage (doublons cross-CRM)
- [x] **Anti-doublon amélioré** : Même téléphone + même produit/jour (PAC, PV, ITE indépendants)
- [x] **Guide refait** : 7 sections (Intro, Démarrage, Formulaires, Routage, Facturation, API, FAQ)
- [x] **Filtres produit** : Boutons Tous/PV/PAC/ITE sur page Formulaires

### Phase 9 - Facturation Inter-CRM
- [x] Dashboard facturation avec stats par CRM
- [x] Configuration prix par lead (PAC/PV/ITE en €)
- [x] Archivage automatique (> 3 mois)

### Phases Précédentes
- [x] Gestion Comptes, LPs, Formulaires
- [x] Générateur de Briefs avec validations automatiques
- [x] Routage intelligent basé sur commandes (départements 01-95)
- [x] Rôles Admin/Éditeur/Lecteur
- [x] Job nocturne retry leads échoués

## Règles Métier Clés

### Anti-Doublon
- **Doublon** = même téléphone + même produit (PAC, PV ou ITE) par jour
- Un client peut s'inscrire PAC et PV le même jour = 2 leads valides

### Exclusion Routage Inter-CRM
- Formulaires de redirection marqués "Exclure du routage"
- Évite de livrer 2x le même client (ex: PAC sur MDL + PV via redirect sur ZR7)

### Routage Intelligent (Optionnel)
- S'active uniquement si commandes configurées
- Formulaire non exclu + département présent
- Fallback vers CRM d'origine si aucune commande trouvée

## Endpoints Principaux

### Leads
```
POST /api/submit-lead          # Soumettre un lead
GET /api/leads                 # Liste des leads (admin)
POST /api/leads/archive        # Archiver > 3 mois
```

### Facturation
```
GET /api/billing/dashboard     # Stats par CRM et période
POST /api/billing/mark-invoiced # Marquer période facturée
GET /api/billing/history       # Historique facturations
DELETE /api/billing/history/{id} # Supprimer enregistrement
```

### Formulaires
```
GET /api/forms?product_type=panneaux # Avec filtre produit
POST /api/forms               # Créer (avec exclude_from_routing)
PUT /api/forms/{id}           # Modifier
```

## Schéma DB

### forms
```json
{
  "code": "PV-TAB-001",
  "product_type": "panneaux",
  "crm_api_key": "uuid",
  "internal_api_key": "uuid",
  "exclude_from_routing": false
}
```

### leads
```json
{
  "phone": "0612345678",
  "product_type": "PV",
  "origin_crm_id": "uuid",
  "target_crm_id": "uuid",
  "routing_reason": "direct_to_origin | rerouted_to_zr7"
}
```

### billing_history
```json
{
  "year": 2026,
  "month": 2,
  "from_crm_id": "uuid",
  "to_crm_id": "uuid",
  "amount": 500.00,
  "lead_count": 20,
  "notes": "Facture #123"
}
```

## Credentials Test
- **Email**: energiebleuciel@gmail.com
- **Password**: 92Ruemarxdormoy

## Backlog

### P0 - Sécurité
- [ ] Backend filtrage par allowed_accounts (faille sécurité)

### P1 - Améliorations
- [ ] Graphiques visuels dashboard facturation
- [ ] Export CSV des leads/facturations

### P2 - Technique
- [ ] Refactoring App.js (4800+ lignes)
- [ ] Refactoring server.py en modules

## Déploiement
- **Prévu**: Hostinger (après validation utilisateur)
