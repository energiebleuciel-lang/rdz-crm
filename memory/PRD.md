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

### Structure Modulaire
```
/app/
├── backend/
│   ├── server.py           # API principale (~3800 lignes)
│   ├── email_service.py    # Service d'emails isolé et non-bloquant ✅
│   ├── scheduler_service.py # Tâches planifiées isolées ✅
│   └── .env
├── frontend/
│   └── src/
│       ├── App.js          # App principale
│       └── components/
│           ├── FormCard.jsx    # Carte formulaire individuelle ✅ (NOUVEAU)
│           ├── FormsGrid.jsx   # Grille de formulaires ✅ (NOUVEAU)
│           └── ui/             # Composants Shadcn
└── memory/
    └── PRD.md
```

## Fonctionnalités Implémentées (09/02/2026)

### ✅ Codes Formulaires Auto-générés
- Format automatique: `PV-001`, `PAC-002`, `ITE-003`, etc.
- Compteur intelligent par type de produit
- Vérification d'unicité automatique
- Fonctionne pour création ET duplication

### ✅ Statistiques de Conversion
- **Démarrés**: Nombre de fois où le formulaire a été chargé (via `/api/track/form-start`)
- **Terminés**: Nombre de leads soumis
- **% Conversion**: Terminés / Démarrés × 100
- Affichage visuel dans les cartes avec barres de progression

### ✅ UI Formulaires Style Landbot
- Vue en cartes avec stats visuelles (Démarrés, Terminés, % Conversion)
- Vue liste (tableau) en alternative
- Filtres par produit (PV/PAC/ITE), statut, recherche
- Toggle grille/liste
- Badges produits colorés
- Barres de progression visuelles
- Actions au hover : Brief, Copier ID, Éditer, Dupliquer, Archiver

### ✅ Brief Développeur
- Endpoint `/api/forms/{form_id}/brief` génère :
  - Script de tracking JavaScript complet
  - Exemple d'utilisation HTML
  - Champs requis et optionnels
  - Aides financières par produit
  - Endpoint API et clé

### ✅ Composants Modulaires Indépendants
- `FormCard.jsx` - Carte individuelle avec gestion d'erreurs isolée
- `FormsGrid.jsx` - Grille avec filtres, recherche et actions
- Chaque composant est indépendant et ne peut pas casser l'autre

### ✅ Système d'Emails SendGrid (Code prêt)
- Service email isolé et non-bloquant
- Templates HTML pour alertes critiques
- Templates pour résumés quotidiens/hebdomadaires
- ⚠️ EN ATTENTE: Vérification Sender Identity

## Endpoints API

### Formulaires
```
GET    /api/forms               # Liste avec stats
POST   /api/forms               # Créer (code auto-généré)
GET    /api/forms/{id}/brief    # Brief développeur complet
POST   /api/forms/{id}/duplicate # Dupliquer (code auto-généré)
DELETE /api/forms/{id}          # Archiver
```

### Tracking (Public - pour les formulaires externes)
```
POST /api/track/form-start      # Tracker le chargement du formulaire
POST /api/v1/leads              # Soumettre un lead
```

### Emails
```
POST /api/email/test            # Email de test
GET  /api/email/config          # Configuration email
```

## Comment fonctionne le taux de conversion ?

1. **Formulaire externe intègre le script de tracking** (généré par `/api/forms/{id}/brief`)
2. **Au chargement** : Le script appelle `/api/track/form-start` → compteur "Démarrés" +1
3. **À la soumission** : Le script appelle `/api/v1/leads` → compteur "Terminés" +1
4. **Calcul** : Conversion = Terminés / Démarrés × 100

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
- [x] Codes formulaires auto-générés
- [x] Stats de conversion fonctionnelles
- [x] UI Cartes style Landbot
- [x] Brief développeur avec script tracking
- [x] Composants modulaires indépendants

### P1 - En Attente
- [ ] **Vérification SendGrid** - Utilisateur doit vérifier son email
- [ ] Configuration des Aides financières dans le formulaire
- [ ] File d'attente leads (si API down)
- [ ] Retry automatique des leads échoués

### P2 - Technique
- [ ] Refactoring App.js en composants
- [ ] Refactoring server.py en modules
- [ ] Supprimer bouton "Régénérer" clé API

## Déploiement
- **Live**: https://rdz-group-ltd.online (Hostinger VPS)
- **Preview**: https://leadflow-106.preview.emergentagent.com
- **GitHub**: PRIVÉ ✅
