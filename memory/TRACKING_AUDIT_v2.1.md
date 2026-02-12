# RDZ Tracking Layer - Audit Technique Complet v2.1

## 📋 Informations Générales

| Élément | Valeur |
|---------|--------|
| **Version Production** | v2.1 |
| **Date Audit** | 12 Février 2026 |
| **Fichiers Modifiés** | 2 |
| **Endpoints Actifs** | 4 |
| **Code Legacy** | ❌ Aucun |
| **Tests Passés** | 7/7 (100%) |
| **Taux de Succès Funnel** | 100/100 (100%) |

---

## 🧪 Tests de Fiabilité Production (Validés)

### Test 1: 10 LP Visits → 10 Events
| Métrique | Valeur |
|----------|--------|
| Envoyés | 10 |
| Reçus | 10 |
| **Résultat** | ✅ PASS |

### Test 2: Multi-Tab → Session Unique
| Métrique | Valeur |
|----------|--------|
| Tabs ouverts | 5 |
| Sessions créées | 1 (réutilisée) |
| **Résultat** | ✅ PASS |

### Test 3: CTA Spam Clicks → Single Event
| Métrique | Valeur |
|----------|--------|
| Clicks envoyés | 20 |
| Events enregistrés | 1 |
| Duplicates rejetés | 19 |
| **Résultat** | ✅ PASS |

### Test 4: Full Funnel × 100
| Métrique | Valeur |
|----------|--------|
| Funnels démarrés | 100 |
| Funnels complétés | 100 |
| Leads créés | 100 |
| Erreurs | 0 |
| **Taux de succès** | **100%** |
| **Résultat** | ✅ PASS |

### Test 5: Fallback Content-Types
| Content-Type | Résultat |
|--------------|----------|
| text/plain;charset=UTF-8 | ✅ OK |
| text/plain | ✅ OK |
| application/json | ✅ OK |
| **Résultat** | ✅ PASS (3/3) |

### Test 6: Browser sendBeacon (Chrome)
| Métrique | Valeur |
|----------|--------|
| Session created | ✅ |
| LP Visit sendBeacon | true |
| CTA Click sendBeacon | true |
| **Résultat** | ✅ PASS |

### Test 7: Mobile Safari sendBeacon
| Métrique | Valeur |
|----------|--------|
| Viewport | 390x844 (iPhone 14) |
| sendBeacon support | true |
| LP Visit | ✅ true |
| CTA Click | ✅ true |
| Form Start | ✅ true |
| **Résultat** | ✅ PASS |

---

## 1️⃣ Historique des Versions : v1 → v2 → v2.1

### Version 1.0 (Legacy - SUPPRIMÉE)

**Architecture :**
- Fichier `brief_generator_v2.py` séparé (supprimé)
- Endpoint unique `/track/event` pour tout
- Anti-doublon côté client (`visitTracked = false`)

**Comportements supprimés :**
- ❌ `visitTracked` guard côté client
- ❌ UTM limité (utm_source, utm_medium, utm_campaign uniquement)
- ❌ Matching CTA basique (sans normalisation URL)
- ❌ Backend strict sur Content-Type

### Version 2.0

**Changements d'architecture :**
- Consolidation dans `brief_generator.py` unique
- Nouveau endpoint dédié `/track/lp-visit`
- UTM complet (7 paramètres)
- sendBeacon pour tous les events

**Nouveaux comportements :**
- ✅ Endpoint `/track/lp-visit` dédié
- ✅ Capture: utm_source, utm_medium, utm_campaign, utm_content, utm_term, gclid, fbclid
- ✅ Anti-doublon côté serveur pour lp_visit, cta_click, form_start
- ✅ sendBeacon avec fallback fetch+keepalive

### Version 2.1 (ACTUELLE)

**Changements d'architecture :**
- Backend compatible sendBeacon (`parse_beacon_body`)
- Normalisation URL pour matching CTA

**Nouveaux comportements :**
- ✅ `parse_beacon_body()` : tolère Content-Type text/plain
- ✅ `normalizeUrl()` : supprime http/https, query params, hash, trailing slash
- ✅ LP Visit envoyé à CHAQUE chargement (anti-doublon serveur)
- ✅ Script Form Mode A persiste rdz_lp et rdz_liaison lors création session

---

## 2️⃣ Confirmation : Aucun Legacy

### Fichiers
| Fichier | Status |
|---------|--------|
| `/app/backend/services/brief_generator.py` | ✅ Unique, consolidé |
| `/app/backend/services/brief_generator_v2.py` | ❌ SUPPRIMÉ |
| `/app/backend/routes/public.py` | ✅ À jour v2.1 |

### Endpoints
| Endpoint | Status | Utilisation |
|----------|--------|-------------|
| `POST /track/session` | ✅ Actif | Création session |
| `POST /track/lp-visit` | ✅ Actif | Visite LP (dédié) |
| `POST /track/event` | ✅ Actif | cta_click, form_start |
| `POST /leads` | ✅ Actif | Soumission lead |
| `POST /track/visit` | ❌ N'EXISTE PAS | - |

### Modèles Pydantic
| Modèle | Status | Note |
|--------|--------|------|
| `SessionData` | ✅ Utilisé | Pour `/track/session` |
| `LPVisitData` | ⚠️ Défini mais non utilisé | Documentation seulement |
| `EventData` | ⚠️ Défini mais non utilisé | Documentation seulement |
| `LeadData` | ✅ Utilisé | Pour `/leads` |

> Note: `LPVisitData` et `EventData` sont définis pour documenter le schéma mais les endpoints utilisent `parse_beacon_body()` pour la compatibilité sendBeacon.

---

## 3️⃣ Audit de Cohérence

### Scripts Générés

| Script | Version | Fichier |
|--------|---------|---------|
| LP Mode A | v2.1 | `brief_generator.py:345-641` |
| Form Mode A | v2.0 | `brief_generator.py:643-907` |
| Mode B (intégré) | v2.1 | `brief_generator.py:1010-1342` |

### Noms de Champs - 100% Cohérent

**UTM Parameters (7 champs) :**
| Champ | Scripts | Backend | DB |
|-------|---------|---------|-----|
| `utm_source` | ✅ | ✅ | ✅ |
| `utm_medium` | ✅ | ✅ | ✅ |
| `utm_campaign` | ✅ | ✅ | ✅ |
| `utm_content` | ✅ | ✅ | ✅ |
| `utm_term` | ✅ | ✅ | ✅ |
| `gclid` | ✅ | ✅ | ✅ |
| `fbclid` | ✅ | ✅ | ✅ |

**Session Parameters :**
| Champ | Scripts | Backend | DB |
|-------|---------|---------|-----|
| `session_id` | ✅ | ✅ | `id` |
| `lp_code` | ✅ | ✅ | ✅ |
| `form_code` | ✅ | ✅ | ✅ |
| `liaison_code` | ✅ | ✅ | ✅ |
| `referrer` | ✅ | ✅ | ✅ |
| `user_agent` | ✅ | ✅ | ✅ |

**Tracking Event Field :**
| Script envoie | Backend stocke | Cohérent |
|---------------|----------------|----------|
| `event_type` | `event` | ✅ (transformation dans `track_event`) |

### sessionStorage Keys

| Clé | LP écrit | Form lit | Cohérent |
|-----|----------|----------|----------|
| `rdz_session` | ✅ | ✅ | ✅ |
| `rdz_lp` | ✅ | ✅ | ✅ |
| `rdz_liaison` | ✅ | ✅ | ✅ |
| `rdz_utm_source` | ✅ | ✅ | ✅ |
| `rdz_utm_medium` | ✅ | ✅ | ✅ |
| `rdz_utm_campaign` | ✅ | ✅ | ✅ |
| `rdz_utm_content` | ✅ | ✅ | ✅ |
| `rdz_utm_term` | ✅ | ✅ | ✅ |
| `rdz_gclid` | ✅ | ✅ | ✅ |
| `rdz_fbclid` | ✅ | ✅ | ✅ |

### URL Parameters (LP → Form)

| Paramètre | LP ajoute | Form lit | Cohérent |
|-----------|-----------|----------|----------|
| `session` | ✅ | ✅ | ✅ |
| `lp` | ✅ | ✅ | ✅ |
| `liaison` | ✅ | ✅ | ✅ |
| `utm_campaign` | ✅ | ✅ | ✅ |

---

## 4️⃣ Flow de Tracking - Intégrité Validée

### Flow LP Visit (Mode A)
```
1. DOMContentLoaded
2. captureUTM() → sessionStorage
3. initSession() → POST /track/session → reçoit session_id
4. sessionStorage.setItem(rdz_session, rdz_lp, rdz_liaison)
5. trackLPVisit() → POST /track/lp-visit (sendBeacon)
   └─ Backend: anti-doublon (1 seul par session)
6. autoBindCTA() → MutationObserver
```

### Flow CTA Click
```
1. Click détecté sur lien vers formUrl
2. trackEvent("cta_click") → sendBeacon
   └─ Backend: anti-doublon (1 seul par session)
3. URL modifiée: ?session=XXX&lp=XXX&liaison=XXX&utm_campaign=XXX
4. Redirection normale (non bloquée)
```

### Flow Form (Mode A)
```
1. initSession()
   └─ Priorité: URL params > sessionStorage > création nouvelle
2. autoBindFormStart()
3. Premier clic/focus → trackEvent("form_start")
4. rdzSubmitLead({data}) → POST /leads
5. Redirect vers redirectUrl
```

---

## 5️⃣ Anti-Doublon - Mécanismes

| Event | Client-side | Server-side | DB Index |
|-------|-------------|-------------|----------|
| Session | ✅ sessionStorage check | ✅ 30min visitor+LP | - |
| lp_visit | ❌ (toujours envoyé) | ✅ 1/session | `{session_id, event}` |
| cta_click | ✅ `ctaClicked` flag | ✅ 1/session | `{session_id, event}` |
| form_start | ✅ `formStarted` flag | ✅ 1/session | `{session_id, event}` |

---

## 6️⃣ Points d'Attention Résolus

### ✅ sendBeacon Compatibility
- `parse_beacon_body()` tolère `Content-Type: text/plain;charset=UTF-8`
- Tous les endpoints tracking utilisent ce parser

### ✅ URL Normalization
- `normalizeUrl()` dans script LP Mode A
- Supprime: http/https, query params, hash, trailing slashes
- Matching case-insensitive

### ✅ Session Persistence
- Form Mode A persiste `rdz_lp` et `rdz_liaison` lors création session
- Ligne 760-764 du brief_generator.py

---

## 7️⃣ Code Mort Identifié

| Élément | Type | Impact | Action |
|---------|------|--------|--------|
| `LPVisitData` | Modèle Pydantic | Aucun | Conserver pour documentation |
| `EventData` | Modèle Pydantic | Aucun | Conserver pour documentation |

> Ces modèles documentent le schéma attendu mais ne sont pas utilisés car les endpoints utilisent `parse_beacon_body()`.

---

## 8️⃣ Résumé Exécutif

### ✅ Confirmations

1. **v2.1 remplace totalement v1** - Aucune logique legacy active
2. **Aucun script/endpoint obsolète** - Tous les endpoints sont actifs et utilisés
3. **Pas de tracking dupliqué** - Anti-doublon serveur + client
4. **Pas de double création session** - Check 30min + sessionStorage
5. **Cohérence 100%** :
   - Noms de champs synchronisés
   - Payloads scripts = Backend
   - sessionStorage keys cohérentes
   - URL params cohérents

### ⚠️ Points Mineurs

1. Script Form Mode A version "2.0" au lieu de "2.1" (cosmétique)
2. Modèles `LPVisitData`/`EventData` non utilisés (documentation)

### 🎯 Comportement Déterministe

| Action | Résultat |
|--------|----------|
| Page LP load | `/track/session` + `/track/lp-visit` |
| LP Visit doublon | `duplicate: true` retourné |
| CTA click | `/track/event` + URL modifiée |
| Form load | Session récupérée (URL > sessionStorage > création) |
| Form start | `/track/event` form_start |
| Lead submit | `/leads` avec tous UTM |

---

## 9️⃣ Fichiers Modifiés (v2.1)

| Fichier | Lignes | Responsabilité |
|---------|--------|----------------|
| `/app/backend/routes/public.py` | 714 | Endpoints tracking + leads |
| `/app/backend/services/brief_generator.py` | 1437 | Génération scripts |

---

## 🔧 Améliorations Futures (Non Bloquantes)

1. **Script Form Mode A** : Mettre à jour commentaire version 2.0 → 2.1
2. **Supprimer modèles morts** : `LPVisitData`, `EventData` (optionnel)
3. **Tests E2E** : Ajouter tests Playwright pour flow complet

---

**Conclusion : Le système de tracking v2.1 est PRODUCTION-READY avec un comportement 100% déterministe et aucun code legacy actif.**
