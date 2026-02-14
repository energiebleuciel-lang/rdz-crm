# NAMING & SCHEMA STANDARD — RDZ CRM v1.0.0

## 1. CONVENTIONS DE NOMMAGE OFFICIELLES

### 1.1 Regles generales
| Contexte | Convention | Exemple |
|----------|-----------|---------|
| Champs DB | snake_case francais quand possible | `departement`, `produit`, `nom` |
| Champs DB (technique) | snake_case anglais | `created_at`, `updated_at`, `is_lb` |
| Routes API | kebab-case | `/api/public/track/lp-visit` |
| Prefixes API | snake_case (FastAPI tags) | `tags=["Clients"]` |
| Collections DB | snake_case pluriel | `leads`, `deliveries`, `billing_records` |
| Entities | MAJUSCULE | `ZR7`, `MDL` |
| Produits | MAJUSCULE | `PV`, `PAC`, `ITE` |
| Statuts | snake_case | `pending_csv`, `ready_to_send`, `no_open_orders` |
| Booleans DB | prefixe `is_` ou `has_` ou verbe passe | `is_lb`, `is_duplicate`, `was_replaced` |
| Dates | suffixe `_at` (ISO string) | `created_at`, `delivered_at`, `routed_at` |
| IDs | suffixe `_id` (UUID string) | `client_id`, `lead_id`, `delivery_id` |
| Prix | suffixe descriptif | `prix_lead`, `unit_price_eur`, `unit_price_ht` |

### 1.2 Inconsistances actuelles (documentees)

| Champ A | Champ B | Collection | Status |
|---------|---------|------------|--------|
| `produit` | `product` / `product_code` | leads vs intercompany vs billing | ACCEPTE: `produit` = business, `product_code` = billing |
| `register_date` (int ms) | `created_at` (ISO str) | leads | LEGACY: `register_date` garde pour compat, `created_at` = reference |
| `delivered_to_client_id` | `delivery_client_id` | leads | DUAL: ancien=daily_delivery, nouveau=routing_immediat |
| `delivered_at` | `routed_at` | leads | DUAL: ancien=daily_delivery, nouveau=routing_immediat |

---

## 2. SCHEMA MAP — COLLECTIONS PRINCIPALES

### 2.1 `leads` (Collection principale)

| Champ | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | string (UUID) | OUI | - | Identifiant unique |
| `phone` | string | OUI | - | Format normalise: `0XXXXXXXXX` |
| `phone_quality` | string | NON | - | `valid` / `suspicious` / `invalid` |
| `departement` | string | OUI | - | Code dept 2 chiffres (ex: `75`) |
| `nom` | string | OUI | - | Nom de famille |
| `prenom` | string | NON | `""` | Prenom |
| `email` | string | NON | `""` | Email |
| `entity` | string | OUI | - | `ZR7` ou `MDL` |
| `lead_owner_entity` | string | NON | - | Entity d'origine (immutable) |
| `produit` | string | OUI | - | `PV` / `PAC` / `ITE` |
| `status` | string | OUI | `new` | Voir Section 3.1 |
| `register_date` | int | OUI | - | Unix timestamp ms (legacy) |
| `created_at` | string (ISO) | OUI | - | Date creation |
| `updated_at` | string (ISO) | NON | - | Derniere modification |
| `source` | string | NON | `""` | Source attribution |
| `lead_source_type` | string | NON | - | `provider` / `internal_lp` / `direct` |
| `provider_id` | string | NON | null | ID du provider source |
| `provider_slug` | string | NON | null | Slug du provider |
| `entity_locked` | bool | NON | false | Si verrouille par provider |
| `is_lb` | bool | NON | false | Lead Backlog |
| `lb_since` | string (ISO) | NON | null | Date passage LB |
| `lb_reason` | string | NON | null | `age_8_days` / `already_delivered` |
| `is_duplicate` | bool | NON | false | Legacy flag doublon |
| `was_replaced` | bool | NON | false | Remplace par LB |
| `replacement_source` | string | NON | null | `LB` |
| `replacement_lead_id` | string | NON | null | ID du LB de remplacement |
| `session_id` | string | NON | `""` | Session visiteur |
| `form_code` | string | NON | `""` | Code formulaire |
| `lp_code` | string | NON | `""` | Code landing page |
| `liaison_code` | string | NON | `""` | Code liaison tracking |
| `utm_source` | string | NON | `""` | UTM source |
| `utm_medium` | string | NON | `""` | UTM medium |
| `utm_campaign` | string | NON | `""` | UTM campaign |
| `custom_fields` | dict | NON | `{}` | Champs secondaires |
| `ip` | string | NON | `""` | IP du soumetteur |
| `delivery_id` | string | NON | null | ID delivery (nouveau format) |
| `delivery_client_id` | string | NON | null | Client cible (nouveau format) |
| `delivery_client_name` | string | NON | null | Nom client (nouveau format) |
| `delivery_commande_id` | string | NON | null | Commande cible |
| `routing_mode` | string | NON | null | `normal` / `fallback_no_orders` |
| `routed_at` | string (ISO) | NON | null | Date routing (nouveau format) |
| `delivered_to_client_id` | string | NON | null | Client (ancien format) |
| `delivered_to_client_name` | string | NON | null | Nom (ancien format) |
| `delivered_at` | string (ISO) | NON | null | Date livraison (ancien format) |
| `hold_reason` | string | NON | null | Raison blocage source |
| `routing_reason` | string | NON | null | Raison echec routing |

### 2.2 `deliveries`

| Champ | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | string (UUID) | OUI | - | Identifiant unique |
| `lead_id` | string | OUI | - | Lead associe |
| `client_id` | string | OUI | - | Client destinataire |
| `client_name` | string | OUI | - | Nom client (snapshot) |
| `commande_id` | string | OUI | - | Commande source |
| `entity` | string | OUI | - | `ZR7` / `MDL` |
| `produit` | string | OUI | - | `PV` / `PAC` / `ITE` |
| `status` | string | OUI | `pending_csv` | Voir Section 3.2 |
| `outcome` | string | NON | `accepted` | `accepted` / `rejected` / `removed` |
| `delivery_method` | string | NON | `csv_email` | `csv_email` / `realtime` / `manual` |
| `is_lb` | bool | NON | false | Lead LB |
| `routing_mode` | string | NON | null | Mode routing |
| `sent_to` | array[string] | NON | `[]` | Emails destinataires |
| `send_attempts` | int | NON | 0 | Nombre tentatives |
| `last_sent_at` | string (ISO) | NON | null | Dernier envoi |
| `last_error` | string | NON | null | Derniere erreur |
| `sent_by` | string | NON | null | Email utilisateur |
| `csv_content` | string | NON | null | Contenu CSV |
| `csv_filename` | string | NON | null | Nom fichier |
| `csv_generated_at` | string (ISO) | NON | null | Date generation CSV |
| `batch_id` | string | NON | null | ID batch cron |
| `client_group_key` | string | NON | `""` | Cle overlap guard |
| `is_shared_client_30d` | bool | NON | false | Client partage actif |
| `overlap_fallback_delivery` | bool | NON | false | Livraison fallback overlap |
| `accepted_at` | string (ISO) | NON | null | Date acceptation |
| `rejected_at` | string (ISO) | NON | null | Date rejet |
| `rejected_by` | string | NON | null | Utilisateur rejet |
| `rejection_reason` | string | NON | null | Motif rejet |
| `removed_at` | string (ISO) | NON | null | Date retrait |
| `removed_by` | string | NON | null | Utilisateur retrait |
| `removal_reason` | string | NON | null | Motif retrait |
| `replaced_suspicious_id` | string | NON | null | ID lead suspect remplace |
| `created_at` | string (ISO) | OUI | - | Date creation |
| `updated_at` | string (ISO) | NON | null | Derniere modification |

### 2.3 `clients`

| Champ | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | string (UUID) | OUI | - | ID unique |
| `entity` | string | OUI | - | `ZR7` / `MDL` |
| `name` | string | OUI | - | Nom societe |
| `contact_name` | string | NON | `""` | Contact |
| `email` | string | OUI | - | Email principal |
| `phone` | string | NON | `""` | Telephone |
| `delivery_emails` | array[string] | NON | `[]` | Emails livraison |
| `api_endpoint` | string | NON | `""` | Endpoint API |
| `api_key` | string | NON | `""` | Cle API |
| `auto_send_enabled` | bool | NON | true | Mode auto/manuel |
| `default_prix_lead` | float | NON | 0.0 | Prix par defaut |
| `remise_percent` | float | NON | 0.0 | Remise % |
| `vat_rate` | float | NON | 20.0 | TVA % |
| `payment_terms_days` | int | NON | 30 | Delai paiement |
| `notes` | string | NON | `""` | Notes |
| `active` | bool | NON | true | Actif |
| `created_at` | string (ISO) | OUI | - | Creation |
| `updated_at` | string (ISO) | NON | - | Modification |

### 2.4 `commandes`

| Champ | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | string (UUID) | OUI | - | ID unique |
| `entity` | string | OUI | - | `ZR7` / `MDL` |
| `client_id` | string | OUI | - | Client acheteur |
| `produit` | string | OUI | - | `PV` / `PAC` / `ITE` |
| `departements` | array[string] | OUI | - | Depts couverts (`["*"]` = tous) |
| `quota_semaine` | int | NON | 0 | 0 = illimite |
| `prix_lead` | float | NON | 0.0 | Prix unitaire |
| `lb_target_pct` | float | NON | 0 | Target LB (0.0-1.0) |
| `lb_percent_max` | int | NON | 0 | DEPRECATED |
| `priorite` | int | NON | 5 | 1=haute, 10=basse |
| `auto_renew` | bool | NON | true | Renouvellement auto |
| `remise_percent` | float | NON | 0.0 | Remise specifique |
| `notes` | string | NON | `""` | Notes |
| `active` | bool | NON | true | Actif |

---

## 3. TABLES DE REFERENCE

### 3.1 Lead Status (COMPLET — incluant les statuts non-declares dans l'enum)

| Status | Description | Terminal | Source |
|--------|-------------|----------|--------|
| `new` | Vient d'etre cree, eligible au routing | NON | Ingestion |
| `routed` | Route vers un client, delivery pending | NON | Routing immediat |
| `livre` | Delivery envoyee avec succes | OUI | State machine |
| `duplicate` | Doublon detecte au routing | OUI | Routing engine |
| `no_open_orders` | Aucune commande compatible | NON | Routing engine |
| `hold_source` | Source en blacklist | NON | Source gating |
| `pending_config` | Form_code sans config entity/produit | NON | Ingestion |
| `invalid` | Donnees incompletes ou invalides | OUI | Validation |
| `replaced_by_lb` | Remplace par un LB (phone suspect) | OUI | LB replacement |
| `reserved_for_replacement` | LB reserve pour remplacement | NON | LB replacement |
| `lb` | Lead Backlog (>8j ou deja livre) | NON | Cron daily |
| `non_livre` | Legacy: non livre (ancien systeme) | NON | Legacy |
| `rejet_client` | Legacy: rejete par client | OUI | Legacy |

### 3.2 Delivery Status

| Status | Description | Terminal | Transitions depuis |
|--------|-------------|----------|-------------------|
| `pending_csv` | En attente traitement | NON | (initial) |
| `ready_to_send` | CSV genere, attente envoi | NON | pending_csv |
| `sending` | Envoi en cours | NON | pending_csv, ready_to_send, failed |
| `sent` | Envoye avec succes | OUI | sending |
| `failed` | Erreur d'envoi | NON | pending_csv, ready_to_send, sending |

### 3.3 Delivery Outcome

| Outcome | Description | Billable |
|---------|-------------|----------|
| `accepted` | Accepte par le client (defaut) | OUI |
| `rejected` | Rejete par le client | NON |
| `removed` | Retire par l'admin | NON |

### 3.4 Entities

| Code | Nom complet | SMTP |
|------|-------------|------|
| `ZR7` | ZR7 Consulting / ZR7 Digital | vos-leads@zr7-digital.fr |
| `MDL` | Maison du Lead | livraisonleads@maisonduleads.fr |

### 3.5 Produits

| Code | Nom |
|------|-----|
| `PV` | Panneaux Solaires |
| `PAC` | Pompe a Chaleur |
| `ITE` | Isolation Thermique Exterieure |

### 3.6 Roles RBAC

| Role | Permissions | Entity scope |
|------|------------|--------------|
| `super_admin` | TOUTES (40+) | BOTH (ZR7+MDL) |
| `admin` | Toutes sauf users.manage | Son entity |
| `ops` | View + edit quotas + resend | Son entity |
| `viewer` | Read-only (dashboard, leads, clients, commandes, deliveries, depts) | Son entity |
