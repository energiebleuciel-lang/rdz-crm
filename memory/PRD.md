# EnerSolar CRM - Gestion de Leads Solaires

## Problème Original
CRM multi-tenant pour centraliser et redistribuer les leads solaires (PAC, PV, ITE) vers ZR7 Digital et Maison du Lead.

## URL Production
- **API Backend**: https://rdz-group-ltd.online
- **Preview**: https://sun-leads-pro.preview.emergentagent.com

## Fonctionnalités Implémentées

### ✅ Facturation Inter-CRM avec Navigation par Semaine (09/02/2026)
- **Navigation par semaine**: Boutons < Semaine précédente | Semaine suivante >
- **Affichage dates**: Format "29/12/2025 → 04/01/2026"
- **Bouton "Marquer comme facturé"**: Toggle le statut de facturation par semaine
- **Calcul automatique**: Si ZR7 → MDL = MDL doit payer ZR7
- **APIs**:
  - `GET /api/billing/weeks/current` - Semaine actuelle
  - `GET /api/billing/weeks/{year}/{week}` - Données de facturation d'une semaine
  - `POST /api/billing/weeks/{year}/{week}/invoice` - Marquer comme facturé

### ✅ Prix par Lead dans Commandes (09/02/2026)
- Champ `prix_unitaire` éditable directement dans la liste des commandes
- Format: "Prix: [0] €"
- Mise à jour via API `PUT /api/commandes/{id}`

### ✅ CGU & Politique de Confidentialité dans Comptes (09/02/2026)
- Section dépliable "Textes Légaux (CGU, Confidentialité)"
- Champs:
  - `cgu_text`: Conditions Générales d'Utilisation
  - `privacy_policy_text`: Politique de Confidentialité
  - `legal_mentions_text`: Mentions Légales (optionnel)

### ✅ Logos et Boutons CGU/Privacy dans Brief (09/02/2026)
- `logos_html`: Code HTML avec logos (principal, secondaire, favicon)
- `legal_html`: Boutons cliquables CGU/Privacy qui ouvrent un popup
- Inclus pour les 2 modes: embedded ET redirect

### ✅ Filtrage Leads/Départements par CRM (09/02/2026)
- API `GET /api/leads?crm_id={uuid}` filtre côté backend
- API `GET /api/stats/departements?crm_id={uuid}` filtre côté backend
- Frontend utilise le CRM sélectionné automatiquement

### ✅ Vérification Nocturne (09/02/2026)
- Tâche planifiée APScheduler à 3h UTC tous les jours
- Vérifie tous les leads des 24 dernières heures
- Relance automatiquement les leads échoués (sauf doublons CRM)
- APIs: `/api/verification/run`, `/api/verification/status`

### ✅ Système de Commandes & Routage Cross-CRM
- Routage intelligent des leads basé sur les commandes actives
- Fallback cross-CRM si le CRM principal n'a pas de commande active

### ✅ Gestion des Utilisateurs & Permissions
- CRUD complet des utilisateurs
- Rôles: Admin, Editor, Viewer
- Permissions par section

### ✅ Dashboard Départements
- Statistiques par département, produit, source
- Filtres avancés par période et CRM

## Architecture Technique

### Backend (V2 - Modulaire)
```
/app/backend/
├── server.py              # Point d'entrée FastAPI + APScheduler
├── config.py              # Configuration, DB, helpers
├── models.py              # Modèles Pydantic
├── routes/
│   ├── auth.py            # Login, sessions, users
│   ├── accounts.py        # Comptes (avec CGU)
│   ├── crms.py, lps.py, forms.py, leads.py
│   ├── commandes.py       # Commandes avec prix_unitaire
│   ├── stats.py           # Stats avec filtre CRM
│   ├── billing.py         # Facturation par semaine
│   └── verification.py    # Vérification nocturne
└── services/
    ├── brief_generator.py # Génération scripts + logos + legal
    ├── billing.py         # Calcul facturation par semaine
    └── nightly_verification.py
```

### Frontend (V2 - Modulaire)
```
/app/frontend/src/
├── App.jsx
├── pages/
│   ├── Billing.jsx      # Navigation par semaine
│   ├── Commandes.jsx    # Prix par lead éditable
│   ├── Accounts.jsx     # Section CGU/Privacy
│   ├── Leads.jsx        # Filtré par CRM backend
│   └── Departements.jsx # Filtré par CRM backend
└── hooks/, components/
```

### Collections MongoDB
- `billing_weeks` - Statut facturé par semaine
- `verification_reports` - Rapports vérification nocturne
- `accounts` - Avec champs cgu_text, privacy_policy_text
- `commandes` - Avec champ prix_unitaire

## Endpoints API Clés

### Facturation par Semaine
- `GET /api/billing/weeks/current` - Semaine actuelle
- `GET /api/billing/weeks/{year}/{week}` - Données d'une semaine
- `POST /api/billing/weeks/{year}/{week}/invoice?invoiced=true` - Marquer facturé

### Filtrage CRM
- `GET /api/leads?crm_id={uuid}` - Leads filtrés par CRM
- `GET /api/stats/departements?crm_id={uuid}` - Stats filtrées par CRM

## Credentials Test
- **Email**: energiebleuciel@gmail.com
- **Password**: 92Ruemarxdormoy
- **MDL CRM ID**: 19e96529-6cf5-404c-86a6-a02c32d905a2
- **ZR7 CRM ID**: 0a463b29-ae11-4198-b092-143d7899b62d

## Backlog

### P0 - Critique
- [x] Facturation par semaine avec navigation
- [x] Prix par lead dans Commandes
- [x] CGU/Privacy dans Comptes
- [x] Logos + Legal dans Brief
- [x] Filtrage CRM backend pour Leads/Départements
- [ ] **Déploiement sur Hostinger** (prêt pour déploiement)

### P1 - Important
- [ ] Support complet GTM & Redirect tracking
- [ ] Sous-comptes (Sub-accounts)
- [ ] Sources de diffusion

### P2 - Nice to have
- [ ] Bibliothèque d'images
- [ ] Alertes système
- [ ] Mode Campagne A/B Testing

## Tests
- **Tests backend**: 21/21 passés (100%)
- **Tests frontend**: UI validée
- **Rapport**: `/app/test_reports/iteration_9.json`

## Déploiement
- **Preview**: https://sun-leads-pro.preview.emergentagent.com
- **Production**: https://rdz-group-ltd.online (Hostinger VPS - prêt)
