"""
Brief Generator V2 - Génération de briefs pour LP et Formulaires
Version: 2.0
Date: 2026-02-12

Modes supportés:
- Mode A (separate): LP et Formulaire sur pages séparées
- Mode B (integrated): Formulaire intégré dans la LP

Garde-fous appliqués:
1. CTA navigation: sendBeacon/keepalive, pas de preventDefault abusif
2. Auto-bind CTA: strict match formUrlBase OU data-rdz-cta
3. Robustesse: fail silently, pas de retry infini
4. Liaison_code: jamais remplacé par form_code, UNKNOWN si absent
"""

from config import db, BACKEND_URL

API_URL = BACKEND_URL.rstrip("/")


async def generate_brief_v2(lp_id: str, mode: str = "separate", selected_product: str = None) -> dict:
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
    """Génère le brief Mode A (LP + Form séparés)"""
    
    # Script LP
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
    initialized: false,
    initFailed: false
  }};

  // ══════════════════════════════════════════════════════════
  // SESSION - Création automatique au chargement
  // ══════════════════════════════════════════════════════════
  async function initSession() {{
    if (RDZ.session) return RDZ.session;
    if (RDZ.initFailed) return null; // Ne pas retry si déjà échoué
    
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
        sessionStorage.setItem("rdz_lp", RDZ.lp);
        sessionStorage.setItem("rdz_liaison", RDZ.liaison);
        // Stocker utm_campaign pour transmission au form
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
    
    // Priorité sendBeacon (ne bloque pas la navigation)
    if (navigator.sendBeacon) {{
      navigator.sendBeacon(RDZ.api + "/track/event", new Blob([payload], {{type: "application/json"}}));
    }} else {{
      // Fallback fetch keepalive
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
  // CTA CLICK - 1 seule fois par session
  // Utilise sendBeacon pour ne pas bloquer la navigation
  // ══════════════════════════════════════════════════════════
  var ctaClicked = false;
  
  window.rdzCtaClick = function(e) {{
    if (ctaClicked) return;
    ctaClicked = true;
    
    // Track sans bloquer
    track("cta_click");
    
    // Construire URL avec params session
    if (e && e.currentTarget && e.currentTarget.tagName === "A") {{
      var link = e.currentTarget;
      var href = link.getAttribute("href");
      
      // Ne pas modifier les liens externes ou target="_blank" déjà gérés
      if (href && !href.startsWith("#") && RDZ.session) {{
        try {{
          var url = new URL(href, window.location.origin);
          url.searchParams.set("session", RDZ.session);
          url.searchParams.set("lp", RDZ.lp);
          url.searchParams.set("liaison", RDZ.liaison);
          link.href = url.toString();
        }} catch(err) {{}}
      }}
    }}
    // Ne PAS faire preventDefault - laisser la navigation se faire normalement
  }};

  // ══════════════════════════════════════════════════════════
  // AUTO-BIND CTA - Détection stricte des liens vers le Form
  // Match uniquement sur formUrlBase exact OU data-rdz-cta
  // ══════════════════════════════════════════════════════════
  function autoBindCTA() {{
    var formUrlBase = RDZ.formUrl.split("?")[0].replace(/\\/$/, "").toLowerCase();
    var links = document.querySelectorAll("a[href], [data-rdz-cta]");
    
    links.forEach(function(el) {{
      // Opt-in explicite via data-rdz-cta
      if (el.hasAttribute("data-rdz-cta")) {{
        el.addEventListener("click", function(e) {{ rdzCtaClick(e); }});
        return;
      }}
      
      // Match strict sur URL du form
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

    # Script Form
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
    redirectUrl: "{redirect_url}",
    initialized: false,
    initFailed: false
  }};

  // ══════════════════════════════════════════════════════════
  // SESSION - Priorité: URL → sessionStorage → création
  // Liaison: jamais remplacée par form_code, UNKNOWN si absente
  // ══════════════════════════════════════════════════════════
  async function initSession() {{
    if (RDZ.session) return RDZ.session;
    if (RDZ.initFailed) return null;
    
    var params = new URLSearchParams(window.location.search);
    
    // 1. Priorité : paramètres URL (venant de la LP)
    var urlSession = params.get("session");
    var urlLp = params.get("lp");
    var urlLiaison = params.get("liaison");
    
    if (urlSession) {{
      RDZ.session = urlSession;
      RDZ.lp = urlLp || "";
      RDZ.liaison = urlLiaison || "";  // Jamais form_code, garder vide si absent
      RDZ.initialized = true;
      try {{
        sessionStorage.setItem("rdz_session", RDZ.session);
        if (RDZ.lp) sessionStorage.setItem("rdz_lp", RDZ.lp);
        if (RDZ.liaison) sessionStorage.setItem("rdz_liaison", RDZ.liaison);
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
        RDZ.initialized = true;
        return RDZ.session;
      }}
    }} catch(e) {{}}
    
    // 3. Dernière option : créer nouvelle session
    try {{
      var res = await fetch(RDZ.api + "/track/session", {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        body: JSON.stringify({{
          form_code: RDZ.form,
          lp_code: urlLp || "",
          liaison_code: urlLiaison || "",  // Vide si inconnu, jamais form_code
          referrer: document.referrer,
          utm_source: params.get("utm_source") || "",
          utm_medium: params.get("utm_medium") || "",
          utm_campaign: params.get("utm_campaign") || ""
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

  // ══════════════════════════════════════════════════════════
  // AUTO-BIND FORM START - Sur le conteneur form
  // ══════════════════════════════════════════════════════════
  function autoBindFormStart() {{
    var formEl = document.querySelector(RDZ.formSelector);
    if (formEl) {{
      var trigger = function() {{ rdzFormStart(); }};
      formEl.addEventListener("click", trigger, {{ once: true }});
      formEl.addEventListener("focusin", trigger, {{ once: true }});
    }}
  }}

  // ══════════════════════════════════════════════════════════
  // SUBMIT LEAD - Envoi du formulaire
  // ══════════════════════════════════════════════════════════
  window.rdzSubmitLead = async function(data) {{
    await initSession();
    if (!RDZ.session) {{
      return {{ success: false, error: "Pas de session" }};
    }}

    // Validation téléphone (10 chiffres)
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
        // CONVERSION ADS - Uniquement après confirmation serveur
        if (window.dataLayer) {{
          window.dataLayer.push({{
            event: "form_submitted",
            lead_id: result.lead_id,
            lp_code: RDZ.lp,
            form_code: RDZ.form,
            liaison_code: RDZ.liaison
          }});
        }}
        
        // Redirection après réponse serveur
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
            "summary": "Mode A : 2 pages distinctes. Transmission session via URL (session, lp, liaison). Auto-bind CTA (strict) et Form start.",
            
            "lp_page": {
                "title": "PAGE LP (Landing Page)",
                "steps": [
                    {
                        "step": 1,
                        "action": "GTM à coller dans <head> uniquement",
                        "code_ref": "gtm.head",
                        "important": "Ne jamais mettre de GTM dans <body> ou <noscript>"
                    },
                    {
                        "step": 2,
                        "action": "Script RDZ LP à coller en fin de <body>, avant </body>",
                        "code_ref": "scripts.lp.code",
                        "important": "Ce script gère : session, visite LP, clic CTA, transmission URL"
                    },
                    {
                        "step": 3,
                        "action": "AUTO-BIND : Les liens vers le formulaire sont détectés automatiquement (match strict sur URL)",
                        "details": "Ou ajouter data-rdz-cta sur les éléments CTA pour opt-in explicite",
                        "fallback": "Si besoin manuel : onclick=\"rdzCtaClick(event)\""
                    }
                ]
            },
            
            "form_page": {
                "title": "PAGE FORMULAIRE",
                "steps": [
                    {
                        "step": 1,
                        "action": "GTM à coller dans <head> uniquement",
                        "code_ref": "gtm.head",
                        "important": "Même code GTM que sur la LP"
                    },
                    {
                        "step": 2,
                        "action": "Script RDZ Form à coller en fin de <body>, avant </body>",
                        "code_ref": "scripts.form.code",
                        "important": "Ce script récupère automatiquement session/lp/liaison depuis l'URL"
                    },
                    {
                        "step": 3,
                        "action": "AUTO-BIND FORM START : Détection automatique du premier clic/focus",
                        "details": "Sélecteur utilisé : " + form_selector,
                        "fallback": "Si besoin manuel : onclick=\"rdzFormStart()\""
                    },
                    {
                        "step": 4,
                        "action": "À la soumission, appeler rdzSubmitLead(data)",
                        "example": "rdzSubmitLead({ phone: '0612345678', nom: 'Dupont', departement: '75' })",
                        "important": "La conversion Ads est déclenchée uniquement après confirmation serveur"
                    }
                ]
            },
            
            "session_transmission": {
                "title": "TRANSMISSION SESSION LP → FORM",
                "method": "Les paramètres sont ajoutés automatiquement à l'URL par le script LP",
                "url_example": form_url + "?session=xxx&lp=" + lp_code + "&liaison=" + liaison_code,
                "priority": [
                    "1. Paramètres URL (session, lp, liaison)",
                    "2. sessionStorage (fallback)",
                    "3. Création nouvelle session (dernier recours)"
                ],
                "liaison_rule": "Si liaison inconnue, elle reste vide (jamais remplacée par form_code)"
            },
            
            "field_names": {
                "title": "NOMS DES CHAMPS (NE PAS MODIFIER)",
                "required": ["phone", "nom", "departement"],
                "optional": ["prenom", "civilite", "email", "ville", "adresse", "type_logement", "statut_occupant", "surface_habitable", "annee_construction", "type_chauffage", "facture_electricite", "facture_chauffage", "type_projet", "delai_projet", "budget", "rgpd_consent", "newsletter"],
                "validation": {
                    "phone": "10 chiffres exactement, format français"
                }
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
    """Génère le brief Mode B (Form intégré dans LP)"""
    
    # Script unique
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
    redirectUrl: "{redirect_url}",
    initialized: false,
    initFailed: false
  }};

  // ══════════════════════════════════════════════════════════
  // SESSION - Création/récupération automatique
  // ══════════════════════════════════════════════════════════
  async function initSession() {{
    if (RDZ.session) return RDZ.session;
    if (RDZ.initFailed) return null;
    
    // Tenter de récupérer session existante
    try {{
      RDZ.session = sessionStorage.getItem("rdz_session");
      if (RDZ.session) {{
        RDZ.initialized = true;
        return RDZ.session;
      }}
    }} catch(e) {{}}
    
    try {{
      var params = new URLSearchParams(window.location.search);
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
          utm_campaign: params.get("utm_campaign") || ""
        }})
      }});
      if (!res.ok) throw new Error("HTTP " + res.status);
      var data = await res.json();
      RDZ.session = data.session_id;
      RDZ.initialized = true;
      try {{
        sessionStorage.setItem("rdz_session", RDZ.session);
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
  // CTA CLICK - 1 seule fois par session (sendBeacon)
  // ══════════════════════════════════════════════════════════
  var ctaClicked = false;
  
  window.rdzCtaClick = function() {{
    if (ctaClicked) return;
    ctaClicked = true;
    track("cta_click");
    // Pas de preventDefault - laisser le scroll/navigation se faire
  }};

  // ══════════════════════════════════════════════════════════
  // AUTO-BIND CTA - Détection des anchors vers le form
  // Match strict sur anchor OU data-rdz-cta
  // ══════════════════════════════════════════════════════════
  function autoBindCTA() {{
    var anchors = [RDZ.formAnchor, "#form", "#formulaire", "#contact", "#devis"];
    var links = document.querySelectorAll("a[href], [data-rdz-cta]");
    
    links.forEach(function(el) {{
      // Opt-in explicite
      if (el.hasAttribute("data-rdz-cta")) {{
        el.addEventListener("click", function() {{ rdzCtaClick(); }});
        return;
      }}
      
      // Match strict sur anchor
      var href = el.getAttribute("href");
      if (href && anchors.indexOf(href) !== -1) {{
        el.addEventListener("click", function() {{ rdzCtaClick(); }});
      }}
    }});
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
  // SUBMIT LEAD - Envoi du formulaire
  // ══════════════════════════════════════════════════════════
  window.rdzSubmitLead = async function(data) {{
    await initSession();
    if (!RDZ.session) {{
      return {{ success: false, error: "Pas de session" }};
    }}

    // Validation téléphone (10 chiffres)
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
        // CONVERSION ADS - Uniquement après confirmation serveur
        if (window.dataLayer) {{
          window.dataLayer.push({{
            event: "form_submitted",
            lead_id: result.lead_id,
            lp_code: RDZ.lp,
            form_code: RDZ.form,
            liaison_code: RDZ.liaison
          }});
        }}
        
        // Redirection après réponse serveur
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

    # Construire le brief complet
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
            "summary": "Mode B : 1 seule page avec LP et Formulaire intégrés. 1 seul GTM. 1 seul script RDZ. Auto-bind CTA et Form start.",
            
            "single_page": {
                "title": "PAGE UNIQUE (LP + Formulaire)",
                "steps": [
                    {
                        "step": 1,
                        "action": "GTM à coller dans <head> uniquement",
                        "code_ref": "gtm.head",
                        "important": "1 seul GTM pour toute la page. Ne jamais mettre de GTM dans <body> ou <noscript>"
                    },
                    {
                        "step": 2,
                        "action": "Script RDZ UNIQUE à coller en fin de <body>, avant </body>",
                        "code_ref": "scripts.unique.code",
                        "important": "Ce script gère tout : session, visite LP, CTA, form_start, submit, conversion"
                    },
                    {
                        "step": 3,
                        "action": "AUTO-BIND CTA : Détection des liens anchor vers le formulaire",
                        "details": "Anchors détectés : " + form_anchor + ", #form, #formulaire, #contact, #devis",
                        "fallback": "Ou ajouter data-rdz-cta sur les éléments CTA"
                    },
                    {
                        "step": 4,
                        "action": "AUTO-BIND FORM START : Détection automatique du premier clic/focus",
                        "details": "Sélecteur utilisé : " + form_selector,
                        "fallback": "Si besoin manuel : onclick=\"rdzFormStart()\""
                    },
                    {
                        "step": 5,
                        "action": "À la soumission, appeler rdzSubmitLead(data)",
                        "example": "rdzSubmitLead({ phone: '0612345678', nom: 'Dupont', departement: '75' })",
                        "important": "La conversion Ads est déclenchée uniquement après confirmation serveur"
                    }
                ]
            },
            
            "field_names": {
                "title": "NOMS DES CHAMPS (NE PAS MODIFIER)",
                "required": ["phone", "nom", "departement"],
                "optional": ["prenom", "civilite", "email", "ville", "adresse", "type_logement", "statut_occupant", "surface_habitable", "annee_construction", "type_chauffage", "facture_electricite", "facture_chauffage", "type_projet", "delai_projet", "budget", "rgpd_consent", "newsletter"],
                "validation": {
                    "phone": "10 chiffres exactement, format français"
                }
            }
        }
    }


# ══════════════════════════════════════════════════════════════════════
# Fonction pour générer brief depuis un Form (point d'entrée alternatif)
# ══════════════════════════════════════════════════════════════════════

async def generate_form_brief_v2(form_id: str, mode: str = "separate", selected_product: str = None) -> dict:
    """
    Génère le brief depuis un Form (cherche la LP liée)
    
    Args:
        form_id: ID du formulaire
        mode: "separate" ou "integrated"
        selected_product: Produit sélectionné pour URL de redirection
    """
    
    # Récupérer le Form
    form = await db.forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        return {"error": "Formulaire non trouvé"}
    
    # Chercher la LP liée
    lp_id = form.get("lp_id")
    lp = None
    
    if lp_id:
        lp = await db.lps.find_one({"id": lp_id}, {"_id": 0})
    
    if not lp:
        # Chercher une LP qui référence ce form
        lp = await db.lps.find_one({"form_id": form_id}, {"_id": 0})
    
    if not lp:
        return {"error": "Aucune LP liée à ce formulaire. Veuillez d'abord lier une LP."}
    
    # Utiliser generate_brief_v2 avec l'ID de la LP trouvée
    return await generate_brief_v2(lp["id"], mode, selected_product)
