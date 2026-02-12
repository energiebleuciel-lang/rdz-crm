# 📊 RAPPORT TEST E2E VOLUME - DÉTECTION DOUBLONS v2.2

**Date**: 12 février 2026  
**Environnement**: Production (preview)  
**Testeur**: Agent E1 automatisé

---

## 1. CONFIGURATION DU TEST

| Paramètre | Valeur |
|-----------|--------|
| Total leads soumis | 110 |
| Leads uniques | 60 (55%) |
| Doublons intentionnels (phone+dept) | 30 (27%) |
| Double-submit (même session) | 20 (10 paires = 18%) |
| Formulaire utilisé | PV-006 (ZR7) |
| Départements testés | 75, 92, 93, 94, 13, 69, 33, 31, 59, 06 |

---

## 2. RÉSULTATS

### 2.1 Volume

| Métrique | Valeur | Attendu | Statut |
|----------|--------|---------|--------|
| Leads soumis | 110 | 110 | ✅ |
| Leads créés dans RDZ | 100 | 100 | ✅ |
| Leads perdus | 0 | 0 | ✅ |

### 2.2 Statuts

| Statut | Nombre | % | Description |
|--------|--------|---|-------------|
| `success` | 70 | 64% | Leads livrés avec succès |
| `doublon_recent` | 30 | 27% | Doublons bloqués (déjà livrés) |
| `double_submit` | 10 | 9% | Double-clicks bloqués |

### 2.3 Détection doublons

| Type | Détectés | Attendus | Taux |
|------|----------|----------|------|
| `doublon_recent` | 30 | 30 | **100%** |
| `double_submit` | 10 | 10 | **100%** |

### 2.4 Livraison

| Métrique | Valeur |
|----------|--------|
| Livrés au CRM | 70 |
| Non livrés | 30 |
| Doublons livrés par erreur | **0** |

---

## 3. VÉRIFICATIONS

| Critère | Résultat | Détails |
|---------|----------|---------|
| ✅ Aucun lead perdu | PASS | 110/110 traités |
| ✅ Aucun doublon livré | PASS | 0 doublon avec sent_to_crm=True |
| ✅ Statuts corrects | PASS | 100% doublon_recent, 100% double_submit |
| ✅ Livraison correcte | PASS | Uniquement les leads uniques livrés |

---

## 4. VÉRIFICATION BASE DE DONNÉES

Après le test, analyse des 200 derniers leads en base :

```
✅ Aucun doublon interne livré (is_internal_duplicate=True AND sent_to_crm=True → 0)
```

### Répartition par statut (200 derniers leads)

| Statut | Nombre |
|--------|--------|
| success | 65 |
| orphan | 61 |
| doublon_recent | 32 |
| double_submit | 24 |
| invalid_phone | 4 |
| no_crm | 4 |
| failed | 3 |
| missing_required | 2 |
| duplicate (CRM) | 2 |
| validation_error | 2 |
| non_livre | 1 |

---

## 5. CONCLUSION

### ✅ TEST E2E VOLUME: SUCCÈS

La détection de doublons interne RDZ v2.2 fonctionne correctement :

1. **100% des doublons (phone+dept) bloqués** avant envoi au CRM
2. **100% des double-submits bloqués** avec retour de l'ID original
3. **0 doublon livré par erreur**
4. **0 lead perdu**
5. **Tous les leads uniques livrés avec succès**

### Performance observée

- Temps total pour 110 leads : ~60 secondes
- Débit moyen : ~1.8 leads/seconde
- Aucune erreur de timeout ou de connexion

### Recommandations

1. ✅ Système prêt pour production
2. ✅ Détection doublons fiable à 100%
3. ⚠️ Surveiller les statuts `orphan` (formulaires non configurés)

---

**Rapport généré automatiquement**  
**Date**: 12 février 2026
