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

## APIs CRM Destination
- **ZR7 Digital**: `POST https://app.zr7-digital.fr/lead/api/create_lead/`
- **Maison du Lead**: `POST https://app.maisonsdulead.fr/lead/api/create_lead/`
- **Format**: JSON avec Header `Authorization: <token>`

## API Ce CRM - Envoi des Leads

### Endpoint
```
POST /api/submit-lead
Content-Type: application/json
```

### Body (JSON)
```json
{
  "form_code": "VOTRE-CODE-FORM",  // OBLIGATOIRE
  "phone": "0612345678",           // OBLIGATOIRE
  "nom": "Dupont",                 // optionnel
  "prenom": "Jean",                // optionnel
  "civilite": "M.",                // optionnel (M., Mme)
  "email": "email@example.com",    // optionnel
  "departement": "75",             // optionnel
  "code_postal": "75001",          // optionnel
  "superficie_logement": "120",    // optionnel
  "chauffage_actuel": "Gaz",       // optionnel
  "type_logement": "Maison",       // optionnel
  "statut_occupant": "Propriétaire", // optionnel
  "facture_electricite": "150"     // optionnel
}
```

### Réponse
```json
{
  "success": true,
  "message": "Lead enregistré",
  "status": "success" // ou "failed", "duplicate", "no_config"
}
```

## Fonctionnalités Implémentées

### Phase 8 - Finalisation (Complété - 08/02/2026)
- [x] **Clé API interne visible** dans la liste des formulaires avec bouton copier
- [x] **Brief Generator** : Notice API TOUJOURS incluse (sans checkbox)
- [x] **Suppression réservée aux Admins** : Leads, formulaires, LP, comptes
- [x] **Leads réservés aux Admins** : Onglet Leads déplacé dans Administration, route protégée
- [x] **Guide d'utilisation** : Documentation API complète dans section Formulaires
- [x] **Pas de validation stricte du téléphone** : Seule condition = téléphone présent
- [x] **Tous les champs ZR7/MDL** : prenom, civilite, superficie_logement, chauffage_actuel

## Rôles Utilisateurs

| Rôle | Accès | Peut supprimer | Accès Leads |
|------|-------|----------------|-------------|
| Admin | Complet | ✅ Oui | ✅ Oui |
| Éditeur | Créer/Modifier | ❌ Non | ❌ Non |
| Lecteur | Consultation | ❌ Non | ❌ Non |

## Credentials de Test
- **Email**: energiebleuciel@gmail.com
- **Password**: 92Ruemarxdormoy

## Backlog

### P0 - Sécurité
- [ ] **Backend filtrage par allowed_accounts** : Les endpoints ne filtrent pas encore les données selon les permissions utilisateur

### P1 - Améliorations
- [ ] Générateur de LP HTML avec style officiel
- [ ] Générateur de Formulaires HTML avec GTM intégré

### P2 - Technique
- [ ] Refactoring Frontend (App.js > 4000 lignes)
- [ ] Refactoring Backend (server.py vers modules)
