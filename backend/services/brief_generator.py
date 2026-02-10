"""
Service de génération de Brief
"""

from config import db, BACKEND_URL


async def generate_brief(lp_id: str) -> dict:
    """Génère le brief complet avec scripts + infos compte"""
    
    # Récupérer la LP
    lp = await db.lps.find_one({"id": lp_id}, {"_id": 0})
    if not lp:
        return {"error": "LP non trouvée"}
    
    lp_code = lp.get("code", "")
    lp_url = lp.get("url", "")
    lp_name = lp.get("name", "")
    form_id = lp.get("form_id")
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
    
    # Infos du compte
    account_name = ""
    logos = {}
    gtm = {}
    liens = {}
    
    if account:
        account_name = account.get("name", "")
        
        # Logos
        logos = {
            "principal": account.get("logo_main_url") or account.get("logo_left_url") or "",
            "secondaire": account.get("logo_secondary_url") or account.get("logo_right_url") or "",
            "mini": account.get("logo_mini_url") or account.get("logo_small_url") or "",
            "favicon": account.get("favicon_url") or ""
        }
        
        # GTM
        gtm = {
            "head": account.get("gtm_head") or account.get("gtm_pixel_header") or "",
            "body": account.get("gtm_body") or "",
            "conversion": account.get("gtm_conversion") or account.get("gtm_conversion_code") or ""
        }
        
        # Liens
        liens = {
            "redirection": redirect_url or account.get("default_redirect_url") or "/merci",
            "confidentialite": account.get("privacy_policy_url") or "",
            "mentions_legales": account.get("legal_mentions_url") or ""
        }
        
        # Textes légaux (si URLs vides, on met les textes)
        if not liens["confidentialite"] and account.get("privacy_policy_text"):
            liens["confidentialite_texte"] = account.get("privacy_policy_text")
        if not liens["mentions_legales"] and account.get("legal_mentions_text"):
            liens["mentions_legales_texte"] = account.get("legal_mentions_text")
    
    api_url = BACKEND_URL
    liaison_code = f"{lp_code}_{form_code}"
    
    # Post submit actions
    post_submit = ""
    if tracking_type in ["gtm", "both"] and gtm.get("conversion"):
        post_submit += f"\n        {gtm['conversion']}"
    final_redirect = liens.get("redirection", "/merci")
    if tracking_type in ["redirect", "both"] and final_redirect:
        post_submit += f"\n        setTimeout(function() {{ window.location.href = '{final_redirect}'; }}, 500);"
    
    # ==================== SCRIPT LP ====================
    script_lp = f'''<!-- RDZ TRACKING LP - {lp_code} -->
<script>
(function() {{
  var RDZ = {{
    api: "{api_url}/api/public",
    lp: "{lp_code}",
    form: "{form_code}",
    formUrl: "{form_url}",
    session: null
  }};

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
      return null;
    }}
  }}

  function track(type) {{
    if (!RDZ.session) return;
    fetch(RDZ.api + "/track/event", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{
        session_id: RDZ.session,
        event_type: type,
        lp_code: RDZ.lp,
        form_code: RDZ.form
      }})
    }});
  }}

  document.addEventListener("DOMContentLoaded", function() {{
    initSession().then(function() {{
      track("lp_visit");
    }});
  }});

  window.rdzClickCTA = function() {{
    track("cta_click");
    if (RDZ.formUrl && RDZ.session) {{
      var url = RDZ.formUrl;
      url += (url.indexOf("?") === -1 ? "?" : "&") + "session=" + RDZ.session;
      var params = new URLSearchParams(window.location.search);
      ["utm_source", "utm_medium", "utm_campaign"].forEach(function(p) {{
        if (params.get(p)) url += "&" + p + "=" + encodeURIComponent(params.get(p));
      }});
      window.location.href = url;
    }}
  }};
}})();
</script>'''

    # ==================== SCRIPT FORM ====================
    script_form = f'''<!-- RDZ TRACKING FORM - {form_code} -->
<script>
(function() {{
  var RDZ = {{
    api: "{api_url}/api/public",
    lp: "{lp_code}",
    form: "{form_code}",
    session: null
  }};

  async function initSession() {{
    if (RDZ.session) return RDZ.session;
    var params = new URLSearchParams(window.location.search);
    var sessionFromUrl = params.get("session");
    if (sessionFromUrl) {{
      RDZ.session = sessionFromUrl;
      return RDZ.session;
    }}
    try {{
      var res = await fetch(RDZ.api + "/track/session", {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        credentials: "include",
        body: JSON.stringify({{
          lp_code: params.get("lp") || RDZ.lp,
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
      return null;
    }}
  }}

  function track(type) {{
    if (!RDZ.session) return;
    fetch(RDZ.api + "/track/event", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{
        session_id: RDZ.session,
        event_type: type,
        lp_code: RDZ.lp,
        form_code: RDZ.form
      }})
    }});
  }}

  document.addEventListener("DOMContentLoaded", function() {{
    initSession();
  }});

  var formStarted = false;
  window.rdzFormStart = function() {{
    if (formStarted) return;
    formStarted = true;
    initSession().then(function() {{
      track("form_start");
    }});
  }};

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
        "account": account_name,
        "liaison_code": liaison_code,
        "logos": logos,
        "gtm": gtm,
        "liens": liens,
        "script_lp": script_lp,
        "script_form": script_form,
        "champs": ["phone", "nom", "prenom", "email", "code_postal", "ville", "type_logement", "statut_occupant", "facture_electricite"]
    }


# Alias pour le frontend
async def generate_brief_v2(lp_id: str) -> dict:
    result = await generate_brief(lp_id)
    if "error" in result:
        return result
    return {
        "lp": result["lp"],
        "form": result["form"],
        "account": result["account"],
        "liaison_code": result["liaison_code"],
        "logos": result["logos"],
        "gtm": result["gtm"],
        "liens": result["liens"],
        "scripts": {
            "lp": result["script_lp"],
            "form": result["script_form"]
        },
        "champs": result["champs"]
    }
