# EnerSolar CRM - Gestion de Leads Solaires

## Problème Original
CRM multi-tenant pour centraliser et redistribuer les leads solaires (PAC, PV, ITE) vers ZR7 Digital et Maison du Lead.

## Fonctionnalités Implémentées

### ✅ Système Anti-Bug - File d'Attente des Leads (09/02/2026)
- **File d'attente automatique** : Si un CRM externe (ZR7/MDL) est down, les leads sont automatiquement mis en file d'attente
- **Retry automatique** : 5 tentatives avec délais progressifs (1min, 5min, 15min, 1h, 2h)
- **Monitoring CRM** : Détection automatique de l'état de santé des CRM externes
- **Dashboard temps réel** : Widget "File d'attente des leads" sur le dashboard avec stats
- **Endpoints API** :
  - `GET /api/queue/stats` : Statistiques de la file
  - `GET /api/queue/items` : Liste des éléments en queue
  - `POST /api/queue/process` : Traitement manuel (admin)
  - `POST /api/queue/retry-exhausted` : Réinitialiser les leads épuisés
- **UI Component** : `QueueStatus.jsx` pour visualisation

### ✅ Codes Formulaires Auto-générés
- Format automatique: `PV-001`, `PAC-002`, `ITE-003`
- Compteur intelligent par type de produit
- Fonctionne pour création ET duplication

### ✅ Statistiques de Conversion
- **Démarré** = Premier clic sur bouton "Suivant" ou "Commencer" (trackFormStart())
- **Terminé** = Clic sur bouton final après validation téléphone (submitLeadToCRM())
- **% Conversion** = Terminés / Démarrés × 100

### ✅ Brief Développeur Complet
- Endpoint `/api/forms/{form_id}/brief`
- Script de tracking multi-étapes
- Support logo/badge du compte
- Aides financières avec montants
- 3 options de tracking conversion : GTM, Redirect, ou les 2

### ✅ UI Formulaires Style Landbot
- Vue cartes avec stats visuelles
- Filtres par produit (PV/PAC/ITE)
- Actions: Brief, Copier ID, Éditer, Dupliquer, Archiver

## Architecture Technique

### Backend
- `/app/backend/server.py` - API FastAPI principale
- `/app/backend/lead_queue_service.py` - **NEW** Service de file d'attente
- `/app/backend/email_service.py` - Service d'emails (SendGrid)
- `/app/backend/scheduler_service.py` - Tâches planifiées

### Frontend
- `/app/frontend/src/App.js` - Application React principale
- `/app/frontend/src/components/QueueStatus.jsx` - **NEW** Widget file d'attente
- `/app/frontend/src/components/FormsGrid.jsx` - Grille des formulaires
- `/app/frontend/src/components/FormCard.jsx` - Carte formulaire

### Collections MongoDB
- `leads` - Leads avec statut `queued` si en attente
- `lead_queue` - File d'attente avec metadata de retry
- `forms`, `accounts`, `crms` - Configuration

## Credentials Test
- **Email**: energiebleuciel@gmail.com
- **Password**: 92Ruemarxdormoy

## Backlog

### En Attente (P1)
- [ ] Vérification SendGrid (Settings → Sender Authentication)
- [ ] Mode Campagne Test (multi-LP ou multi-Form)
- [ ] Supprimer bouton "Régénérer" clé API

### Technique (P2)
- [ ] Refactoring App.js en composants séparés
- [ ] Refactoring server.py en modules (routes, services)
- [ ] Formulaires hébergés dans l'app

## Déploiement
- **Live**: https://rdz-group-ltd.online (Hostinger VPS)
- **Preview**: https://leadsolar-1.preview.emergentagent.com
