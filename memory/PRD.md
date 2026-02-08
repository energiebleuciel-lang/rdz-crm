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
    ├── Landing Pages
    │   └── CTA tracking
    ├── Forms
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
- [x] **Filtrage strict par CRM** sur toutes les pages:
  - Dashboard, Leads, Landing Pages, Formulaires, Analytics, Générateur Scripts
- [x] **Nouveau formulaire Sous-comptes** avec:
  - Informations générales: nom, domaine, type de produit (solaire/pompe/isolation)
  - Logos: logo gauche (URL), logo droit (URL), favicon
  - Textes légaux (popup, pas URL): politique confidentialité, mentions légales
  - Tracking: type conversion, layout formulaire, pixel header, URL redirection

### Pages Disponibles
1. **Tableau de bord** - Stats et derniers leads
2. **Analytics** - Taux de conversion, winners/losers
3. **Leads** - Liste avec filtres et export CSV
4. **Landing Pages** - CRUD avec stats CTA
5. **Formulaires** - CRUD avec stats conversion
6. **Sous-comptes** - Configuration par site/projet
7. **Générateur Scripts** - Code tracking pour LPs et Forms
8. **Guide d'utilisation** - Documentation intégrée
9. **Utilisateurs** - Gestion admin
10. **Journal activité** - Logs admin
11. **Paramètres** - Configuration

## Credentials de Test
- **Email**: energiebleuciel@gmail.com
- **Password**: 92Ruemarxdormoy

## API Endpoints Principaux
- `POST /api/auth/login` - Connexion
- `GET /api/crms` - Liste des CRMs
- `GET /api/sub-accounts?crm_id=xxx` - Sous-comptes (filtré par CRM)
- `GET /api/lps?crm_id=xxx` - Landing Pages (filtré par CRM)
- `GET /api/forms?crm_id=xxx` - Formulaires (filtré par CRM)
- `GET /api/leads?crm_id=xxx` - Leads (filtré par CRM)
- `GET /api/analytics/stats?crm_id=xxx` - Statistiques (filtré par CRM)
- `GET /api/analytics/winners?crm_id=xxx` - Winners/Losers (filtré par CRM)
- `POST /api/submit-lead` - Soumission lead (public)
- `POST /api/track/cta-click` - Tracking CTA (public)
- `POST /api/track/form-start` - Tracking form start (public)

## Backlog (P1/P2/P3)

### P1 - Fonctionnalités Core
- [ ] Fonctionnalité CRUD complète pour Landing Pages
- [ ] Fonctionnalité CRUD complète pour Formulaires
- [ ] Générateur de scripts dynamique et fonctionnel
- [ ] Page Analytics avec graphiques et comparaisons
- [ ] Journal d'activité fonctionnel

### P2 - Améliorations
- [ ] Refactoring Frontend: découper App.js (2000+ lignes) en composants
- [ ] Upload d'images pour logos (au lieu d'URLs)
- [ ] Preview/screenshots de LPs et Forms dans le dashboard
- [ ] Duplication de campagnes (LP Taboola -> Outbrain)
- [ ] Commentaires sur LPs et Forms

### P3 - Futur
- [ ] Redéploiement sur Hostinger VPS (remplacer prototype)
- [ ] Docker Compose pour déploiement simplifié
- [ ] Notifications email pour leads échoués
- [ ] API webhooks pour intégrations externes

## Notes Techniques
- Le frontend est un fichier monolithique (`App.js` ~2000 lignes) - refactoring recommandé
- Version déployée sur VPS Hostinger: prototype basique
- Version locale: CRM complet avec toutes les fonctionnalités

## Intégrations Externes
- **Maison du Lead API**: https://maison-du-lead.com/lead/api/create_lead/
- **ZR7 Digital API**: https://app.zr7-digital.fr/lead/api/create_lead/
