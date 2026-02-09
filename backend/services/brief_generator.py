"""
Service de génération de Brief
Génère les scripts et instructions pour les développeurs
"""

from config import db, BACKEND_URL


async def generate_brief(form_id: str) -> dict:
    """
    Génère un brief complet pour un formulaire.
    Inclut les scripts LP et Form, les URLs, et les explications.
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
            liaison_code = f"{lp_code}_{form_code}"
    
    # API URL pour les scripts
    api_url = BACKEND_URL
    
    # ==================== SCRIPT LP ====================
    script_lp = ""
    if lp:
        script_lp = f'''<!-- SCRIPT LP - À coller sur : {lp_url} -->
<script>
(function() {{
  var CONFIG = {{
    API_URL: "{api_url}",
    LP_CODE: "{lp_code}",
    FORM_CODE: "{form_code}",
    FORM_URL: "{form_url}",
    LIAISON_CODE: "{liaison_code}"
  }};

  // Track visite LP au chargement
  function trackVisit() {{
    fetch(CONFIG.API_URL + "/api/track/lp-visit", {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{
        lp_code: CONFIG.LP_CODE,
        referrer: document.referrer
      }})
    }}).catch(function(e) {{ console.log("Tracking error:", e); }});
  }}

  // Track clic CTA
  window.trackCTAClick = function() {{
    fetch(CONFIG.API_URL + "/api/track/cta-click", {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{
        lp_code: CONFIG.LP_CODE,
        form_code: CONFIG.FORM_CODE
      }})
    }}).catch(function(e) {{ console.log("Tracking error:", e); }});
    
    // Rediriger vers le form avec le code de liaison
    var formUrl = CONFIG.FORM_URL;
    if (formUrl.indexOf("?") === -1) {{
      formUrl += "?lp=" + CONFIG.LP_CODE + "&liaison=" + CONFIG.LIAISON_CODE;
    }} else {{
      formUrl += "&lp=" + CONFIG.LP_CODE + "&liaison=" + CONFIG.LIAISON_CODE;
    }}
    window.location.href = formUrl;
  }};

  // Exécuter au chargement
  if (document.readyState === "loading") {{
    document.addEventListener("DOMContentLoaded", trackVisit);
  }} else {{
    trackVisit();
  }}
}})();
</script>

<!-- BOUTON CTA - Exemple d'utilisation -->
<button onclick="trackCTAClick()">Demander un devis gratuit</button>
'''

    # ==================== SCRIPT FORM ====================
    gtm_trigger = ""
    if tracking_type in ["gtm", "both"] and gtm.get("conversion"):
        gtm_trigger = f'''
    // Déclencher GTM
    {gtm.get("conversion", "")}'''
    
    redirect_trigger = ""
    if tracking_type in ["redirect", "both"]:
        redirect_trigger = f'''
    // Rediriger vers page merci
    window.location.href = "{redirect_url}";'''

    script_form = f'''<!-- SCRIPT FORMULAIRE - À coller sur : {form_url} -->
<script>
(function() {{
  var CONFIG = {{
    API_URL: "{api_url}",
    FORM_CODE: "{form_code}",
    LP_CODE: "{lp_code}",
    LIAISON_CODE: "{liaison_code}"
  }};

  // Récupérer LP depuis URL si présent
  var urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get("lp")) CONFIG.LP_CODE = urlParams.get("lp");
  if (urlParams.get("liaison")) CONFIG.LIAISON_CODE = urlParams.get("liaison");

  // Track début de formulaire (1ère interaction)
  var formStarted = false;
  window.trackFormStart = function() {{
    if (formStarted) return;
    formStarted = true;
    
    fetch(CONFIG.API_URL + "/api/track/form-start", {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{
        form_code: CONFIG.FORM_CODE,
        lp_code: CONFIG.LP_CODE,
        liaison_code: CONFIG.LIAISON_CODE
      }})
    }}).catch(function(e) {{ console.log("Tracking error:", e); }});
  }};

  // Soumettre le lead
  window.submitLead = function(leadData) {{
    // Validation téléphone
    var phone = leadData.phone.replace(/\\D/g, "");
    if (phone.length === 9 && phone[0] !== "0") phone = "0" + phone;
    
    if (phone.length !== 10) {{
      alert("Le numéro de téléphone doit contenir 10 chiffres");
      return Promise.reject("Téléphone invalide");
    }}
    if (phone === "0123456789" || /^0(\\d)\\1{{8}}$/.test(phone)) {{
      alert("Numéro de téléphone invalide");
      return Promise.reject("Téléphone invalide");
    }}

    // Préparer les données
    var payload = {{
      form_id: CONFIG.FORM_CODE,
      phone: phone,
      nom: leadData.nom || "",
      prenom: leadData.prenom || "",
      civilite: leadData.civilite || "",
      email: leadData.email || "",
      code_postal: leadData.code_postal || "",
      departement: (leadData.code_postal || "").substring(0, 2),
      type_logement: leadData.type_logement || "",
      statut_occupant: leadData.statut_occupant || "",
      facture_electricite: leadData.facture_electricite || "",
      lp_code: CONFIG.LP_CODE,
      liaison_code: CONFIG.LIAISON_CODE
    }};

    return fetch(CONFIG.API_URL + "/api/v1/leads", {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify(payload)
    }})
    .then(function(response) {{ return response.json(); }})
    .then(function(data) {{
      if (data.success) {{{gtm_trigger}{redirect_trigger}
      }} else {{
        alert("Erreur: " + (data.message || "Erreur inconnue"));
      }}
      return data;
    }})
    .catch(function(error) {{
      console.error("Erreur soumission:", error);
      alert("Une erreur est survenue. Veuillez réessayer.");
      throw error;
    }});
  }};
}})();
</script>

<!-- UTILISATION DANS VOTRE FORMULAIRE -->
<!--
1. Sur le premier champ ou bouton "Suivant", appelez:
   onclick="trackFormStart()"

2. À la soumission finale, appelez:
   submitLead({{
     phone: "0612345678",
     nom: "Dupont",
     prenom: "Jean",
     civilite: "M.",
     email: "jean@email.com",
     code_postal: "75001",
     type_logement: "Maison",
     statut_occupant: "Propriétaire",
     facture_electricite: "100-150€"
   }});
-->
'''

    # ==================== STATS EXPLIQUÉES ====================
    stats_explanation = f'''
📊 STATISTIQUES QUI REMONTERONT DANS VOTRE CRM

┌──────────────────────────────────────────────────────────────┐
│ ÉVÉNEMENTS TRACKÉS                                           │
├──────────────────────────────────────────────────────────────┤
│ • Visites LP    : Nombre de personnes qui voient la LP       │
│                   → Déclenché au chargement de la page LP    │
│                                                              │
│ • Clics CTA     : Nombre de clics sur "Demander un devis"    │
│                   → Déclenché quand trackCTAClick() appelé   │
│                                                              │
│ • Forms démarrés: Nombre qui commencent le formulaire        │
│                   → Déclenché quand trackFormStart() appelé  │
│                                                              │
│ • Leads terminés: Nombre qui valident (téléphone OK)         │
│                   → Déclenché quand submitLead() réussit     │
├──────────────────────────────────────────────────────────────┤
│ TAUX CALCULÉS                                                │
├──────────────────────────────────────────────────────────────┤
│ • LP → Clic      : (Clics CTA / Visites LP) × 100            │
│   Mesure l'efficacité de votre LP à générer des clics        │
│                                                              │
│ • Clic → Démarré : (Forms démarrés / Clics CTA) × 100        │
│   Mesure la transition entre LP et formulaire                │
│                                                              │
│ • Démarré → Fini : (Leads terminés / Forms démarrés) × 100   │
│   Mesure l'efficacité de votre formulaire                    │
│                                                              │
│ • GLOBAL         : (Leads terminés / Visites LP) × 100       │
│   Votre taux de conversion total du tunnel                   │
└──────────────────────────────────────────────────────────────┘
'''

    # ==================== VALIDATION TÉLÉPHONE ====================
    phone_validation = {
        "rules": [
            "10 chiffres obligatoires",
            "Doit commencer par 0",
            "Pas de suite (0123456789)",
            "Pas de répétition (0666666666)"
        ],
        "example": "0612345678"
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
        "stats_explanation": stats_explanation,
        "phone_validation": phone_validation,
        "api_url": api_url
    }
