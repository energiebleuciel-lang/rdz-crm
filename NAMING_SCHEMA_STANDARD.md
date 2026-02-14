# NAMING & SCHEMA STANDARD — RDZ CRM v1.0.0
> Plus jamais de champ duplique / rename accidentel.

---

## CONVENTION NAMING OFFICIELLE

| Regle | Exemple | Anti-pattern |
|-------|---------|-------------|
| Champs DB: `snake_case` | `phone_quality`, `created_at` | ~~phoneQuality~~, ~~createdAt~~ |
| Collections: pluriel | `leads`, `deliveries` | ~~lead~~, ~~delivery~~ |
| Booleen: prefixe `is_` / `was_` / `has_` | `is_lb`, `was_replaced` | ~~lb~~, ~~replaced~~ |
| Date: suffixe `_at` (string ISO UTC) | `created_at`, `routed_at` | ~~creation_date~~, ~~timestamp~~ |
| ID reference: suffixe `_id` (UUID string) | `client_id`, `lead_id` | ~~client~~, ~~leadRef~~ |
| Entity: MAJUSCULE | `ZR7`, `MDL` | ~~zr7~~, ~~Mdl~~ |
| Produit: MAJUSCULE | `PV`, `PAC`, `ITE` | ~~pv~~, ~~Pac~~ |
| Statut: `snake_case` | `pending_csv`, `no_open_orders` | ~~pendingCSV~~ |
| Champ metier FR | `departement`, `produit`, `nom` | ~~department~~, ~~product~~ (sauf billing) |
| Champ technique EN | `status`, `created_at`, `outcome` | — |

### Exceptions documentees

| Champ | Contexte | Raison |
|-------|----------|--------|
| `produit` (leads/commandes) vs `product_code` (billing) | Metier vs facturation | `product_code` est le code billing standardise |
| `register_date` (int ms) + `created_at` (ISO str) | Legacy dans leads | `register_date` garde pour compat externe, `created_at` = reference interne |
| `delivered_to_client_id` + `delivery_client_id` | Ancien vs nouveau routing | Dual: ancien = daily_delivery, nouveau = routing immediat. A unifier post-freeze. |

---

## COLLECTIONS — CHAMPS PRINCIPAUX

### `leads` (collection principale)

| Champ | Type | Requis | Exemple | Note |
|-------|------|--------|---------|------|
| `id` | string UUID | OUI | `"a1b2c3..."` | PK |
| `phone` | string | OUI | `"0612345678"` | Normalise 0XXXXXXXXX |
| `phone_quality` | string | NON | `"valid"` | valid / suspicious / invalid |
| `nom` | string | OUI | `"Dupont"` | |
| `prenom` | string | NON | `"Jean"` | |
| `email` | string | NON | `"j@test.fr"` | |
| `departement` | string | OUI | `"75"` | 2 chiffres |
| `entity` | string | OUI | `"ZR7"` | ZR7 / MDL |
| `produit` | string | OUI | `"PV"` | PV / PAC / ITE |
| `status` | string | OUI | `"new"` | Voir table statuts |
| `lead_source_type` | string | NON | `"provider"` | provider / internal_lp / direct |
| `provider_id` | string | NON | UUID | Si source = provider |
| `entity_locked` | bool | NON | `true` | Verrouille par provider |
| `is_lb` | bool | NON | `false` | Lead Backlog |
| `was_replaced` | bool | NON | `false` | Remplace par LB |
| `session_id` | string | NON | UUID | Session visiteur |
| `source` | string | NON | `"google_ads"` | Attribution source |
| `delivery_client_id` | string | NON | UUID | Client cible (nouveau) |
| `delivery_commande_id` | string | NON | UUID | Commande cible |
| `routed_at` | string ISO | NON | `"2026-02..."` | Date routing (nouveau) |
| `delivered_to_client_id` | string | NON | UUID | Client (ancien format) |
| `delivered_at` | string ISO | NON | | Date livraison (ancien) |
| `created_at` | string ISO | OUI | `"2026-02..."` | Date creation |
| `custom_fields` | dict | NON | `{}` | Champs secondaires libres |

### `deliveries`

| Champ | Type | Requis | Exemple | Note |
|-------|------|--------|---------|------|
| `id` | string UUID | OUI | | PK |
| `lead_id` | string | OUI | UUID | Ref lead |
| `client_id` | string | OUI | UUID | Ref client |
| `client_name` | string | OUI | `"Acme"` | Snapshot |
| `commande_id` | string | OUI | UUID | Ref commande |
| `entity` | string | OUI | `"ZR7"` | |
| `produit` | string | OUI | `"PV"` | |
| `status` | string | OUI | `"pending_csv"` | pending_csv / ready_to_send / sending / sent / failed |
| `outcome` | string | NON | `"accepted"` | accepted / rejected / removed |
| `is_lb` | bool | NON | `false` | |
| `sent_to` | array | NON | `["a@b.fr"]` | Emails destinataires |
| `csv_content` | string | NON | | Contenu CSV |
| `client_group_key` | string | NON | | Cle overlap |
| `is_shared_client_30d` | bool | NON | `false` | Overlap actif |
| `overlap_fallback_delivery` | bool | NON | `false` | Livraison fallback |
| `created_at` | string ISO | OUI | | |

### `clients`

| Champ | Type | Requis | Exemple |
|-------|------|--------|---------|
| `id` | string UUID | OUI | |
| `entity` | string | OUI | `"ZR7"` |
| `name` | string | OUI | `"Acme SAS"` |
| `email` | string | OUI | `"contact@acme.fr"` |
| `delivery_emails` | array | NON | `["leads@acme.fr"]` |
| `auto_send_enabled` | bool | NON | `true` |
| `active` | bool | NON | `true` |

### `commandes`

| Champ | Type | Requis | Exemple |
|-------|------|--------|---------|
| `id` | string UUID | OUI | |
| `entity` | string | OUI | `"ZR7"` |
| `client_id` | string | OUI | UUID |
| `produit` | string | OUI | `"PV"` |
| `departements` | array | OUI | `["75","92"]` ou `["*"]` |
| `quota_semaine` | int | NON | `50` (0 = illimite) |
| `lb_target_pct` | float | NON | `0.20` (20%) |
| `priorite` | int | NON | `5` (1=haute, 10=basse) |
| `active` | bool | NON | `true` |

### `providers`

| Champ | Type | Requis | Exemple |
|-------|------|--------|---------|
| `id` | string UUID | OUI | |
| `name` | string | OUI | `"SolarProvider"` |
| `slug` | string | OUI | `"solar-provider"` (unique) |
| `entity` | string | OUI | `"ZR7"` (verrouillee) |
| `api_key` | string | OUI | `"prov_xxx..."` (unique) |
| `active` | bool | NON | `true` |

---

## MAPPING API PAYLOADS ↔ DB

### POST `/api/public/leads` (Ingestion)

| Payload API | → Champ DB (leads) | Transformation |
|-------------|-------------------|----------------|
| `phone` | `phone` | `normalize_phone_fr()` → `0XXXXXXXXX` |
| `nom` | `nom` | `.strip()` |
| `prenom` | `prenom` | `.strip()` |
| `email` | `email` | `.strip()` |
| `departement` | `departement` | `[:2]` (2 premiers chars) |
| `session_id` | `session_id` | tel quel |
| `form_code` | `form_code` | tel quel |
| `entity` | `entity` | `.upper()`, ou provider.entity, ou form_config |
| `produit` | `produit` | `.upper()`, ou form_config |
| `api_key` | `provider_id`, `provider_slug` | lookup providers, pas stocke directement |
| `civilite`, `ville`, etc. | `custom_fields.{champ}` | tous les champs secondaires |
| *(calcule)* | `phone_quality` | resultat normalize_phone_fr |
| *(calcule)* | `lead_source_type` | provider / internal_lp / direct |
| *(calcule)* | `status` | new / invalid / hold_source / pending_config |
| *(calcule)* | `ip` | `x-forwarded-for` header |
| *(calcule)* | `register_date` | Unix timestamp ms |
| *(calcule)* | `created_at` | ISO UTC string |

### GET `/api/deliveries` (Liste)

| Champ DB (deliveries) | → Champ API reponse | Transformation |
|----------------------|---------------------|----------------|
| `id` | `id` | tel quel |
| `lead_id` | `lead_id` | tel quel |
| `client_name` | `client_name` | tel quel |
| `status` | `status` | tel quel |
| `outcome` | `outcome` | defaut `"accepted"` si absent |
| *(calcule)* | `has_csv` | `bool(csv_filename)` |
| *(calcule)* | `billable` | `status=="sent" and outcome=="accepted"` |
| `csv_content` | *(exclu)* | jamais retourne dans les listes (perf) |

### GET `/api/monitoring/intelligence` (Dashboard strategique)

| Section reponse | Source DB | Aggregation |
|----------------|-----------|-------------|
| `phone_quality` | leads | group by lead_source_type + phone_quality |
| `duplicate_by_source` | leads | group by source, count status=duplicate |
| `duplicate_cross_matrix` | leads | group by phone, find multi-source conflicts |
| `rejections_by_source` | leads | group by source + rejection status |
| `lb_stats` | leads | count suspicious, replaced, stock |
| `kpis` | leads | total, delivered, valid, economic yield |
| `source_scores` | leads | toxicity + trust score par source |
| `cannibalization` | leads | phones presents dans ZR7 ET MDL |
| `overlap_stats` | clients + deliveries | shared emails cross-entity, 30d window |

---

## TABLE DES STATUTS

### Lead statuts

| Status | Terminal | Signification |
|--------|----------|---------------|
| `new` | NON | Cree, eligible routing |
| `routed` | NON | Route, delivery en cours |
| `livre` | OUI | Delivery envoyee |
| `duplicate` | OUI | Doublon 30j detecte |
| `no_open_orders` | NON | Aucune commande compatible |
| `hold_source` | NON | Source blacklistee |
| `pending_config` | NON | Form sans config entity/produit |
| `invalid` | OUI | Donnees invalides |
| `replaced_by_lb` | OUI | Remplace par un LB |
| `reserved_for_replacement` | NON | LB reserve atomiquement |
| `lb` | NON | Lead Backlog (>8j ou deja livre >30j) |

### Delivery statuts

| Status | Terminal | Signification |
|--------|----------|---------------|
| `pending_csv` | NON | En attente traitement |
| `ready_to_send` | NON | CSV genere (mode manuel) |
| `sending` | NON | Envoi en cours |
| `sent` | OUI | Envoye, lead = livre |
| `failed` | NON | Erreur, retry possible |
