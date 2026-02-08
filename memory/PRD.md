# CRM Multi-tenant - Gestion de Leads Solaires

## Problème Original
Créer un CRM multi-tenant pour la gestion de leads solaires permettant de:
- Gérer des leads provenant de plusieurs sources (Landing Pages, formulaires)
- Envoyer les leads à différents CRM externes (Maison du Lead, ZR7 Digital)
- Organiser les données par CRMs (tenants) et sous-comptes (projets/sites web)

## Architecture Technique

### Stack
- **Frontend**: React 18 avec Tailwind CSS, React Router
- **Backend**: FastAPI (Python)
- **Base de données**: MongoDB
- **Authentification**: JWT

### Structure des Données
```
CRMs (tenants)
└── Sub-accounts (projects/websites)
    ├── Landing Pages (redirect ou intégré)
    │   └── CTA tracking
    ├── Forms (tracking redirect/GTM/aucun)
    │   └── Conversion tracking
    └── Leads
```

## Fonctionnalités Implémentées

### Phase 1 - Core (Complété)
- [x] Authentification JWT (login/logout)
- [x] Dashboard avec statistiques
- [x] Gestion des utilisateurs (admin, editor, viewer)
- [x] Sélecteur CRM global (Maison du Lead, ZR7 Digital)
- [x] Guide d'utilisation intégré

### Phase 2 - Filtrage CRM & Sous-comptes (Complété - 08/02/2026)
- [x] Filtrage strict par CRM sur toutes les pages
- [x] Formulaire Sous-comptes avec: logos gauche/droit, textes légaux popup, type de produit

### Phase 3 - Fonctionnalités Avancées (Complété - 08/02/2026)
- [x] **Bibliothèque d'Assets**:
  - Stocker URLs d'images/logos avec labels personnalisés
  - Filtres: Tous / Globaux / Par sous-compte
  - CRUD complet avec preview

- [x] **Gestion des Leads**:
  - Suppression de leads (simple et multiple)
  - Checkboxes de sélection avec "Tout sélectionner"
  - Validation: téléphone 10 chiffres, nom obligatoire (min 2 chars)
  - Code postal France métropolitaine uniquement (01-95)

- [x] **Types de LP**:
  - **Redirect**: LP redirige vers formulaire externe (URL à saisir)
  - **Intégré**: Formulaire directement dans la LP
  - Duplication de LP (nouveau code/nom)
  - Commentaires pour génération scripts

- [x] **Tracking Formulaire**:
  - **Redirect**: Page de merci (pas besoin de GTM)
  - **GTM / Code JS**: Event tracking
  - **Aucun**: Pas de tracking
  - Duplication de formulaire (seule la clé API change)
  - Commentaires pour génération

### Pages Disponibles
1. **Tableau de bord** - Stats et derniers leads
2. **Analytics** - Taux de conversion, winners/losers
3. **Leads** - Liste avec filtres, suppression, export CSV
4. **Landing Pages** - CRUD, types redirect/intégré, duplication
5. **Formulaires** - CRUD, tracking redirect/GTM, duplication
6. **Sous-comptes** - Configuration par site/projet, templates
7. **Bibliothèque Assets** - URLs images/logos avec labels
8. **Générateur Scripts** - Code tracking pour LPs et Forms
9. **Guide d'utilisation** - Documentation intégrée
10. **Utilisateurs** - Gestion admin
11. **Journal activité** - Logs admin
12. **Paramètres** - Configuration CRMs

## Credentials de Test
- **Email**: energiebleuciel@gmail.com
- **Password**: 92Ruemarxdormoy

## API Endpoints Principaux
- `POST /api/auth/login` - Connexion
- `GET /api/crms` - Liste des CRMs
- `GET /api/sub-accounts?crm_id=xxx` - Sous-comptes
- `GET/POST /api/assets` - Bibliothèque d'assets
- `GET /api/lps?crm_id=xxx` - Landing Pages
- `POST /api/lps/{id}/duplicate` - Dupliquer LP
- `GET /api/forms?crm_id=xxx` - Formulaires
- `POST /api/forms/{id}/duplicate` - Dupliquer Form (nouvelle clé API)
- `GET /api/leads?crm_id=xxx` - Leads
- `DELETE /api/leads/{id}` - Supprimer lead
- `DELETE /api/leads` - Supprimer plusieurs leads
- `POST /api/submit-lead` - Soumission lead (validation: phone 10, nom required, CP France metro)
- `GET /api/analytics/stats?crm_id=xxx` - Statistiques

## Backlog (P1/P2/P3)

### P1 - Prochaines étapes
- [ ] Générateur de LP et Formulaires (système génère le code HTML/CSS/JS)
- [ ] Templates de formulaire par sous-compte (champs à afficher par défaut)
- [ ] Sélection d'assets depuis la bibliothèque lors de création LP/Form

### P2 - Améliorations
- [ ] Refactoring Frontend: découper App.js (2500+ lignes) en composants
- [ ] Upload d'images pour logos (au lieu d'URLs)
- [ ] Preview/screenshots de LPs et Forms

### P3 - Futur
- [ ] Redéploiement sur Hostinger VPS (remplacer prototype)
- [ ] Docker Compose pour déploiement simplifié
- [ ] Notifications email pour leads échoués
- [ ] API webhooks pour intégrations externes

## Notes Techniques
- Le frontend est un fichier monolithique (`App.js` ~2500 lignes) - refactoring recommandé
- Version déployée sur VPS Hostinger: prototype basique
- Version locale: CRM complet avec toutes les fonctionnalités

## Tests
- `/app/test_reports/iteration_1.json` - Tests filtrage CRM (26/26 PASS)
- `/app/test_reports/iteration_2.json` - Tests nouvelles fonctionnalités (32/32 PASS)
- `/app/backend/tests/test_new_features.py` - Tests unitaires backend

## Intégrations Externes
- **Maison du Lead API**: https://maison-du-lead.com/lead/api/create_lead/
- **ZR7 Digital API**: https://app.zr7-digital.fr/lead/api/create_lead/
