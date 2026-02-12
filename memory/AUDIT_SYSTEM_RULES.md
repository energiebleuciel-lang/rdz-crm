# 🔍 AUDIT COMPLET - RÈGLES SYSTÈME RDZ

**Date**: 12 février 2026  
**Version**: 2.2 (mise à jour)  
**Objectif**: Documenter toutes les règles métier effectives du système RDZ

---

## 📋 1. AUDIT RÈGLES DOUBLONS

### 1.1 Architecture de détection (v2.2)

**✅ MISE À JOUR v2.2**: Le système RDZ dispose maintenant d'une **détection de doublons interne** en plus de la détection CRM externe.

| Couche | Détection | Critères | Comportement |
|--------|-----------|----------|--------------|
| **RDZ interne (v2.2)** | ✅ Oui | phone + dept + 30 jours | Bloque l'envoi CRM, marque le statut |
| CRM externe (ZR7/MDL) | ✅ Oui | phone (selon leur config) | Retourne "doublon" si existe |

### 1.2 Champs utilisés pour détection RDZ interne

```
Source: /app/backend/services/duplicate_detector.py
```

| Critère | Valeur | Description |
|---------|--------|-------------|
| **Téléphone** | Exact | Numéro normalisé (format français 10 chiffres) |
| **Département** | Exact | Code département (01-95, 2A, 2B) |
| **Fenêtre** | 30 jours | `DUPLICATE_WINDOW_DAYS = 30` |

### 1.3 Fenêtre de temps

**RDZ interne** : 30 jours (configurable via `DUPLICATE_WINDOW_DAYS`)  
**CRM externe** : Définie par le CRM (généralement 30 jours aussi)

### 1.4 Statuts liés aux doublons (v2.2)

| Statut | Détecté par | Signification | Livrable? |
|--------|-------------|---------------|-----------|
| `doublon_recent` | **RDZ interne** | Lead existant déjà livré | ❌ Non |
| `non_livre` | **RDZ interne** | Lead existant non livré | ❌ Non (original redistribuable) |
| `double_submit` | **RDZ interne** | Double-clic (< 5 sec) | ❌ Non |
| `duplicate` | CRM externe | CRM a détecté un doublon | ✅ Oui (déjà envoyé) |

### 1.5 Comportement de détection (v2.2)

**Ordre de vérification** :
1. **Double-submit** : Même session + phone dans les 5 dernières secondes
2. **Doublon récent** : Même phone + dept, déjà livré dans les 30 jours
3. **Non livré** : Même phone + dept, existe mais non livré

**Si doublon détecté** :
- Lead **créé dans RDZ** (toujours, pour traçabilité)
- Lead **non envoyé** au CRM externe
- Flags ajoutés : `is_internal_duplicate`, `duplicate_type`, `original_lead_id`

### 1.6 Protection contre livraison doublon

**Double protection** :
1. **RDZ interne (v2.2)** : Bloque l'envoi AVANT appel CRM → Économie d'appels API
2. **CRM externe** : Dernière ligne de défense si le doublon passe

### 1.7 ✅ IMPLÉMENTÉ v2.2

La détection de doublons interne est maintenant active. Voir documentation complète :
`/app/memory/DUPLICATE_DETECTION_v2.2.md`

---

## 📋 2. AUDIT ROUTING / LIVRAISON CRM

### 2.1 Décision de routing

```
Source: /app/backend/routes/public.py (lignes 448-504)
```

**Moment de la décision** : À la création du lead (POST /api/public/leads)

**Algorithme de routing** :

```
1. Vérifier si le formulaire a target_crm ET crm_api_key
   → SI OUI: Chercher commande active pour ce CRM
   → SI NON: status = "no_crm" ou "no_api_key"

2. SI commande trouvée pour CRM principal:
   → final_crm = target_crm
   → routing_reason = "commande_{crm_slug}"

3. SI pas de commande ET allow_cross_crm = True:
   → Chercher commande sur l'autre CRM
   → SI trouvée ET clé API disponible:
      → final_crm = autre_crm
      → is_transferred = True
      → routing_reason = "cross_crm_{slug}"

4. SI toujours pas de CRM:
   → status = "pending_no_order"
   → Lead sauvegardé, en attente de redistribution
```

### 2.2 Conditions qui bloquent la livraison

| Condition | Statut assigné | Lead créé? | Comportement |
|-----------|----------------|------------|--------------|
| Phone invalide | `invalid_phone` | ✅ Oui | Lead créé mais non envoyé |
| Nom manquant | `missing_required` | ✅ Oui | Lead créé mais non envoyé |
| Département manquant | `missing_required` | ✅ Oui | Lead créé mais non envoyé |
| Formulaire non trouvé | `orphan` | ✅ Oui | Lead créé mais non envoyé |
| CRM non configuré | `no_crm` | ✅ Oui | Lead créé mais non envoyé |
| Clé API manquante | `no_api_key` | ✅ Oui | Lead créé mais non envoyé |
| Pas de commande active | `pending_no_order` | ✅ Oui | Lead créé, en attente |

**RÈGLE ABSOLUE** : Le lead est **TOUJOURS** créé dans RDZ, peu importe les erreurs.

### 2.3 Mapping des champs envoyés aux CRMs

```
Source: /app/backend/services/lead_sender.py (lignes 64-89)
```

| Champ RDZ | Champ CRM | Requis? |
|-----------|-----------|---------|
| `phone` | `phone` | ✅ Oui |
| `nom` | `nom` | ✅ Oui |
| `prenom` | `prenom` | Non |
| `email` | `email` | Non |
| `civilite` | `civilite` | Non |
| `register_date` | `register_date` | ✅ Oui (timestamp) |
| `departement` | `custom_fields.departement` | Non |
| `ville` | `custom_fields.ville` | Non |
| `adresse` | `custom_fields.adresse` | Non |
| `type_logement` | `custom_fields.type_logement` | Non |
| `statut_occupant` | `custom_fields.statut_occupant` | Non |
| `surface_habitable` | `custom_fields.superficie_logement` | Non |
| `type_chauffage` | `custom_fields.chauffage_actuel` | Non |
| `facture_electricite` | `custom_fields.facture_electricite` | Non |
| `facture_chauffage` | `custom_fields.facture_chauffage` | Non |
| `type_projet` | `custom_fields.type_projet` | Non |
| `delai_projet` | `custom_fields.delai_projet` | Non |
| `budget` | `custom_fields.budget` | Non |
| `product_type` | `custom_fields.product_type` | Non |
| `lp_code` | `custom_fields.lp_code` | Non |
| `liaison_code` | `custom_fields.liaison_code` | Non |
| `utm_source` | `custom_fields.utm_source` | Non |
| `utm_medium` | `custom_fields.utm_medium` | Non |
| `utm_campaign` | `custom_fields.utm_campaign` | Non |

### 2.4 Vérification de livraison (Logs/Preuves)

**Champs de preuve dans le lead** :

| Champ | Description |
|-------|-------------|
| `api_status` | Statut final (success, failed, duplicate, etc.) |
| `sent_to_crm` | Boolean - True si envoyé avec succès |
| `sent_at` | Timestamp de l'envoi |
| `target_crm` | Slug du CRM de destination |
| `routing_reason` | Raison du routing (commande_zr7, cross_crm_mdl, etc.) |
| `api_response` | Réponse du CRM (en cas d'erreur) |
| `retry_count` | Nombre de tentatives |

**Requête pour vérifier la livraison** :
```python
lead = await db.leads.find_one({"id": lead_id})
if lead["api_status"] == "success" and lead["sent_to_crm"]:
    print(f"Livré à {lead['target_crm']} le {lead['sent_at']}")
```

---

## 📋 3. AUDIT STATUTS & LIFECYCLE LEAD

### 3.1 Liste complète des statuts

```
Source: /app/backend/schema_locked.py (ligne 334)
```

| Statut | Signification | Qui l'assigne | Transition possible vers |
|--------|---------------|---------------|-------------------------|
| `pending` | En cours de traitement | Backend | success, failed, queued |
| `success` | Livré avec succès | CRM externe | (final) |
| `failed` | Échec de livraison | Backend/CRM | queued, success (retry) |
| `duplicate` | Doublon détecté | CRM externe | (final) |
| `queued` | En file d'attente | Backend | success, failed, exhausted |
| `no_crm` | CRM non configuré | Backend | pending (si config ajoutée) |
| `no_api_key` | Clé API manquante | Backend | pending (si clé ajoutée) |
| `orphan` | Formulaire non trouvé | Backend | (nécessite correction manuelle) |
| `invalid_phone` | Téléphone invalide | Backend | (nécessite correction manuelle) |
| `missing_required` | Champs obligatoires manquants | Backend | (nécessite correction manuelle) |
| `pending_no_order` | Pas de commande active | Backend | success (auto-redistribution) |
| `pending_manual` | Trop vieux pour auto-redistribution | Scheduler | success (redistribution manuelle) |
| `validation_error` | Rejeté par CRM (validation) | CRM externe | (nécessite correction) |
| `auth_error` | Erreur d'authentification CRM | CRM externe | (nécessite correction clé) |
| `server_error` | Erreur serveur CRM | CRM externe | queued (retry auto) |
| `timeout` | Timeout de l'API CRM | Backend | queued (retry auto) |
| `connection_error` | Erreur de connexion | Backend | queued (retry auto) |

### 3.2 Transitions de statuts

```
                    ┌──────────────────┐
                    │      CRÉATION    │
                    └────────┬─────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
   ┌─────────┐         ┌──────────┐         ┌──────────┐
   │ pending │         │ no_crm   │         │ orphan   │
   └────┬────┘         │ no_api_  │         │invalid_  │
        │              │ key      │         │ phone    │
        │              │pending_  │         │missing_  │
        │              │no_order  │         │ required │
        │              └──────────┘         └──────────┘
        │                    │                    
        ▼                    ▼                    
   ┌─────────┐         ┌───────────┐              
   │   CRM   │◄────────│ Auto/Man  │              
   │  ENVOI  │         │  Redistr. │              
   └────┬────┘         └───────────┘              
        │                                        
   ┌────┴────┬────────────┬───────────┐
   │         │            │           │
   ▼         ▼            ▼           ▼
┌───────┐ ┌────────┐ ┌─────────┐ ┌────────┐
│success│ │duplicate│ │ queued  │ │ failed │
└───────┘ └────────┘ └────┬────┘ └────────┘
                          │
                          ▼
                   ┌────────────┐
                   │ retry (5x) │
                   └──────┬─────┘
                          │
              ┌───────────┴───────────┐
              │                       │
              ▼                       ▼
         ┌─────────┐            ┌───────────┐
         │ success │            │ exhausted │
         └─────────┘            └───────────┘
```

### 3.3 Leads sans commande (conservation)

```
Source: /app/backend/routes/public.py (ligne 502)
```

**Comportement** :
1. Lead créé avec `api_status: "pending_no_order"`
2. Lead conservé indéfiniment dans RDZ
3. Flag `manual_only: False` (éligible auto-redistribution)
4. Si commande s'active dans les 8 jours → Auto-redistribution
5. Après 8 jours → Marqué `manual_only: True`, `api_status: "pending_manual"`

---

## 📋 4. AUDIT REDISTRIBUTION & SCHEDULER

### 4.1 Règles de redistribution automatique

```
Source: /app/backend/services/lead_redistributor.py
```

**Seuil** : `DAYS_AUTO_REDISTRIBUTION = 8` jours

| Âge du lead | Redistribution | Statut |
|-------------|----------------|--------|
| < 8 jours | ✅ Automatique | `pending_no_order` |
| ≥ 8 jours | ❌ Manuelle uniquement | `pending_manual` |

**Déclencheur auto-redistribution** :
- Quand une commande passe de `active: false` à `active: true`
- Le système cherche automatiquement les leads éligibles

```
Source: /app/backend/routes/commandes.py (ligne 125-129)
```

```python
if data.active:
    from services.lead_redistributor import redistribute_leads_for_command
    redistrib_result = await redistribute_leads_for_command(commande)
```

### 4.2 Job `mark_old_leads_as_manual_only`

```
Source: /app/backend/services/lead_redistributor.py (lignes 185-212)
Source: /app/backend/server.py (lignes 90-98)
```

**Configuration** :
- Fréquence : Tous les jours à **4h UTC**
- Critères :
  - `api_status == "pending_no_order"`
  - `manual_only != True`
  - `created_at < (now - 8 jours)`

**Action** :
```python
await db.leads.update_many(
    {...},
    {"$set": {
        "manual_only": True,
        "api_status": "pending_manual",
        "manual_only_at": now_iso()
    }}
)
```

### 4.3 Protection contre redistribution non souhaitée

**Mécanismes de protection** :

1. **Clé de redistribution** : Les redistributions inter-CRM utilisent des clés API spéciales configurées dans `system_config.redistribution_keys`
2. **Vérification commande** : `has_commande()` vérifie qu'une commande active existe
3. **Flag manual_only** : Les leads > 8 jours ne sont jamais auto-redistribués
4. **Logs** : Toutes les redistributions sont loggées avec `distribution_reason`

---

## 📋 5. AUDIT UI / CRÉATION FORMULAIRE

### 5.1 Valeurs auto-configurées à la création

```
Source: /app/backend/routes/lps.py (lignes 130-205)
```

**Création LP + Form (duo obligatoire)** :

| Champ | Auto-configuré? | Valeur par défaut |
|-------|-----------------|-------------------|
| `lp.code` | ✅ Oui | `LP-XXX` (auto-incrémenté) |
| `form.code` | ✅ Oui | `{PRODUCT}-XXX` (ex: PV-001) |
| `liaison_code` | ✅ Oui | `{lp_code}_{form_code}` |
| `lp.status` | ✅ Oui | `"active"` |
| `form.status` | ✅ Oui | `"active"` |
| `form.lp_id` | ✅ Oui | Lié automatiquement |
| `lp.form_id` | ✅ Oui | Lié automatiquement |
| `tracking_type` | ✅ Oui | `"redirect"` |
| `redirect_url` | ✅ Oui | `"/merci"` |
| `allow_cross_crm` | ✅ Oui | `True` |

### 5.2 Champs obligatoires (création LP)

```
Source: /app/backend/models.py - LPCreate
```

| Champ | Requis | Description |
|-------|--------|-------------|
| `name` | ✅ Oui | Nom de la LP |
| `url` | ✅ Oui | URL de la landing page |
| `account_id` | ✅ Oui | ID du compte |
| `product_type` | ✅ Oui | PV, PAC ou ITE |

### 5.3 Validations backend

```
Source: /app/backend/routes/forms.py (lignes 353-365)
Source: /app/backend/routes/lps.py (lignes 234-245)
```

| Validation | Fichier | Ligne | Comportement |
|------------|---------|-------|--------------|
| Form sans LP interdit | forms.py | 361-365 | HTTP 400 |
| Dissociation LP↔Form interdite | forms.py | 437-440 | HTTP 400 |
| Suppression clé API interdite | forms.py | 471-477 | HTTP 400 |
| Compte inexistant | lps.py | 137-139 | HTTP 400 |

### 5.4 Garde-fous API directe

**Protections contre contournement UI** :

1. **Création Form standalone** :
```python
if not data.lp_id:
    raise HTTPException(status_code=400, 
        detail="Un formulaire doit obligatoirement être lié à une Landing Page.")
```

2. **Dissociation Form de LP** :
```python
if data.lp_id is not None and data.lp_id == "":
    raise HTTPException(status_code=400, 
        detail="Impossible de dissocier un formulaire de sa Landing Page.")
```

3. **Suppression clé API** :
```python
if existing_api_key and data.crm_api_key == "":
    raise HTTPException(status_code=400, 
        detail="Impossible de supprimer la clé API une fois enregistrée.")
```

---

## 📋 6. EXEMPLES CONCRETS DE CAS

### 6.1 Cas : Doublon récent (< 30 jours CRM)

```
Scénario: Lead téléphone 0612345678 soumis 2 fois en 1 semaine

1. Premier lead soumis:
   - Créé dans RDZ (ID: lead-001)
   - Envoyé à ZR7
   - ZR7 retourne: 201 Created
   - RDZ stocke: api_status="success", sent_to_crm=True

2. Deuxième lead soumis (même téléphone):
   - Créé dans RDZ (ID: lead-002) ← Lead distinct créé!
   - Envoyé à ZR7
   - ZR7 retourne: 200 "doublon"
   - RDZ stocke: api_status="duplicate", sent_to_crm=True
   
Résultat: 2 leads dans RDZ, 1 seul accepté par ZR7
```

### 6.2 Cas : Doublon hors fenêtre (> 30 jours CRM)

```
Scénario: Lead téléphone 0612345678 soumis après 2 mois

1. Premier lead (il y a 2 mois):
   - api_status="success"

2. Nouveau lead (aujourd'hui, même téléphone):
   - Créé dans RDZ (nouvel ID)
   - Envoyé à ZR7
   - ZR7 accepte (hors fenêtre doublon)
   - api_status="success"

Résultat: 2 leads distincts, tous deux livrés
```

### 6.3 Cas : Lead sans commande active

```
Scénario: Lead soumis mais pas de commande ZR7 pour ce département

1. Lead soumis (form avec target_crm="zr7", dept="75"):
   - Créé dans RDZ
   - has_commande("zr7", "PV", "75") → False
   - api_status="pending_no_order"
   - manual_only=False
   
2. Jour 3: Commande ZR7 activée pour dept 75:
   - Trigger: redistribute_leads_for_command()
   - Lead trouvé (age < 8j, status=pending_no_order)
   - Envoyé à ZR7
   - api_status="success", distribution_reason="auto_redistribution"

3. Alternative - Jour 10: Si commande activée après 8j:
   - Lead marqué manual_only=True
   - Pas d'auto-redistribution
   - Admin doit utiliser force_send()
```

### 6.4 Cas : Lead sans téléphone valide

```
Scénario: Téléphone "abc123" soumis

1. Lead soumis:
   - validate_phone_fr("abc123") → (False, "Format invalide")
   - Lead créé avec phone="abc123", phone_invalid=True
   - api_status="invalid_phone"
   - sent_to_crm=False

Résultat: Lead conservé mais non envoyé au CRM
```

### 6.5 Cas : Formulaire sans CRM configuré

```
Scénario: Form PV-099 sans target_crm ni crm_api_key

1. Lead soumis:
   - Form trouvé mais target_crm=""
   - api_status="no_crm"
   - distribution_reason="CRM_NOT_CONFIGURED"

Résultat: Lead conservé, en attente de configuration
```

---

## 📋 7. TESTS E2E RECOMMANDÉS

### 7.1 Checklist de tests

| Test | Description | Priorité |
|------|-------------|----------|
| ✅ Happy Path ZR7 | LP → CTA → Form → Submit → ZR7 → success | P0 |
| ✅ Happy Path MDL | LP → CTA → Form → Submit → MDL → success | P0 |
| ⏳ Doublon | Soumettre même téléphone 2x → 2ème = duplicate | P0 |
| ⏳ Phone invalide | Soumettre phone "abc" → invalid_phone | P1 |
| ⏳ Sans commande | Désactiver commande → pending_no_order | P1 |
| ⏳ Auto-redistribution | Activer commande → lead redistribué | P1 |
| ⏳ Manual only | Lead > 8j → Scheduler → pending_manual | P2 |
| ⏳ Cross-CRM | Config cross → Fallback vers autre CRM | P1 |
| ⏳ Retry queue | Simuler erreur serveur → queued → retry | P2 |

### 7.2 Script de test E2E complet

```bash
# Test 1: Happy Path ZR7
curl -X POST "$API/api/public/leads" -H "Content-Type: application/json" \
  -d '{"session_id":"test","form_code":"PV-006","phone":"0612345678","nom":"Test","departement":"75"}'
# Attendu: status=success, crm=zr7

# Test 2: Doublon
curl -X POST "$API/api/public/leads" -H "Content-Type: application/json" \
  -d '{"session_id":"test2","form_code":"PV-006","phone":"0612345678","nom":"Test2","departement":"75"}'
# Attendu: status=duplicate

# Test 3: Phone invalide
curl -X POST "$API/api/public/leads" -H "Content-Type: application/json" \
  -d '{"session_id":"test3","form_code":"PV-006","phone":"invalid","nom":"Test3","departement":"75"}'
# Attendu: status=invalid_phone, warning=PHONE_INVALID

# Test 4: Sans département
curl -X POST "$API/api/public/leads" -H "Content-Type: application/json" \
  -d '{"session_id":"test4","form_code":"PV-006","phone":"0698765432","nom":"Test4"}'
# Attendu: status=missing_required, warning=MISSING_REQUIRED
```

---

## 📋 8. FICHIERS DE RÉFÉRENCE

| Règle | Fichier | Lignes |
|-------|---------|--------|
| Routing leads | `/app/backend/routes/public.py` | 379-691 |
| Envoi CRM | `/app/backend/services/lead_sender.py` | 38-172 |
| Commandes | `/app/backend/routes/commandes.py` | 62-89 |
| Redistribution | `/app/backend/services/lead_redistributor.py` | 89-212 |
| Scheduler | `/app/backend/server.py` | 64-104 |
| Validation LP/Form | `/app/backend/routes/forms.py` | 353-489 |
| Création LP+Form | `/app/backend/routes/lps.py` | 130-205 |

---

## 📋 9. RECOMMANDATIONS

### 9.1 Améliorations prioritaires

1. **⚠️ CRITIQUE**: Implémenter détection de doublons interne RDZ
   - Critères: `phone + departement + product_type + fenêtre 30 jours`
   - Éviter création de leads dupliqués avant envoi CRM

2. **Ajouter index MongoDB** pour performance doublons:
   ```python
   await db.leads.create_index([("phone", 1), ("departement", 1), ("product_type", 1), ("created_at", -1)])
   ```

3. **Logging amélioré** pour traçabilité complète

### 9.2 Points de vigilance

1. Le formulaire DOIT avoir `target_crm` ET `crm_api_key` pour envoyer
2. Les leads sont TOUJOURS créés dans RDZ, même en erreur
3. La redistribution auto ne fonctionne que < 8 jours
4. Les clés de redistribution sont séparées des clés formulaires

---

**Document créé le**: 12 février 2026  
**Auteur**: Agent E1  
**Validé par**: En attente validation utilisateur
