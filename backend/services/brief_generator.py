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
    if tracking_type in ["redirect", "both"] and redirect_url:
        redirect_trigger = f'''
        // Rediriger vers page merci
        window.location.href = "{redirect_url}";'''
    
    # Si tracking_type = "none", pas de trigger automatique
    if tracking_type == "none":
        gtm_trigger = ""
        redirect_trigger = ""
        after_submit_comment = "// Pas d'action automatique - le formulaire gère lui-même la suite"
    else:
        after_submit_comment = ""

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

    # ==================== RÉSULTAT SIMPLIFIÉ ====================
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
        "api_url": api_url
    }



async def generate_brief_for_lp(lp_id: str) -> dict:
    """
    Génère un brief complet pour une LP + Form (duo)
    - Mode EMBEDDED : 1 script unique (tout sur même page)
    - Mode REDIRECT : 2 scripts séparés (LP + Form)
    Inclut le bandeau CGU/Privacy pour la LP
    """
    # Récupérer la LP
    lp = await db.lps.find_one({"id": lp_id}, {"_id": 0})
    if not lp:
        return {"error": "LP non trouvée"}
    
    lp_code = lp.get("code", "")
    lp_url = lp.get("url", "")
    lp_name = lp.get("name", "")
    form_mode = lp.get("form_mode", "redirect")  # embedded ou redirect
    form_id = lp.get("form_id")
    product_type = lp.get("product_type", "")
    tracking_type = lp.get("tracking_type", "redirect")
    redirect_url = lp.get("redirect_url", "/merci")
    
    # Récupérer le Form lié
    form = None
    form_code = ""
    form_url = ""
    if form_id:
        form = await db.forms.find_one({"id": form_id}, {"_id": 0})
        if form:
            form_code = form.get("code", "")
            form_url = form.get("url", "")
    
    if not form:
        return {"error": "Form lié non trouvé"}
    
    # Code de liaison
    liaison_code = f"{lp_code}_{form_code}"
    
    # Récupérer le compte
    account = await db.accounts.find_one({"id": lp.get("account_id")}, {"_id": 0})
    if not account:
        return {"error": "Compte non trouvé"}
    
    account_name = account.get("name", "")
    
    # Logos
    logos = {
        "main": account.get("logo_main_url", ""),
        "secondary": account.get("logo_secondary_url", ""),
        "mini": account.get("logo_mini_url", "")
    }
    
    # GTM
    gtm = {
        "head": account.get("gtm_head", ""),
        "body": account.get("gtm_body", ""),
        "conversion": account.get("gtm_conversion", "")
    }
    
    # Textes légaux (cgu_text est le nouveau champ, legal_mentions_text est l'ancien fallback)
    legal = {
        "cgu": account.get("cgu_text", "") or account.get("legal_mentions_text", ""),
        "privacy": account.get("privacy_policy_text", "")
    }
    
    api_url = BACKEND_URL
    
    # ==================== LOGOS HTML ====================
    logos_html = ""
    if logos.get("main") or logos.get("secondary") or logos.get("mini"):
        logos_html = f'''
<!-- ========== LOGOS (à utiliser dans votre page) ========== -->
<!-- Logo Principal (Header gauche) -->
{f'<img src="{logos.get("main")}" alt="{account_name}" style="height:50px;width:auto;" class="logo-main" />' if logos.get("main") else "<!-- Pas de logo principal configuré -->"}

<!-- Logo Secondaire (Header droite) -->
{f'<img src="{logos.get("secondary")}" alt="{account_name}" style="height:40px;width:auto;" class="logo-secondary" />' if logos.get("secondary") else "<!-- Pas de logo secondaire configuré -->"}

<!-- Favicon / Mini Logo -->
{f'<link rel="icon" href="{logos.get("mini")}" type="image/x-icon" />' if logos.get("mini") else "<!-- Pas de favicon configuré -->"}

<!-- URLs des logos pour utilisation dynamique -->
<script>
window.__LOGOS__ = {{
  main: "{logos.get('main', '')}",
  secondary: "{logos.get('secondary', '')}",
  mini: "{logos.get('mini', '')}"
}};
</script>
'''

    # ==================== BOUTONS CGU/PRIVACY (popup/accordion) ====================
    legal_buttons_html = ""
    if legal.get("cgu") or legal.get("privacy"):
        legal_buttons_html = f'''
<!-- ========== BOUTONS CGU/PRIVACY (à placer en bas de page) ========== -->
<div id="legal-buttons" style="position:fixed;bottom:0;left:0;right:0;background:#f8f9fa;border-top:1px solid #e9ecef;padding:10px 20px;font-size:12px;z-index:9999;">
  <div style="max-width:1200px;margin:0 auto;display:flex;justify-content:center;gap:30px;align-items:center;">
    {f"""<button onclick="openLegalPopup('cgu')" 
            style="background:none;border:none;color:#007bff;cursor:pointer;padding:5px 10px;font-size:12px;text-decoration:underline;">
      Conditions Générales d'Utilisation
    </button>""" if legal.get("cgu") else ""}
    {f"""<button onclick="openLegalPopup('privacy')" 
            style="background:none;border:none;color:#007bff;cursor:pointer;padding:5px 10px;font-size:12px;text-decoration:underline;">
      Politique de Confidentialité
    </button>""" if legal.get("privacy") else ""}
    <span style="color:#6c757d;">© {account_name}</span>
  </div>
</div>

<!-- Popup CGU/Privacy -->
<div id="legal-popup" style="display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);z-index:10000;justify-content:center;align-items:center;">
  <div style="background:white;border-radius:8px;max-width:700px;width:90%;max-height:80vh;overflow:hidden;box-shadow:0 10px 40px rgba(0,0,0,0.2);">
    <div style="padding:15px 20px;border-bottom:1px solid #e9ecef;display:flex;justify-content:space-between;align-items:center;">
      <h3 id="legal-popup-title" style="margin:0;font-size:16px;color:#333;"></h3>
      <button onclick="closeLegalPopup()" style="background:none;border:none;font-size:24px;cursor:pointer;color:#666;">&times;</button>
    </div>
    <div id="legal-popup-content" style="padding:20px;overflow-y:auto;max-height:60vh;font-size:13px;line-height:1.6;color:#444;"></div>
  </div>
</div>

<script>
// Textes légaux
var __LEGAL_TEXTS__ = {{
  cgu: `{legal.get("cgu", "").replace("`", "\\`").replace("${", "\\${") if legal.get("cgu") else ""}`,
  privacy: `{legal.get("privacy", "").replace("`", "\\`").replace("${", "\\${") if legal.get("privacy") else ""}`
}};

function openLegalPopup(type) {{
  var popup = document.getElementById('legal-popup');
  var title = document.getElementById('legal-popup-title');
  var content = document.getElementById('legal-popup-content');
  
  title.textContent = type === 'cgu' ? "Conditions Générales d'Utilisation" : "Politique de Confidentialité";
  content.innerHTML = __LEGAL_TEXTS__[type].replace(/\\n/g, '<br>');
  popup.style.display = 'flex';
}}

function closeLegalPopup() {{
  document.getElementById('legal-popup').style.display = 'none';
}}

// Fermer popup en cliquant dehors
document.getElementById('legal-popup').addEventListener('click', function(e) {{
  if (e.target === this) closeLegalPopup();
}});
</script>
'''

    # ==================== GÉNÉRATION SCRIPTS ====================
    
    # GTM trigger après submit
    gtm_trigger = ""
    if tracking_type in ["gtm", "both"] and gtm.get("conversion"):
        gtm_trigger = f'''
        // Déclencher GTM conversion
        {gtm.get("conversion", "")}'''
    
    redirect_trigger = ""
    if tracking_type in ["redirect", "both"] and redirect_url:
        redirect_trigger = f'''
        // Rediriger vers page merci
        window.location.href = "{redirect_url}";'''

    if form_mode == "embedded":
        # ==================== MODE EMBEDDED : 1 SCRIPT UNIQUE ====================
        script_combined = f'''<!-- ================================================================ -->
<!-- SCRIPT LP + FORM COMBINÉ (Mode Embedded - Même page)            -->
<!-- LP: {lp_code} | Form: {form_code} | Liaison: {liaison_code}     -->
<!-- À coller sur : {lp_url}                                          -->
<!-- ================================================================ -->

{f"""<!-- GTM Head -->
{gtm.get("head", "")}""" if gtm.get("head") else ""}

<script>
(function() {{
  // ========== CONFIGURATION ==========
  var CONFIG = {{
    API_URL: "{api_url}",
    LP_CODE: "{lp_code}",
    FORM_CODE: "{form_code}",
    LIAISON_CODE: "{liaison_code}",
    PRODUCT_TYPE: "{product_type}",
    MODE: "embedded"
  }};

  // Exposer le contexte pour le formulaire
  window.__EnerSolar_CONTEXT__ = CONFIG;

  // ========== UTM PARAMS ==========
  var urlParams = new URLSearchParams(window.location.search);
  var UTM = {{
    source: urlParams.get("utm_source") || "",
    medium: urlParams.get("utm_medium") || "",
    campaign: urlParams.get("utm_campaign") || ""
  }};

  // ========== TRACKING LP ==========
  function trackLPView() {{
    fetch(CONFIG.API_URL + "/api/track/lp-visit", {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{
        lp_code: CONFIG.LP_CODE,
        referrer: document.referrer
      }})
    }}).catch(function(e) {{ console.log("[EnerSolar] LP view error:", e); }});
    
    // Push GTM dataLayer
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({{
      event: "lp_view",
      lp_code: CONFIG.LP_CODE,
      product_type: CONFIG.PRODUCT_TYPE
    }});
  }}

  // ========== TRACKING CTA (scroll vers form) ==========
  window.trackCTAClick = function(ctaId, ctaText) {{
    fetch(CONFIG.API_URL + "/api/track/cta-click", {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{
        lp_code: CONFIG.LP_CODE,
        form_code: CONFIG.FORM_CODE
      }})
    }}).catch(function(e) {{ console.log("[EnerSolar] CTA click error:", e); }});
    
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({{
      event: "cta_click",
      lp_code: CONFIG.LP_CODE,
      cta_id: ctaId || "unknown",
      cta_text: ctaText || "unknown"
    }});
    
    // Scroll vers le formulaire
    var formEl = document.getElementById("form-container") || document.getElementById("formulaire");
    if (formEl) {{
      formEl.scrollIntoView({{ behavior: "smooth", block: "start" }});
    }}
  }};

  // ========== TRACKING FORM START ==========
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
    }}).catch(function(e) {{ console.log("[EnerSolar] Form start error:", e); }});
    
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({{
      event: "form_start",
      form_code: CONFIG.FORM_CODE,
      lp_code: CONFIG.LP_CODE
    }});
  }};

  // ========== VALIDATION TÉLÉPHONE ==========
  window.validatePhone = function(phone) {{
    var digits = phone.replace(/\\D/g, "");
    if (digits.length === 9 && digits[0] !== "0") digits = "0" + digits;
    if (digits.length !== 10) return {{ valid: false, error: "Le numéro doit contenir 10 chiffres" }};
    if (!digits.startsWith("0")) return {{ valid: false, error: "Le numéro doit commencer par 0" }};
    if (digits === "0123456789" || /^0(\\d)\\1{{8}}$/.test(digits)) return {{ valid: false, error: "Numéro invalide" }};
    return {{ valid: true, phone: digits }};
  }};

  // ========== SOUMISSION LEAD ==========
  window.submitLead = function(leadData) {{
    var phoneCheck = validatePhone(leadData.phone || "");
    if (!phoneCheck.valid) {{
      alert(phoneCheck.error);
      return Promise.reject(phoneCheck.error);
    }}

    var payload = {{
      form_id: CONFIG.FORM_CODE,
      phone: phoneCheck.phone,
      nom: leadData.nom || "",
      prenom: leadData.prenom || "",
      civilite: leadData.civilite || "",
      email: leadData.email || "",
      code_postal: leadData.code_postal || "",
      departement: (leadData.code_postal || "").substring(0, 2),
      ville: leadData.ville || "",
      adresse: leadData.adresse || "",
      type_logement: leadData.type_logement || "",
      statut_occupant: leadData.statut_occupant || "",
      surface_habitable: leadData.surface_habitable || "",
      annee_construction: leadData.annee_construction || "",
      type_chauffage: leadData.type_chauffage || "",
      facture_electricite: leadData.facture_electricite || "",
      facture_chauffage: leadData.facture_chauffage || "",
      type_projet: leadData.type_projet || "",
      delai_projet: leadData.delai_projet || "",
      budget: leadData.budget || "",
      lp_code: CONFIG.LP_CODE,
      liaison_code: CONFIG.LIAISON_CODE,
      source: leadData.source || UTM.source || "",
      utm_source: UTM.source,
      utm_medium: UTM.medium,
      utm_campaign: UTM.campaign,
      rgpd_consent: leadData.rgpd_consent !== false,
      newsletter: leadData.newsletter || false
    }};

    return fetch(CONFIG.API_URL + "/api/v1/leads", {{
      method: "POST",
      headers: {{ 
        "Content-Type": "application/json",
        "Authorization": "Token VOTRE_CLE_API"
      }},
      body: JSON.stringify(payload)
    }})
    .then(function(response) {{ return response.json(); }})
    .then(function(data) {{
      if (data.success) {{
        console.log("[EnerSolar] Lead envoyé:", data.lead_id);
        
        window.dataLayer = window.dataLayer || [];
        window.dataLayer.push({{
          event: "form_submit",
          form_code: CONFIG.FORM_CODE,
          lp_code: CONFIG.LP_CODE,
          lead_id: data.lead_id,
          product_type: CONFIG.PRODUCT_TYPE,
          department: payload.departement
        }});{gtm_trigger}{redirect_trigger}
      }} else {{
        console.error("[EnerSolar] Erreur:", data.error || data.message);
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

  // ========== INIT ==========
  if (document.readyState === "loading") {{
    document.addEventListener("DOMContentLoaded", trackLPView);
  }} else {{
    trackLPView();
  }}
  
  console.log("[EnerSolar] Script LP+Form initialisé (embedded)");
  console.log("[EnerSolar] LP:", CONFIG.LP_CODE, "| Form:", CONFIG.FORM_CODE, "| Liaison:", CONFIG.LIAISON_CODE);
}})();
</script>

{f"""<!-- GTM Body (à placer juste après <body>) -->
{gtm.get("body", "")}""" if gtm.get("body") else ""}

<!-- ========== UTILISATION DES CTA ========== -->
<!--
Tous vos boutons CTA doivent utiliser cette fonction :

<button onclick="trackCTAClick('hero-btn', 'Demander un devis')">
  Demander un devis gratuit
</button>

<a href="javascript:void(0)" onclick="trackCTAClick('sidebar-btn', 'Estimation')">
  Estimation gratuite
</a>
-->

<!-- ========== CONTENEUR FORMULAIRE ========== -->
<!--
Placez votre formulaire dans un conteneur avec cet ID :

<div id="form-container">
  <!-- Votre formulaire ici -->
  <input type="text" onfocus="trackFormStart()" placeholder="Votre nom">
  ...
  <button onclick="submitLead({{phone: '...', nom: '...', ...}})">Envoyer</button>
</div>
-->

{logos_html}

{legal_buttons_html}
'''
        
        return {
            "mode": "embedded",
            "lp": {
                "id": lp_id,
                "code": lp_code,
                "name": lp_name,
                "url": lp_url,
                "product_type": product_type
            },
            "form": {
                "id": form_id,
                "code": form_code,
                "name": form.get("name", ""),
                "url": form_url
            },
            "liaison_code": liaison_code,
            "account": {
                "name": account_name,
                "logos": logos,
                "gtm": gtm,
                "legal": legal
            },
            "scripts": {
                "combined": script_combined,
                "logos_html": logos_html,
                "legal_html": legal_buttons_html,
                "lp": None,
                "form": None
            },
            "script_count": 1,
            "lead_fields": LEAD_FIELDS,
            "api_url": api_url,
            "tracking_type": tracking_type,
            "redirect_url": redirect_url
        }
    
    else:
        # ==================== MODE REDIRECT : 2 SCRIPTS SÉPARÉS ====================
        
        # Script LP
        script_lp = f'''<!-- ================================================================ -->
<!-- SCRIPT LP (Mode Redirect - Page séparée du Form)                -->
<!-- LP: {lp_code} | Form: {form_code} | Liaison: {liaison_code}     -->
<!-- À coller sur : {lp_url}                                          -->
<!-- ================================================================ -->

{f"""<!-- GTM Head -->
{gtm.get("head", "")}""" if gtm.get("head") else ""}

<script>
(function() {{
  // ========== CONFIGURATION LP ==========
  var CONFIG = {{
    API_URL: "{api_url}",
    LP_CODE: "{lp_code}",
    FORM_CODE: "{form_code}",
    FORM_URL: "{form_url}",
    LIAISON_CODE: "{liaison_code}",
    PRODUCT_TYPE: "{product_type}",
    MODE: "redirect"
  }};

  // ========== UTM PARAMS ==========
  var urlParams = new URLSearchParams(window.location.search);
  var UTM = {{
    source: urlParams.get("utm_source") || "",
    medium: urlParams.get("utm_medium") || "",
    campaign: urlParams.get("utm_campaign") || ""
  }};

  // ========== TRACKING LP VIEW ==========
  function trackLPView() {{
    fetch(CONFIG.API_URL + "/api/track/lp-visit", {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{
        lp_code: CONFIG.LP_CODE,
        referrer: document.referrer
      }})
    }}).catch(function(e) {{ console.log("[EnerSolar] LP view error:", e); }});
    
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({{
      event: "lp_view",
      lp_code: CONFIG.LP_CODE,
      product_type: CONFIG.PRODUCT_TYPE
    }});
  }}

  // ========== TRACKING CTA + REDIRECT ==========
  window.trackCTAClick = function(ctaId, ctaText) {{
    fetch(CONFIG.API_URL + "/api/track/cta-click", {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{
        lp_code: CONFIG.LP_CODE,
        form_code: CONFIG.FORM_CODE
      }})
    }}).catch(function(e) {{ console.log("[EnerSolar] CTA click error:", e); }});
    
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({{
      event: "cta_click",
      lp_code: CONFIG.LP_CODE,
      cta_id: ctaId || "unknown",
      cta_text: ctaText || "unknown"
    }});
    
    // Construire URL du form avec paramètres
    var formUrl = CONFIG.FORM_URL;
    var sep = formUrl.indexOf("?") === -1 ? "?" : "&";
    formUrl += sep + "lp=" + CONFIG.LP_CODE + "&liaison=" + CONFIG.LIAISON_CODE;
    
    // Ajouter UTM
    if (UTM.source) formUrl += "&utm_source=" + encodeURIComponent(UTM.source);
    if (UTM.medium) formUrl += "&utm_medium=" + encodeURIComponent(UTM.medium);
    if (UTM.campaign) formUrl += "&utm_campaign=" + encodeURIComponent(UTM.campaign);
    
    // Rediriger vers le formulaire
    window.location.href = formUrl;
  }};

  // ========== INIT ==========
  if (document.readyState === "loading") {{
    document.addEventListener("DOMContentLoaded", trackLPView);
  }} else {{
    trackLPView();
  }}
  
  console.log("[EnerSolar] Script LP initialisé (redirect)");
  console.log("[EnerSolar] LP:", CONFIG.LP_CODE, "| Form URL:", CONFIG.FORM_URL);
}})();
</script>

{f"""<!-- GTM Body (à placer juste après <body>) -->
{gtm.get("body", "")}""" if gtm.get("body") else ""}

<!-- ========== UTILISATION DES CTA ========== -->
<!--
Tous vos boutons CTA doivent utiliser cette fonction :

<button onclick="trackCTAClick('hero-btn', 'Demander un devis')">
  Demander un devis gratuit
</button>

<a href="javascript:void(0)" onclick="trackCTAClick('sidebar-btn', 'Estimation')">
  Estimation gratuite
</a>

Les visiteurs seront redirigés vers : {form_url}?lp={lp_code}&liaison={liaison_code}
-->

{logos_html}

{legal_buttons_html}
'''

        # Script Form (page séparée)
        script_form = f'''<!-- ================================================================ -->
<!-- SCRIPT FORM (Mode Redirect - Page séparée de la LP)             -->
<!-- Form: {form_code} | Reçoit les params de LP: {lp_code}          -->
<!-- À coller sur : {form_url}                                        -->
<!-- ================================================================ -->

{f"""<!-- GTM Head -->
{gtm.get("head", "")}""" if gtm.get("head") else ""}

<script>
(function() {{
  // ========== CONFIGURATION FORM ==========
  var CONFIG = {{
    API_URL: "{api_url}",
    FORM_CODE: "{form_code}",
    LP_CODE: "",
    LIAISON_CODE: "",
    PRODUCT_TYPE: "{product_type}",
    MODE: "redirect"
  }};

  // ========== LIRE PARAMS URL (venant de la LP) ==========
  var urlParams = new URLSearchParams(window.location.search);
  CONFIG.LP_CODE = urlParams.get("lp") || "";
  CONFIG.LIAISON_CODE = urlParams.get("liaison") || "";
  
  var UTM = {{
    source: urlParams.get("utm_source") || "",
    medium: urlParams.get("utm_medium") || "",
    campaign: urlParams.get("utm_campaign") || ""
  }};

  // Exposer le contexte
  window.__EnerSolar_CONTEXT__ = CONFIG;

  // ========== TRACKING FORM VIEW ==========
  function trackFormView() {{
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({{
      event: "form_view",
      form_code: CONFIG.FORM_CODE,
      lp_code: CONFIG.LP_CODE,
      liaison_code: CONFIG.LIAISON_CODE
    }});
  }}

  // ========== TRACKING FORM START ==========
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
    }}).catch(function(e) {{ console.log("[EnerSolar] Form start error:", e); }});
    
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({{
      event: "form_start",
      form_code: CONFIG.FORM_CODE,
      lp_code: CONFIG.LP_CODE
    }});
  }};

  // ========== VALIDATION TÉLÉPHONE ==========
  window.validatePhone = function(phone) {{
    var digits = phone.replace(/\\D/g, "");
    if (digits.length === 9 && digits[0] !== "0") digits = "0" + digits;
    if (digits.length !== 10) return {{ valid: false, error: "Le numéro doit contenir 10 chiffres" }};
    if (!digits.startsWith("0")) return {{ valid: false, error: "Le numéro doit commencer par 0" }};
    if (digits === "0123456789" || /^0(\\d)\\1{{8}}$/.test(digits)) return {{ valid: false, error: "Numéro invalide" }};
    return {{ valid: true, phone: digits }};
  }};

  // ========== SOUMISSION LEAD ==========
  window.submitLead = function(leadData) {{
    var phoneCheck = validatePhone(leadData.phone || "");
    if (!phoneCheck.valid) {{
      alert(phoneCheck.error);
      return Promise.reject(phoneCheck.error);
    }}

    var payload = {{
      form_id: CONFIG.FORM_CODE,
      phone: phoneCheck.phone,
      nom: leadData.nom || "",
      prenom: leadData.prenom || "",
      civilite: leadData.civilite || "",
      email: leadData.email || "",
      code_postal: leadData.code_postal || "",
      departement: (leadData.code_postal || "").substring(0, 2),
      ville: leadData.ville || "",
      adresse: leadData.adresse || "",
      type_logement: leadData.type_logement || "",
      statut_occupant: leadData.statut_occupant || "",
      surface_habitable: leadData.surface_habitable || "",
      annee_construction: leadData.annee_construction || "",
      type_chauffage: leadData.type_chauffage || "",
      facture_electricite: leadData.facture_electricite || "",
      facture_chauffage: leadData.facture_chauffage || "",
      type_projet: leadData.type_projet || "",
      delai_projet: leadData.delai_projet || "",
      budget: leadData.budget || "",
      lp_code: CONFIG.LP_CODE,
      liaison_code: CONFIG.LIAISON_CODE,
      source: leadData.source || UTM.source || "",
      utm_source: UTM.source,
      utm_medium: UTM.medium,
      utm_campaign: UTM.campaign,
      rgpd_consent: leadData.rgpd_consent !== false,
      newsletter: leadData.newsletter || false
    }};

    return fetch(CONFIG.API_URL + "/api/v1/leads", {{
      method: "POST",
      headers: {{ 
        "Content-Type": "application/json",
        "Authorization": "Token VOTRE_CLE_API"
      }},
      body: JSON.stringify(payload)
    }})
    .then(function(response) {{ return response.json(); }})
    .then(function(data) {{
      if (data.success) {{
        console.log("[EnerSolar] Lead envoyé:", data.lead_id);
        
        window.dataLayer = window.dataLayer || [];
        window.dataLayer.push({{
          event: "form_submit",
          form_code: CONFIG.FORM_CODE,
          lp_code: CONFIG.LP_CODE,
          lead_id: data.lead_id,
          product_type: CONFIG.PRODUCT_TYPE,
          department: payload.departement
        }});{gtm_trigger}{redirect_trigger}
      }} else {{
        console.error("[EnerSolar] Erreur:", data.error || data.message);
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

  // ========== INIT ==========
  if (document.readyState === "loading") {{
    document.addEventListener("DOMContentLoaded", trackFormView);
  }} else {{
    trackFormView();
  }}
  
  console.log("[EnerSolar] Script Form initialisé (redirect)");
  console.log("[EnerSolar] Form:", CONFIG.FORM_CODE, "| LP source:", CONFIG.LP_CODE, "| Liaison:", CONFIG.LIAISON_CODE);
}})();
</script>

{f"""<!-- GTM Body (à placer juste après <body>) -->
{gtm.get("body", "")}""" if gtm.get("body") else ""}

<!-- ========== UTILISATION DANS LE FORMULAIRE ========== -->
<!--
1. Sur le premier champ ou bouton "Suivant" :
   <input type="text" onfocus="trackFormStart()" placeholder="Votre nom">

2. À la soumission finale :
   <button onclick="submitLead({{phone: '...', nom: '...', ...}})">Envoyer</button>
-->
'''

        return {
            "mode": "redirect",
            "lp": {
                "id": lp_id,
                "code": lp_code,
                "name": lp_name,
                "url": lp_url,
                "product_type": product_type
            },
            "form": {
                "id": form_id,
                "code": form_code,
                "name": form.get("name", ""),
                "url": form_url
            },
            "liaison_code": liaison_code,
            "account": {
                "name": account_name,
                "logos": logos,
                "gtm": gtm,
                "legal": legal
            },
            "scripts": {
                "combined": None,
                "logos_html": logos_html,
                "legal_html": legal_buttons_html,
                "lp": script_lp,
                "form": script_form
            },
            "script_count": 2,
            "lead_fields": LEAD_FIELDS,
            "api_url": api_url,
            "tracking_type": tracking_type,
            "redirect_url": redirect_url
        }
