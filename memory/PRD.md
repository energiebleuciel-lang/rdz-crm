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

### Phase 12 - Protection & Traçabilité (08/02/2026)
- [x] **Protection des formulaires** :
  - DELETE archive au lieu de supprimer (leads conservés)
  - Clé API CRM protégée (non modifiable après création)
  - Product_type protégé (non modifiable)
  - Suppression permanente uniquement avec code de confirmation
- [x] **Traçabilité complète des leads** :
  - `target_crm_name` / `target_crm_slug` : Plateforme cible
  - `status_detail` : "envoyé/zr7" ou "envoyé/mdl"
  - Colonnes Produit (PV/PAC/ITE) et Plateforme sur page Leads
- [x] **Tests API réels réussis** :
  - ZR7 Digital : ✅ Leads envoyés avec succès
  - Maison du Lead : ✅ Leads envoyés avec succès

### Phase 11 - Sécurité & Analytics (08/02/2026)
- [x] **Sécurité multi-tenant** : Filtrage des données par `allowed_accounts` pour utilisateurs non-admin
  - `/api/accounts` : filtre par comptes autorisés
  - `/api/forms` : filtre par comptes autorisés
  - `/api/leads` : filtre par formulaires des comptes autorisés
  - `/api/lps` : filtre par comptes autorisés
- [x] **Stats de transformation sur page Formulaires** :
  - Colonne "Démarrés" (form_starts)
  - Colonne "Complétés" (leads)
  - Colonne "% Transfo" (conversion_rate avec couleurs)
  - Colonne "Produit" (badges PV/PAC/ITE colorés)
- [x] **Champ civilite** ajouté à l'envoi API vers ZR7/MDL

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

## Sécurité Multi-Tenant

### Fonctions de filtrage (server.py)
```python
def get_account_filter(user: dict) -> dict:
    """Filtre MongoDB pour comptes autorisés"""
    if user.get("role") == "admin":
        return {}
    allowed = user.get("allowed_accounts", [])
    return {"id": {"$in": allowed}} if allowed else {}

def get_account_ids_filter(user: dict) -> dict:
    """Filtre pour entités liées à un account_id"""
    if user.get("role") == "admin":
        return {}
    allowed = user.get("allowed_accounts", [])
    return {"account_id": {"$in": allowed}} if allowed else {}
```

### Comment assigner un utilisateur à des comptes
1. Admin va dans "Utilisateurs"
2. Édite l'utilisateur
3. Définit `allowed_accounts` = liste des IDs de comptes autorisés
4. Si vide, l'utilisateur voit tout (comme avant)

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
GET /api/leads                 # Liste des leads (filtré par allowed_accounts)
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

### users
```json
{
  "email": "user@example.com",
  "role": "editor",
  "allowed_accounts": ["account-id-1", "account-id-2"]
}
```

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

### P0 - Complété ✅
- [x] Backend filtrage par allowed_accounts

### P1 - Améliorations
- [ ] Graphiques visuels dashboard facturation
- [ ] Export CSV des leads/facturations

### P2 - Technique
- [ ] Refactoring App.js (5000+ lignes)
- [ ] Refactoring server.py en modules

## Déploiement
- **Live**: https://rdz-group-ltd.online (Hostinger VPS)
- **Preview**: https://leadflow-106.preview.emergentagent.com
