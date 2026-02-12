# RDZ CRM - Product Requirements Document

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
Février 2026 - RDZ Tracking Layer v2.0 implémenté avec :
- Endpoint `/track/lp-visit` dédié avec UTM complet
- Capture UTM complète (source, medium, campaign, content, term, gclid, fbclid)
- sendBeacon pour fiabilité tracking
- MutationObserver pour CTA dynamiques
- Anti-doublon server-side pour tous les events
