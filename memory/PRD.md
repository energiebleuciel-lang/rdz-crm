# EnerSolar CRM - Gestion de Leads Solaires

## Problème Original
CRM multi-tenant pour centraliser et redistribuer les leads solaires (PAC, PV, ITE) vers ZR7 Digital et Maison du Lead.

## Fonctionnalités Implémentées (09/02/2026)

### ✅ Codes Formulaires Auto-générés
- Format automatique: `PV-001`, `PAC-002`, `ITE-003`
- Compteur intelligent par type de produit
- Fonctionne pour création ET duplication

### ✅ Statistiques de Conversion
- **Démarré** = Premier clic sur bouton "Suivant" ou "Commencer" (trackFormStart())
- **Terminé** = Clic sur bouton final après validation téléphone (submitLeadToCRM())
- **% Conversion** = Terminés / Démarrés × 100

### ✅ Brief Développeur Complet
- Endpoint `/api/forms/{form_id}/brief`
- Script de tracking multi-étapes
- Support logo/badge du compte
- Aides financières avec montants

### ✅ UI Formulaires Style Landbot
- Vue cartes avec stats visuelles
- Filtres par produit (PV/PAC/ITE)
- Actions: Brief, Copier ID, Éditer, Dupliquer, Archiver

## Comment fonctionne le tracking ?

```
ÉTAPE 1 (Premier bouton "Suivant")
  └── trackFormStart() → compteur "Démarrés" +1

ÉTAPE 2, 3... (Navigation)
  └── Pas de tracking

ÉTAPE FINALE (Bouton "Recevoir mon devis" - après validation téléphone)
  └── submitLeadToCRM() → compteur "Terminés" +1
```

## Script de Tracking (Exemple)

```html
<!-- Bouton SUIVANT (déclenche Démarré) -->
<button onclick="trackFormStart(); showStep(2);">Suivant →</button>

<!-- Bouton FINAL (déclenche Terminé - disabled si téléphone invalide) -->
<button onclick="submitForm();" id="submitBtn" disabled>
  ✓ Recevoir mon devis gratuit
</button>

<script>
// Activer le bouton final seulement si téléphone valide
document.querySelector('input[name="phone"]').addEventListener('input', function(e) {
  var isValid = /^0[0-9]{9}$/.test(e.target.value.replace(/\s/g, ''));
  document.getElementById('submitBtn').disabled = !isValid;
});
</script>
```

## Aides Financières par Produit

### PV (Panneaux Solaires)
- Prime Autoconsommation: Jusqu'à 2 520€
- TVA Réduite: 10% au lieu de 20%
- Revente EDF OA

### PAC (Pompes à Chaleur)
- MaPrimeRénov': Jusqu'à 11 000€
- Prime CEE: Variable
- TVA Réduite: 5.5%
- Éco-PTZ: Jusqu'à 50 000€

### ITE (Isolation)
- MaPrimeRénov': Jusqu'à 75€/m²
- Prime CEE: Variable
- TVA Réduite: 5.5%

## Credentials Test
- **Email**: energiebleuciel@gmail.com
- **Password**: 92Ruemarxdormoy

## Backlog

### En Attente
- [ ] Vérification SendGrid (Settings → Sender Authentication)
- [ ] Configuration des Aides dans le formulaire de création
- [ ] File d'attente leads (si API down)

### Technique
- [ ] Refactoring App.js en composants
- [ ] Refactoring server.py en modules

## Déploiement
- **Live**: https://rdz-group-ltd.online
- **Preview**: https://leadflow-106.preview.emergentagent.com
- **GitHub**: PRIVÉ ✅
