# 📋 DOCUMENTATION: Système LB (Lead Backup) v1.0

**Date**: 12 février 2026  
**Version**: 1.0  
**Objectif**: Documenter la logique de remplacement automatique par LB

---

## 1. CONCEPT

### 1.1 Objectif

Quand un lead est bloqué (doublon), au lieu de perdre le slot/quota du client :
- On cherche un **LB (Lead Backup)** = lead réel existant, redistribuable
- On l'envoie automatiquement au CRM en remplacement
- Le quota est rempli à 100% sans perte

### 1.2 Règles strictes

| Règle | Description |
|-------|-------------|
| ✅ Uniquement des leads réels | Jamais créer de faux leads |
| ✅ Données non modifiées | On envoie le LB tel quel |
| ✅ Traçabilité complète | Lien doublon ↔ LB conservé |
| ✅ FIFO (First In First Out) | Les plus anciens sont envoyés en premier |

---

## 2. DÉFINITION D'UN LB

### 2.1 Critères de sélection

Un lead est éligible comme LB si :

| Critère | Valeur | Description |
|---------|--------|-------------|
| Département | Exact | Même département que le doublon |
| Product Type | Exact | Même type de produit (PV, PAC, ITE) |
| Phone | Valide | Numéro de téléphone présent et valide |
| Nom | Présent | Nom du contact présent |
| Statut | Redistribuable | `pending_no_order`, `pending_manual`, `non_livre`, `no_crm`, `no_api_key`, `failed` |
| Envoyé au CRM | Non | `sent_to_crm = False` |

### 2.2 Priorité de sélection

```
1. FRESH LEADS (< 30 jours)
   └── Leads récents non encore livrés
   └── Priorité aux plus anciens (FIFO)

2. AGED LEADS / LB (> 30 jours)
   └── Leads plus anciens, jamais livrés à CE CRM
   └── Priorité aux plus anciens (FIFO)

3. PAS DE LB
   └── Crédit/Report (quota non rempli)
```

---

## 3. STATUTS

### 3.1 Nouveaux statuts/champs

| Champ | Type | Description |
|-------|------|-------------|
| `is_lb_replacement` | Boolean | True si ce lead a été envoyé comme LB |
| `lb_replaced_doublon_id` | String | ID du doublon qu'il remplace |
| `lb_sent_at` | DateTime | Date/heure d'envoi comme LB |
| `lb_type` | String | "fresh" ou "aged" |
| `lb_replacement_id` | String | Sur le doublon: ID du LB qui l'a remplacé |
| `lb_replacement_status` | String | Sur le doublon: statut de l'envoi LB |

### 3.2 Warnings retournés

| Warning | Description |
|---------|-------------|
| `DUPLICATE_REPLACED_BY_LB` | Doublon remplacé avec succès par un LB |
| `DUPLICATE_NO_LB` | Doublon détecté mais aucun LB disponible |

---

## 4. FLUX DE TRAITEMENT

```
┌─────────────────────┐
│   LEAD SOUMIS       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ DÉTECTION DOUBLON?  │
└──────────┬──────────┘
           │
    Non ───┼─── Oui
           │     │
           ▼     ▼
    ┌───────────────────┐
    │ ENVOI NORMAL      │
    │ AU CRM            │
    └───────────────────┘
                │
                ▼
    ┌───────────────────┐
    │ RECHERCHE LB      │
    │ (même dept/prod)  │
    └────────┬──────────┘
             │
      Non ───┼─── Oui
             │     │
             ▼     ▼
    ┌───────────┐ ┌───────────────────┐
    │ CRÉDIT/   │ │ ENVOI LB AU CRM   │
    │ REPORT    │ └────────┬──────────┘
    └───────────┘          │
                           ▼
              ┌─────────────────────────┐
              │ MISE À JOUR TRAÇABILITÉ │
              │ - Doublon: lb_replacement_id │
              │ - LB: is_lb_replacement │
              └─────────────────────────┘
```

---

## 5. FICHIERS DE RÉFÉRENCE

| Fichier | Rôle |
|---------|------|
| `/app/backend/services/lead_replacement.py` | Service LB (recherche + envoi) |
| `/app/backend/routes/public.py` | Intégration dans submit_lead |

### 5.1 Fonctions principales

```python
# Recherche un LB compatible
async def find_replacement_lead(
    target_crm: str,
    departement: str,
    product_type: str,
    excluded_lead_id: Optional[str] = None
) -> LBResult

# Exécute l'envoi du LB
async def execute_lb_replacement(
    lb_lead: Dict,
    target_crm: str,
    crm_api_key: str,
    original_doublon_id: str
) -> Tuple[bool, str, Optional[str]]

# Traitement complet (recherche + envoi)
async def process_doublon_with_replacement(
    doublon_lead: Dict,
    target_crm: str,
    crm_api_key: str
) -> Dict[str, Any]
```

---

## 6. EXEMPLES

### 6.1 Doublon avec remplacement réussi

```json
// Réponse API
{
  "success": true,
  "lead_id": "abc123...",
  "status": "doublon_recent",
  "warning": "DUPLICATE_REPLACED_BY_LB",
  "message": "Doublon remplacé par LB (xyz789...) - success",
  "lb": {
    "found": true,
    "sent": true,
    "lb_id": "xyz789...",
    "lb_status": "success",
    "lb_type": "fresh"
  }
}
```

### 6.2 Doublon sans LB disponible

```json
{
  "success": true,
  "lead_id": "abc123...",
  "status": "doublon_recent",
  "warning": "DUPLICATE_NO_LB",
  "message": "Doublon détecté - Aucun lead redistribuable pour 75/PV",
  "lb": {
    "found": false,
    "sent": false
  }
}
```

---

## 7. STATISTIQUES

```python
from services.lead_replacement import get_lb_stats

stats = await get_lb_stats()
# {
#   "total_lb_sent": 150,
#   "lb_fresh": 120,
#   "lb_aged": 30,
#   "lb_success": 145,
#   "lb_failed": 5,
#   "doublons_with_replacement": 150,
#   "replacement_rate": 96.7
# }
```

---

## 8. CONFIGURATION

| Paramètre | Valeur | Description |
|-----------|--------|-------------|
| `LB_MIN_AGE_DAYS` | 30 | Âge minimum pour être considéré comme LB aged |
| `FRESH_MAX_AGE_DAYS` | 30 | Âge max pour être considéré comme fresh |
| `REDISTRIBUTABLE_STATUSES` | Liste | Statuts éligibles pour redistribution |

---

**Document créé le**: 12 février 2026  
**Auteur**: Agent E1  
**Validé**: Tests E2E passés avec succès
