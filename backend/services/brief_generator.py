"""
Service de génération de Brief
Génère les scripts et instructions pour les développeurs
Scripts LP et Form sont synchronisés avec le même code de liaison
"""

from config import db, BACKEND_URL


# Liste des champs disponibles pour les leads
LEAD_FIELDS = {
    "identite": [
        {"key": "phone", "label": "Téléphone", "required": True, "example": "0612345678"},
        {"key": "nom", "label": "Nom", "required": False, "example": "Dupont"},
        {"key": "prenom", "label": "Prénom", "required": False, "example": "Jean"},
        {"key": "civilite", "label": "Civilité", "required": False, "example": "M.", "options": ["M.", "Mme", "Mlle"]},
        {"key": "email", "label": "Email", "required": False, "example": "jean@email.com"},
    ],
    "localisation": [
        {"key": "code_postal", "label": "Code Postal", "required": False, "example": "75001"},
        {"key": "departement", "label": "Département", "required": False, "example": "75", "note": "Auto-extrait du code postal"},
        {"key": "ville", "label": "Ville", "required": False, "example": "Paris"},
        {"key": "adresse", "label": "Adresse", "required": False, "example": "12 rue de la Paix"},
    ],
    "logement": [
        {"key": "type_logement", "label": "Type de logement", "required": False, "example": "Maison", "options": ["Maison", "Appartement"]},
        {"key": "statut_occupant", "label": "Statut occupant", "required": False, "example": "Propriétaire", "options": ["Propriétaire", "Locataire"]},
        {"key": "surface_habitable", "label": "Surface habitable (m²)", "required": False, "example": "120"},
        {"key": "annee_construction", "label": "Année construction", "required": False, "example": "1985"},
        {"key": "type_chauffage", "label": "Type de chauffage", "required": False, "example": "Électrique", "options": ["Électrique", "Gaz", "Fioul", "Bois", "Autre"]},
    ],
    "energie": [
        {"key": "facture_electricite", "label": "Facture électricité mensuelle", "required": False, "example": "100-150€", "options": ["<50€", "50-100€", "100-150€", "150-200€", ">200€"]},
        {"key": "facture_chauffage", "label": "Facture chauffage annuelle", "required": False, "example": "1500€"},
    ],
    "projet": [
        {"key": "type_projet", "label": "Type de projet", "required": False, "example": "Installation", "options": ["Installation", "Remplacement", "Rénovation"]},
        {"key": "delai_projet", "label": "Délai projet", "required": False, "example": "3 mois", "options": ["Immédiat", "1-3 mois", "3-6 mois", "6-12 mois", "> 1 an"]},
        {"key": "budget", "label": "Budget estimé", "required": False, "example": "10000€"},
    ],
    "tracking": [
        {"key": "lp_code", "label": "Code LP", "required": False, "note": "Auto-transmis par le script LP"},
        {"key": "liaison_code", "label": "Code de liaison", "required": False, "note": "Auto-généré: LP_CODE_FORM_CODE"},
        {"key": "source", "label": "Source", "required": False, "example": "google"},
        {"key": "utm_source", "label": "UTM Source", "required": False},
        {"key": "utm_medium", "label": "UTM Medium", "required": False},
        {"key": "utm_campaign", "label": "UTM Campaign", "required": False},
    ],
    "consentement": [
        {"key": "rgpd_consent", "label": "Consentement RGPD", "required": False, "type": "boolean", "default": True},
        {"key": "newsletter", "label": "Newsletter", "required": False, "type": "boolean", "default": False},
    ]
}


async def generate_brief(form_id: str) -> dict:
    """
    Génère un brief complet pour un formulaire.
    Inclut les scripts LP et Form SYNCHRONISÉS, les URLs, et les explications.
    """
    # Récupérer le formulaire
    form = await db.forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        return {"error": "Formulaire non trouvé"}
    
    form_code = form.get("code", "")
    form_url = form.get("url", "")
    product_type = form.get("product_type", "")
    tracking_type = form.get("tracking_type", "redirect")
    redirect_url = form.get("redirect_url", "/merci")
    
    # Récupérer le compte
    account = await db.accounts.find_one({"id": form.get("account_id")}, {"_id": 0})
    account_name = account.get("name", "") if account else ""
    
    # Logos
    logos = {
        "main": account.get("logo_main_url", "") if account else "",
        "secondary": account.get("logo_secondary_url", "") if account else "",
        "mini": account.get("logo_mini_url", "") if account else ""
    }
    
    # GTM
    gtm = {
        "head": account.get("gtm_head", "") if account else "",
        "body": account.get("gtm_body", "") if account else "",
        "conversion": account.get("gtm_conversion", "") if account else ""
    }
    
    # LP liée ?
    lp = None
    lp_code = ""
    lp_url = ""
    liaison_code = ""
    
    if form.get("lp_id"):
        lp = await db.lps.find_one({"id": form["lp_id"]}, {"_id": 0})
        if lp:
            lp_code = lp.get("code", "")
            lp_url = lp.get("url", "")
            # Code de liaison SYNCHRONISÉ entre LP et Form
            liaison_code = f"{lp_code}_{form_code}"
    
    # API URL pour les scripts
    api_url = BACKEND_URL
    
    # ==================== SCRIPT LP ====================
    # Ce script est installé sur la Landing Page
    # Il track les visites et redirige vers le formulaire avec le code de liaison
    script_lp = ""
    if lp:
        script_lp = f'''<!-- ========================================== -->
<!-- SCRIPT LP - À coller sur : {lp_url} -->
<!-- Code LP: {lp_code} | Form lié: {form_code} -->
<!-- ========================================== -->
<script>
(function() {{
  // ========== CONFIGURATION ==========
  // Ces codes sont SYNCHRONISÉS avec le formulaire
  var CONFIG = {{
    API_URL: "{api_url}",
    LP_CODE: "{lp_code}",           // Code unique de cette LP
    FORM_CODE: "{form_code}",       // Code du formulaire lié
    FORM_URL: "{form_url}",         // URL du formulaire
    LIAISON_CODE: "{liaison_code}"  // Code de liaison LP_FORM
  }};

  // ========== TRACK VISITE LP ==========
  // Appelé automatiquement au chargement de la page
  function trackVisit() {{
    fetch(CONFIG.API_URL + "/api/track/lp-visit", {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{
        lp_code: CONFIG.LP_CODE,
        referrer: document.referrer
      }})
    }}).catch(function(e) {{ console.log("[EnerSolar] Tracking LP visit error:", e); }});
  }}

  // ========== TRACK CLIC CTA ==========
  // À appeler sur le clic du bouton CTA
  window.trackCTAClick = function() {{
    // Track le clic
    fetch(CONFIG.API_URL + "/api/track/cta-click", {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{
        lp_code: CONFIG.LP_CODE,
        form_code: CONFIG.FORM_CODE
      }})
    }}).catch(function(e) {{ console.log("[EnerSolar] Tracking CTA error:", e); }});
    
    // Construire l'URL du formulaire avec les paramètres de tracking
    var formUrl = CONFIG.FORM_URL;
    var separator = formUrl.indexOf("?") === -1 ? "?" : "&";
    formUrl += separator + "lp=" + CONFIG.LP_CODE + "&liaison=" + CONFIG.LIAISON_CODE;
    
    // Ajouter les UTM si présents dans l'URL actuelle
    var urlParams = new URLSearchParams(window.location.search);
    ["utm_source", "utm_medium", "utm_campaign"].forEach(function(param) {{
      if (urlParams.get(param)) {{
        formUrl += "&" + param + "=" + encodeURIComponent(urlParams.get(param));
      }}
    }});
    
    // Redirection vers le formulaire
    window.location.href = formUrl;
  }};

  // ========== AUTO-INIT ==========
  if (document.readyState === "loading") {{
    document.addEventListener("DOMContentLoaded", trackVisit);
  }} else {{
    trackVisit();
  }}
  
  console.log("[EnerSolar] Script LP initialisé - Code:", CONFIG.LP_CODE);
}})();
</script>

<!-- ========== EXEMPLE D'UTILISATION ========== -->
<!-- 
Ajoutez onclick="trackCTAClick()" sur votre bouton CTA:

<button onclick="trackCTAClick()" class="btn-cta">
  Demander un devis gratuit
</button>

Ou avec un lien:
<a href="javascript:void(0)" onclick="trackCTAClick()">
  Obtenir mon estimation
</a>
-->
'''

    # ==================== SCRIPT FORM ====================
    # Ce script est installé sur le Formulaire
    # Il récupère les codes de la LP et envoie les leads à l'API
    gtm_trigger = ""
    if tracking_type in ["gtm", "both"] and gtm.get("conversion"):
        gtm_trigger = f'''
        // Déclencher GTM conversion
        {gtm.get("conversion", "")}'''
    
    redirect_trigger = ""
    if tracking_type in ["redirect", "both"]:
        redirect_trigger = f'''
        // Rediriger vers page merci
        window.location.href = "{redirect_url}";'''

    script_form = f'''<!-- ========================================== -->
<!-- SCRIPT FORMULAIRE - À coller sur : {form_url} -->
<!-- Code Form: {form_code} | LP liée: {lp_code or "Aucune"} -->
<!-- ========================================== -->
<script>
(function() {{
  // ========== CONFIGURATION ==========
  // Ces codes sont SYNCHRONISÉS avec la LP
  var CONFIG = {{
    API_URL: "{api_url}",
    FORM_CODE: "{form_code}",       // Code unique de ce formulaire
    LP_CODE: "{lp_code}",           // Code LP par défaut (si liée)
    LIAISON_CODE: "{liaison_code}"  // Code de liaison LP_FORM
  }};

  // ========== RÉCUPÉRER PARAMÈTRES URL ==========
  // Les paramètres venant de la LP ont priorité
  var urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get("lp")) CONFIG.LP_CODE = urlParams.get("lp");
  if (urlParams.get("liaison")) CONFIG.LIAISON_CODE = urlParams.get("liaison");
  
  // Récupérer UTM
  var UTM = {{
    source: urlParams.get("utm_source") || "",
    medium: urlParams.get("utm_medium") || "",
    campaign: urlParams.get("utm_campaign") || ""
  }};

  // ========== TRACK DÉBUT FORMULAIRE ==========
  // À appeler sur la première interaction (clic "Suivant", premier champ...)
  var formStarted = false;
  window.trackFormStart = function() {{
    if (formStarted) return; // Éviter les doublons
    formStarted = true;
    
    fetch(CONFIG.API_URL + "/api/track/form-start", {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{
        form_code: CONFIG.FORM_CODE,
        lp_code: CONFIG.LP_CODE,
        liaison_code: CONFIG.LIAISON_CODE
      }})
    }}).catch(function(e) {{ console.log("[EnerSolar] Tracking form start error:", e); }});
  }};

  // ========== VALIDATION TÉLÉPHONE ==========
  window.validatePhone = function(phone) {{
    var digits = phone.replace(/\\D/g, "");
    
    // Ajouter 0 si 9 chiffres
    if (digits.length === 9 && digits[0] !== "0") {{
      digits = "0" + digits;
    }}
    
    // Vérifications
    if (digits.length !== 10) {{
      return {{ valid: false, error: "Le numéro doit contenir 10 chiffres" }};
    }}
    if (!digits.startsWith("0")) {{
      return {{ valid: false, error: "Le numéro doit commencer par 0" }};
    }}
    if (digits === "0123456789" || /^0(\\d)\\1{{8}}$/.test(digits)) {{
      return {{ valid: false, error: "Numéro invalide" }};
    }}
    
    return {{ valid: true, phone: digits }};
  }};

  // ========== SOUMETTRE LE LEAD ==========
  // Appeler cette fonction à la soumission finale du formulaire
  window.submitLead = function(leadData) {{
    // Valider téléphone
    var phoneCheck = validatePhone(leadData.phone || "");
    if (!phoneCheck.valid) {{
      alert(phoneCheck.error);
      return Promise.reject(phoneCheck.error);
    }}

    // Construire le payload avec TOUS les champs
    var payload = {{
      // Obligatoire
      form_id: CONFIG.FORM_CODE,
      phone: phoneCheck.phone,
      
      // Identité
      nom: leadData.nom || "",
      prenom: leadData.prenom || "",
      civilite: leadData.civilite || "",
      email: leadData.email || "",
      
      // Localisation
      code_postal: leadData.code_postal || "",
      departement: (leadData.code_postal || "").substring(0, 2),
      ville: leadData.ville || "",
      adresse: leadData.adresse || "",
      
      // Logement
      type_logement: leadData.type_logement || "",
      statut_occupant: leadData.statut_occupant || "",
      surface_habitable: leadData.surface_habitable || "",
      annee_construction: leadData.annee_construction || "",
      type_chauffage: leadData.type_chauffage || "",
      
      // Énergie
      facture_electricite: leadData.facture_electricite || "",
      facture_chauffage: leadData.facture_chauffage || "",
      
      // Projet
      type_projet: leadData.type_projet || "",
      delai_projet: leadData.delai_projet || "",
      budget: leadData.budget || "",
      
      // Tracking (SYNCHRONISÉ avec la LP)
      lp_code: CONFIG.LP_CODE,
      liaison_code: CONFIG.LIAISON_CODE,
      source: leadData.source || UTM.source || "",
      utm_source: UTM.source,
      utm_medium: UTM.medium,
      utm_campaign: UTM.campaign,
      
      // Consentement
      rgpd_consent: leadData.rgpd_consent !== false,
      newsletter: leadData.newsletter || false
    }};

    // Envoi à l'API
    return fetch(CONFIG.API_URL + "/api/v1/leads", {{
      method: "POST",
      headers: {{ 
        "Content-Type": "application/json",
        "Authorization": "Token VOTRE_CLE_API"  // Remplacer par votre clé
      }},
      body: JSON.stringify(payload)
    }})
    .then(function(response) {{ return response.json(); }})
    .then(function(data) {{
      if (data.success) {{
        console.log("[EnerSolar] Lead envoyé avec succès:", data.lead_id);{gtm_trigger}{redirect_trigger}
      }} else {{
        console.error("[EnerSolar] Erreur envoi lead:", data.error || data.message);
        alert("Erreur: " + (data.error || data.message || "Une erreur est survenue"));
      }}
      return data;
    }})
    .catch(function(error) {{
      console.error("[EnerSolar] Erreur technique:", error);
      alert("Une erreur technique est survenue. Veuillez réessayer.");
      throw error;
    }});
  }};

  // ========== AUTO-INIT ==========
  console.log("[EnerSolar] Script Form initialisé - Code:", CONFIG.FORM_CODE);
  if (CONFIG.LP_CODE) {{
    console.log("[EnerSolar] LP liée:", CONFIG.LP_CODE, "| Liaison:", CONFIG.LIAISON_CODE);
  }}
}})();
</script>

<!-- ========== EXEMPLE D'UTILISATION ========== -->
<!--
1. Sur le premier champ ou bouton "Suivant":
   <input type="text" onfocus="trackFormStart()" placeholder="Votre nom">
   <button type="button" onclick="trackFormStart()">Suivant</button>

2. À la soumission finale:
   <button type="button" onclick="submitMyForm()">Valider</button>

   <script>
   function submitMyForm() {{
     submitLead({{
       // Obligatoire
       phone: document.getElementById('phone').value,
       
       // Identité
       nom: document.getElementById('nom').value,
       prenom: document.getElementById('prenom').value,
       email: document.getElementById('email').value,
       
       // Localisation
       code_postal: document.getElementById('code_postal').value,
       
       // Logement
       type_logement: document.getElementById('type_logement').value,
       statut_occupant: document.getElementById('statut_occupant').value,
       
       // Énergie
       facture_electricite: document.getElementById('facture').value
     }});
   }}
   </script>
-->
'''

    # ==================== STATS EXPLIQUÉES ====================
    stats_explanation = f'''
📊 STATISTIQUES TRACKÉES ET REMONTÉES DANS VOTRE CRM

┌────────────────────────────────────────────────────────────────┐
│ 🔵 ÉVÉNEMENTS SUR LA LANDING PAGE ({lp_code or "Pas de LP liée"})            │
├────────────────────────────────────────────────────────────────┤
│ • Visites LP      : Nombre de visiteurs sur la LP              │
│                     → Déclenché automatiquement au chargement  │
│                                                                │
│ • Clics CTA       : Nombre de clics sur le bouton d'action     │
│                     → Déclenché par trackCTAClick()            │
├────────────────────────────────────────────────────────────────┤
│ 🟢 ÉVÉNEMENTS SUR LE FORMULAIRE ({form_code})                  │
├────────────────────────────────────────────────────────────────┤
│ • Forms démarrés  : Nombre qui commencent le formulaire        │
│                     → Déclenché par trackFormStart()           │
│                                                                │
│ • Leads terminés  : Nombre qui valident (téléphone OK)         │
│                     → Déclenché par submitLead() avec succès   │
├────────────────────────────────────────────────────────────────┤
│ 📈 TAUX DE CONVERSION                                          │
├────────────────────────────────────────────────────────────────┤
│ • LP → CTA        : (Clics CTA / Visites LP) × 100             │
│   → Mesure l'efficacité de votre LP à générer des clics        │
│                                                                │
│ • CTA → Démarré   : (Forms démarrés / Clics CTA) × 100         │
│   → Mesure la transition entre LP et formulaire                │
│                                                                │
│ • Démarré → Fini  : (Leads terminés / Forms démarrés) × 100    │
│   → Mesure l'efficacité de votre formulaire                    │
│                                                                │
│ • CONVERSION TOTALE: (Leads terminés / Visites LP) × 100       │
│   → Votre taux de conversion global du tunnel                  │
└────────────────────────────────────────────────────────────────┘

🔗 CODE DE LIAISON: {liaison_code or "Aucun (pas de LP liée)"}
   Ce code unique permet de tracer tout le parcours d'un visiteur
   de la LP jusqu'à la conversion.
'''

    # ==================== VALIDATION TÉLÉPHONE ====================
    phone_validation = {
        "rules": [
            "10 chiffres obligatoires",
            "Doit commencer par 0",
            "Pas de suite (0123456789)",
            "Pas de répétition (0666666666)"
        ],
        "example": "0612345678",
        "auto_format": "Si 9 chiffres sans 0, ajoute automatiquement le 0"
    }

    # ==================== RÉSULTAT ====================
    return {
        "form": {
            "id": form_id,
            "code": form_code,
            "name": form.get("name", ""),
            "url": form_url,
            "product_type": product_type,
            "tracking_type": tracking_type,
            "redirect_url": redirect_url
        },
        "lp": {
            "id": lp.get("id") if lp else None,
            "code": lp_code,
            "name": lp.get("name") if lp else None,
            "url": lp_url,
            "linked": lp is not None
        },
        "liaison_code": liaison_code,
        "account": {
            "name": account_name,
            "logos": logos,
            "gtm": gtm
        },
        "scripts": {
            "lp": script_lp if lp else None,
            "form": script_form
        },
        "lead_fields": LEAD_FIELDS,
        "stats_explanation": stats_explanation,
        "phone_validation": phone_validation,
        "api_url": api_url
    }
