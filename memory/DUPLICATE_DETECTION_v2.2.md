# 📋 DOCUMENTATION: Détection de Doublons Internes RDZ v2.2

**Date**: 12 février 2026  
**Version**: 2.2  
**Objectif**: Documenter la logique de détection de doublons interne à RDZ

---

## 1. ARCHITECTURE

### 1.1 Fichiers concernés

| Fichier | Rôle |
|---------|------|
| `/app/backend/services/duplicate_detector.py` | Service de détection (logique) |
| `/app/backend/routes/public.py` | Endpoint `POST /api/public/leads` (intégration) |
| `/app/backend/server.py` | Index MongoDB pour performance |

### 1.2 Index MongoDB

```python
# Index composite pour détection doublons (phone + dept + date)
await db.leads.create_index(
    [("phone", 1), ("departement", 1), ("created_at", -1)],
    background=True,
    name="idx_duplicate_detection"
)

# Index pour anti double-submit (session + phone + date)
await db.leads.create_index(
    [("session_id", 1), ("phone", 1), ("created_at", -1)],
    background=True,
    name="idx_double_submit_detection"
)
```

---

## 2. RÈGLES DE DÉTECTION

### 2.1 Critères de doublon

| Critère | Valeur | Description |
|---------|--------|-------------|
| Téléphone | Exact | Numéro normalisé (format français 10 chiffres) |
| Département | Exact | Code département (01-95, 2A, 2B) |
| Fenêtre | 30 jours | Lead dans les 30 derniers jours |

**Formule** : `doublon = (phone == phone_existant) AND (dept == dept_existant) AND (created_at > now - 30 jours)`

### 2.2 Cas spécial: Anti double-submit

| Critère | Valeur | Description |
|---------|--------|-------------|
| Session | Exact | Même session_id |
| Téléphone | Exact | Même numéro |
| Fenêtre | 5 secondes | Soumission dans les 5 dernières secondes |

---

## 3. STATUTS ET COMPORTEMENTS

### 3.1 Nouveaux statuts ajoutés

| Statut | Condition | Livrable? | Redistribuable? |
|--------|-----------|-----------|-----------------|
| `doublon_recent` | Lead existant déjà livré (sent_to_crm=True) | ❌ Non | ❌ Non |
| `non_livre` | Lead existant non livré (sent_to_crm=False) | ❌ Non | ✅ Oui (original) |
| `double_submit` | Même session + phone dans les 5s | ❌ Non | ❌ Non |

### 3.2 Champs ajoutés au lead

```json
{
  "is_internal_duplicate": true,       // Boolean: doublon détecté par RDZ
  "duplicate_type": "doublon_recent",  // "doublon_recent" | "non_livre" | "double_submit" | null
  "original_lead_id": "abc123...",     // ID du lead original (si doublon)
  "is_doublon_recent": true,           // Shortcut pour doublon livré
  "is_non_livre": false,               // Shortcut pour doublon non livré
  "is_double_submit": false            // Shortcut pour double-clic
}
```

### 3.3 Flowchart de décision

```
                     ┌─────────────────┐
                     │   SOUMISSION    │
                     │     LEAD        │
                     └────────┬────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │ Phone valide?   │
                     │ Dept présent?   │
                     └────────┬────────┘
                              │
                    Non ──────┼────── Oui
                              │         │
                              ▼         ▼
                     ┌───────────┐ ┌─────────────────┐
                     │ Erreurs   │ │ CHECK DOUBLONS  │
                     │ (invalid, │ │ INTERNES RDZ    │
                     │ missing)  │ └────────┬────────┘
                     └───────────┘          │
                                            ▼
                              ┌─────────────────────────┐
                              │ Même phone + dept       │
                              │ dans les 30 jours?      │
                              └───────────┬─────────────┘
                                          │
                             Non ─────────┼─────────── Oui
                                          │              │
                                          ▼              ▼
                              ┌───────────────┐ ┌─────────────────┐
                              │ CHECK DOUBLE  │ │ Lead original   │
                              │ SUBMIT (5s)   │ │ livré?          │
                              └───────┬───────┘ └────────┬────────┘
                                      │                  │
                               Non ───┤           Oui ───┼─── Non
                                      │                  │       │
                                      ▼                  ▼       ▼
                              ┌───────────────┐ ┌─────────┐ ┌─────────┐
                              │ CONTINUER     │ │DOUBLON  │ │ NON     │
                              │ ROUTING CRM   │ │ RECENT  │ │ LIVRE   │
                              └───────────────┘ └─────────┘ └─────────┘
```

---

## 4. EXEMPLES D'UTILISATION

### 4.1 Lead nouveau (pas doublon)

```bash
curl -X POST "$API/api/public/leads" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc123",
    "form_code": "PV-006",
    "phone": "0712345678",
    "nom": "Dupont",
    "departement": "75"
  }'

# Réponse:
{
  "success": true,
  "lead_id": "...",
  "status": "success",  // ou pending, no_crm, etc.
  "crm": "zr7",
  "message": "Envoyé vers ZR7"
}
```

### 4.2 Doublon récent (déjà livré)

```bash
# Même phone + dept que lead existant livré
curl -X POST "$API/api/public/leads" \
  -d '{"session_id":"xyz","form_code":"PV-006","phone":"0712345678","nom":"Martin","departement":"75"}'

# Réponse:
{
  "success": true,
  "lead_id": "...",         // Nouveau lead créé mais non envoyé
  "status": "doublon_recent",
  "crm": "none",
  "message": "Doublon détecté - lead déjà livré (original: abc123...)",
  "warning": "DUPLICATE_DELIVERED",
  "stored": true            // Lead quand même stocké dans RDZ
}
```

### 4.3 Non livré (redistribuable)

```bash
# Même phone + dept que lead existant NON livré
# Réponse:
{
  "success": true,
  "lead_id": "...",
  "status": "non_livre",
  "message": "Doublon détecté - lead existant non livré (original: abc123...)",
  "warning": "DUPLICATE_NOT_SENT",
  "stored": true
}
```

### 4.4 Double-submit (protection)

```bash
# 2 soumissions rapides avec même session + phone
# Première réponse: normal
# Deuxième réponse:
{
  "success": true,
  "lead_id": "abc123...",   // ID du PREMIER lead (pas un nouveau)
  "status": "double_submit",
  "message": "Double soumission détectée - lead déjà créé",
  "warning": "DOUBLE_SUBMIT"
}
```

---

## 5. COMPORTEMENT CLÉS

### 5.1 Le lead est TOUJOURS créé

Même en cas de doublon, le lead est **toujours sauvegardé** dans RDZ avec les flags appropriés. Cela permet :
- Traçabilité complète
- Audit des tentatives
- Possibilité de redistribution manuelle si nécessaire

### 5.2 Pas d'envoi au CRM si doublon

Si un doublon est détecté (`doublon_recent` ou `non_livre`), le lead n'est **jamais** envoyé au CRM externe. Cela évite :
- Double facturation
- Pollution de la base CRM
- Rejection par le CRM (qui a sa propre détection)

### 5.3 Double-submit retourne l'ID original

En cas de double-clic, on retourne l'ID du **premier lead** créé, pas un nouveau. Le deuxième lead est quand même créé (pour audit) mais l'utilisateur reçoit une confirmation cohérente.

---

## 6. PRIORITÉ DES VÉRIFICATIONS

L'ordre de vérification dans `submit_lead()` est :

1. **Formulaire non trouvé** → `orphan`
2. **Téléphone invalide** → `invalid_phone`
3. **Champs obligatoires manquants** → `missing_required`
4. **Double-submit (5s)** → `double_submit`
5. **Doublon récent (livré)** → `doublon_recent`
6. **Doublon non livré** → `non_livre`
7. **CRM non configuré** → `no_crm`
8. **Clé API manquante** → `no_api_key`
9. **Pas de commande** → `pending_no_order`
10. **OK** → `pending` → envoi CRM

---

## 7. STATISTIQUES

Un endpoint pour récupérer les stats des doublons est disponible via le service :

```python
from services.duplicate_detector import get_duplicate_stats
stats = await get_duplicate_stats()
# {
#   "doublon_recent": 15,
#   "non_livre": 8,
#   "double_submit": 3,
#   "total_duplicates": 26,
#   "window_days": 30
# }
```

---

**Document créé le**: 12 février 2026  
**Auteur**: Agent E1  
**Validé**: Tests E2E passés avec succès
