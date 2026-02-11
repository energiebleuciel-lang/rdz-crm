# 📋 FICHE DE SUIVI - RDZ CRM

**Dernière mise à jour :** Février 2026  
**Statut projet :** ✅ Production

---

## 🔒 NOYAU CRITIQUE VERROUILLÉ

**⛔ LE SYSTÈME D'INTÉGRATION LEADS EST DÉFINITIVEMENT VERROUILLÉ ⛔**

| Fonction | Fichier | Rôle |
|----------|---------|------|
| `submit_lead()` | `public.py` | Réception leads |
| `has_commande()` | `commandes.py` | Routage CRM |
| `send_to_crm_v2()` | `lead_sender.py` | Envoi vers ZR7/MDL |
| `add_to_queue()` | `lead_sender.py` | Retry automatique |
| `validate_phone_fr()` | `config.py` | Validation téléphone |
| `create_session()` | `public.py` | Session tracking |
| `track_event()` | `public.py` | Événements |

**Pour modifier :** "Je déverrouille le noyau critique pour modifier [fonction]"

**Fichier de référence :** `/app/backend/core_locked.py`

---

## 🎯 RÉSUMÉ DU PROJET

**RDZ CRM** est un CRM multi-tenant pour la collecte et distribution de leads vers deux CRMs externes :
- **ZR7 Digital** (slug: `zr7`)
- **Maison du Lead** (slug: `mdl`)

### Flux principal
```
Visiteur → Landing Page → Formulaire → RDZ (collecte) → ZR7 ou MDL (distribution)
```

---

## 🖥️ INFORMATIONS TECHNIQUES

### Serveur Production
- **Domaine :** https://rdz-group-ltd.online/
- **IP :** 72.60.189.23
- **SSH :** `ssh root@72.60.189.23`
- **Chemin :** `/var/www/rdz-crm/`

### Commande de déploiement
```bash
cd /var/www/rdz-crm && git pull origin main && systemctl restart crm-backend && cd frontend && npm run build
```

### Stack technique
- **Backend :** FastAPI + MongoDB (port 8001)
- **Frontend :** React + TailwindCSS + Shadcn/UI
- **Base de données :** MongoDB

### Credentials de test
- **Login UI :** `energiebleuciel@gmail.com` / `92Ruemarxdormoy`

---

## 🔒 SCHEMA VERROUILLÉ

### Règle absolue
**AUCUN renommage de champ sans déverrouillage explicite.**

Pour modifier un nom, dire :
> "Je déverrouille le schema pour modifier [nom_du_champ]"

### Champs principaux (38 verrouillés)
| Champ | Description |
|-------|-------------|
| `phone` | Téléphone (obligatoire) |
| `nom`, `prenom` | Identité |
| `email` | Email |
| `departement` | Code département (01-95) |
| `ville` | Ville |
| `type_logement` | Maison, Appartement |
| `statut_occupant` | Propriétaire, Locataire |
| `facture_electricite` | Tranche facture |
| `target_crm` | CRM destination (slug) |
| `api_status` | pending/success/failed/duplicate/no_crm |

### ❌ CHAMPS INTERDITS (ne jamais utiliser)
| Interdit | Utiliser à la place |
|----------|---------------------|
| `code_postal` | `departement` |
| `department` | `departement` |
| `cp`, `zipcode` | `departement` |
| `target_crm_id` | `target_crm` |

### Fichiers de référence
- `/app/backend/schema_locked.py`
- `/app/memory/SCHEMA_LOCKED.md`

---

## ✅ CE QUI A ÉTÉ FAIT (Février 2026)

### Audit technique complet
- [x] Fonction `has_commande` centralisée (supprimé duplication)
- [x] Migration vers `send_to_crm_v2` partout
- [x] URLs CRM dynamiques (plus hardcodées)
- [x] Signature corrigée : `has_commande(crm_id, product_type, departement)`

### Sécurités implémentées
- [x] **Code formulaire** : Non modifiable après création
- [x] **Clé API formulaire** : Non supprimable une fois définie
- [x] **Clé API RDZ** : Permanente, non régénérable

### Template brief amélioré
- [x] Template complet avec tous les noms de champs corrects
- [x] Avertissement `departement` (pas `department`)
- [x] Liste des champs interdits dans le script généré

### Migration code_postal → departement
- [x] Backend : Tous les fichiers migrés
- [x] Frontend : Affichage mis à jour
- [x] Scripts : Template avec `departement`

### Autres fonctionnalités
- [x] Bibliothèque Médias (upload/gestion images)
- [x] Menu sidebar réorganisé en catégories
- [x] Fallback CRM (si échec primaire → essai secondaire)
- [x] Compteur "Terminé" = tous les leads créés

---

## 📁 FICHIERS CLÉS

### Backend
| Fichier | Rôle |
|---------|------|
| `/backend/routes/public.py` | API publique (tracking + leads) |
| `/backend/routes/leads.py` | API leads interne |
| `/backend/routes/forms.py` | Gestion formulaires |
| `/backend/routes/commandes.py` | Commandes + `has_commande()` |
| `/backend/services/brief_generator.py` | Génération scripts tracking |
| `/backend/services/lead_sender.py` | Envoi vers CRMs externes |
| `/backend/schema_locked.py` | Schema verrouillé |

### Frontend
| Fichier | Rôle |
|---------|------|
| `/frontend/src/pages/Leads.jsx` | Liste leads |
| `/frontend/src/pages/Forms.jsx` | Gestion formulaires |
| `/frontend/src/pages/LandingPages.jsx` | LPs + Brief |
| `/frontend/src/pages/Media.jsx` | Bibliothèque médias |
| `/frontend/src/components/Layout.jsx` | Sidebar menu |

---

## 🔄 API ENDPOINTS CLÉS

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/public/track/session` | POST | Créer session |
| `/api/public/track/event` | POST | Tracker événement |
| `/api/public/leads` | POST | Soumettre lead (public) |
| `/api/leads` | GET | Liste leads (auth) |
| `/api/leads/export` | GET | Export CSV (clé API RDZ) |
| `/api/forms/{id}` | PUT | Modifier formulaire |
| `/api/lps/{id}/brief` | GET | Générer brief |

---

## 🎯 BACKLOG / À FAIRE

### Priorité haute (P0)
- [ ] Vérifier déploiement production après modifications

### Priorité moyenne (P1)
- [ ] Sous-comptes utilisateurs
- [ ] Configuration détaillée types de produits
- [ ] Ajouter `/frontend/build` au `.gitignore`

### Backlog (P2-P3)
- [ ] Alertes email (SendGrid)
- [ ] A/B Testing ("Mode Campagne")
- [ ] Amélioration bibliothèque images

---

## ⚠️ POINTS D'ATTENTION

1. **Le champ `departement`** doit être utilisé partout (pas `department`, pas `code_postal`)

2. **Les clés API formulaires** ne peuvent plus être supprimées une fois définies

3. **Le code formulaire** (PV-001, etc.) ne peut plus être modifié

4. **Fallback CRM** : Si envoi échoue vers CRM primaire et `allow_cross_crm=true`, le lead est envoyé vers l'autre CRM

5. **Template brief** : Inclut maintenant un exemple complet avec les bons noms de champs

---

## 📞 EN CAS DE PROBLÈME

### Logs backend
```bash
journalctl -u crm-backend -f
```

### Redémarrer backend
```bash
systemctl restart crm-backend
```

### Rebuild frontend
```bash
cd /var/www/rdz-crm/frontend && npm run build
```

---

## 📝 NOTES POUR LA PROCHAINE SESSION

- Toujours lire cette fiche en début de session
- Vérifier le fichier `/app/memory/PRD.md` pour le contexte complet
- Consulter `/app/backend/schema_locked.py` avant tout renommage
- Tester les modifications en prévisualisation avant déploiement

---

**Langue préférée :** Français 🇫🇷
