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
  └── Sous-compte (plusieurs par CRM)
        ├── Types de produits (plusieurs par sous-compte)
        │     ├── Panneaux solaires (10 000€ aides)
        │     ├── Pompe à chaleur (10 000€ aides)
        │     └── Isolation extérieure (13 000€ aides)
        ├── Landing Pages (redirect ou intégré) - HTML généré
        └── Formulaires - HTML généré
              └── Taux conversion (démarrés → finis)
```

## Sous-comptes Configurés
- **MDL**: MDL, BRANDSPOT, OBJECTIF ACADEMIE, AUDIT GREEN
- **ZR7**: ZR7, AZ

## Sources de Diffusion Configurées
- **Native**: Taboola, Outbrain, MGID, Mediago, Yahoo Gemini
- **Google**: Google Ads, YouTube Ads
- **Facebook/Meta**: Facebook Ads, Instagram Ads
- **TikTok**: TikTok Ads
- Possibilité d'en ajouter au fur et à mesure

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

### Phase 4 - Dashboard Comparatif & Config (Complété - 08/02/2026)
- [x] **Dashboard Comparatif Global** (`/compare`)
  - Filtres: CRM / Type de diffusion / Période
  - Métriques: Clics CTA, Forms démarrés, Leads, Taux conversion
  - Comparaison par source de diffusion (Native/Google/Facebook/TikTok)
  - Comparaison par CRM (MDL vs ZR7)

- [x] **Gestion Sources de Diffusion** (`/diffusion`)
  - CRUD des plateformes de diffusion
  - Catégorisation (Native, Google, Facebook, TikTok, Autre)
  - Ajout de nouvelles sources à la demande

- [x] **Gestion Types de Produits** (`/products`)
  - Configuration des produits avec montants d'aides
  - Liste des aides disponibles (MaPrimeRenov, CEE, TVA réduite, Autoconsommation)
  - Instructions automatiques pour génération de scripts

### Pages Disponibles
1. **Tableau de bord** - Stats et derniers leads
2. **Dashboard Comparatif** - Compare par source/CRM en temps réel
3. **Analytics** - Taux de conversion, winners/losers
4. **Leads** - Liste avec suppression, export CSV
5. **Landing Pages** - CRUD, types redirect/intégré, duplication
6. **Formulaires** - CRUD, tracking redirect/GTM, duplication
7. **Sous-comptes** - Configuration par site/projet
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
- `GET /api/analytics/compare` - Dashboard comparatif avec filtres
- `GET/POST /api/diffusion-sources` - Gestion sources diffusion
- `GET/POST/PUT/DELETE /api/product-types` - Gestion types produits
- `POST /api/lps/{id}/duplicate` - Dupliquer LP
- `POST /api/forms/{id}/duplicate` - Dupliquer Form (nouvelle clé API)
- `DELETE /api/leads/{id}` - Supprimer lead
- `POST /api/submit-lead` - Soumission lead (validation: phone 10, nom, CP France)

## Instructions par Produit (pour génération)
- **Panneaux solaires**: 10 000€ d'aides, MaPrimeRenov, CEE, Autoconsommation, TVA réduite
- **Pompe à chaleur**: 10 000€ d'aides, MaPrimeRenov, CEE, TVA réduite
- **Isolation Extérieure**: 13 000€ d'aides, MaPrimeRenov, CEE, TVA réduite

## Backlog (P1/P2)

### P1 - Prochaines étapes
- [ ] **Générateur de LP HTML** - Style officiel, code couleur, 1 ou 2 logos
- [ ] **Générateur de Formulaires HTML** - Avec tracking GTM intégré
- [ ] **Options de personnalisation** - Badges confiance, certifications
- [ ] Sélection d'assets depuis la bibliothèque lors de création

### P2 - Améliorations
- [ ] Refactoring Frontend (App.js > 3500 lignes)
- [ ] Redéploiement sur Hostinger VPS
- [ ] Graphiques visuels dans Dashboard Comparatif

## Tests Effectués
- `/app/test_reports/iteration_1.json` - Tests filtrage CRM (26/26 PASS)
- `/app/test_reports/iteration_2.json` - Tests nouvelles fonctionnalités (32/32 PASS)

## Intégrations Externes
- **Maison du Lead API**: https://maison-du-lead.com/lead/api/create_lead/
- **ZR7 Digital API**: https://app.zr7-digital.fr/lead/api/create_lead/
