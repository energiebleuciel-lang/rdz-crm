# CRM Multi-tenant - Gestion de Leads Solaires

## Problème Original
Créer un CRM multi-tenant pour la gestion de leads solaires. Le système centralise toutes les informations (logos, images, codes GTM, textes légaux) au niveau du Compte, génère des briefs textuels pour les développeurs, et route les leads vers les CRM destination (ZR7 Digital ou Maison du Lead).

## Architecture Technique

### Stack
- **Frontend**: React 18 avec Tailwind CSS, React Router
- **Backend**: FastAPI (Python)
- **Base de données**: MongoDB
- **Authentification**: JWT

### Flux des Leads
```
[Formulaire Web]
     ↓ (Lead soumis via /api/submit-lead avec form_code)
[CE CRM] → Stocke le lead (tous les champs)
     ↓ (Si téléphone présent + crm_api_key configurée → envoi instantané)
[ZR7 ou MDL] → Via leur API avec crm_api_key
     ↓ (Tous les jours à 03h00)
[Job nocturne] → Réessaie les leads échoués des dernières 24h
```

### Structure des Données
```
CRM (MDL ou ZR7)
  └── Compte (Client, Site, Domaine)
        ├── Logos (principal, secondaire, petit, favicon)
        ├── Bibliothèque d'images (bannières, produits)
        ├── Codes GTM (pixel, conversion, CTA)
        ├── URLs de redirection nommées
        ├── Textes légaux
        ├── Landing Pages (avec code HTML)
        └── Formulaires
              ├── internal_api_key (auto-générée, pour recevoir les leads)
              └── crm_api_key (fournie par l'utilisateur, pour envoyer vers ZR7/MDL)
```

## APIs CRM Destination
- **ZR7 Digital**: `POST https://app.zr7-digital.fr/lead/api/create_lead/`
- **Maison du Lead**: `POST https://app.maisonsdulead.fr/lead/api/create_lead/`
- **Format**: JSON avec Header `Authorization: <token>`
- **Champs**: phone, register_date, nom, prenom, email, custom_fields (superficie_logement, chauffage_actuel, departement, code_postal, type_logement, statut_occupant, facture_electricite)

## Fonctionnalités Implémentées

### Phase 1-7 (Complétées - voir historique)

### Phase 8 - Finalisation (Complété - 08/02/2026)
- [x] **Clé API interne visible dans la liste** : Colonne "Clé API (pour vos scripts)" avec bouton copier
- [x] **Suppression réservée aux Admins** : Leads, formulaires, LP, comptes - seuls les admins peuvent supprimer
- [x] **Pas de validation stricte du téléphone** : Le téléphone est requis mais pas de validation du format
- [x] **Tous les champs ZR7/MDL** : prenom, civilite, superficie_logement, chauffage_actuel ajoutés
- [x] **Génération clés manquantes** : Endpoint `/api/forms/generate-missing-keys` pour les formulaires existants
- [x] **Régénération clé** : Endpoint `/api/forms/{id}/regenerate-key` pour régénérer une clé
- [x] **Guide d'utilisation réécrit** : Reflète le fonctionnement réel du CRM avec sections claires
- [x] **Brief Generator amélioré** : Inclut internal_api_key et crm_api_key + images du compte

## API Endpoints Principaux

### Leads
- `POST /api/submit-lead` - Soumet un lead (téléphone requis, envoi instantané si config OK)
- `POST /api/leads/retry/{lead_id}` - Réessayer un lead spécifique
- `POST /api/leads/retry-failed?hours=24` - Job nocturne retry des leads échoués
- `DELETE /api/leads/{id}` - Supprimer un lead (ADMIN ONLY)
- `POST /api/leads/bulk-delete` - Supprimer plusieurs leads (ADMIN ONLY)

### Formulaires
- `POST /api/forms` - Créer (génère `internal_api_key` automatiquement)
- `PUT /api/forms/{id}` - Modifier
- `DELETE /api/forms/{id}` - Supprimer (ADMIN ONLY)
- `POST /api/forms/{id}/duplicate` - Dupliquer avec nouvelle clé
- `POST /api/forms/generate-missing-keys` - Générer les clés manquantes (ADMIN ONLY)
- `POST /api/forms/{id}/regenerate-key` - Régénérer la clé

### Brief Generator
- `POST /api/generate-brief/lp` - Générer brief LP (avec images du compte)
- `POST /api/generate-brief/form` - Générer brief formulaire (avec internal_api_key + crm_api_key)

## Credentials de Test
- **Email**: energiebleuciel@gmail.com
- **Password**: 92Ruemarxdormoy

## Backlog

### P0 - Sécurité (PRIORITAIRE)
- [ ] **Backend filtrage par allowed_accounts** : Les endpoints ne filtrent pas encore les données selon les permissions utilisateur

### P1 - Améliorations
- [ ] Générateur de LP HTML avec style officiel
- [ ] Générateur de Formulaires HTML avec GTM intégré

### P2 - Technique
- [ ] Refactoring Frontend (App.js > 4000 lignes)
- [ ] Refactoring Backend (server.py vers modules)
- [ ] Graphiques visuels dans Dashboard Comparatif

## Rôles Utilisateurs
- **Admin** : Accès complet + peut supprimer (leads, formulaires, LP, comptes)
- **Éditeur** : Créer et modifier. Pas de suppression
- **Lecteur** : Consultation uniquement
