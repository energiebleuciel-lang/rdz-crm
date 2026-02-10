# 🔒 SCHEMA VERROUILLÉ - RDZ CRM

**STATUT: VERROUILLÉ**  
**Date de verrouillage:** Février 2026  
**Demandé par:** Utilisateur

---

## ⚠️ RÈGLE ABSOLUE

**AUCUN renommage de champ n'est autorisé sans déverrouillage explicite.**

Pour modifier un nom de champ, l'utilisateur DOIT dire:
> "Je déverrouille le schema pour modifier [nom_du_champ]"

Sans cette phrase exacte, le schema reste verrouillé et toute modification est interdite.

---

## 🔒 CHAMPS LEAD VERROUILLÉS

### Identité
| Champ | Type | Description |
|-------|------|-------------|
| `phone` | string | Téléphone (10 chiffres) |
| `nom` | string | Nom de famille |
| `prenom` | string | Prénom |
| `civilite` | string | M., Mme, Mlle |
| `email` | string | Email |

### Localisation
| Champ | Type | Description |
|-------|------|-------------|
| `departement` | string | Code département (01-95) |
| `ville` | string | Nom ville |
| `adresse` | string | Adresse postale |

### Logement
| Champ | Type | Description |
|-------|------|-------------|
| `type_logement` | string | Maison, Appartement |
| `statut_occupant` | string | Propriétaire, Locataire |
| `surface_habitable` | string | Surface m² |
| `annee_construction` | string | Année |
| `type_chauffage` | string | Type chauffage |

### Énergie
| Champ | Type | Description |
|-------|------|-------------|
| `facture_electricite` | string | Tranche facture |
| `facture_chauffage` | string | Tranche facture |

### Projet
| Champ | Type | Description |
|-------|------|-------------|
| `type_projet` | string | Installation, Remplacement |
| `delai_projet` | string | Délai |
| `budget` | string | Budget |

### Tracking
| Champ | Type | Description |
|-------|------|-------------|
| `form_code` | string | Code formulaire (PV-001) |
| `lp_code` | string | Code LP (LP-001) |
| `liaison_code` | string | Code liaison |
| `session_id` | string | ID session |
| `utm_source` | string | UTM Source |
| `utm_medium` | string | UTM Medium |
| `utm_campaign` | string | UTM Campaign |

### CRM & Routing
| Champ | Type | Description |
|-------|------|-------------|
| `origin_crm` | string | CRM origine (slug) |
| `target_crm` | string | CRM destination (slug) |
| `is_transferred` | boolean | Transféré? |
| `routing_reason` | string | Raison routage |
| `allow_cross_crm` | boolean | Cross-CRM autorisé? |
| `api_status` | string | Statut API |
| `sent_to_crm` | boolean | Envoyé? |

### Consentement
| Champ | Type | Description |
|-------|------|-------------|
| `rgpd_consent` | boolean | RGPD OK |
| `newsletter` | boolean | Newsletter |

### Metadata
| Champ | Type | Description |
|-------|------|-------------|
| `id` | string | UUID |
| `created_at` | string | Date ISO |
| `register_date` | integer | Timestamp |
| `ip` | string | IP |

---

## 🚫 CHAMPS INTERDITS (JAMAIS UTILISER)

| Champ Interdit | Utiliser à la place |
|----------------|---------------------|
| `code_postal` | `departement` |
| `target_crm_id` | `target_crm` |
| `target_crm_slug` | `target_crm` |
| `source` | `utm_source` |
| `cp` | `departement` |
| `postal_code` | `departement` |
| `zipcode` | `departement` |

---

## 🏷️ SLUGS CRM VERROUILLÉS

| Slug | Nom |
|------|-----|
| `zr7` | ZR7 Digital |
| `mdl` | Maison du Lead |

---

## 📊 EVENTS TRACKING VERROUILLÉS

| Event | Description |
|-------|-------------|
| `lp_visit` | Visite LP |
| `cta_click` | Clic CTA |
| `form_start` | Début form |
| `form_submit` | Soumission |

---

## 📦 PRODUCT TYPES VERROUILLÉS

- `PV` - Panneaux solaires
- `PAC` - Pompe à chaleur
- `ITE` - Isolation thermique

---

## 🔐 PROCÉDURE DE DÉVERROUILLAGE

1. L'utilisateur dit: **"Je déverrouille le schema pour modifier [nom_du_champ]"**
2. L'agent confirme le déverrouillage temporaire
3. La modification est effectuée
4. L'agent re-verrouille automatiquement après la modification
5. Mise à jour de ce document si nécessaire

---

**Fichier de référence:** `/app/backend/schema_locked.py`
