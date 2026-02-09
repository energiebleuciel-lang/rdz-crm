# EnerSolar CRM - Gestion de Leads Solaires

## Problème Original
CRM multi-tenant pour centraliser et redistribuer les leads solaires (PAC, PV, ITE) vers ZR7 Digital et Maison du Lead, avec routage intelligent et facturation inter-CRM.

## Architecture Technique

### Stack
- **Frontend**: React 18 + Tailwind CSS + React Router
- **Backend**: FastAPI (Python)
- **Base de données**: MongoDB
- **Authentification**: JWT (UI) + Token-based (API v1)
- **Emails**: SendGrid (en attente de vérification expéditeur)
- **Scheduler**: APScheduler (résumés quotidiens/hebdomadaires)

### Structure Modulaire (Nouveau)
```
/app/
├── backend/
│   ├── server.py           # API principale (3700+ lignes)
│   ├── email_service.py    # Service d'emails isolé et indépendant
│   ├── scheduler_service.py # Tâches planifiées isolées
│   └── .env
├── frontend/
│   └── src/
│       ├── App.js          # App principale
│       └── components/
│           ├── FormCard.jsx    # Carte formulaire individuelle (NOUVEAU)
│           ├── FormsGrid.jsx   # Grille de formulaires (NOUVEAU)
│           └── ui/             # Composants Shadcn
└── memory/
    └── PRD.md
```

## Fonctionnalités Implémentées

### Phase 13 - UI Cartes & Emails (09/02/2026)
- [x] **Nouvelle UI Formulaires (Style Landbot)** :
  - Vue cartes avec stats visuelles (Démarrés, Terminés, % Conversion)
  - Vue liste (tableau) en alternative
  - Filtres par produit (PV/PAC/ITE), statut, recherche
  - Toggle grille/liste
  - Badges produits colorés
  - Barres de progression visuelles
- [x] **Composants modulaires indépendants** :
  - `FormCard.jsx` - Carte individuelle isolée
  - `FormsGrid.jsx` - Grille avec filtres et actions
  - Gestion d'erreurs isolée (try-catch partout)
- [x] **Système d'emails SendGrid** (EN ATTENTE) :
  - Service email isolé et non-bloquant
  - Templates HTML pour alertes critiques
  - Templates pour résumés quotidiens/hebdomadaires
  - ⚠️ En attente de vérification Sender Identity

### Phase 12 - Protection & Traçabilité (08/02/2026)
- [x] Protection des formulaires (archivage, champs non-modifiables)
- [x] Traçabilité complète des leads
- [x] Tests API réels réussis (ZR7 + MDL)

### Phases Précédentes
- [x] API v1 style Landbot (clé globale)
- [x] Sécurité multi-tenant
- [x] Dashboard facturation
- [x] Routage intelligent
- [x] Backup/Restore

## Endpoints Principaux

### API v1 (Nouveau)
```
POST /api/v1/leads              # Soumission lead (clé globale en header)
GET  /api/settings/api-key      # Récupérer clé API globale
```

### Emails
```
POST /api/email/test            # Envoyer email de test
POST /api/email/send-daily-summary    # Forcer envoi résumé quotidien
POST /api/email/send-weekly-summary   # Forcer envoi résumé hebdomadaire
GET  /api/email/config          # Configuration email
```

### Formulaires
```
GET    /api/forms               # Liste formulaires
POST   /api/forms               # Créer formulaire
POST   /api/forms/{id}/duplicate # Dupliquer formulaire
DELETE /api/forms/{id}          # Archiver formulaire
```

## Configuration SendGrid (À FAIRE)

L'utilisateur doit vérifier son adresse email d'expéditeur :
1. Aller sur https://app.sendgrid.com
2. Settings → Sender Authentication
3. "Verify a Single Sender"
4. Entrer : `factures.zr7digital@gmail.com`
5. Cliquer le lien de confirmation dans l'email

## Credentials Test
- **Email**: energiebleuciel@gmail.com
- **Password**: 92Ruemarxdormoy
- **ZR7 API Key (PV)**: 342b6515-7424-43a6-b5c9-142385fc6ef1
- **MDL API Key (PV)**: 00f4e557-4903-47c6-87db-e3d41460ce45

## Backlog

### P0 - Complété ✅
- [x] UI Cartes style Landbot
- [x] Duplication formulaires
- [x] Service emails (code)
- [x] Scheduler (code)

### P1 - En Attente
- [ ] **Vérification SendGrid** - Utilisateur doit vérifier son email
- [ ] Configuration des Aides financières (MaPrimeRenov, CEE, etc.)
- [ ] File d'attente leads (si API down)
- [ ] Retry automatique des leads échoués

### P2 - Technique
- [ ] Refactoring App.js (5000+ lignes)
- [ ] Refactoring server.py en modules
- [ ] Supprimer bouton "Régénérer" clé API

## Déploiement
- **Live**: https://rdz-group-ltd.online (Hostinger VPS)
- **Preview**: https://leadflow-106.preview.emergentagent.com
- **GitHub**: PRIVÉ ✅
