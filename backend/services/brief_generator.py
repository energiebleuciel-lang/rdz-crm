"""
Service de génération de Brief
Génère 2 scripts séparés : un pour LP, un pour Form
"""

from config import db, BACKEND_URL


async def generate_brief(lp_id: str) -> dict:
    """Génère le brief avec 2 scripts séparés (LP + Form)"""
    
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
    
    gtm_conversion = account.get("gtm_conversion", "") if account else ""
    
    api_url = BACKEND_URL
    liaison_code = f"{lp_code}_{form_code}"
    
    # Actions après soumission
    post_submit = ""
    if tracking_type in ["gtm", "both"] and gtm_conversion:
        post_submit += f"\n        {gtm_conversion}"
    if tracking_type in ["redirect", "both"] and redirect_url:
        post_submit += f"\n        setTimeout(function() {{ window.location.href = '{redirect_url}'; }}, 500);"
    
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
      return null;
    }}
  }}

  // Tracker événement
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

  // VISITE LP - Automatique au chargement
  document.addEventListener("DOMContentLoaded", function() {{
    initSession().then(function() {{
      track("lp_visit");
    }});
  }});

  // CLIC CTA - Appeler sur le bouton CTA
  window.rdzClickCTA = function() {{
    track("cta_click");
    // Rediriger vers le formulaire avec session_id
    if (RDZ.formUrl && RDZ.session) {{
      var url = RDZ.formUrl;
      url += (url.indexOf("?") === -1 ? "?" : "&") + "session=" + RDZ.session;
      // Conserver les UTM
      var params = new URLSearchParams(window.location.search);
      ["utm_source", "utm_medium", "utm_campaign"].forEach(function(p) {{
        if (params.get(p)) url += "&" + p + "=" + encodeURIComponent(params.get(p));
      }});
      window.location.href = url;
    }}
  }};
}})();
</script>

<!--
UTILISATION :
1. Coller ce script sur la page LP ({lp_url})
2. Sur le bouton CTA : onclick="rdzClickCTA()"

Exemple :
<button onclick="rdzClickCTA()">Demander un devis</button>
-->'''

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

  // Récupérer ou créer session
  async function initSession() {{
    if (RDZ.session) return RDZ.session;
    
    var params = new URLSearchParams(window.location.search);
    
    // Récupérer session depuis URL (venant de la LP)
    var sessionFromUrl = params.get("session");
    if (sessionFromUrl) {{
      RDZ.session = sessionFromUrl;
      return RDZ.session;
    }}
    
    // Sinon créer nouvelle session (accès direct au form)
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

  // Tracker événement
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

  // Init au chargement
  document.addEventListener("DOMContentLoaded", function() {{
    initSession();
  }});

  // FORM DÉMARRÉ - Appeler sur le premier bouton du formulaire
  var formStarted = false;
  window.rdzFormStart = function() {{
    if (formStarted) return;
    formStarted = true;
    initSession().then(function() {{
      track("form_start");
    }});
  }};

  // FORM FINI - Appeler avec les données du lead
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
</script>

<!--
UTILISATION :
1. Coller ce script sur la page formulaire ({form_url})
2. Sur le premier bouton du form : onclick="rdzFormStart()"
3. À la soumission : rdzSubmitLead({{phone, nom, code_postal, ...}})

Exemple :
<button onclick="rdzFormStart()">Suivant</button>
<button onclick="envoyerLead()">Envoyer</button>

<script>
function envoyerLead() {{
  rdzSubmitLead({{
    phone: document.getElementById("phone").value,
    nom: document.getElementById("nom").value,
    code_postal: document.getElementById("cp").value
  }});
}}
</script>
-->'''

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
        "liaison_code": liaison_code,
        "script_lp": script_lp,
        "script_form": script_form,
        "instructions": {
            "lp": {
                "installer": f"Coller le Script LP sur {lp_url}",
                "cta": 'onclick="rdzClickCTA()" sur le bouton CTA'
            },
            "form": {
                "installer": f"Coller le Script Form sur {form_url}",
                "start": 'onclick="rdzFormStart()" sur le premier bouton',
                "submit": "rdzSubmitLead({phone, nom, code_postal, ...})"
            }
        },
        "champs": ["phone", "nom", "prenom", "email", "code_postal", "ville", "type_logement", "statut_occupant", "facture_electricite"]
    }


# Alias pour compatibilité frontend
async def generate_brief_v2(lp_id: str) -> dict:
    result = await generate_brief(lp_id)
    if "error" in result:
        return result
    return {
        "lp": result["lp"],
        "form": result["form"],
        "mode": "redirect",
        "liaison_code": result["liaison_code"],
        "scripts": {
            "lp": result["script_lp"],
            "form": result["script_form"]
        },
        "instructions": result["instructions"],
        "lead_fields": {
            "obligatoire": [{"key": "phone", "label": "Téléphone", "required": True}],
            "identite": [{"key": "nom", "label": "Nom"}, {"key": "prenom", "label": "Prénom"}, {"key": "email", "label": "Email"}],
            "localisation": [{"key": "code_postal", "label": "Code Postal"}, {"key": "ville", "label": "Ville"}],
            "logement": [{"key": "type_logement", "label": "Type"}, {"key": "statut_occupant", "label": "Statut"}]
        }
    }
