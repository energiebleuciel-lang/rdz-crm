# RDZ CRM - Product Requirements Document

## Description
CRM multi-tenant pour la gestion et distribution de leads vers ZR7 Digital et Maison du Lead (MDL).

## Architecture

### Flux Principal
```
Visiteur → LP → Form → RDZ (collecte) → ZR7 ou MDL (distribution)
```

### Clés API
- **Clé API RDZ** : unique, non modifiable, pour récupérer les leads (`GET /api/leads/export`)
- **Clés API ZR7/MDL** : par formulaire, pour envoyer les leads
- **Clés de redistribution** : 6 clés (ZR7/MDL × PV/PAC/ITE) pour envoi inter-CRM

### Règle critique : Lead TOUJOURS sauvegardé (Février 2026)
```
AVANT: Clé API vide → return error → Lead PERDU ❌
APRÈS: Clé API vide → Lead sauvegardé avec status "no_api_key" → Envoi manuel possible ✅
```

## Statuts de Lead

| Statut | Description | Action admin |
|--------|-------------|--------------|
| `success` | Envoyé au CRM avec succès | - |
| `duplicate` | Doublon détecté par le CRM | - |
| `queued` | En file d'attente (retry) | Automatique |
| `failed` | Erreur d'envoi CRM | Forcer envoi |
| `no_crm` | CRM non configuré sur le formulaire | Configurer CRM |
| `no_api_key` | **NOUVEAU** - Clé API manquante | Forcer envoi |
| `pending_no_order` | Pas de commande active (<8j) | Redistribution auto |
| `pending_manual` | Pas de commande active (>8j) | Redistribution manuelle |

## Fonctionnalités Implémentées

### ✅ Correction critique : Lead toujours sauvegardé (Février 2026)

**Problème résolu :**
- Les leads n'étaient PAS créés si la clé API du formulaire était vide
- Le visiteur voyait une erreur sur le formulaire

**Solution implémentée :**
- Le lead est TOUJOURS sauvegardé dans RDZ
- Nouveau statut `no_api_key` pour identifier ces cas
- Réponse API toujours `success: true` pour le formulaire
- Badge orange "Sans clé" visible dans l'admin
- Admin peut utiliser "Forcer envoi" pour envoyer manuellement

### ✅ Fonctionnalités Admin (Février 2026)

**Page Leads - Actions individuelles:**
- Édition lead (PUT /api/leads/{id}) : phone, email, nom, prenom, departement, ville, notes_admin
- Suppression lead (DELETE /api/leads/{id}) : suppression définitive
- Forcer envoi CRM (POST /api/leads/{id}/force-send) : vers ZR7 ou MDL

**Page Leads - Actions de masse:**
- Sélection multiple via checkboxes
- Barre d'actions apparaît quand sélection active
- Édition masse : modifier département, ville, notes pour X leads
- Suppression masse : supprimer X leads
- Envoi masse : forcer envoi de X leads vers un CRM

**Page Forms - Reset Stats:**
- Bouton Reset Stats (admin only) sur chaque carte formulaire
- Modal de confirmation avec warning
- Crée un snapshot avant reset
- Marque les leads comme `stats_reset: true`
- Les leads ne sont PAS supprimés, juste exclus des stats

### ✅ Scheduler (APScheduler)
- **3h UTC** : Vérification nocturne des leads
- **4h UTC** : Marquage leads > 8 jours comme `pending_manual`
- **Toutes les 5 min** : Traitement de la file d'attente

## API Réponses

### POST /api/public/leads

**Cas 1: Envoi réussi**
```json
{"success": true, "lead_id": "...", "status": "success", "crm": "zr7", "message": "Envoyé vers ZR7"}
```

**Cas 2: Clé API manquante (NOUVEAU)**
```json
{"success": true, "lead_id": "...", "status": "no_api_key", "crm": "zr7", "message": "Lead enregistré - Clé API manquante", "warning": "API_KEY_MISSING", "stored": true}
```

**Cas 3: En attente de commande**
```json
{"success": true, "lead_id": "...", "status": "pending_no_order", "message": "Lead enregistré - En attente de commande active"}
```

## 🔒 SCHEMA VERROUILLÉ

**Champs lead normalisés:**
```
origin_crm      : slug CRM d'origine (compte)
target_crm      : slug CRM de destination
is_transferred  : boolean (transfert inter-CRM)
routing_reason  : raison du routing
distribution_reason: raison détaillée (API_KEY_MISSING, NO_ELIGIBLE_ORDER, etc.)
allow_cross_crm : boolean
api_status      : Enum (voir tableau ci-dessus)
sent_to_crm     : boolean
departement     : code département (01-95, 2A, 2B)
```

## À Faire

### 🔶 Priorité Haute
- Tests end-to-end complets du nouveau cycle de vie

### 🔷 Priorité Moyenne
- Sous-comptes
- Configuration détaillée des Types de Produits

### ⬜ Backlog
- Alertes email (SendGrid)
- A/B Testing ("Mode Campagne")

## Credentials Test
- **UI Login** : `energiebleuciel@gmail.com` / `92Ruemarxdormoy`

## URLs CRM
- **ZR7** : `https://app.zr7-digital.fr/lead/api/create_lead/`
- **MDL** : `https://maison-du-lead.com/lead/api/create_lead/`

## Dernière Mise à Jour
Février 2026 - Correction critique : Lead TOUJOURS sauvegardé même sans clé API
