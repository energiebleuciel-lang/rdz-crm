# 📋 DOCUMENTATION SYSTÈME FORMULAIRES LEADS

## 🎯 Résumé du Projet

Système centralisé de formulaires de génération de leads avec :
- Backend central (FastAPI + MongoDB)
- Dashboard admin pour voir tous les leads
- Support multi-formulaires avec APIs différentes

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    SERVEUR CENTRAL                       │
│                                                          │
│  api.tondomaine.com     → Backend FastAPI (port 8001)   │
│  admin.tondomaine.com   → Dashboard React (/admin)      │
│  MongoDB                → Base de données locale        │
│                                                          │
└─────────────────────────────────────────────────────────┘
         │
         │ Reçoit les leads de tous les formulaires
         │
    ┌────┴────┬─────────────┬─────────────┐
    ▼         ▼             ▼             ▼
┌────────┐ ┌────────┐ ┌────────┐    ┌────────┐
│Form 1  │ │Form 2  │ │Form 3  │    │Form N  │
│PV      │ │PAC     │ │Isol.   │    │...     │
└────────┘ └────────┘ └────────┘    └────────┘
```

---

## 📁 Structure des Fichiers

### Backend (server.py)
```
/backend/
├── server.py          # API FastAPI
├── requirements.txt   # Dépendances Python
└── .env              # Variables d'environnement
```

### Frontend Formulaire
```
/frontend/
├── src/
│   ├── components/
│   │   ├── FormulaireSolaire/
│   │   │   ├── index.js           # Formulaire principal
│   │   │   ├── api.js             # Config API + form_id
│   │   │   ├── Logo.js            # Logos et branding
│   │   │   └── SimulationLoader.js # Animation chargement
│   │   ├── AdminDashboard/
│   │   │   └── index.js           # Dashboard admin
│   │   └── ui/                    # Composants shadcn
│   ├── App.js
│   └── index.css
└── public/
    └── site-independant.png
```

---

## 🔌 Endpoints API

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/submit-lead` | POST | Soumettre un lead |
| `/api/leads` | GET | Liste tous les leads |
| `/api/leads?status=failed` | GET | Leads en échec |
| `/api/leads/retry-failed` | POST | Réessayer les échecs |
| `/api/admin/stats` | GET | Statistiques globales |
| `/api/admin/forms` | GET | Liste des formulaires |
| `/api/admin/form-configs` | GET | Configs des APIs |
| `/api/admin/form-configs` | POST | Ajouter une config |

---

## 📝 Format d'un Lead

```json
{
  "id": "uuid",
  "form_id": "pv-outbrain-2026",
  "form_name": "PV Solaire Outbrain 2026",
  "phone": "0612345678",
  "nom": "Jean Dupont",
  "email": "email@test.com",
  "departement": "75",
  "type_logement": "maison",
  "statut_occupant": "proprietaire",
  "facture_electricite": "100-150",
  "created_at": "2026-02-07T19:41:28",
  "api_status": "success|failed|duplicate|pending",
  "api_response": "...",
  "api_url": "https://maison-du-lead.com/..."
}
```

---

## ⚙️ Configuration d'un Formulaire

### Dans api.js de chaque formulaire :
```javascript
export const FORM_CONFIG = {
  form_id: "pv-outbrain-2026",      // Identifiant unique
  form_name: "PV Solaire Outbrain"  // Nom affiché
};
```

### Config API dans la base (optionnel si API différente) :
```json
{
  "form_id": "pac-taboola-2026",
  "form_name": "PAC Taboola",
  "api_url": "https://autre-api.com/leads",
  "api_key": "xxx-xxx-xxx",
  "redirect_url": "https://site.com/merci",
  "active": true
}
```

---

## 🔐 Variables d'Environnement

### Backend (.env)
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=leads_db
```

### Frontend (.env)
```
REACT_APP_BACKEND_URL=https://api.tondomaine.com
```

---

## 📋 Template pour Nouveau Formulaire

Quand tu demandes un nouveau formulaire, donne ces infos :

```
=== NOUVEAU FORMULAIRE ===

NOM: [Nom du formulaire]
IDENTIFIANT: [ex: pac-google-2026]

API:
- URL: [URL de l'API destination]
- CLÉ: [Clé API]
- FORMAT: [Lien doc API si différent]

REDIRECTION: [URL page merci après soumission]

BRANDING:
- Nom du site affiché: [ex: MaPrime-PAC.fr]
- Logo droite: [URL image partenaires]
- Message avertissement: [ex: "Réservé aux propriétaires"]

QUESTIONS (cocher obligatoires):
- [ ] Type logement (maison/appartement)
- [ ] Propriétaire/Locataire
- [ ] Facture électricité
- [x] Nom (OBLIGATOIRE)
- [x] Département (OBLIGATOIRE)
- [ ] Email
- [x] Téléphone (OBLIGATOIRE)
- [ ] Autres: ...

SIMULATIONS:
- [ ] Après étape logement
- [x] Après soumission finale
```

---

## 🚀 Commandes Déploiement

### Installer sur serveur Ubuntu :
```bash
# MongoDB
apt install mongodb-org

# Backend
cd /var/www/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001

# Frontend
cd /var/www/frontend
npm install
npm run build
```

---

## 📅 Historique des Formulaires Créés

| Date | Form ID | Nom | API | Status |
|------|---------|-----|-----|--------|
| 2026-02-07 | pv-outbrain-2026 | PV Solaire Outbrain | maison-du-lead.com | ✅ Actif |

---

## ⚠️ Notes Importantes

1. **Les leads sont TOUJOURS sauvegardés en MongoDB** avant envoi API (jamais perdus)
2. **Chaque formulaire a un form_id unique** pour le tracking
3. **Le dashboard /admin** montre tous les formulaires automatiquement
4. **API par défaut** : maison-du-lead.com avec clé 0c21a444-2fc9-412f-9092-658cb6d62de6

---

## 📞 Pour nouvelle conversation

Copie-colle ce message au début de chaque nouvelle conversation :

```
Je reprends le projet de système de formulaires leads.
Voici la doc : [colle le contenu de ce fichier]
Je veux : [ta demande]
```
