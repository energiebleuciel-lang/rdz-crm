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
[Routage intelligent] → Si commandes configurées + formulaire non exclu + limite non atteinte
     → CRM origine a commande ? → Envoi vers origine
     → Sinon, autre CRM a commande + limite OK ? → Reroutage
     → Aucun ou limite atteinte ? → Fallback vers origine
     ↓
[ZR7 ou MDL] → Via API externe
     ↓
[Facturation] → Si reroutage, montants calculés
```

## Fonctionnalités Implémentées

### Phase 10 - Finalisation (08/02/2026)
- [x] **Sélection produit visible** : Gros boutons jaunes PAC/PV/ITE dans le formulaire
- [x] **Limites inter-CRM** : Nombre max de leads par produit par mois qu'un CRM peut recevoir
- [x] **Nettoyage CTA** : Suppression des stats CTA non utilisées
- [x] **Marquage facturation** : Bouton "Marquer ce mois comme facturé" avec historique
- [x] **Exclusion routage** : Checkbox par formulaire pour éviter reroutage
- [x] **Anti-doublon amélioré** : Même téléphone + même produit/jour
- [x] **Guide refait** : 7 sections claires

### Phases Précédentes
- [x] Dashboard facturation avec stats par CRM
- [x] Configuration prix par lead (PAC/PV/ITE en €)
- [x] Archivage automatique (> 3 mois)
- [x] Gestion Comptes, LPs, Formulaires
- [x] Générateur de Briefs
- [x] Routage intelligent basé sur commandes (départements 01-95)
- [x] Rôles Admin/Éditeur/Lecteur
- [x] Job nocturne retry leads échoués

## Configuration CRM (Paramètres)

### Commandes
- Départements par produit (PAC, PV, ITE) où ce CRM accepte des leads
- Si un département n'est pas dans les commandes, le lead peut être rerouté

### Prix par lead
- Prix en € par produit pour calculer la facturation inter-CRM

### Limites de routage
- Nombre max de leads inter-CRM par produit par mois (0 = illimité)
- Si limite atteinte, pas de reroutage vers ce CRM

## Règles Métier Clés

### Anti-Doublon
- **Doublon** = même téléphone + même produit (PAC, PV ou ITE) par jour
- Un client peut s'inscrire PAC et PV le même jour = 2 leads valides

### Exclusion Routage Inter-CRM
- Formulaires de redirection marqués "Exclure du routage"
- Évite de livrer 2x le même client cross-CRM

### Limites de Routage
- Ex: ZR7 peut recevoir max 100 PAC/mois des autres CRMs
- Si limite atteinte, les leads restent sur leur CRM d'origine

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
```

### CRM Configuration
```
PUT /api/crms/{id}
Body: {
  "commandes": {"PAC": ["75", "92"], "PV": ["13"], "ITE": []},
  "lead_prices": {"PAC": 25.0, "PV": 20.0, "ITE": 30.0},
  "routing_limits": {"PAC": 100, "PV": 200, "ITE": 50}
}
```

## Schéma DB

### crms
```json
{
  "name": "Maison du Lead",
  "slug": "mdl",
  "commandes": {"PAC": ["75", "92"], "PV": [], "ITE": []},
  "lead_prices": {"PAC": 28.0, "PV": 22.0, "ITE": 35.0},
  "routing_limits": {"PAC": 100, "PV": 200, "ITE": 0}
}
```

### forms
```json
{
  "code": "PV-TAB-001",
  "product_type": "panneaux",
  "exclude_from_routing": false
}
```

## Credentials Test
- **Email**: energiebleuciel@gmail.com
- **Password**: 92Ruemarxdormoy

## Backlog

### P0 - Sécurité
- [ ] Backend filtrage par allowed_accounts

### P1 - Améliorations
- [ ] Graphiques visuels dashboard facturation
- [ ] Export CSV des leads/facturations

### P2 - Technique
- [ ] Refactoring App.js (5000+ lignes)
- [ ] Refactoring server.py en modules

## Déploiement
- **Prévu**: Hostinger (après validation utilisateur)
