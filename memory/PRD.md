# CRM Multi-tenant - Gestion de Leads Solaires

## Problème Original
Créer un CRM multi-tenant pour la gestion de leads solaires permettant de générer automatiquement des LP et formulaires HTML avec tracking intégré.

## Architecture Technique

### Stack
- **Frontend**: React 18 avec Tailwind CSS, React Router
- **Backend**: FastAPI (Python)
- **Base de données**: MongoDB
- **Authentification**: JWT

### Structure des Données
```
CRM (MDL ou ZR7)
  └── Compte (plusieurs par CRM)
        ├── Types de produits (plusieurs par compte)
        │     ├── Panneaux solaires (10 000€ aides)
        │     ├── Pompe à chaleur (10 000€ aides)
        │     └── Isolation extérieure (13 000€ aides)
        ├── Landing Pages (redirect ou intégré) - HTML généré
        └── Formulaires - HTML généré
              └── Taux conversion (démarrés → finis)
```

## Comptes Configurés
- **MDL (Maison du Lead)**: MDL, SPOOT, OBJECTIF ACADEMIE, AUDIT GREEN
- **ZR7 (ZR7 Digital)**: ZR7, AZ

## APIs CRM Externes
- **Maison du Lead**: `https://maison-du-lead.com/lead/api/create_lead/`
- **ZR7 Digital**: `https://app.zr7-digital.fr/lead/api/create_lead/`

## Sources de Diffusion Configurées
- **Native**: Taboola, Outbrain, MGID, Mediago, Yahoo Gemini
- **Google**: Google Ads, YouTube Ads
- **Facebook/Meta**: Facebook Ads, Instagram Ads
- **TikTok**: TikTok Ads

## Fonctionnalités Implémentées

### Phase 1 - Core (Complété)
- [x] Authentification JWT (login/logout)
- [x] Dashboard avec statistiques
- [x] Gestion des utilisateurs (admin, editor, viewer)
- [x] Sélecteur CRM global (Maison du Lead, ZR7 Digital)

### Phase 2 - Filtrage & Assets (Complété)
- [x] Filtrage strict par CRM sur toutes les pages
- [x] Bibliothèque d'Assets (stocker URLs images avec labels)
- [x] Suppression de leads (simple et multiple)

### Phase 3 - LP & Forms Avancés (Complété)
- [x] Types de LP: redirect (vers form externe) ou intégré
- [x] Tracking formulaire: redirect (pas besoin GTM) / GTM / aucun
- [x] Duplication LP et Forms (seule clé API change pour forms)
- [x] Validation leads: téléphone 10 chiffres, nom obligatoire, CP France métro

### Phase 4 - Dashboard Comparatif & Config (Complété)
- [x] Dashboard Comparatif Global (`/compare`)
- [x] Gestion Sources de Diffusion (`/diffusion`)
- [x] Gestion Types de Produits (`/products`)

### Phase 5 - Refactoring Structural (Complété - 08/02/2026)
- [x] Renommage "sous-compte" → "compte" dans toute l'application
- [x] Migration collection DB `sub_accounts` → `accounts`
- [x] Correction bug suppression leads (nouveau endpoint POST /api/leads/bulk-delete)
- [x] Création des 6 comptes par défaut (MDL, ZR7, SPOOT, AZ, OBJECTIF ACADEMIE, AUDIT GREEN)
- [x] Routes API rétrocompatibles (/api/sub-accounts fonctionne toujours)

### Pages Disponibles
1. **Tableau de bord** - Stats et derniers leads
2. **Dashboard Comparatif** - Compare par source/CRM en temps réel
3. **Analytics** - Taux de conversion, winners/losers
4. **Leads** - Liste avec suppression, export CSV
5. **Landing Pages** - CRUD, types redirect/intégré, duplication
6. **Formulaires** - CRUD, tracking redirect/GTM, duplication
7. **Comptes** - Configuration par site/projet avec GTM et logos
8. **Bibliothèque Assets** - URLs images/logos avec labels
9. **Générateur Scripts** - Code tracking pour LPs et Forms
10. **Guide d'utilisation** - Documentation intégrée
11. **Utilisateurs** - Gestion admin
12. **Journal activité** - Logs admin
13. **Sources Diffusion** - Gestion des plateformes
14. **Types Produits** - Configuration produits et aides
15. **Paramètres** - Configuration CRMs

## Credentials de Test
- **Email**: energiebleuciel@gmail.com
- **Password**: 92Ruemarxdormoy

## API Endpoints Principaux
- `GET /api/accounts` - Liste des comptes (remplace /api/sub-accounts)
- `POST /api/accounts` - Créer un compte
- `PUT /api/accounts/{id}` - Modifier un compte
- `DELETE /api/accounts/{id}` - Supprimer un compte
- `DELETE /api/leads/{id}` - Supprimer un lead
- `POST /api/leads/bulk-delete` - Supprimer plusieurs leads (body: {lead_ids: [...]})
- `GET /api/analytics/compare` - Dashboard comparatif avec filtres
- `POST /api/lps/{id}/duplicate` - Dupliquer LP
- `POST /api/forms/{id}/duplicate` - Dupliquer Form

## Backlog (P1/P2)

### P0 - Prochaines étapes PRIORITAIRES
- [ ] **Générateur de LP HTML** - Style officiel, code couleur, 1 ou 2 logos
- [ ] **Générateur de Formulaires HTML** - Avec tracking GTM intégré
- [ ] **Mise à jour Guide d'utilisation** - Obsolète après refactoring

### P1 - Améliorations
- [ ] Options de personnalisation LP/Forms - Badges confiance, certifications
- [ ] Sélection d'assets depuis la bibliothèque lors de création
- [ ] Analytics formulaire démarré vs. complété

### P2 - Technique
- [ ] Refactoring Frontend (App.js > 3500 lignes)
- [ ] Refactoring Backend (server.py vers modules)
- [ ] Redéploiement sur Hostinger VPS
- [ ] Graphiques visuels dans Dashboard Comparatif

## Tests Effectués
- `/app/test_reports/iteration_1.json` - Tests filtrage CRM (26/26 PASS)
- `/app/test_reports/iteration_2.json` - Tests nouvelles fonctionnalités (32/32 PASS)
- `/app/test_reports/iteration_3.json` - Tests refactoring compte/leads (14/14 PASS, 100%)

## Intégrations Externes
- **Maison du Lead API**: POST avec Authorization header (token), JSON body
- **ZR7 Digital API**: POST avec Authorization header (token), JSON body
