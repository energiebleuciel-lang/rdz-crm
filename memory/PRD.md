# RDZ CRM - Product Requirements Document

## 🔒 STANDARDS PERMANENTS (À RESPECTER POUR TOUTES LES ÉVOLUTIONS)

### 1. UI - Simplicité Maximale
```
╔══════════════════════════════════════════════════════════════════════════════╗
║  RÈGLE UI                                                                    ║
║                                                                              ║
║  • Toujours simplifier au maximum l'interface                               ║
║  • Création LP + Form : automatique, rapide, en quelques clics              ║
║  • Zéro configuration technique visible                                      ║
║  • Zéro champ inutile                                                        ║
║  • Objectif : utilisation la plus simple possible                           ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### 2. Tracking & Versioning - Une Seule Version
```
╔══════════════════════════════════════════════════════════════════════════════╗
║  RÈGLE VERSIONING                                                            ║
║                                                                              ║
║  • Une seule version active (actuellement v2.1)                              ║
║  • Aucun code legacy conservé                                                ║
║  • Aucun ancien script ou endpoint                                           ║
║  • JAMAIS plusieurs versions en parallèle                                    ║
║  • Objectif : une seule source, zéro risque                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### 3. Tests E2E Obligatoires - Avant Chaque Mise en Production
```
╔══════════════════════════════════════════════════════════════════════════════╗
║  RÈGLE TESTS                                                                 ║
║                                                                              ║
║  À chaque modification, test complet du flux :                               ║
║  LP → Session → CTA → Form → Submit → Backend → CRM → Routing → Livraison   ║
║                                                                              ║
║  Confirmer systématiquement :                                                ║
║  • 0 perte de données                                                        ║
║  • 0 doublon                                                                 ║
║  • 0 champ manquant                                                          ║
║  • 0 incohérence                                                             ║
║  • 100% des leads reçus correctement                                         ║
║                                                                              ║
║  Objectif : cohérence totale avant production                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### 4. Liaison LP ↔ Form - Obligatoire
```
╔══════════════════════════════════════════════════════════════════════════════╗
║  RÈGLE LIAISON                                                               ║
║                                                                              ║
║  • Une LP doit TOUJOURS être liée à un Form                                  ║
║  • Un Form doit TOUJOURS avoir une LP                                        ║
║  • Pas de Form standalone                                                    ║
║  • Pas de LP sans Form                                                       ║
║  • Lien non supprimable une fois créé                                        ║
║                                                                              ║
║  Objectif : zéro lead orphelin, attribution parfaite                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## Description
CRM multi-tenant pour la gestion et distribution de leads vers ZR7 Digital et Maison du Lead (MDL).

## Architecture

### Flux Principal
```
Visiteur → LP → Form → RDZ (collecte) → ZR7 ou MDL (distribution)
```

## RÈGLE ABSOLUE : Lead TOUJOURS sauvegardé dans RDZ

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  🔐 PRINCIPE FONDAMENTAL                                                      ║
║                                                                              ║
║  TOUT lead soumis est TOUJOURS créé dans RDZ, peu importe les erreurs :      ║
║  - Formulaire non trouvé → lead "orphelin"                                   ║
║  - Téléphone invalide → lead avec flag "phone_invalid"                       ║
║  - Clé API manquante → lead "no_api_key"                                     ║
║  - CRM non configuré → lead "no_crm"                                         ║
║  - Pas de commande → lead "pending_no_order"                                 ║
║                                                                              ║
║  Le visiteur voit TOUJOURS une redirection normale (success: true)           ║
║  L'admin peut TOUJOURS "Forcer envoi" plus tard                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

## Statuts de Lead (api_status)

| Statut | Description | Badge UI | Action admin |
|--------|-------------|----------|--------------|
| `success` | Envoyé au CRM | ✅ Vert | - |
| `duplicate` | Doublon CRM | ⚠️ Orange | - |
| `queued` | En file d'attente | 🔵 Bleu | Automatique |
| `failed` | Erreur d'envoi | ❌ Rouge | Forcer envoi |
| `no_crm` | CRM non configuré | ⚪ Gris | Configurer CRM |
| `no_api_key` | Clé API manquante | ⚠️ Jaune | Forcer envoi |
| `orphan` | Formulaire non trouvé | ❌ Rouge | Audit |
| `invalid_phone` | Téléphone invalide | ❌ Rouge | Éditer + Forcer |
| `pending_no_order` | Pas de commande (<8j) | ⚠️ Orange | Auto-redistribution |
| `pending_manual` | Pas de commande (>8j) | 🔵 Bleu | Redistribution manuelle |

## Flags de diagnostic (sur chaque lead)

```json
{
  "phone_invalid": true/false,    // Téléphone non valide (format FR)
  "form_not_found": true/false,   // Formulaire non trouvé en DB
  "distribution_reason": "..."    // Raison détaillée du statut
}
```

## API Réponses POST /api/public/leads

**Réponse TOUJOURS `success: true` + `stored: true`** (sauf erreur serveur)

```json
// Cas normal
{"success": true, "lead_id": "...", "status": "success", "crm": "zr7"}

// Clé API manquante
{"success": true, "lead_id": "...", "status": "no_api_key", "warning": "API_KEY_MISSING", "stored": true}

// Formulaire non trouvé
{"success": true, "lead_id": "...", "status": "orphan", "warning": "FORM_NOT_FOUND", "stored": true}

// Téléphone invalide
{"success": true, "lead_id": "...", "status": "invalid_phone", "warning": "PHONE_INVALID", "stored": true}
```

## Scripts LP & Formulaire - RDZ Tracking Layer v2.0

### Endpoints de Tracking
| Endpoint | Méthode | Description | Anti-doublon |
|----------|---------|-------------|--------------|
| `/api/public/track/session` | POST | Création session visiteur | ✅ 30min |
| `/api/public/track/lp-visit` | POST | Visite LP avec UTM complet | ✅ 1/session |
| `/api/public/track/event` | POST | Events (cta_click, form_start) | ✅ 1/session |
| `/api/public/leads` | POST | Soumission lead | - |

### Paramètres UTM Capturés
- `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term`
- `gclid` (Google Click ID)
- `fbclid` (Facebook Click ID)
- `referrer`, `user_agent`

### Fonctionnalités du Script LP (v2.0)
1. **Session Initialization** : Création/réutilisation session avec anti-doublon
2. **LP Visit Tracking** : Endpoint dédié `/track/lp-visit` avec UTM complet
3. **Campaign Capture** : URL > sessionStorage, persistance toute la session
4. **CTA Click Tracking** : sendBeacon + injection params URL (`?session=...&lp=...&liaison=...&utm_campaign=...`)
5. **Auto Binding** : Détection automatique liens vers form, MutationObserver pour CTA dynamiques
6. **Reliability** : sendBeacon prioritaire, fail silently, keepalive, ne bloque jamais la redirection

### Script Form (Mode A)
- Récupération session depuis URL (`?session=`) ou sessionStorage
- Tracking form_start au premier clic/focus
- Soumission lead avec `rdzSubmitLead({data})`

**Le visiteur ne voit JAMAIS d'erreur** - il est toujours redirigé.

## Fonctionnalités Admin

### Actions sur Leads
- **Voir** : Détails complets du lead
- **Éditer** : Modifier phone, email, nom, departement, notes_admin
- **Forcer envoi** : Envoyer vers ZR7 ou MDL (utilise clés redistribution)
- **Supprimer** : Suppression définitive

### Actions de Masse
- Sélection multiple via checkboxes
- Édition masse
- Suppression masse
- Envoi masse vers CRM

### Reset Stats Formulaire
- Remet les compteurs à zéro
- Les leads ne sont PAS supprimés
- Snapshot créé avant reset

## Scheduler (APScheduler)
- **3h UTC** : Vérification nocturne
- **4h UTC** : Marquage leads > 8 jours comme `pending_manual`
- **5 min** : Traitement file d'attente

## 🔒 SCHEMA VERROUILLÉ

Champs obligatoires normalisés (NE PAS MODIFIER) :
- `departement` (pas "code_postal", pas "department")
- `target_crm` (slug: "zr7" ou "mdl")
- `api_status` (enum ci-dessus)

## Credentials Test
- **UI Login** : `energiebleuciel@gmail.com` / `92Ruemarxdormoy`

## URLs CRM
- **ZR7** : `https://app.zr7-digital.fr/lead/api/create_lead/`
- **MDL** : `https://maison-du-lead.com/lead/api/create_lead/`

## Dernière Mise à Jour
Février 2026 - Système complet sécurisé :

### Monitoring v1.0 (NEW - Février 2026)
**Endpoint** : `GET /api/monitoring/stats`
- Taux de succès par CRM / produit / compte (fenêtres 24h et 7j)
- Alertes automatiques si `success_rate < 80%` ou spike de fails (>3x moyenne horaire)
- Breakdown des raisons d'échec par catégorie (failed, doublon_recent, no_crm, orphan, etc.)
- Page UI dédiée `/monitoring` avec KPI, alertes collapsables, tables par dimension
- Détection spike : compare dernière heure vs moyenne horaire 24h

### RDZ Tracking v2.1 (Version Unique)
- Endpoint `/track/lp-visit` dédié avec UTM complet
- Capture UTM complète (source, medium, campaign, content, term, gclid, fbclid)
- sendBeacon pour fiabilité tracking
- MutationObserver pour CTA dynamiques
- Anti-doublon server-side pour tous les events
- Backend compatible sendBeacon (parse_beacon_body)
- Tests de fiabilité : 7/7 PASS, 100/100 funnel E2E

### Briefs v2.2 - Conversion GTM + Redirection Produit (NEW)
**Nouvelles sections automatiques dans les briefs Form et LP+Form:**

1. **Redirection post-submit par produit**
   - URLs configurées dans Paramètres compte : `redirect_url_pv`, `redirect_url_pac`, `redirect_url_ite`
   - Exemple : PV → `/merci-solaire`, PAC → `/merci-pompe-a-chaleur`
   - Déclenchement : après submit réussi + validation téléphone

2. **Code conversion GTM**
   - Champ compte : `gtm_conversion`
   - Injection automatique dans le script Form
   - Déclenchement : après submit valide, avant redirection
   - Compatible : gtag(), dataLayer.push()
   - Variables disponibles : `data.lead_id`, `data.lp_code`, `data.form_code`, `data.utm_campaign`

**Flux post-submit:**
```
Submit → Validation → DataLayer standard → Code GTM personnalisé → Redirection
```

### Détection Doublons Interne v2.2 (VALIDÉ)
- Critères : phone + département + fenêtre 30 jours
- Statuts : `doublon_recent` (déjà livré), `non_livre` (redistribuable), `double_submit` (anti double-clic)
- Protection anti double-submit : 5 secondes
- Lead TOUJOURS créé (traçabilité) mais non envoyé si doublon
- Index MongoDB optimisés pour performance
- **TEST E2E VOLUME : 100 leads, 100% succès, 0 doublon livré**
- Documentation : `/app/memory/DUPLICATE_DETECTION_v2.2.md`
- Rapport de test : `/app/memory/TEST_VOLUME_REPORT_2026-02-12.md`

### Système LB (Lead Backup) v1.0 (EN DÉVELOPPEMENT - DÉSACTIVÉ)
- ⚠️ **Feature flag: ENABLE_LB_REPLACEMENT = False**
- Remplacement automatique des doublons par LB
- LB = lead réel existant, > 30 jours, jamais livré à ce CRM, même dept/produit
- Priorité: Fresh leads < 30j → LB aged > 30j → Crédit/report
- Jamais de faux leads, données non modifiées
- Traçabilité complète (doublon ↔ LB)
- TEST: 100% LB trouvés, système opérationnel
- Documentation : `/app/memory/LB_REPLACEMENT_v1.0.md`
- **ACTIVATION: Nécessite validation CTO**

### Système Commandes/Distribution (EN DÉVELOPPEMENT - DÉSACTIVÉ)
- ⚠️ **Feature flag: ENABLE_COMMANDES_ROUTING = False**
- Routing basé sur les commandes actives
- Cross-CRM automatique si pas de commande
- **ACTIVATION: Nécessite validation CTO**

### Pipeline Production ACTIF - Routing Account-Centric v1.0 (NEW - Février 2026)
```
RDZ → API → ZR7/MDL (basé sur account.crm_routing[product_type])
```

**Chemin unique d'envoi : `send_to_crm()` dans `services/lead_sender.py`**
- Aucun legacy (send_to_crm_v2 supprimé, ancien send_to_crm supprimé)
- Un seul flux : `submit_lead → routing (account.crm_routing) → delivery_mode=API → send_to_crm`

**Nouveau modèle de routing :**
- Chaque compte (`accounts`) possède un champ `crm_routing` :
  ```json
  {
    "PV":  {"target_crm": "zr7", "api_key": "xxx", "delivery_mode": "api"},
    "PAC": {"target_crm": "mdl", "api_key": "yyy", "delivery_mode": "api"},
    "ITE": {"target_crm": "zr7", "api_key": "zzz", "delivery_mode": "api"}
  }
  ```
- **Hiérarchie de résolution :**
  1. `form.target_crm` + `form.crm_api_key` → override optionnel (whitelist: zr7, mdl)
  2. `account.crm_routing[product_type]` → config par défaut du compte
  3. Aucun → `no_crm`

**Sécurité API keys :**
- Une clé configurée ne peut JAMAIS être supprimée/vidée → rotation uniquement
- Validation backend : `target_crm ∈ {zr7, mdl}`, `product_type ∈ {PV, PAC, ITE}`
- UI : pas de bouton delete, seulement remplacement

**UI Settings CRM Routing :**
- Section "Routing CRM par produit" dans le modal d'édition de compte
- Tableau PV/PAC/ITE avec select CRM, input clé API, select mode
- Résumé badges sur chaque carte de compte (PV → ZR7, PAC → MDL, etc.)

**Champs de traçabilité sur chaque lead :**
- `routing_source` : `account_routing`, `form_override`, ou `none`
- `routing_reason` : `account_routing_zr7`, `form_override_mdl`, etc.

**Logs structurés :**
```
[ROUTING] lead_phone=XXXX account_id=... product=PV source=account_routing target_crm=zr7
[ROUTING_RESULT] lead_id=... account_id=... product_type=PV routing_source=account_routing target_crm=zr7 status=success
[ROUTING_WARN] form override rejeté: target_crm='invalid' not in whitelist
```

**Tests validés : 10/10 + validations sécurité**
- PV/PAC/ITE routing via account ✅
- Form override ✅
- No config → no_crm ✅
- Config partielle ✅
- Override incomplet → fallback account ✅
- Mise à jour crm_routing via API ✅
- Multi-produit ✅
- Champs routing_source présents ✅
- Suppression clé API → REJETÉ ✅
- CRM invalide → REJETÉ ✅
- Rotation clé → ACCEPTÉ ✅
- Détection doublons v2.2 toujours active ✅
- Feature flags LB/Commandes toujours désactivés ✅

### Liaison LP ↔ Form Obligatoire
- Création LP génère automatiquement Form lié
- Form standalone interdit
- Lien non supprimable
- Objectif : zéro lead orphelin
