"""
Service de génération de Brief
"""

from config import db, BACKEND_URL


async def generate_brief(lp_id: str) -> dict:
    """Génère le brief avec script de tracking pour une LP"""
    
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
    
    # Récupérer le Form lié
    form = None
    form_code = ""
    form_url = ""
    
    if form_id:
        form = await db.forms.find_one({"id": form_id}, {"_id": 0})
    
    if not form:
        form = await db.forms.find_one({"lp_id": lp_id}, {"_id": 0})
    
    if form:
        form_code = form.get("code", "")
        form_url = form.get("url", "")
        if not product_type:
            product_type = form.get("product_type", "")
        if not tracking_type or tracking_type == "redirect":
            tracking_type = form.get("tracking_type", "redirect")
        if not redirect_url or redirect_url == "/merci":
            redirect_url = form.get("redirect_url", "/merci")
    
    if not form:
        return {"error": "Form lié non trouvé"}
    
    # Récupérer le compte
    account_id = lp.get("account_id") or form.get("account_id")
    account = None
    if account_id:
        account = await db.accounts.find_one({"id": account_id}, {"_id": 0})
    
    account_name = account.get("name", "") if account else ""
    gtm_conversion = account.get("gtm_conversion", "") if account else ""
    
    api_url = BACKEND_URL
    liaison_code = f"{lp_code}_{form_code}"
    
    # Actions après soumission
    post_submit = ""
    if tracking_type in ["gtm", "both"] and gtm_conversion:
        post_submit += f"\n        {gtm_conversion}"
    if tracking_type in ["redirect", "both"] and redirect_url:
        post_submit += f"\n        setTimeout(function() {{ window.location.href = '{redirect_url}'; }}, 500);"
    
    # Script de tracking
    script = f'''<!-- RDZ TRACKING - {lp_code} -->
<script>
(function() {{
  var RDZ = {{
    api: "{api_url}/api/public",
    lp: "{lp_code}",
    form: "{form_code}",
    session: null
  }};

  // Créer session
  async function initSession() {{
    if (RDZ.session) return RDZ.session;
    var params = new URLSearchParams(window.location.search);
    try {{
      var res = await fetch(RDZ.api + "/track/session", {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        credentials: "include",
        body: JSON.stringify({{
          lp_code: RDZ.lp,
          form_code: RDZ.form,
          referrer: document.referrer,
          utm_source: params.get("utm_source") || "",
          utm_medium: params.get("utm_medium") || "",
          utm_campaign: params.get("utm_campaign") || ""
        }})
      }});
      var data = await res.json();
      RDZ.session = data.session_id;
      return RDZ.session;
    }} catch(e) {{
      console.error("[RDZ] Session error:", e);
      return null;
    }}
  }}

  // Tracker un événement
  async function track(type) {{
    var sid = RDZ.session || await initSession();
    if (!sid) return;
    fetch(RDZ.api + "/track/event", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{
        session_id: sid,
        event_type: type,
        lp_code: RDZ.lp,
        form_code: RDZ.form
      }})
    }}).catch(function(e) {{}});
  }}

  // 1. VISITE LP - Automatique
  document.addEventListener("DOMContentLoaded", function() {{
    initSession().then(function() {{
      track("lp_visit");
    }});
  }});

  // 2. CLIC CTA - Appeler onclick="rdzClickCTA()"
  window.rdzClickCTA = function() {{
    track("cta_click");
  }};

  // 3. FORM DÉMARRÉ - Appeler onclick="rdzFormStart()" sur premier bouton
  window.rdzFormStart = function() {{
    if (window._rdzStarted) return;
    window._rdzStarted = true;
    track("form_start");
  }};

  // 4. FORM FINI - Appeler rdzSubmitLead({{phone, nom, ...}})
  window.rdzSubmitLead = async function(data) {{
    var sid = RDZ.session || await initSession();
    if (!sid) {{
      alert("Erreur de session");
      return {{success: false}};
    }}
    try {{
      var res = await fetch(RDZ.api + "/leads", {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        body: JSON.stringify(Object.assign({{
          session_id: sid,
          form_code: RDZ.form
        }}, data))
      }});
      var result = await res.json();
      if (result.success) {{{post_submit}
      }} else {{
        alert(result.error || "Erreur");
      }}
      return result;
    }} catch(e) {{
      alert("Erreur technique");
      return {{success: false}};
    }}
  }};
}})();
</script>'''

    return {
        "lp": {
            "id": lp_id,
            "code": lp_code,
            "name": lp_name,
            "url": lp_url
        },
        "form": {
            "id": form.get("id") if form else None,
            "code": form_code,
            "name": form.get("name", "") if form else "",
            "url": form_url
        },
        "mode": form_mode,
        "liaison_code": liaison_code,
        "script": script,
        "instructions": {
            "visite_lp": "Automatique",
            "clic_cta": 'onclick="rdzClickCTA()"',
            "form_start": 'onclick="rdzFormStart()" sur premier bouton',
            "form_submit": "rdzSubmitLead({phone, nom, code_postal, ...})"
        },
        "champs": ["phone", "nom", "prenom", "email", "code_postal", "ville", "type_logement", "statut_occupant", "facture_electricite"]
    }


# Alias pour compatibilité
async def generate_brief_v2(lp_id: str) -> dict:
    result = await generate_brief(lp_id)
    # Adapter le format pour le frontend existant
    if "error" in result:
        return result
    return {
        "lp": result["lp"],
        "form": result["form"],
        "mode": result["mode"],
        "liaison_code": result["liaison_code"],
        "scripts": {
            "universal": result["script"],
            "combined": result["script"]
        },
        "instructions": result["instructions"],
        "lead_fields": {
            "obligatoire": [{"key": "phone", "label": "Téléphone", "required": True}],
            "identite": [{"key": "nom", "label": "Nom"}, {"key": "prenom", "label": "Prénom"}, {"key": "email", "label": "Email"}],
            "localisation": [{"key": "code_postal", "label": "Code Postal"}, {"key": "ville", "label": "Ville"}],
            "logement": [{"key": "type_logement", "label": "Type"}, {"key": "statut_occupant", "label": "Statut"}]
        }
    }
