"""
Service de génération de Brief v2
Scripts simplifiés (~50 lignes) avec:
- Cookie de session fonctionnel
- Tracking unifié
- Pas de clé API visible (tout côté serveur)
"""

from config import db, BACKEND_URL


async def generate_brief_v2(lp_id: str) -> dict:
    """
    Génère un brief v2 avec scripts simplifiés.
    
    Nouveautés:
    - 1 seul script universel (embedded ou redirect)
    - Cookie de session automatique
    - Pas de clé API dans le script
    - ~50 lignes au lieu de 500+
    """
    # Récupérer la LP
    lp = await db.lps.find_one({"id": lp_id}, {"_id": 0})
    if not lp:
        return {"error": "LP non trouvée"}
    
    lp_code = lp.get("code", "")
    lp_url = lp.get("url", "")
    lp_name = lp.get("name", "")
    form_mode = lp.get("form_mode", "redirect")
    form_id = lp.get("form_id")
    product_type = lp.get("product_type", "")
    tracking_type = lp.get("tracking_type", "redirect")
    redirect_url = lp.get("redirect_url", "/merci")
    
    # Récupérer le Form lié (2 méthodes : lp.form_id OU form.lp_id)
    form = None
    form_code = ""
    form_url = ""
    
    # Méthode 1: LP a un form_id
    if form_id:
        form = await db.forms.find_one({"id": form_id}, {"_id": 0})
    
    # Méthode 2: Form a un lp_id qui pointe vers cette LP
    if not form:
        form = await db.forms.find_one({"lp_id": lp_id}, {"_id": 0})
    
    if form:
        form_code = form.get("code", "")
        form_url = form.get("url", "")
        # Prendre les valeurs du form si pas sur la LP
        if not product_type:
            product_type = form.get("product_type", "")
        if not tracking_type or tracking_type == "redirect":
            tracking_type = form.get("tracking_type", "redirect")
        if not redirect_url or redirect_url == "/merci":
            redirect_url = form.get("redirect_url", "/merci")
    
    if not form:
        return {"error": "Form lié non trouvé. Veuillez lier un formulaire à cette LP."}
    
    # Récupérer le compte depuis LP ou Form
    account_id = lp.get("account_id") or form.get("account_id")
    account = None
    if account_id:
        account = await db.accounts.find_one({"id": account_id}, {"_id": 0})
    
    # Si pas de compte, créer une structure par défaut
    account_name = account.get("name", "N/A") if account else "N/A"
    
    # GTM conversion
    gtm_conversion = account.get("gtm_conversion", "") if account else ""
    
    api_url = BACKEND_URL
    liaison_code = f"{lp_code}_{form_code}"
    
    # ==================== SCRIPT UNIVERSEL V2 ====================
    # Ce script fonctionne pour embedded ET redirect
    
    gtm_trigger_js = ""
    if tracking_type in ["gtm", "both"] and gtm_conversion:
        gtm_trigger_js = f"""
          // GTM Conversion
          {gtm_conversion}"""
    
    redirect_trigger_js = ""
    if tracking_type in ["redirect", "both"] and redirect_url:
        redirect_trigger_js = f"""
          // Redirection
          setTimeout(function() {{ window.location.href = "{redirect_url}"; }}, 500);"""
    
    script_universal = f'''<!-- =================================================== -->
<!-- RDZ TRACKING SCRIPT v2 - {lp_code} + {form_code} -->
<!-- Mode: {form_mode.upper()} | Produit: {product_type} -->
<!-- =================================================== -->
<script>
(function() {{
  "use strict";
  
  var RDZ = {{
    API: "{api_url}/api/public",
    LP: "{lp_code}",
    FORM: "{form_code}",
    MODE: "{form_mode}",
    FORM_URL: "{form_url}",
    session: null
  }};

  // === INIT SESSION ===
  async function initSession() {{
    if (RDZ.session) return RDZ.session;
    
    var params = new URLSearchParams(window.location.search);
    var body = {{
      lp_code: params.get("lp") || RDZ.LP,
      form_code: params.get("form") || RDZ.FORM,
      referrer: document.referrer,
      utm_source: params.get("utm_source") || "",
      utm_medium: params.get("utm_medium") || "",
      utm_campaign: params.get("utm_campaign") || ""
    }};
    
    try {{
      var res = await fetch(RDZ.API + "/track/session", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        credentials: "include",
        body: JSON.stringify(body)
      }});
      var data = await res.json();
      RDZ.session = data.session_id;
      console.log("[RDZ] Session:", RDZ.session);
      return RDZ.session;
    }} catch(e) {{
      console.error("[RDZ] Session error:", e);
      return null;
    }}
  }}

  // === TRACK EVENT ===
  async function track(type, extra) {{
    var sid = RDZ.session || await initSession();
    if (!sid) return;
    
    fetch(RDZ.API + "/track/event", {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{
        session_id: sid,
        event_type: type,
        lp_code: RDZ.LP,
        form_code: RDZ.FORM,
        data: extra || {{}}
      }})
    }}).catch(function(e) {{ console.log("[RDZ] Track error:", e); }});
  }}

  // === PUBLIC FUNCTIONS ===
  
  // Track CTA click (for redirect mode, also navigates to form)
  window.rdzClickCTA = function(ctaId) {{
    track("cta_click", {{ cta_id: ctaId || "main" }});
    
    if (RDZ.MODE === "redirect" && RDZ.FORM_URL) {{
      var url = RDZ.FORM_URL;
      url += (url.indexOf("?") === -1 ? "?" : "&") + "lp=" + RDZ.LP + "&session=" + RDZ.session;
      
      var params = new URLSearchParams(window.location.search);
      ["utm_source", "utm_medium", "utm_campaign"].forEach(function(p) {{
        if (params.get(p)) url += "&" + p + "=" + encodeURIComponent(params.get(p));
      }});
      
      window.location.href = url;
    }} else {{
      // Embedded mode - scroll to form
      var el = document.getElementById("rdz-form") || document.getElementById("form");
      if (el) el.scrollIntoView({{ behavior: "smooth" }});
    }}
  }};
  
  // Track form start (call on first field focus)
  window.rdzFormStart = function() {{
    if (window._rdzFormStarted) return;
    window._rdzFormStarted = true;
    track("form_start");
  }};
  
  // Submit lead
  window.rdzSubmitLead = async function(leadData) {{
    var sid = RDZ.session || await initSession();
    if (!sid) {{
      alert("Erreur de session. Veuillez rafraîchir la page.");
      return {{ success: false, error: "No session" }};
    }}
    
    var payload = Object.assign({{
      session_id: sid,
      form_code: RDZ.FORM
    }}, leadData);
    
    try {{
      var res = await fetch(RDZ.API + "/leads", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(payload)
      }});
      var data = await res.json();
      
      if (data.success) {{
        console.log("[RDZ] Lead sent:", data.lead_id);{gtm_trigger_js}{redirect_trigger_js}
      }} else {{
        console.error("[RDZ] Lead error:", data.error);
        alert(data.error || "Une erreur est survenue");
      }}
      
      return data;
    }} catch(e) {{
      console.error("[RDZ] Submit error:", e);
      alert("Erreur technique. Veuillez réessayer.");
      return {{ success: false, error: e.message }};
    }}
  }};

  // === AUTO INIT ===
  document.addEventListener("DOMContentLoaded", function() {{
    initSession().then(function() {{
      track("lp_visit");
    }});
  }});
  
  console.log("[RDZ] Script v2 loaded - LP:", RDZ.LP, "| Form:", RDZ.FORM);
}})();
</script>

<!-- === USAGE === -->
<!--
1. CTA BUTTON (déclenche tracking + navigation si redirect):
   <button onclick="rdzClickCTA('hero')">Demander un devis</button>

2. FORM START (sur premier champ ou bouton suivant):
   <input onfocus="rdzFormStart()" placeholder="Votre nom">

3. SUBMIT (à la soumission finale):
   <button onclick="submitMyForm()">Envoyer</button>
   
   <script>
   function submitMyForm() {{
     rdzSubmitLead({{
       phone: document.getElementById("phone").value,
       nom: document.getElementById("nom").value,
       prenom: document.getElementById("prenom").value,
       email: document.getElementById("email").value,
       code_postal: document.getElementById("cp").value,
       type_logement: document.getElementById("logement").value,
       statut_occupant: document.getElementById("statut").value,
       facture_electricite: document.getElementById("facture").value
     }});
   }}
   </script>
-->
'''

    # ==================== CHAMPS DISPONIBLES ====================
    lead_fields = {
        "identite": [
            {"key": "phone", "label": "Téléphone", "required": True},
            {"key": "nom", "label": "Nom"},
            {"key": "prenom", "label": "Prénom"},
            {"key": "civilite", "label": "Civilité"},
            {"key": "email", "label": "Email"}
        ],
        "localisation": [
            {"key": "code_postal", "label": "Code Postal"},
            {"key": "ville", "label": "Ville"},
            {"key": "adresse", "label": "Adresse"}
        ],
        "logement": [
            {"key": "type_logement", "label": "Type de logement"},
            {"key": "statut_occupant", "label": "Statut occupant"},
            {"key": "surface_habitable", "label": "Surface (m²)"},
            {"key": "annee_construction", "label": "Année construction"},
            {"key": "type_chauffage", "label": "Type chauffage"}
        ],
        "energie": [
            {"key": "facture_electricite", "label": "Facture électricité"},
            {"key": "facture_chauffage", "label": "Facture chauffage"}
        ],
        "projet": [
            {"key": "type_projet", "label": "Type projet"},
            {"key": "delai_projet", "label": "Délai"},
            {"key": "budget", "label": "Budget"}
        ]
    }
    
    return {
        "version": "2.0",
        "mode": form_mode,
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
            "name": account_name
        },
        "scripts": {
            "universal": script_universal,
            # Pas de scripts séparés - tout est dans le script universel
            "lp": None,
            "form": None,
            "combined": script_universal
        },
        "script_count": 1,
        "lead_fields": lead_fields,
        "api_url": api_url,
        "tracking_type": tracking_type,
        "redirect_url": redirect_url,
        "endpoints": {
            "init_session": f"{api_url}/api/public/track/session",
            "track_event": f"{api_url}/api/public/track/event",
            "submit_lead": f"{api_url}/api/public/leads",
            "get_config": f"{api_url}/api/public/config/{form_code}"
        },
        "instructions": {
            "installation": f"Copiez le script ci-dessus et collez-le sur votre page ({lp_url})",
            "cta": 'Ajoutez onclick="rdzClickCTA()" sur vos boutons CTA',
            "form_start": 'Ajoutez onfocus="rdzFormStart()" sur le premier champ du formulaire',
            "submit": 'Appelez rdzSubmitLead({phone: "...", nom: "...", ...}) à la soumission'
        }
    }


# Garder l'ancienne fonction pour compatibilité
async def generate_brief(form_id: str) -> dict:
    """Ancienne fonction - redirige vers v2 si possible"""
    form = await db.forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        return {"error": "Formulaire non trouvé"}
    
    # Si le form a une LP liée, utiliser v2
    if form.get("lp_id"):
        lp = await db.lps.find_one({"id": form["lp_id"]}, {"_id": 0})
        if lp:
            return await generate_brief_v2(lp.get("id"))
    
    # Sinon utiliser l'ancienne méthode (fallback)
    from services.brief_generator_legacy import generate_brief_legacy
    return await generate_brief_legacy(form_id)
