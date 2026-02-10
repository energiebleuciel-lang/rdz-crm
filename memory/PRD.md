# RDZ CRM - Product Requirements Document

## Description
CRM multi-tenant pour la gestion et distribution de leads vers ZR7 Digital et Maison du Lead (MDL).

## Architecture

### Flux Principal
```
Visiteur → LP → Form → RDZ (collecte) → ZR7 ou MDL (distribution)
```

### Clés API
- **Clé API RDZ** : unique, non modifiable, pour récupérer les leads (`GET /api/leads/export`)
- **Clés API ZR7/MDL** : par formulaire, pour envoyer les leads

### Vérification Commandes
Avant d'envoyer un lead :
1. Vérifier si le CRM cible a une commande pour ce département + produit
2. Si non et `allow_cross_crm` = true, essayer l'autre CRM
3. Si aucun CRM disponible, stocker avec status "no_crm"

## Fonctionnalités Implémentées

### ✅ API
- `GET /api/leads/export` - Récupérer leads avec clé API RDZ
- `POST /api/public/track/session` - Créer session visiteur
- `POST /api/public/track/event` - Tracker événement
- `POST /api/public/leads` - Soumettre lead

### ✅ Tracking Events
- `lp_visit` - Visite de la LP (automatique)
- `cta_click` - Clic sur bouton CTA
- `form_start` - Premier bouton du formulaire cliqué
- `form_submit` - Lead soumis

### ✅ Configuration
- Page Settings : Clé API RDZ visible, non modifiable
- Page Formulaires : target_crm + crm_api_key par formulaire
- Brief : Script de tracking simplifié

## À Faire

### 🔶 Priorité Haute
- **Séparer tracking LP / Form** : Pour pas fausser les stats du funnel
  - Option 1 : 1 script avec paramètre `page` (lp ou form)
  - Option 2 : 2 scripts séparés

### 🔷 Priorité Moyenne
- Tests end-to-end complets
- Déploiement sur VPS Hostinger

### ⬜ Backlog
- Sous-comptes
- Alertes email
- A/B Testing

## Credentials Test
- **UI Login** : `energiebleuciel@gmail.com` / `92Ruemarxdormoy`

## URLs CRM
- **ZR7** : `https://app.zr7-digital.fr/lead/api/create_lead/`
- **MDL** : `https://maison-du-lead.com/lead/api/create_lead/`

## Dernière Mise à Jour
2026-02-10 - Refactoring complet du système de tracking et API
