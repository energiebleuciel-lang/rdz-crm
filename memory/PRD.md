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
- `GET /api/accounts/{id}/brief-options` - Options disponibles pour mini brief
- `POST /api/accounts/{id}/mini-brief` - Générer mini brief sélectif
- `GET /api/leads/stats/global?crm_id=...` - Stats leads filtrées par CRM
- `GET /api/queue/stats?crm_id=...` - Stats queue filtrées par CRM

### ✅ Tracking Events
- `lp_visit` - Visite de la LP (automatique)
- `cta_click` - Clic sur bouton CTA
- `form_start` - Premier bouton du formulaire cliqué
- `form_submit` - Lead soumis

### ✅ Configuration
- Page Settings : Clé API RDZ visible, non modifiable
- Page Formulaires : target_crm + crm_api_key par formulaire
- Brief LP/Form : Scripts de tracking séparés (LP + Form)

### ✅ Mini Brief Sélectif (Décembre 2025)
Fonctionnalité sur la page Comptes permettant de générer un brief personnalisé avec sélection des éléments :
- **Logos** : Logo Principal, Logo Secondaire
- **GTM & Tracking** : Code GTM (Head), Code GTM (Body), Code de Tracking Conversion
- **Textes Légaux** : Texte Mentions Légales, Texte Politique de Confidentialité, Texte CGU
- **Autres** : URL de Redirection
- Boutons "Copier" individuels + "Copier tout"
- Éléments non configurés affichés en grisé avec badge "Non configuré"
- Bouton d'accès rapide dans le modal Brief LP

### ✅ Dashboard filtré par CRM (Décembre 2025)
- Le Tableau de bord affiche maintenant les stats filtrées par CRM sélectionné
- Indication du CRM actif sous le titre
- Stats leads et queue filtrées automatiquement

### ✅ Page Leads améliorée (Décembre 2025)
- **CRM d'origine** : Chaque lead affiche maintenant son CRM d'origine (basé sur le compte)
- **Badge Transféré** : Si un lead est transféré inter-CRM, un badge "→ ZR7" ou "→ MDL" s'affiche
- **Nouveaux filtres** :
  - Filtre "Transférés" : Tous / Transférés uniquement / Non transférés
  - Filtre "Période" : Date de début et date de fin
- **Colonne "Distribution"** séparée de "CRM Origine"
- **Modal de détail enrichi** : Section "CRM & Distribution" avec toutes les infos

### ✅ Audit Technique Complet (Décembre 2025)
Audit exhaustif du système avant déploiement :

**Corrections effectuées :**
- Ligne dupliquée dans `public.py` supprimée
- Champs lead harmonisés entre toutes les APIs
- Champs obsolètes (`target_crm_id`, `target_crm_slug`) supprimés
- 26+ leads existants normalisés en base
- Export CSV mis à jour avec nouveaux champs
- Billing.py adapté au nouveau schéma
- Corrections lint dans auth.py, lps.py, billing.py, lead_sender.py

**Schéma Lead Normalisé :**
```
origin_crm      : slug CRM d'origine (compte)
target_crm      : slug CRM de destination
is_transferred  : boolean (transfert inter-CRM)
routing_reason  : raison du routing
allow_cross_crm : boolean
api_status      : pending|success|failed|duplicate|no_crm
sent_to_crm     : boolean
```

**Tests passés :**
- ✅ Lint Python backend (routes, services)
- ✅ Lint JavaScript frontend (pages)
- ✅ Import tous les modules
- ✅ Démarrage serveur FastAPI (102 routes)
- ✅ Test E2E complet (Session → Tracking → Lead → Routage → Validation)

## À Faire

### 🔶 Priorité Haute
- Tests end-to-end complets du flux LP → Form → Lead
- Déploiement sur VPS Hostinger (`/var/www/crm-leads/`)

### 🔷 Priorité Moyenne
- Sous-comptes
- Configuration détaillée des Types de Produits

### ⬜ Backlog
- Alertes email (SendGrid - en pause)
- Bibliothèque d'images
- A/B Testing ("Mode Campagne")

## Credentials Test
- **UI Login** : `energiebleuciel@gmail.com` / `92Ruemarxdormoy`

## URLs CRM
- **ZR7** : `https://app.zr7-digital.fr/lead/api/create_lead/`
- **MDL** : `https://maison-du-lead.com/lead/api/create_lead/`

## Dernière Mise à Jour
Décembre 2025 - Dashboard filtré par CRM + Bouton Mini Brief dans Brief LP
