"""
Service de génération de Brief
Version fusionnée avec Mode A/B et transmission utm_campaign

Modes supportés:
- Mode A (separate): LP et Formulaire sur pages séparées
- Mode B (integrated): Formulaire intégré dans la LP

Règles utm_campaign:
- Mode B: lire utm_campaign dans URL, envoyer dans track/session + /leads
- Mode A LP: lire utm_campaign, envoyer dans track/session, stocker sessionStorage, ajouter à URL form
- Mode A Form: récupérer utm_campaign (URL priorité, sinon sessionStorage), envoyer dans /leads
"""

from config import db, BACKEND_URL

API_URL = BACKEND_URL.rstrip("/")


# ══════════════════════════════════════════════════════════════════════════════
# MINI BRIEF - Pour les comptes (logos, GTM, textes légaux)
# Utilisé par: routes/accounts.py
# ══════════════════════════════════════════════════════════════════════════════

async def generate_mini_brief(account_id: str, selections: list) -> dict:
    """
    Génère un mini brief sélectif basé sur les éléments choisis par l'utilisateur
    
    selections peut contenir:
    - logo_principal
    - logo_secondaire
    - gtm_head
    - gtm_body
    - gtm_conversion
    - mentions_legales_texte
    - confidentialite_texte
    - cgu_texte
    - url_redirection
    """
    
    account = await db.accounts.find_one({"id": account_id}, {"_id": 0})
    if not account:
        return {"error": "Compte non trouvé"}
    
    brief_items = []
    
    # Logos
    if "logo_principal" in selections:
        logo = account.get("logo_main_url") or account.get("logo_left_url") or ""
        if logo:
            brief_items.append({
                "type": "logo_principal",
                "label": "Logo Principal",
                "value": logo,
                "format": "url"
            })
    
    if "logo_secondaire" in selections:
        logo = account.get("logo_secondary_url") or account.get("logo_right_url") or ""
        if logo:
            brief_items.append({
                "type": "logo_secondaire",
                "label": "Logo Secondaire",
                "value": logo,
                "format": "url"
            })
    
    # GTM
    if "gtm_head" in selections:
        gtm = account.get("gtm_head") or account.get("gtm_pixel_header") or ""
        if gtm:
            brief_items.append({
                "type": "gtm_head",
                "label": "Code GTM (Head)",
                "value": gtm,
                "format": "code"
            })
    
    if "gtm_body" in selections:
        gtm = account.get("gtm_body") or ""
        if gtm:
            brief_items.append({
                "type": "gtm_body",
                "label": "Code GTM (Body)",
                "value": gtm,
                "format": "code"
            })
    
    if "gtm_conversion" in selections:
        gtm = account.get("gtm_conversion") or account.get("gtm_conversion_code") or ""
        if gtm:
            brief_items.append({
                "type": "gtm_conversion",
                "label": "Code de Tracking Conversion",
                "value": gtm,
                "format": "code"
            })
    
    # Textes légaux
    if "mentions_legales_texte" in selections:
        texte = account.get("legal_mentions_text") or ""
        if texte:
            brief_items.append({
                "type": "mentions_legales_texte",
                "label": "Texte Mentions Légales",
                "value": texte,
                "format": "text"
            })
    
    if "confidentialite_texte" in selections:
        texte = account.get("privacy_policy_text") or ""
        if texte:
            brief_items.append({
                "type": "confidentialite_texte",
                "label": "Texte Politique de Confidentialité",
                "value": texte,
                "format": "text"
            })
    
    if "cgu_texte" in selections:
        texte = account.get("cgu_text") or ""
        if texte:
            brief_items.append({
                "type": "cgu_texte",
                "label": "Texte CGU",
                "value": texte,
                "format": "text"
            })
    
    # URL de redirection par défaut
    if "url_redirection" in selections:
        url = account.get("default_redirect_url") or "/merci"
        brief_items.append({
            "type": "url_redirection",
            "label": "URL de Redirection",
            "value": url,
            "format": "url"
        })
    
    return {
        "account_id": account_id,
        "account_name": account.get("name", ""),
        "items": brief_items,
        "generated_at": __import__("datetime").datetime.utcnow().isoformat()
    }


async def get_account_brief_options(account_id: str) -> dict:
    """
    Récupère la liste des éléments disponibles pour le mini brief d'un compte
    """
    
    account = await db.accounts.find_one({"id": account_id}, {"_id": 0})
    if not account:
        return {"error": "Compte non trouvé"}
    
    options = []
    
    # Logos
    if account.get("logo_main_url") or account.get("logo_left_url"):
        options.append({"key": "logo_principal", "label": "Logo Principal", "category": "Logos", "has_value": True})
    else:
        options.append({"key": "logo_principal", "label": "Logo Principal", "category": "Logos", "has_value": False})
    
    if account.get("logo_secondary_url") or account.get("logo_right_url"):
        options.append({"key": "logo_secondaire", "label": "Logo Secondaire", "category": "Logos", "has_value": True})
    else:
        options.append({"key": "logo_secondaire", "label": "Logo Secondaire", "category": "Logos", "has_value": False})
    
    # GTM
    if account.get("gtm_head") or account.get("gtm_pixel_header"):
        options.append({"key": "gtm_head", "label": "Code GTM (Head)", "category": "GTM & Tracking", "has_value": True})
    else:
        options.append({"key": "gtm_head", "label": "Code GTM (Head)", "category": "GTM & Tracking", "has_value": False})
    
    if account.get("gtm_body"):
        options.append({"key": "gtm_body", "label": "Code GTM (Body)", "category": "GTM & Tracking", "has_value": True})
    else:
        options.append({"key": "gtm_body", "label": "Code GTM (Body)", "category": "GTM & Tracking", "has_value": False})
    
    if account.get("gtm_conversion") or account.get("gtm_conversion_code"):
        options.append({"key": "gtm_conversion", "label": "Code de Tracking Conversion", "category": "GTM & Tracking", "has_value": True})
    else:
        options.append({"key": "gtm_conversion", "label": "Code de Tracking Conversion", "category": "GTM & Tracking", "has_value": False})
    
    # Textes légaux
    if account.get("legal_mentions_text"):
        options.append({"key": "mentions_legales_texte", "label": "Texte Mentions Légales", "category": "Textes Légaux", "has_value": True})
    else:
        options.append({"key": "mentions_legales_texte", "label": "Texte Mentions Légales", "category": "Textes Légaux", "has_value": False})
    
    if account.get("privacy_policy_text"):
        options.append({"key": "confidentialite_texte", "label": "Texte Politique de Confidentialité", "category": "Textes Légaux", "has_value": True})
    else:
        options.append({"key": "confidentialite_texte", "label": "Texte Politique de Confidentialité", "category": "Textes Légaux", "has_value": False})
    
    if account.get("cgu_text"):
        options.append({"key": "cgu_texte", "label": "Texte CGU", "category": "Textes Légaux", "has_value": True})
    else:
        options.append({"key": "cgu_texte", "label": "Texte CGU", "category": "Textes Légaux", "has_value": False})
    
    # URL de redirection
    options.append({"key": "url_redirection", "label": "URL de Redirection", "category": "Autres", "has_value": True})
    
    return {
        "account_id": account_id,
        "account_name": account.get("name", ""),
        "options": options
    }


# ══════════════════════════════════════════════════════════════════════════════
# BRIEF PRINCIPAL - Mode A (séparé) / Mode B (intégré)
# Utilisé par: routes/lps.py, routes/forms.py
# ══════════════════════════════════════════════════════════════════════════════

async def generate_brief(lp_id: str, mode: str = "separate", selected_product: str = None) -> dict:
    """
    Génère le brief complet pour une liaison LP/Form
    
    Args:
        lp_id: ID de la LP
        mode: "separate" (Mode A) ou "integrated" (Mode B)
        selected_product: Produit sélectionné (PV, PAC, ITE) pour URL de redirection
    
    Returns:
        Brief complet avec métadonnées, GTM, scripts et instructions
    """
    
    # Récupérer la LP
    lp = await db.lps.find_one({"id": lp_id}, {"_id": 0})
    if not lp:
        return {"error": "LP non trouvée"}
    
    lp_code = lp.get("code", "")
    lp_url = lp.get("url", "")
    lp_name = lp.get("name", "")
    form_id = lp.get("form_id")
    
    # Récupérer le Form lié
    form = None
    if form_id:
        form = await db.forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        form = await db.forms.find_one({"lp_id": lp_id}, {"_id": 0})
    
    if not form:
        return {"error": "Formulaire lié non trouvé. Veuillez lier un formulaire à cette LP."}
    
    form_code = form.get("code", "")
    form_url = form.get("url", "")
    form_name = form.get("name", "")
    product_type = form.get("product_type", "PV")
    
    # Liaison code
    liaison_code = f"{lp_code}_{form_code}"
    
    # Récupérer le compte
    account_id = form.get("account_id") or lp.get("account_id")
    account = None
    if account_id:
        account = await db.accounts.find_one({"id": account_id}, {"_id": 0})
    
    account_name = account.get("name", "") if account else ""
    
    # GTM (HEAD uniquement)
    gtm_head = ""
    if account:
        gtm_head = account.get("gtm_head", "") or account.get("gtm_pixel_header", "") or ""
    
    # URL de redirection
    redirect_url = form.get("redirect_url", "/merci")
    if selected_product and account:
        product_key = f"redirect_url_{selected_product.lower()}"
        product_redirect_url = account.get(product_key, "")
        if product_redirect_url:
            redirect_url = product_redirect_url
    
    # Sélecteur form
    form_selector = "#rdz-form, form, [data-rdz-form]"
    form_anchor = "#formulaire"
    
    # Générer le brief selon le mode
    if mode == "integrated":
        return await _generate_mode_b(
            lp_code=lp_code,
            lp_url=lp_url,
            lp_name=lp_name,
            form_code=form_code,
            form_url=form_url,
            form_name=form_name,
            liaison_code=liaison_code,
            product_type=product_type,
            account_name=account_name,
            gtm_head=gtm_head,
            redirect_url=redirect_url,
            form_selector=form_selector,
            form_anchor=form_anchor,
            selected_product=selected_product
        )
    else:
        return await _generate_mode_a(
            lp_code=lp_code,
            lp_url=lp_url,
            lp_name=lp_name,
            form_code=form_code,
            form_url=form_url,
            form_name=form_name,
            liaison_code=liaison_code,
            product_type=product_type,
            account_name=account_name,
            gtm_head=gtm_head,
            redirect_url=redirect_url,
            form_selector=form_selector,
            selected_product=selected_product
        )


async def _generate_mode_a(
    lp_code: str,
    lp_url: str,
    lp_name: str,
    form_code: str,
    form_url: str,
    form_name: str,
    liaison_code: str,
    product_type: str,
    account_name: str,
    gtm_head: str,
    redirect_url: str,
    form_selector: str,
    selected_product: str = None
) -> dict:
    """
    Génère le brief Mode A (LP + Form séparés)
    
    utm_campaign:
    - Script LP: lire depuis URL, envoyer dans track/session, stocker sessionStorage, ajouter à URL form
    - Script Form: récupérer (URL priorité, sinon sessionStorage), envoyer dans /leads
    """
    
    # ══════════════════════════════════════════════════════════
    # SCRIPT LP - Mode A
    # ══════════════════════════════════════════════════════════
    script_lp = f'''<!-- RDZ TRACKING - LANDING PAGE {lp_code} -->
<!-- À coller en fin de <body>, avant </body> -->
<script>
(function() {{
  "use strict";
  
  var RDZ = {{
    api: "{API_URL}/api/public",
    lp: "{lp_code}",
    form: "{form_code}",
    liaison: "{liaison_code}",
    formUrl: "{form_url}",
    session: null,
    utm_campaign: "",
    initialized: false,
    initFailed: false
  }};

  // ══════════════════════════════════════════════════════════
  // SESSION + UTM_CAMPAIGN - Création automatique au chargement
  // ══════════════════════════════════════════════════════════
  async function initSession() {{
    if (RDZ.session) return RDZ.session;
    if (RDZ.initFailed) return null;
    
    try {{
      var params = new URLSearchParams(window.location.search);
      
      // Capturer utm_campaign depuis URL
      RDZ.utm_campaign = params.get("utm_campaign") || "";
      
      var res = await fetch(RDZ.api + "/track/session", {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        body: JSON.stringify({{
          lp_code: RDZ.lp,
          form_code: RDZ.form,
          liaison_code: RDZ.liaison,
          referrer: document.referrer,
          utm_source: params.get("utm_source") || "",
          utm_medium: params.get("utm_medium") || "",
          utm_campaign: RDZ.utm_campaign
        }})
      }});
      if (!res.ok) throw new Error("HTTP " + res.status);
      var data = await res.json();
      RDZ.session = data.session_id;
      RDZ.initialized = true;
      
      // Stocker en sessionStorage pour transmission au form
      try {{
        sessionStorage.setItem("rdz_session", RDZ.session);
        sessionStorage.setItem("rdz_lp", RDZ.lp);
        sessionStorage.setItem("rdz_liaison", RDZ.liaison);
        if (RDZ.utm_campaign) {{
          sessionStorage.setItem("rdz_utm_campaign", RDZ.utm_campaign);
        }}
      }} catch(e) {{}}
      
      return RDZ.session;
    }} catch(e) {{
      console.warn("[RDZ] Session init failed:", e.message);
      RDZ.initFailed = true;
      return null;
    }}
  }}

  // Tracking best-effort (sendBeacon prioritaire)
  function track(eventType) {{
    if (!RDZ.session) return;
    var payload = JSON.stringify({{
      session_id: RDZ.session,
      event_type: eventType,
      lp_code: RDZ.lp,
      form_code: RDZ.form,
      liaison_code: RDZ.liaison
    }});
    
    if (navigator.sendBeacon) {{
      navigator.sendBeacon(RDZ.api + "/track/event", new Blob([payload], {{type: "application/json"}}));
    }} else {{
      fetch(RDZ.api + "/track/event", {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        body: payload,
        keepalive: true
      }}).catch(function() {{}});
    }}
  }}

  // ══════════════════════════════════════════════════════════
  // VISITE LP - Automatique au chargement
  // ══════════════════════════════════════════════════════════
  document.addEventListener("DOMContentLoaded", async function() {{
    await initSession();
    if (RDZ.session) track("lp_visit");
    autoBindCTA();
  }});

  // ══════════════════════════════════════════════════════════
  // CTA CLICK - Transmet session + lp + liaison + utm_campaign
  // ══════════════════════════════════════════════════════════
  var ctaClicked = false;
  
  window.rdzCtaClick = function(e) {{
    if (ctaClicked) return;
    ctaClicked = true;
    
    track("cta_click");
    
    // Construire URL avec tous les params
    if (e && e.currentTarget && e.currentTarget.tagName === "A") {{
      var link = e.currentTarget;
      var href = link.getAttribute("href");
      
      if (href && !href.startsWith("#") && RDZ.session) {{
        try {{
          var url = new URL(href, window.location.origin);
          url.searchParams.set("session", RDZ.session);
          url.searchParams.set("lp", RDZ.lp);
          url.searchParams.set("liaison", RDZ.liaison);
          // Transmettre utm_campaign au form
          if (RDZ.utm_campaign) {{
            url.searchParams.set("utm_campaign", RDZ.utm_campaign);
          }}
          link.href = url.toString();
        }} catch(err) {{}}
      }}
    }}
  }};

  // ══════════════════════════════════════════════════════════
  // AUTO-BIND CTA - Match strict sur formUrl OU data-rdz-cta
  // ══════════════════════════════════════════════════════════
  function autoBindCTA() {{
    var formUrlBase = RDZ.formUrl.split("?")[0].replace(/\\/$/, "").toLowerCase();
    var links = document.querySelectorAll("a[href], [data-rdz-cta]");
    
    links.forEach(function(el) {{
      if (el.hasAttribute("data-rdz-cta")) {{
        el.addEventListener("click", function(e) {{ rdzCtaClick(e); }});
        return;
      }}
      
      if (el.href) {{
        var linkHref = el.href.split("?")[0].replace(/\\/$/, "").toLowerCase();
        if (linkHref === formUrlBase) {{
          el.addEventListener("click", function(e) {{ rdzCtaClick(e); }});
        }}
      }}
    }});
  }}

}})();
</script>'''

    # ══════════════════════════════════════════════════════════
    # SCRIPT FORM - Mode A
    # ══════════════════════════════════════════════════════════
    script_form = f'''<!-- RDZ TRACKING - FORMULAIRE {form_code} -->
<!-- À coller en fin de <body>, avant </body> -->
<script>
(function() {{
  "use strict";
  
  var RDZ = {{
    api: "{API_URL}/api/public",
    form: "{form_code}",
    formSelector: "{form_selector}",
    session: null,
    lp: "",
    liaison: "",
    utm_campaign: "",
    redirectUrl: "{redirect_url}",
    initialized: false,
    initFailed: false
  }};

  // ══════════════════════════════════════════════════════════
  // SESSION + UTM_CAMPAIGN - Priorité: URL → sessionStorage → création
  // ══════════════════════════════════════════════════════════
  async function initSession() {{
    if (RDZ.session) return RDZ.session;
    if (RDZ.initFailed) return null;
    
    var params = new URLSearchParams(window.location.search);
    
    // 1. Priorité : paramètres URL (venant de la LP)
    var urlSession = params.get("session");
    var urlLp = params.get("lp");
    var urlLiaison = params.get("liaison");
    var urlUtmCampaign = params.get("utm_campaign");
    
    if (urlSession) {{
      RDZ.session = urlSession;
      RDZ.lp = urlLp || "";
      RDZ.liaison = urlLiaison || "";
      // utm_campaign: URL priorité
      RDZ.utm_campaign = urlUtmCampaign || "";
      RDZ.initialized = true;
      
      // Stocker pour persistance
      try {{
        sessionStorage.setItem("rdz_session", RDZ.session);
        if (RDZ.lp) sessionStorage.setItem("rdz_lp", RDZ.lp);
        if (RDZ.liaison) sessionStorage.setItem("rdz_liaison", RDZ.liaison);
        if (RDZ.utm_campaign) sessionStorage.setItem("rdz_utm_campaign", RDZ.utm_campaign);
      }} catch(e) {{}}
      
      return RDZ.session;
    }}
    
    // 2. Fallback : sessionStorage
    try {{
      var storedSession = sessionStorage.getItem("rdz_session");
      if (storedSession) {{
        RDZ.session = storedSession;
        RDZ.lp = sessionStorage.getItem("rdz_lp") || "";
        RDZ.liaison = sessionStorage.getItem("rdz_liaison") || "";
        // utm_campaign depuis sessionStorage si pas dans URL
        RDZ.utm_campaign = urlUtmCampaign || sessionStorage.getItem("rdz_utm_campaign") || "";
        RDZ.initialized = true;
        return RDZ.session;
      }}
    }} catch(e) {{}}
    
    // 3. Dernière option : créer nouvelle session
    try {{
      // utm_campaign depuis URL même sans session existante
      RDZ.utm_campaign = urlUtmCampaign || "";
      
      var res = await fetch(RDZ.api + "/track/session", {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        body: JSON.stringify({{
          form_code: RDZ.form,
          lp_code: urlLp || "",
          liaison_code: urlLiaison || "",
          referrer: document.referrer,
          utm_source: params.get("utm_source") || "",
          utm_medium: params.get("utm_medium") || "",
          utm_campaign: RDZ.utm_campaign
        }})
      }});
      if (!res.ok) throw new Error("HTTP " + res.status);
      var data = await res.json();
      RDZ.session = data.session_id;
      RDZ.lp = urlLp || "";
      RDZ.liaison = urlLiaison || "";
      RDZ.initialized = true;
      
      try {{
        sessionStorage.setItem("rdz_session", RDZ.session);
        if (RDZ.utm_campaign) sessionStorage.setItem("rdz_utm_campaign", RDZ.utm_campaign);
      }} catch(e) {{}}
      
      return RDZ.session;
    }} catch(e) {{
      console.warn("[RDZ] Session init failed:", e.message);
      RDZ.initFailed = true;
      return null;
    }}
  }}

  // Tracking best-effort
  function track(eventType) {{
    if (!RDZ.session) return;
    var payload = JSON.stringify({{
      session_id: RDZ.session,
      event_type: eventType,
      lp_code: RDZ.lp,
      form_code: RDZ.form,
      liaison_code: RDZ.liaison
    }});
    
    if (navigator.sendBeacon) {{
      navigator.sendBeacon(RDZ.api + "/track/event", new Blob([payload], {{type: "application/json"}}));
    }} else {{
      fetch(RDZ.api + "/track/event", {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        body: payload,
        keepalive: true
      }}).catch(function() {{}});
    }}
  }}

  // ══════════════════════════════════════════════════════════
  // FORM START - Premier clic/focus dans le formulaire
  // ══════════════════════════════════════════════════════════
  var formStarted = false;
  
  window.rdzFormStart = async function() {{
    if (formStarted) return;
    formStarted = true;
    await initSession();
    track("form_start");
  }};

  function autoBindFormStart() {{
    var formEl = document.querySelector(RDZ.formSelector);
    if (formEl) {{
      var trigger = function() {{ rdzFormStart(); }};
      formEl.addEventListener("click", trigger, {{ once: true }});
      formEl.addEventListener("focusin", trigger, {{ once: true }});
    }}
  }}

  // ══════════════════════════════════════════════════════════
  // SUBMIT LEAD - Envoi avec utm_campaign
  // ══════════════════════════════════════════════════════════
  window.rdzSubmitLead = async function(data) {{
    await initSession();
    if (!RDZ.session) {{
      return {{ success: false, error: "Pas de session" }};
    }}

    var phone = (data.phone || "").replace(/\\D/g, "");
    if (phone.length !== 10) {{
      return {{ success: false, error: "Téléphone invalide (10 chiffres requis)" }};
    }}

    try {{
      var res = await fetch(RDZ.api + "/leads", {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        body: JSON.stringify({{
          session_id: RDZ.session,
          form_code: RDZ.form,
          lp_code: RDZ.lp,
          liaison_code: RDZ.liaison,
          utm_campaign: RDZ.utm_campaign,
          phone: phone,
          nom: data.nom || "",
          prenom: data.prenom || "",
          civilite: data.civilite || "",
          email: data.email || "",
          departement: data.departement || "",
          ville: data.ville || "",
          adresse: data.adresse || "",
          type_logement: data.type_logement || "",
          statut_occupant: data.statut_occupant || "",
          surface_habitable: data.surface_habitable || "",
          annee_construction: data.annee_construction || "",
          type_chauffage: data.type_chauffage || "",
          facture_electricite: data.facture_electricite || "",
          facture_chauffage: data.facture_chauffage || "",
          type_projet: data.type_projet || "",
          delai_projet: data.delai_projet || "",
          budget: data.budget || "",
          rgpd_consent: data.rgpd_consent || false,
          newsletter: data.newsletter || false
        }})
      }});
      
      var result = await res.json();
      
      if (result.success) {{
        if (window.dataLayer) {{
          window.dataLayer.push({{
            event: "form_submitted",
            lead_id: result.lead_id,
            lp_code: RDZ.lp,
            form_code: RDZ.form,
            liaison_code: RDZ.liaison,
            utm_campaign: RDZ.utm_campaign
          }});
        }}
        
        if (RDZ.redirectUrl) {{
          window.location.href = RDZ.redirectUrl;
        }}
      }}
      
      return result;
    }} catch(e) {{
      console.error("[RDZ] Submit error:", e.message);
      return {{ success: false, error: e.message }};
    }}
  }};

  // Init au chargement
  document.addEventListener("DOMContentLoaded", function() {{
    initSession();
    autoBindFormStart();
  }});

}})();
</script>'''

    # Construire le brief complet
    return {
        "mode": "separate",
        "mode_label": "Mode A - LP et Formulaire sur pages séparées",
        
        "metadata": {
            "lp_code": lp_code,
            "form_code": form_code,
            "liaison_code": liaison_code,
            "product_type": product_type,
            "account_name": account_name,
            "selected_product": selected_product
        },
        
        "lp": {
            "code": lp_code,
            "url": lp_url,
            "name": lp_name
        },
        
        "form": {
            "code": form_code,
            "url": form_url,
            "name": form_name,
            "selector": form_selector
        },
        
        "gtm": {
            "head": gtm_head
        },
        
        "scripts": {
            "lp": {
                "code": script_lp,
                "placement": "end_body"
            },
            "form": {
                "code": script_form,
                "placement": "end_body"
            }
        },
        
        "instructions": {
            "summary": "Mode A : 2 pages distinctes. Transmission session + utm_campaign via URL. Auto-bind CTA et Form start.",
            
            "lp_page": {
                "title": "PAGE LP (Landing Page)",
                "steps": [
                    {"step": 1, "action": "GTM dans <head> uniquement", "code_ref": "gtm.head"},
                    {"step": 2, "action": "Script RDZ LP en fin de <body>", "code_ref": "scripts.lp.code"},
                    {"step": 3, "action": "AUTO-BIND: liens vers form détectés automatiquement, ou ajouter data-rdz-cta"}
                ]
            },
            
            "form_page": {
                "title": "PAGE FORMULAIRE",
                "steps": [
                    {"step": 1, "action": "GTM dans <head> uniquement", "code_ref": "gtm.head"},
                    {"step": 2, "action": "Script RDZ Form en fin de <body>", "code_ref": "scripts.form.code"},
                    {"step": 3, "action": "AUTO-BIND FORM START: premier clic/focus détecté"},
                    {"step": 4, "action": "Soumission: rdzSubmitLead({phone, nom, departement, ...})"}
                ]
            },
            
            "session_transmission": {
                "title": "TRANSMISSION LP → FORM",
                "url_example": form_url + "?session=xxx&lp=" + lp_code + "&liaison=" + liaison_code + "&utm_campaign=xxx",
                "priority": ["1. Paramètres URL", "2. sessionStorage (fallback)", "3. Nouvelle session"]
            },
            
            "field_names": {
                "title": "NOMS DES CHAMPS (NE PAS MODIFIER)",
                "required": ["phone", "nom", "departement"],
                "optional": ["prenom", "civilite", "email", "ville", "adresse", "type_logement", "statut_occupant", "surface_habitable", "annee_construction", "type_chauffage", "facture_electricite", "facture_chauffage", "type_projet", "delai_projet", "budget", "rgpd_consent", "newsletter"]
            }
        }
    }


async def _generate_mode_b(
    lp_code: str,
    lp_url: str,
    lp_name: str,
    form_code: str,
    form_url: str,
    form_name: str,
    liaison_code: str,
    product_type: str,
    account_name: str,
    gtm_head: str,
    redirect_url: str,
    form_selector: str,
    form_anchor: str,
    selected_product: str = None
) -> dict:
    """
    Génère le brief Mode B (Form intégré dans LP)
    
    utm_campaign: lire dans URL, envoyer dans track/session + /leads au submit
    """
    
    script_unique = f'''<!-- RDZ TRACKING - LP + FORMULAIRE INTÉGRÉS -->
<!-- {lp_code} + {form_code} -->
<!-- À coller en fin de <body>, avant </body> -->
<script>
(function() {{
  "use strict";
  
  var RDZ = {{
    api: "{API_URL}/api/public",
    lp: "{lp_code}",
    form: "{form_code}",
    liaison: "{liaison_code}",
    formSelector: "{form_selector}",
    formAnchor: "{form_anchor}",
    session: null,
    utm_campaign: "",
    redirectUrl: "{redirect_url}",
    initialized: false,
    initFailed: false
  }};

  // ══════════════════════════════════════════════════════════
  // SESSION + UTM_CAMPAIGN - Création/récupération automatique
  // ══════════════════════════════════════════════════════════
  async function initSession() {{
    if (RDZ.session) return RDZ.session;
    if (RDZ.initFailed) return null;
    
    // Récupérer session existante
    try {{
      RDZ.session = sessionStorage.getItem("rdz_session");
      RDZ.utm_campaign = sessionStorage.getItem("rdz_utm_campaign") || "";
      if (RDZ.session) {{
        RDZ.initialized = true;
        return RDZ.session;
      }}
    }} catch(e) {{}}
    
    try {{
      var params = new URLSearchParams(window.location.search);
      
      // Capturer utm_campaign depuis URL
      RDZ.utm_campaign = params.get("utm_campaign") || "";
      
      var res = await fetch(RDZ.api + "/track/session", {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        body: JSON.stringify({{
          lp_code: RDZ.lp,
          form_code: RDZ.form,
          liaison_code: RDZ.liaison,
          referrer: document.referrer,
          utm_source: params.get("utm_source") || "",
          utm_medium: params.get("utm_medium") || "",
          utm_campaign: RDZ.utm_campaign
        }})
      }});
      if (!res.ok) throw new Error("HTTP " + res.status);
      var data = await res.json();
      RDZ.session = data.session_id;
      RDZ.initialized = true;
      
      try {{
        sessionStorage.setItem("rdz_session", RDZ.session);
        if (RDZ.utm_campaign) sessionStorage.setItem("rdz_utm_campaign", RDZ.utm_campaign);
      }} catch(e) {{}}
      
      return RDZ.session;
    }} catch(e) {{
      console.warn("[RDZ] Session init failed:", e.message);
      RDZ.initFailed = true;
      return null;
    }}
  }}

  // Tracking best-effort
  function track(eventType) {{
    if (!RDZ.session) return;
    var payload = JSON.stringify({{
      session_id: RDZ.session,
      event_type: eventType,
      lp_code: RDZ.lp,
      form_code: RDZ.form,
      liaison_code: RDZ.liaison
    }});
    
    if (navigator.sendBeacon) {{
      navigator.sendBeacon(RDZ.api + "/track/event", new Blob([payload], {{type: "application/json"}}));
    }} else {{
      fetch(RDZ.api + "/track/event", {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        body: payload,
        keepalive: true
      }}).catch(function() {{}});
    }}
  }}

  // ══════════════════════════════════════════════════════════
  // VISITE LP - Automatique au chargement
  // ══════════════════════════════════════════════════════════
  document.addEventListener("DOMContentLoaded", async function() {{
    await initSession();
    if (RDZ.session) track("lp_visit");
    autoBindCTA();
    autoBindFormStart();
  }});

  // ══════════════════════════════════════════════════════════
  // CTA CLICK - 1 seule fois par session
  // ══════════════════════════════════════════════════════════
  var ctaClicked = false;
  
  window.rdzCtaClick = function() {{
    if (ctaClicked) return;
    ctaClicked = true;
    track("cta_click");
  }};

  function autoBindCTA() {{
    var anchors = [RDZ.formAnchor, "#form", "#formulaire", "#contact", "#devis"];
    var links = document.querySelectorAll("a[href], [data-rdz-cta]");
    
    links.forEach(function(el) {{
      if (el.hasAttribute("data-rdz-cta")) {{
        el.addEventListener("click", function() {{ rdzCtaClick(); }});
        return;
      }}
      
      var href = el.getAttribute("href");
      if (href && anchors.indexOf(href) !== -1) {{
        el.addEventListener("click", function() {{ rdzCtaClick(); }});
      }}
    }});
  }}

  // ══════════════════════════════════════════════════════════
  // FORM START - Premier clic/focus
  // ══════════════════════════════════════════════════════════
  var formStarted = false;
  
  window.rdzFormStart = async function() {{
    if (formStarted) return;
    formStarted = true;
    await initSession();
    track("form_start");
  }};

  function autoBindFormStart() {{
    var formEl = document.querySelector(RDZ.formSelector);
    if (formEl) {{
      var trigger = function() {{ rdzFormStart(); }};
      formEl.addEventListener("click", trigger, {{ once: true }});
      formEl.addEventListener("focusin", trigger, {{ once: true }});
    }}
  }}

  // ══════════════════════════════════════════════════════════
  // SUBMIT LEAD - Envoi avec utm_campaign
  // ══════════════════════════════════════════════════════════
  window.rdzSubmitLead = async function(data) {{
    await initSession();
    if (!RDZ.session) {{
      return {{ success: false, error: "Pas de session" }};
    }}

    var phone = (data.phone || "").replace(/\\D/g, "");
    if (phone.length !== 10) {{
      return {{ success: false, error: "Téléphone invalide (10 chiffres requis)" }};
    }}

    try {{
      var res = await fetch(RDZ.api + "/leads", {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        body: JSON.stringify({{
          session_id: RDZ.session,
          form_code: RDZ.form,
          lp_code: RDZ.lp,
          liaison_code: RDZ.liaison,
          utm_campaign: RDZ.utm_campaign,
          phone: phone,
          nom: data.nom || "",
          prenom: data.prenom || "",
          civilite: data.civilite || "",
          email: data.email || "",
          departement: data.departement || "",
          ville: data.ville || "",
          adresse: data.adresse || "",
          type_logement: data.type_logement || "",
          statut_occupant: data.statut_occupant || "",
          surface_habitable: data.surface_habitable || "",
          annee_construction: data.annee_construction || "",
          type_chauffage: data.type_chauffage || "",
          facture_electricite: data.facture_electricite || "",
          facture_chauffage: data.facture_chauffage || "",
          type_projet: data.type_projet || "",
          delai_projet: data.delai_projet || "",
          budget: data.budget || "",
          rgpd_consent: data.rgpd_consent || false,
          newsletter: data.newsletter || false
        }})
      }});
      
      var result = await res.json();
      
      if (result.success) {{
        if (window.dataLayer) {{
          window.dataLayer.push({{
            event: "form_submitted",
            lead_id: result.lead_id,
            lp_code: RDZ.lp,
            form_code: RDZ.form,
            liaison_code: RDZ.liaison,
            utm_campaign: RDZ.utm_campaign
          }});
        }}
        
        if (RDZ.redirectUrl) {{
          window.location.href = RDZ.redirectUrl;
        }}
      }}
      
      return result;
    }} catch(e) {{
      console.error("[RDZ] Submit error:", e.message);
      return {{ success: false, error: e.message }};
    }}
  }};

}})();
</script>'''

    return {
        "mode": "integrated",
        "mode_label": "Mode B - Formulaire intégré dans la Landing Page",
        
        "metadata": {
            "lp_code": lp_code,
            "form_code": form_code,
            "liaison_code": liaison_code,
            "product_type": product_type,
            "account_name": account_name,
            "selected_product": selected_product
        },
        
        "lp": {
            "code": lp_code,
            "url": lp_url,
            "name": lp_name
        },
        
        "form": {
            "code": form_code,
            "url": form_url,
            "name": form_name,
            "selector": form_selector,
            "anchor": form_anchor
        },
        
        "gtm": {
            "head": gtm_head
        },
        
        "scripts": {
            "unique": {
                "code": script_unique,
                "placement": "end_body"
            }
        },
        
        "instructions": {
            "summary": "Mode B : 1 page avec LP + Form intégrés. 1 seul GTM. 1 seul script. utm_campaign lu depuis URL.",
            
            "single_page": {
                "title": "PAGE UNIQUE (LP + Formulaire)",
                "steps": [
                    {"step": 1, "action": "GTM dans <head> uniquement", "code_ref": "gtm.head"},
                    {"step": 2, "action": "Script RDZ unique en fin de <body>", "code_ref": "scripts.unique.code"},
                    {"step": 3, "action": "AUTO-BIND CTA: anchors détectés automatiquement"},
                    {"step": 4, "action": "AUTO-BIND FORM START: premier clic/focus détecté"},
                    {"step": 5, "action": "Soumission: rdzSubmitLead({phone, nom, departement, ...})"}
                ]
            },
            
            "field_names": {
                "title": "NOMS DES CHAMPS (NE PAS MODIFIER)",
                "required": ["phone", "nom", "departement"],
                "optional": ["prenom", "civilite", "email", "ville", "adresse", "type_logement", "statut_occupant", "surface_habitable", "annee_construction", "type_chauffage", "facture_electricite", "facture_chauffage", "type_projet", "delai_projet", "budget", "rgpd_consent", "newsletter"]
            }
        }
    }


# ══════════════════════════════════════════════════════════════════════════════
# BRIEF DEPUIS FORM - Point d'entrée alternatif
# ══════════════════════════════════════════════════════════════════════════════

async def generate_form_brief(form_id: str, mode: str = "separate", selected_product: str = None) -> dict:
    """
    Génère le brief depuis un Form (cherche la LP liée)
    
    Args:
        form_id: ID du formulaire
        mode: "separate" ou "integrated"
        selected_product: Produit sélectionné pour URL de redirection
    """
    
    form = await db.forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        return {"error": "Formulaire non trouvé"}
    
    # Chercher la LP liée
    lp_id = form.get("lp_id")
    lp = None
    
    if lp_id:
        lp = await db.lps.find_one({"id": lp_id}, {"_id": 0})
    
    if not lp:
        lp = await db.lps.find_one({"form_id": form_id}, {"_id": 0})
    
    if not lp:
        return {"error": "Aucune LP liée à ce formulaire. Veuillez d'abord lier une LP."}
    
    return await generate_brief(lp["id"], mode, selected_product)
