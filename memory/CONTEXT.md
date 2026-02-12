# 🧠 CONTEXTE COMPLET - RDZ CRM

> **⚠️ FICHIER CRITIQUE : À LIRE EN DÉBUT DE CHAQUE SESSION**
> 
> Ce fichier contient TOUT l'historique du projet.
> Il est mis à jour à chaque session et sauvegardé sur GitHub.

**Dernière mise à jour :** 12 Février 2026  
**Langue préférée :** Français 🇫🇷

---

## 📋 TABLE DES MATIÈRES

1. [Résumé du projet](#1-résumé-du-projet)
2. [Architecture technique](#2-architecture-technique)
3. [Serveur production](#3-serveur-production)
4. [Intégrations CRM](#4-intégrations-crm)
5. [Schéma base de données](#5-schéma-base-de-données)
6. [Fonctionnalités implémentées](#6-fonctionnalités-implémentées)
7. [Historique complet des sessions](#7-historique-complet-des-sessions)
8. [Bugs connus et résolus](#8-bugs-connus-et-résolus)
9. [Fichiers critiques](#9-fichiers-critiques)
10. [Credentials](#10-credentials)
11. [Backlog et roadmap](#11-backlog-et-roadmap)
12. [Notes importantes](#12-notes-importantes)

---

## 1. RÉSUMÉ DU PROJET

### Qu'est-ce que RDZ CRM ?

**RDZ CRM** est une plateforme de gestion et distribution de leads pour le secteur de l'énergie (panneaux solaires, pompes à chaleur, isolation).

### Flux principal
```
┌──────────────────────────────────────────────────────────────────────────┐
│                         FLUX DE LEAD RDZ                                  │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│   VISITEUR → Landing Page → Formulaire → RDZ (stockage) → CRM externe    │
│                                                              │            │
│                                                    ┌─────────┴─────────┐  │
│                                                    │                   │  │
│                                                   ZR7               MDL   │
│                                                 Digital        (Maison    │
│                                                              du Lead)     │
└──────────────────────────────────────────────────────────────────────────┘
```

### Règle fondamentale
```
╔══════════════════════════════════════════════════════════════════════════╗
║  🔐 RÈGLE ABSOLUE : LE LEAD EST TOUJOURS SAUVEGARDÉ DANS RDZ            ║
║                                                                          ║
║  Peu importe l'erreur (formulaire invalide, téléphone invalide,         ║
║  clé API manquante, pas de commande), le lead est TOUJOURS créé         ║
║  avec un statut approprié pour traitement ultérieur par l'admin.        ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## 2. ARCHITECTURE TECHNIQUE

### Stack
| Composant | Technologie |
|-----------|-------------|
| **Backend** | FastAPI (Python 3.11) |
| **Frontend** | React 18 + TailwindCSS + Shadcn/UI |
| **Base de données** | MongoDB 7 |
| **Serveur web** | Nginx |
| **Process manager** | systemd |

### Structure du projet
```
/var/www/rdz-crm/
├── backend/
│   ├── server.py              # Point d'entrée FastAPI
│   ├── config.py              # Configuration + helpers
│   ├── models.py              # Modèles Pydantic
│   ├── schema_locked.py       # Schema verrouillé
│   ├── core_locked.py         # Fonctions critiques verrouillées
│   ├── routes/
│   │   ├── public.py          # 🔒 API publique (leads + tracking)
│   │   ├── leads.py           # API leads interne
│   │   ├── forms.py           # Gestion formulaires
│   │   ├── lps.py             # Landing pages
│   │   ├── commandes.py       # Commandes + has_commande()
│   │   ├── accounts.py        # Comptes clients
│   │   ├── crms.py            # Configuration CRMs
│   │   ├── auth.py            # Authentification
│   │   ├── billing.py         # Facturation
│   │   ├── settings.py        # Paramètres
│   │   └── stats.py           # Statistiques
│   └── services/
│       ├── lead_sender.py     # 🔒 Envoi vers CRMs (ZR7/MDL)
│       ├── lead_redistributor.py # Redistribution leads
│       ├── brief_generator.py # Génération scripts tracking
│       ├── billing.py         # Calculs facturation
│       └── nightly_verification.py # Vérifications nocturnes
├── frontend/
│   ├── src/
│   │   ├── pages/             # Pages principales
│   │   ├── components/        # Composants réutilisables
│   │   └── components/ui/     # Shadcn/UI
│   └── build/                 # Build production
└── memory/
    ├── CONTEXT.md             # 👈 CE FICHIER
    ├── PRD.md                 # Requirements
    ├── FICHE_SUIVI.md         # Suivi projet
    └── SCHEMA_LOCKED.md       # Schema verrouillé
```

---

## 3. SERVEUR PRODUCTION

### Informations serveur Hostinger
| Élément | Valeur |
|---------|--------|
| **Domaine** | https://rdz-group-ltd.online/ |
| **Hébergeur** | Hostinger VPS |
| **OS** | Ubuntu 24.04 |
| **SSH** | `ssh root@72.60.189.23` |
| **Chemin** | `/var/www/rdz-crm/` |

### Services systemd
```bash
# Backend FastAPI
systemctl status crm-backend
systemctl restart crm-backend

# MongoDB
systemctl status mongod

# Nginx
systemctl status nginx
```

### Commandes de déploiement
```bash
# Déploiement complet
cd /var/www/rdz-crm && git pull origin main && systemctl restart crm-backend && cd frontend && npm run build

# Logs backend
journalctl -u crm-backend -f

# Logs nginx
tail -f /var/log/nginx/error.log
```

---

## 4. INTÉGRATIONS CRM

### CRMs externes
| CRM | Slug | URL API |
|-----|------|---------|
| **ZR7 Digital** | `zr7` | `https://app.zr7-digital.fr/lead/api/create_lead/` |
| **Maison du Lead** | `mdl` | `https://maison-du-lead.com/lead/api/create_lead/` |

### Format API (identique ZR7 et MDL)
```json
POST /lead/api/create_lead/
Headers:
  Authorization: {token}
  Content-Type: application/json

Body:
{
  "phone": "0612345678",
  "register_date": 1707753600,
  "nom": "Dupont",
  "prenom": "Jean",
  "email": "jean@email.com",
  "civilite": "M.",
  "custom_fields": {
    "departement": {"value": "75"},
    "type_logement": {"value": "Maison"},
    "statut_occupant": {"value": "Propriétaire"}
  }
}
```

### Réponses CRM
| Code | Signification | Status RDZ |
|------|---------------|------------|
| 201 | Lead créé | `success` |
| 200 + "doublon" | Déjà existant | `duplicate` |
| 403 | Token invalide | `auth_error` |
| 400 | Données invalides | `validation_error` |
| 500+ | Erreur serveur | `server_error` → queue |

### Système de clés API
1. **Clé formulaire** : Configurée sur chaque formulaire, utilisée pour envoi normal
2. **Clés redistribution** : 6 clés (ZR7×3 produits + MDL×3 produits) dans Paramètres, pour envoi inter-CRM

---

## 5. SCHÉMA BASE DE DONNÉES

### Collection `leads`
```javascript
{
  // Identifiants
  "id": "uuid",
  "session_id": "uuid",
  "form_id": "uuid",
  "form_code": "PV-001",
  "account_id": "uuid",
  
  // Contact (OBLIGATOIRES: phone, nom, departement)
  "phone": "0612345678",
  "nom": "Dupont",
  "prenom": "Jean",
  "civilite": "M.",
  "email": "email@test.com",
  
  // Localisation
  "departement": "75",        // ⚠️ PAS "code_postal" !
  "ville": "Paris",
  "adresse": "123 rue...",
  
  // Logement
  "type_logement": "Maison",
  "statut_occupant": "Propriétaire",
  "surface_habitable": "100",
  "annee_construction": "1990",
  "type_chauffage": "Gaz",
  
  // Énergie
  "facture_electricite": "100-150€",
  "facture_chauffage": "150-200€",
  
  // Projet
  "type_projet": "Installation",
  "product_type": "PV",       // PV, PAC, ITE
  "delai_projet": "3 mois",
  "budget": "10000-15000€",
  
  // Tracking
  "lp_code": "LP-001",
  "liaison_code": "LP-001_PV-001",
  "utm_source": "google",
  "utm_medium": "cpc",
  "utm_campaign": "pv_2026",
  
  // CRM Routing
  "origin_crm": "zr7",        // CRM du compte
  "target_crm": "zr7",        // CRM destination finale
  "is_transferred": false,    // Transféré vers autre CRM ?
  "routing_reason": "commande_zr7",
  "allow_cross_crm": true,
  "distribution_reason": "COMMANDE_ZR7",
  
  // Status
  "api_status": "success",    // Voir enum ci-dessous
  "api_response": "...",
  "sent_to_crm": true,
  "sent_at": "2026-02-12T10:30:00Z",
  
  // Flags diagnostic
  "phone_invalid": false,
  "missing_nom": false,
  "missing_dept": false,
  "form_not_found": false,
  "manual_only": false,
  
  // Consentement
  "rgpd_consent": true,
  "newsletter": false,
  
  // Metadata
  "ip": "1.2.3.4",
  "register_date": 1707753600,
  "created_at": "2026-02-12T10:30:00Z"
}
```

### Enum `api_status`
| Status | Description | Badge UI |
|--------|-------------|----------|
| `pending` | En cours d'envoi | ⏳ |
| `success` | Envoyé avec succès | ✅ Vert |
| `duplicate` | Doublon détecté par CRM | ⚠️ Orange |
| `failed` | Erreur d'envoi | ❌ Rouge |
| `queued` | En file d'attente retry | 🔵 Bleu |
| `no_crm` | CRM non configuré | ⚪ Gris |
| `no_api_key` | Clé API manquante | ⚠️ Jaune |
| `orphan` | Formulaire non trouvé | ❌ Rouge |
| `invalid_phone` | Téléphone invalide | ❌ Rouge |
| `missing_required` | Champs obligatoires manquants | ⚠️ Orange |
| `pending_no_order` | Pas de commande active (<8j) | ⏳ Orange |
| `pending_manual` | Redistribution manuelle (>8j) | 🔵 Bleu |
| `validation_error` | Rejeté par CRM (données invalides) | ❌ Rouge |
| `auth_error` | Token CRM invalide | ❌ Rouge |

---

## 6. FONCTIONNALITÉS IMPLÉMENTÉES

### ✅ Core (100%)
- [x] Authentification JWT
- [x] Gestion multi-CRM (ZR7 + MDL)
- [x] Routing intelligent (commandes + cross-CRM)
- [x] File d'attente retry automatique
- [x] Tracking LP + Formulaires
- [x] Brief génération (scripts tracking)

### ✅ Admin UI (100%)
- [x] Dashboard statistiques
- [x] Liste leads avec filtres avancés
- [x] Voir/Éditer/Supprimer lead
- [x] Forcer envoi vers CRM
- [x] Actions de masse (éditer, supprimer, envoyer)
- [x] Reset stats formulaire (sans supprimer leads)
- [x] Gestion comptes, formulaires, LPs
- [x] Configuration commandes par département
- [x] 6 clés API redistribution dans Paramètres

### ✅ Système de leads robuste (100%)
- [x] Lead TOUJOURS sauvegardé (jamais perdu)
- [x] Statuts d'erreur détaillés
- [x] Redistribution auto < 8 jours
- [x] Passage manual_only > 8 jours
- [x] Scheduler APScheduler

### 🔒 Sécurités (100%)
- [x] Code formulaire non modifiable
- [x] Clé API non supprimable
- [x] Noyau critique verrouillé
- [x] Schema DB verrouillé

---

## 7. HISTORIQUE COMPLET DES SESSIONS

### Session 1 - Création initiale (Janvier 2026)
- Création du projet RDZ CRM
- Architecture backend FastAPI + MongoDB
- Frontend React + TailwindCSS
- Intégration ZR7 et MDL basique

### Session 2 - Amélioration tracking (Janvier 2026)
- Système de sessions visiteur
- Tracking événements (lp_visit, cta_click, form_submit)
- Brief generator avec scripts

### Session 3 - Multi-CRM et commandes (Janvier 2026)
- Gestion commandes par département
- Routing intelligent vers CRM
- Cross-CRM si pas de commande

### Session 4 - Audit technique majeur (Février 2026)
- Migration `code_postal` → `departement`
- Centralisation `has_commande()` (suppression duplications)
- URLs CRM dynamiques (plus hardcodées)
- Verrouillage schema et noyau critique

### Session 5 - Fonctionnalités Admin (Février 2026)
- CRUD complet leads (éditer, supprimer)
- Forcer envoi vers CRM spécifique
- Actions de masse
- Reset stats formulaire
- Interface clés redistribution

### Session 6 - Lead Always Saved (Février 2026)
- Refonte complète `submit_lead()`
- Lead TOUJOURS créé, jamais rejeté
- Nouveaux statuts d'erreur
- Badges et filtres frontend
- Champs obligatoires (phone, nom, departement)

### Session 7 - Corrections bugs (12 Février 2026)
- Fix bug JSON `force-send` (sérialisation réponse)
- Analyse logique doublons (détection par CRM externe)
- Instructions déploiement Hostinger

---

## 8. BUGS CONNUS ET RÉSOLUS

### ✅ Résolus

| Bug | Cause | Solution | Date |
|-----|-------|----------|------|
| `force-send` retourne JSON error | `response` non sérialisable | `str(response)[:500]` | 12/02/2026 |
| Reset stats ne fonctionne pas | Filtre `stats_reset` manquant | Ajout `{"stats_reset": {"$ne": true}}` | 11/02/2026 |
| LP tracking ne marche pas | Script mal généré | Refonte `brief_generator.py` | 11/02/2026 |
| Leads perdus si pas de commande | Return avant save | "Lead always saved" paradigm | 10/02/2026 |
| Duplication `has_commande` | Code copié dans plusieurs fichiers | Import centralisé depuis `commandes.py` | 09/02/2026 |

### ⚠️ À surveiller

| Issue | Description | Status |
|-------|-------------|--------|
| `validation_error` | CRM rejette certains leads | Dépend des règles CRM |
| `auth_error` / Token invalide | Clé API expirée ou incorrecte | Vérifier config formulaire |

---

## 9. FICHIERS CRITIQUES

### 🔒 Fichiers verrouillés (NE PAS MODIFIER sans déverrouillage)

| Fichier | Fonctions critiques |
|---------|---------------------|
| `/backend/routes/public.py` | `submit_lead()`, `create_session()`, `track_event()` |
| `/backend/routes/commandes.py` | `has_commande()` |
| `/backend/services/lead_sender.py` | `send_to_crm_v2()`, `add_to_queue()` |
| `/backend/config.py` | `validate_phone_fr()` |

### Déverrouillage
Pour modifier ces fichiers, dire :
> "Je déverrouille le noyau critique pour modifier [fonction]"

---

## 10. CREDENTIALS

### Login UI Admin
```
Email: energiebleuciel@gmail.com
Password: 92Ruemarxdormoy
```

### Serveur SSH
```
ssh root@72.60.189.23
```

### MongoDB
```
mongodb://localhost:27017/rdz_production
```

---

## 11. BACKLOG ET ROADMAP

### 🔴 P0 - Critique
- [x] Fix bug `force-send` JSON
- [ ] Vérifier déploiement production

### 🟠 P1 - Important
- [ ] Sous-comptes utilisateurs
- [ ] Configuration détaillée types de produits
- [ ] Test complet scheduler aging leads

### 🟡 P2 - Normal
- [ ] Alertes email (SendGrid)
- [ ] Amélioration bibliothèque médias

### 🟢 P3 - Nice to have
- [ ] A/B Testing ("Mode Campagne")
- [ ] Export PDF rapports

---

## 12. NOTES IMPORTANTES

### ⚠️ Points d'attention

1. **Champ `departement`** : TOUJOURS utiliser `departement`, JAMAIS `code_postal`, `department`, `cp`

2. **Doublons** : La détection est faite par le CRM externe (ZR7/MDL), pas par RDZ

3. **validation_error** : Signifie que le CRM a rejeté les données (format incorrect côté CRM)

4. **Token invalide** : La clé API du formulaire est expirée ou incorrecte

5. **Cross-CRM** : Si `allow_cross_crm=true` et envoi échoue, le système essaie l'autre CRM

6. **Clés redistribution** : Utilisées uniquement pour envoi vers CRM différent de l'origine

### 📝 Commandes utiles production

```bash
# Logs en direct
journalctl -u crm-backend -f

# Redémarrer backend
systemctl restart crm-backend

# Rebuild frontend
cd /var/www/rdz-crm/frontend && npm run build

# Status MongoDB
systemctl status mongod

# Déploiement complet
cd /var/www/rdz-crm && git pull origin main && systemctl restart crm-backend && cd frontend && npm run build
```

---

## 📅 CHANGELOG

| Date | Modification |
|------|--------------|
| 12/02/2026 | Fix bug JSON force-send, création CONTEXT.md |
| 11/02/2026 | Fix reset stats, fix LP tracking |
| 10/02/2026 | Paradigme "Lead always saved" |
| 09/02/2026 | Audit technique, centralisation has_commande |
| 08/02/2026 | Fonctionnalités admin (CRUD, force-send, mass actions) |

---

**🔄 Ce fichier est automatiquement mis à jour à chaque session.**
**📤 Pensez à "Save to GitHub" avant de quitter !**
