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

### Vérification Commandes
Avant d'envoyer un lead :
1. Vérifier si le CRM cible a une commande pour ce département + produit
2. Si non et `allow_cross_crm` = true, essayer l'autre CRM
3. Si aucun CRM disponible, stocker avec status "pending_no_order"

## Fonctionnalités Implémentées

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

### ✅ Cycle de vie des Leads (Février 2026)

**Nouveau comportement :**
1. Tous les leads sont TOUJOURS sauvegardés en base, même sans commande
2. Si pas de commande → `api_status: "pending_no_order"`
3. Auto-redistribution quand commande activée (si lead < 8 jours)
4. Leads > 8 jours → `api_status: "pending_manual"` (scheduler quotidien 4h UTC)
5. Redistribution manuelle par admin pour leads > 8 jours

**Statuts de lead :**
- `pending` : En cours de traitement
- `success` : Envoyé avec succès
- `failed` : Échec d'envoi
- `duplicate` : Doublon détecté
- `no_crm` : Pas de CRM configuré
- `queued` : En file d'attente
- `pending_no_order` : En attente (pas de commande, < 8 jours)
- `pending_manual` : Redistribution manuelle requise (> 8 jours)

### ✅ Scheduler (APScheduler)
- **3h UTC** : Vérification nocturne des leads
- **4h UTC** : Marquage leads > 8 jours comme `pending_manual`
- **Toutes les 5 min** : Traitement de la file d'attente

### ✅ API

**Routes publiques:**
- `POST /api/public/track/session` - Créer session visiteur
- `POST /api/public/track/event` - Tracker événement
- `POST /api/public/leads` - Soumettre lead
- `GET /api/forms/public/{code}` - Config formulaire public

**Routes authentifiées:**
- `GET /api/leads/export` - Export leads avec clé API RDZ
- `GET /api/leads/stats/global` - Stats globales (filtrées par CRM)

**Routes admin:**
- `PUT /api/leads/{id}` - Modifier lead
- `DELETE /api/leads/{id}` - Supprimer lead
- `POST /api/leads/{id}/force-send` - Forcer envoi CRM
- `POST /api/forms/{id}/reset-stats` - Reset statistiques
- `GET /api/leads/pending` - Leads en attente redistribution
- `GET/PUT /api/config/redistribution-keys` - Clés redistribution inter-CRM

### 🔒 SCHEMA VERROUILLÉ

**Champs lead normalisés:**
```
origin_crm      : slug CRM d'origine (compte)
target_crm      : slug CRM de destination
is_transferred  : boolean (transfert inter-CRM)
routing_reason  : raison du routing
allow_cross_crm : boolean
api_status      : Enum ci-dessus
sent_to_crm     : boolean
departement     : code département (01-95, 2A, 2B)
```

**Champs interdits (JAMAIS UTILISER):**
- `code_postal` → Utiliser `departement`
- `target_crm_id` → Utiliser `target_crm`

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
Février 2026 - Fonctionnalités Admin complètes + Scheduler lead aging
