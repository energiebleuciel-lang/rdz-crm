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
    
    # Code conversion GTM (exécuté après submit valide)
    gtm_conversion = ""
    if account:
        gtm_conversion = account.get("gtm_conversion", "") or ""
    
    # URL de redirection par produit
    redirect_url = form.get("redirect_url", "/merci")
    if selected_product and account:
        product_key = f"redirect_url_{selected_product.lower()}"
        product_redirect_url = account.get(product_key, "")
        if product_redirect_url:
            redirect_url = product_redirect_url
    # Fallback: utiliser aussi le product_type du form si selected_product n'est pas défini
    elif product_type and account:
        product_key = f"redirect_url_{product_type.lower()}"
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
            gtm_conversion=gtm_conversion,
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
            gtm_conversion=gtm_conversion,
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
    gtm_conversion: str,
    redirect_url: str,
    form_selector: str,
    selected_product: str = None
) -> dict:
    """
    Génère le brief Mode A (LP + Form séparés)
    
    utm_campaign:
    - Script LP: lire depuis URL, envoyer dans track/session, stocker sessionStorage, ajouter à URL form
    - Script Form: récupérer (URL priorité, sinon sessionStorage), envoyer dans /leads
    
    Post-submit:
    - Exécuter gtm_conversion (si défini)
    - Rediriger vers redirect_url
    """
    
    # Formater le code conversion GTM en fonction JavaScript
    # Si vide ou null, on met null. Sinon on wrap dans une fonction
    if gtm_conversion and gtm_conversion.strip():
        # Le code conversion est wrappé dans une fonction qui reçoit les données du lead
        gtm_conversion_js = f'''function(data) {{
      try {{
        // Variables disponibles: data.lead_id, data.lp_code, data.form_code, data.liaison_code, data.utm_campaign, data.utm_source, data.utm_medium
        {gtm_conversion}
      }} catch(e) {{ console.warn("RDZ GTM Conversion error:", e); }}
    }}'''
    else:
        gtm_conversion_js = "null"
    
    # ══════════════════════════════════════════════════════════
    # SCRIPT LP - Mode A - RDZ TRACKING COMPLET
    # ══════════════════════════════════════════════════════════
    script_lp = f'''<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<!-- RDZ TRACKING - LANDING PAGE {lp_code}                                       -->
<!-- À coller AVANT </body>                                                       -->
<!-- Version: 2.1 - Tracking complet, sendBeacon compatible, URL normalisée      -->
<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<script>
(function() {{
  "use strict";
  
  // ══════════════════════════════════════════════════════════
  // CONFIGURATION
  // ══════════════════════════════════════════════════════════
  var RDZ = {{
    api: "{API_URL}/api/public",
    lp: "{lp_code}",
    form: "{form_code}",
    liaison: "{liaison_code}",
    formUrl: "{form_url}",
    session: null,
    utm: {{}},
    initialized: false,
    initFailed: false
  }};

  // ══════════════════════════════════════════════════════════
  // UTILS - Normalisation URL pour matching CTA
  // ══════════════════════════════════════════════════════════
  function normalizeUrl(url) {{
    if (!url) return "";
    try {{
      // Supprimer protocole, query params, hash, trailing slash
      return url
        .replace(/^https?:\\/\\//i, "")  // Supprimer http:// ou https://
        .split("?")[0]                   // Supprimer query params
        .split("#")[0]                   // Supprimer hash
        .replace(/\\/+$/, "")            // Supprimer trailing slashes
        .toLowerCase();
    }} catch(e) {{
      return url.toLowerCase();
    }}
  }}

  // ══════════════════════════════════════════════════════════
  // 3. CAMPAIGN CAPTURE - URL puis sessionStorage
  // ══════════════════════════════════════════════════════════
  function captureUTM() {{
    var params = new URLSearchParams(window.location.search);
    var keys = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "gclid", "fbclid"];
    
    keys.forEach(function(key) {{
      // Priorité 1: URL
      var val = params.get(key);
      if (val) {{
        RDZ.utm[key] = val;
        try {{ sessionStorage.setItem("rdz_" + key, val); }} catch(e) {{}}
      }} else {{
        // Priorité 2: sessionStorage
        try {{ RDZ.utm[key] = sessionStorage.getItem("rdz_" + key) || ""; }} catch(e) {{ RDZ.utm[key] = ""; }}
      }}
    }});
  }}

  // ══════════════════════════════════════════════════════════
  // 1. SESSION INITIALIZATION - Anti-doublon côté serveur
  // ══════════════════════════════════════════════════════════
  async function initSession() {{
    if (RDZ.session) return RDZ.session;
    if (RDZ.initFailed) return null;
    
    // Vérifier session existante pour cette LP
    try {{
      var stored = sessionStorage.getItem("rdz_session");
      var storedLp = sessionStorage.getItem("rdz_lp");
      if (stored && storedLp === RDZ.lp) {{
        RDZ.session = stored;
        RDZ.initialized = true;
        return RDZ.session;
      }}
    }} catch(e) {{}}
    
    try {{
      captureUTM();
      
      var res = await fetch(RDZ.api + "/track/session", {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        body: JSON.stringify({{
          lp_code: RDZ.lp,
          form_code: RDZ.form,
          liaison_code: RDZ.liaison,
          referrer: document.referrer,
          user_agent: navigator.userAgent,
          utm_source: RDZ.utm.utm_source || "",
          utm_medium: RDZ.utm.utm_medium || "",
          utm_campaign: RDZ.utm.utm_campaign || "",
          utm_content: RDZ.utm.utm_content || "",
          utm_term: RDZ.utm.utm_term || "",
          gclid: RDZ.utm.gclid || "",
          fbclid: RDZ.utm.fbclid || ""
        }})
      }});
      
      if (!res.ok) throw new Error("HTTP " + res.status);
      var data = await res.json();
      RDZ.session = data.session_id;
      RDZ.initialized = true;
      
      // Stocker pour persistance et transmission au form
      try {{
        sessionStorage.setItem("rdz_session", RDZ.session);
        sessionStorage.setItem("rdz_lp", RDZ.lp);
        sessionStorage.setItem("rdz_liaison", RDZ.liaison);
      }} catch(e) {{}}
      
      return RDZ.session;
    }} catch(e) {{
      // Fail silently - ne pas bloquer le site
      RDZ.initFailed = true;
      return null;
    }}
  }}

  // ══════════════════════════════════════════════════════════
  // 2. LP VISIT TRACKING - TOUJOURS envoyé (anti-doublon serveur)
  // ══════════════════════════════════════════════════════════
  function trackLPVisit() {{
    if (!RDZ.session) return;
    
    var payload = JSON.stringify({{
      session_id: RDZ.session,
      lp_code: RDZ.lp,
      utm_source: RDZ.utm.utm_source || "",
      utm_medium: RDZ.utm.utm_medium || "",
      utm_campaign: RDZ.utm.utm_campaign || "",
      utm_content: RDZ.utm.utm_content || "",
      utm_term: RDZ.utm.utm_term || "",
      gclid: RDZ.utm.gclid || "",
      fbclid: RDZ.utm.fbclid || "",
      referrer: document.referrer,
      user_agent: navigator.userAgent
    }});
    
    // sendBeacon pour fiabilité (fonctionne même si page fermée)
    if (navigator.sendBeacon) {{
      navigator.sendBeacon(RDZ.api + "/track/lp-visit", new Blob([payload], {{type: "application/json"}}));
    }} else {{
      fetch(RDZ.api + "/track/lp-visit", {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        body: payload,
        keepalive: true
      }}).catch(function() {{}});
    }}
  }}

  // ══════════════════════════════════════════════════════════
  // 7. RELIABILITY - sendBeacon pour tous les events
  // ══════════════════════════════════════════════════════════
  function trackEvent(eventType) {{
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
  // 4. CTA CLICK - sendBeacon + URL params transmission
  // ══════════════════════════════════════════════════════════
  var ctaClicked = false;
  
  function handleCtaClick(e) {{
    // Track 1 seule fois (anti-doublon serveur aussi)
    if (!ctaClicked) {{
      ctaClicked = true;
      trackEvent("cta_click");
    }}
    
    // Ne JAMAIS bloquer la redirection
    if (!e || !e.currentTarget) return;
    
    var link = e.currentTarget;
    var href = link.getAttribute("href");
    
    if (!href || href.startsWith("#") || !RDZ.session) return;
    
    try {{
      var url = new URL(href, window.location.origin);
      
      // Ajouter les params obligatoires
      url.searchParams.set("session", RDZ.session);
      url.searchParams.set("lp", RDZ.lp);
      url.searchParams.set("liaison", RDZ.liaison);
      
      // Transmettre utm_campaign (ne pas écraser si déjà présent)
      if (RDZ.utm.utm_campaign && !url.searchParams.has("utm_campaign")) {{
        url.searchParams.set("utm_campaign", RDZ.utm.utm_campaign);
      }}
      
      link.href = url.toString();
    }} catch(err) {{
      // Fail silently - ne pas bloquer la redirection
    }}
  }}
  
  // Exposer globalement pour usage manuel
  window.rdzCtaClick = handleCtaClick;

  // ══════════════════════════════════════════════════════════
  // 5. AUTO BINDING - Matching URL normalisé (http/https, slash, params)
  // ══════════════════════════════════════════════════════════
  function autoBindCTA() {{
    var formUrlNormalized = normalizeUrl(RDZ.formUrl);
    
    function bindLink(el) {{
      if (el._rdzBound) return;
      el._rdzBound = true;
      
      // data-rdz-cta = binding manuel explicite
      if (el.hasAttribute("data-rdz-cta")) {{
        el.addEventListener("click", handleCtaClick);
        return;
      }}
      
      // Auto-détection des liens vers le form (URL normalisée)
      var linkHref = el.getAttribute("href");
      if (linkHref && !linkHref.startsWith("#")) {{
        var linkNormalized = normalizeUrl(linkHref);
        // Match exact ou contenu
        if (linkNormalized === formUrlNormalized || 
            linkNormalized.indexOf(formUrlNormalized) !== -1 ||
            formUrlNormalized.indexOf(linkNormalized) !== -1) {{
          el.addEventListener("click", handleCtaClick);
        }}
      }}
    }}
    
    // Bind initial
    document.querySelectorAll("a[href], [data-rdz-cta]").forEach(bindLink);
    
    // MutationObserver pour les CTA ajoutés après chargement
    if (window.MutationObserver) {{
      var observer = new MutationObserver(function(mutations) {{
        mutations.forEach(function(m) {{
          m.addedNodes.forEach(function(node) {{
            if (node.nodeType === 1) {{
              if (node.tagName === "A" || (node.hasAttribute && node.hasAttribute("data-rdz-cta"))) {{
                bindLink(node);
              }}
              if (node.querySelectorAll) {{
                node.querySelectorAll("a[href], [data-rdz-cta]").forEach(bindLink);
              }}
            }}
          }});
        }});
      }});
      observer.observe(document.body, {{ childList: true, subtree: true }});
    }}
  }}

  // ══════════════════════════════════════════════════════════
  // INITIALISATION AU CHARGEMENT
  // ══════════════════════════════════════════════════════════
  document.addEventListener("DOMContentLoaded", async function() {{
    captureUTM();
    await initSession();
    // LP Visit part TOUJOURS (anti-doublon géré côté serveur)
    trackLPVisit();
    autoBindCTA();
  }});

  // Backup: si DOMContentLoaded déjà passé
  if (document.readyState !== "loading") {{
    captureUTM();
    initSession().then(function() {{
      trackLPVisit();
      autoBindCTA();
    }});
  }}

}})();
</script>'''

    # ══════════════════════════════════════════════════════════
    # SCRIPT FORM - Mode A - Récupération session + UTM
    # ══════════════════════════════════════════════════════════
    script_form = f'''<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<!-- RDZ TRACKING - FORMULAIRE {form_code}                                       -->
<!-- À coller AVANT </body>                                                       -->
<!-- Version: 2.1 - Récupération session LP + UTM, persistance rdz_lp/liaison    -->
<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<script>
(function() {{
  "use strict";
  
  // ══════════════════════════════════════════════════════════
  // CONFIGURATION
  // ══════════════════════════════════════════════════════════
  var RDZ = {{
    api: "{API_URL}/api/public",
    form: "{form_code}",
    formSelector: "{form_selector}",
    session: null,
    lp: "",
    liaison: "",
    utm: {{}},
    redirectUrl: "{redirect_url}",
    initialized: false,
    initFailed: false,
    // Code conversion GTM (exécuté après submit valide, avant redirection)
    conversionCode: {gtm_conversion_js}
  }};

  // ══════════════════════════════════════════════════════════
  // CAMPAIGN CAPTURE - URL puis sessionStorage
  // ══════════════════════════════════════════════════════════
  function captureUTM() {{
    var params = new URLSearchParams(window.location.search);
    var keys = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "gclid", "fbclid"];
    
    keys.forEach(function(key) {{
      var val = params.get(key);
      if (val) {{
        RDZ.utm[key] = val;
        try {{ sessionStorage.setItem("rdz_" + key, val); }} catch(e) {{}}
      }} else {{
        try {{ RDZ.utm[key] = sessionStorage.getItem("rdz_" + key) || ""; }} catch(e) {{ RDZ.utm[key] = ""; }}
      }}
    }});
  }}

  // ══════════════════════════════════════════════════════════
  // GTM CONVERSION - Exécuter le code de conversion
  // ══════════════════════════════════════════════════════════
  function executeConversion(leadId) {{
    if (!RDZ.conversionCode) return;
    
    try {{
      // Injecter les variables disponibles
      var conversionData = {{
        lead_id: leadId,
        lp_code: RDZ.lp,
        form_code: RDZ.form,
        liaison_code: RDZ.liaison,
        utm_campaign: RDZ.utm.utm_campaign || "",
        utm_source: RDZ.utm.utm_source || "",
        utm_medium: RDZ.utm.utm_medium || ""
      }};
      
      // Exécuter le code conversion (déjà une fonction)
      if (typeof RDZ.conversionCode === "function") {{
        RDZ.conversionCode(conversionData);
      }}
    }} catch(e) {{
      console.warn("RDZ Conversion error:", e);
    }}
  }}

  // ══════════════════════════════════════════════════════════
  // SESSION - Priorité: URL → sessionStorage → création
  // ══════════════════════════════════════════════════════════
  async function initSession() {{
    if (RDZ.session) return RDZ.session;
    if (RDZ.initFailed) return null;
    
    var params = new URLSearchParams(window.location.search);
    captureUTM();
    
    // 1. Priorité : paramètres URL (venant de la LP)
    var urlSession = params.get("session");
    var urlLp = params.get("lp");
    var urlLiaison = params.get("liaison");
    
    if (urlSession) {{
      RDZ.session = urlSession;
      RDZ.lp = urlLp || "";
      RDZ.liaison = urlLiaison || "";
      RDZ.initialized = true;
      
      // Stocker pour persistance
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
          liaison_code: urlLiaison || "",
          referrer: document.referrer,
          user_agent: navigator.userAgent,
          utm_source: RDZ.utm.utm_source || "",
          utm_medium: RDZ.utm.utm_medium || "",
          utm_campaign: RDZ.utm.utm_campaign || "",
          utm_content: RDZ.utm.utm_content || "",
          utm_term: RDZ.utm.utm_term || "",
          gclid: RDZ.utm.gclid || "",
          fbclid: RDZ.utm.fbclid || ""
        }})
      }});
      
      if (!res.ok) throw new Error("HTTP " + res.status);
      var data = await res.json();
      RDZ.session = data.session_id;
      RDZ.lp = urlLp || data.lp_code || "";
      RDZ.liaison = urlLiaison || "";
      RDZ.initialized = true;
      
      // IMPORTANT: Persister rdz_lp et rdz_liaison aussi
      try {{
        sessionStorage.setItem("rdz_session", RDZ.session);
        if (RDZ.lp) sessionStorage.setItem("rdz_lp", RDZ.lp);
        if (RDZ.liaison) sessionStorage.setItem("rdz_liaison", RDZ.liaison);
      }} catch(e) {{}}
      
      return RDZ.session;
    }} catch(e) {{
      RDZ.initFailed = true;
      return null;
    }}
  }}

  // ══════════════════════════════════════════════════════════
  // TRACKING avec sendBeacon
  // ══════════════════════════════════════════════════════════
  function trackEvent(eventType) {{
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
  // FORM START - Premier clic/focus
  // ══════════════════════════════════════════════════════════
  var formStarted = false;
  
  window.rdzFormStart = async function() {{
    if (formStarted) return;
    formStarted = true;
    await initSession();
    trackEvent("form_start");
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
  // SUBMIT LEAD
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
          utm_campaign: RDZ.utm.utm_campaign || "",
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
        // 1. DataLayer standard (toujours)
        if (window.dataLayer) {{
          window.dataLayer.push({{
            event: "form_submitted",
            lead_id: result.lead_id,
            lp_code: RDZ.lp,
            form_code: RDZ.form,
            liaison_code: RDZ.liaison,
            utm_campaign: RDZ.utm.utm_campaign || ""
          }});
        }}
        
        // 2. Code conversion GTM personnalisé (si défini)
        executeConversion(result.lead_id);
        
        // 3. Redirection (après conversion)
        if (RDZ.redirectUrl) {{
          // Petit délai pour laisser le temps aux pixels de s'exécuter
          setTimeout(function() {{
            window.location.href = RDZ.redirectUrl;
          }}, 100);
        }}
      }}
      
      return result;
    }} catch(e) {{
      return {{ success: false, error: e.message }};
    }}
  }};

  // ══════════════════════════════════════════════════════════
  // INITIALISATION
  // ══════════════════════════════════════════════════════════
  document.addEventListener("DOMContentLoaded", function() {{
    initSession();
    autoBindFormStart();
  }});

  if (document.readyState !== "loading") {{
    initSession();
    autoBindFormStart();
  }}

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
    gtm_conversion: str,
    redirect_url: str,
    form_selector: str,
    form_anchor: str,
    selected_product: str = None
) -> dict:
    """
    Génère le brief Mode B (Form intégré dans LP)
    
    Tracking complet avec UTM, sendBeacon et anti-doublon
    
    Post-submit:
    - Exécuter gtm_conversion (si défini)
    - Rediriger vers redirect_url
    """
    
    # Formater le code conversion GTM en fonction JavaScript
    if gtm_conversion and gtm_conversion.strip():
        gtm_conversion_js = f'''function(data) {{
      try {{
        // Variables disponibles: data.lead_id, data.lp_code, data.form_code, data.liaison_code, data.utm_campaign, data.utm_source, data.utm_medium
        {gtm_conversion}
      }} catch(e) {{ console.warn("RDZ GTM Conversion error:", e); }}
    }}'''
    else:
        gtm_conversion_js = "null"
    
    script_unique = f'''<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<!-- RDZ TRACKING - LP + FORMULAIRE INTÉGRÉS                                     -->
<!-- {lp_code} + {form_code}                                                      -->
<!-- À coller AVANT </body>                                                       -->
<!-- Version: 2.2 - Tracking complet + Conversion GTM + Redirection produit      -->
<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<script>
(function() {{
  "use strict";
  
  // ══════════════════════════════════════════════════════════
  // CONFIGURATION
  // ══════════════════════════════════════════════════════════
  var RDZ = {{
    api: "{API_URL}/api/public",
    lp: "{lp_code}",
    form: "{form_code}",
    liaison: "{liaison_code}",
    formSelector: "{form_selector}",
    formAnchor: "{form_anchor}",
    session: null,
    utm: {{}},
    redirectUrl: "{redirect_url}",
    initialized: false,
    initFailed: false,
    // Code conversion GTM (exécuté après submit valide, avant redirection)
    conversionCode: {gtm_conversion_js}
  }};

  // ══════════════════════════════════════════════════════════
  // 3. CAMPAIGN CAPTURE - URL puis sessionStorage
  // ══════════════════════════════════════════════════════════
  function captureUTM() {{
    var params = new URLSearchParams(window.location.search);
    var keys = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "gclid", "fbclid"];
    
    keys.forEach(function(key) {{
      var val = params.get(key);
      if (val) {{
        RDZ.utm[key] = val;
        try {{ sessionStorage.setItem("rdz_" + key, val); }} catch(e) {{}}
      }} else {{
        try {{ RDZ.utm[key] = sessionStorage.getItem("rdz_" + key) || ""; }} catch(e) {{ RDZ.utm[key] = ""; }}
      }}
    }});
  }}

  // ══════════════════════════════════════════════════════════
  // GTM CONVERSION - Exécuter le code de conversion
  // ══════════════════════════════════════════════════════════
  function executeConversion(leadId) {{
    if (!RDZ.conversionCode) return;
    
    try {{
      var conversionData = {{
        lead_id: leadId,
        lp_code: RDZ.lp,
        form_code: RDZ.form,
        liaison_code: RDZ.liaison,
        utm_campaign: RDZ.utm.utm_campaign || "",
        utm_source: RDZ.utm.utm_source || "",
        utm_medium: RDZ.utm.utm_medium || ""
      }};
      
      if (typeof RDZ.conversionCode === "function") {{
        RDZ.conversionCode(conversionData);
      }}
    }} catch(e) {{
      console.warn("RDZ Conversion error:", e);
    }}
  }}

  // ══════════════════════════════════════════════════════════
  // 1. SESSION INITIALIZATION - Anti-doublon côté serveur
  // ══════════════════════════════════════════════════════════
  async function initSession() {{
    if (RDZ.session) return RDZ.session;
    if (RDZ.initFailed) return null;
    
    // Vérifier session existante pour cette LP
    try {{
      var stored = sessionStorage.getItem("rdz_session");
      var storedLp = sessionStorage.getItem("rdz_lp");
      if (stored && storedLp === RDZ.lp) {{
        RDZ.session = stored;
        RDZ.initialized = true;
        return RDZ.session;
      }}
    }} catch(e) {{}}
    
    try {{
      captureUTM();
      
      var res = await fetch(RDZ.api + "/track/session", {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        body: JSON.stringify({{
          lp_code: RDZ.lp,
          form_code: RDZ.form,
          liaison_code: RDZ.liaison,
          referrer: document.referrer,
          user_agent: navigator.userAgent,
          utm_source: RDZ.utm.utm_source || "",
          utm_medium: RDZ.utm.utm_medium || "",
          utm_campaign: RDZ.utm.utm_campaign || "",
          utm_content: RDZ.utm.utm_content || "",
          utm_term: RDZ.utm.utm_term || "",
          gclid: RDZ.utm.gclid || "",
          fbclid: RDZ.utm.fbclid || ""
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
      }} catch(e) {{}}
      
      return RDZ.session;
    }} catch(e) {{
      RDZ.initFailed = true;
      return null;
    }}
  }}

  // ══════════════════════════════════════════════════════════
  // 2. LP VISIT TRACKING - TOUJOURS envoyé (anti-doublon serveur)
  // ══════════════════════════════════════════════════════════
  function trackLPVisit() {{
    if (!RDZ.session) return;
    
    var payload = JSON.stringify({{
      session_id: RDZ.session,
      lp_code: RDZ.lp,
      utm_source: RDZ.utm.utm_source || "",
      utm_medium: RDZ.utm.utm_medium || "",
      utm_campaign: RDZ.utm.utm_campaign || "",
      utm_content: RDZ.utm.utm_content || "",
      utm_term: RDZ.utm.utm_term || "",
      gclid: RDZ.utm.gclid || "",
      fbclid: RDZ.utm.fbclid || "",
      referrer: document.referrer,
      user_agent: navigator.userAgent
    }});
    
    if (navigator.sendBeacon) {{
      navigator.sendBeacon(RDZ.api + "/track/lp-visit", new Blob([payload], {{type: "application/json"}}));
    }} else {{
      fetch(RDZ.api + "/track/lp-visit", {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        body: payload,
        keepalive: true
      }}).catch(function() {{}});
    }}
  }}

  // ══════════════════════════════════════════════════════════
  // 7. RELIABILITY - sendBeacon pour tous les events
  // ══════════════════════════════════════════════════════════
  function trackEvent(eventType) {{
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
  // 4. CTA CLICK - vers anchor form
  // ══════════════════════════════════════════════════════════
  var ctaClicked = false;
  
  function handleCtaClick() {{
    if (ctaClicked) return;
    ctaClicked = true;
    trackEvent("cta_click");
  }}
  
  window.rdzCtaClick = handleCtaClick;

  // ══════════════════════════════════════════════════════════
  // 5. AUTO BINDING - CTA vers anchors form
  // ══════════════════════════════════════════════════════════
  function autoBindCTA() {{
    var anchors = [RDZ.formAnchor, "#form", "#formulaire", "#contact", "#devis"];
    
    function bindLink(el) {{
      if (el._rdzBound) return;
      el._rdzBound = true;
      
      if (el.hasAttribute("data-rdz-cta")) {{
        el.addEventListener("click", handleCtaClick);
        return;
      }}
      
      var href = el.getAttribute("href");
      if (href && anchors.indexOf(href) !== -1) {{
        el.addEventListener("click", handleCtaClick);
      }}
    }}
    
    document.querySelectorAll("a[href], [data-rdz-cta]").forEach(bindLink);
    
    // MutationObserver pour les CTA dynamiques
    if (window.MutationObserver) {{
      var observer = new MutationObserver(function(mutations) {{
        mutations.forEach(function(m) {{
          m.addedNodes.forEach(function(node) {{
            if (node.nodeType === 1) {{
              if (node.tagName === "A" || (node.hasAttribute && node.hasAttribute("data-rdz-cta"))) {{
                bindLink(node);
              }}
              if (node.querySelectorAll) {{
                node.querySelectorAll("a[href], [data-rdz-cta]").forEach(bindLink);
              }}
            }}
          }});
        }});
      }});
      observer.observe(document.body, {{ childList: true, subtree: true }});
    }}
  }}

  // ══════════════════════════════════════════════════════════
  // FORM START - Premier clic/focus
  // ══════════════════════════════════════════════════════════
  var formStarted = false;
  
  window.rdzFormStart = async function() {{
    if (formStarted) return;
    formStarted = true;
    await initSession();
    trackEvent("form_start");
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
  // SUBMIT LEAD
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
          utm_campaign: RDZ.utm.utm_campaign || "",
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
        // 1. DataLayer standard (toujours)
        if (window.dataLayer) {{
          window.dataLayer.push({{
            event: "form_submitted",
            lead_id: result.lead_id,
            lp_code: RDZ.lp,
            form_code: RDZ.form,
            liaison_code: RDZ.liaison,
            utm_campaign: RDZ.utm.utm_campaign || ""
          }});
        }}
        
        // 2. Code conversion GTM personnalisé (si défini)
        executeConversion(result.lead_id);
        
        // 3. Redirection (après conversion)
        if (RDZ.redirectUrl) {{
          // Petit délai pour laisser le temps aux pixels de s'exécuter
          setTimeout(function() {{
            window.location.href = RDZ.redirectUrl;
          }}, 100);
        }}
      }}
      
      return result;
    }} catch(e) {{
      return {{ success: false, error: e.message }};
    }}
  }};

  // ══════════════════════════════════════════════════════════
  // INITIALISATION
  // ══════════════════════════════════════════════════════════
  document.addEventListener("DOMContentLoaded", async function() {{
    captureUTM();
    await initSession();
    // LP Visit part TOUJOURS (anti-doublon géré côté serveur)
    trackLPVisit();
    autoBindCTA();
    autoBindFormStart();
  }});

  if (document.readyState !== "loading") {{
    captureUTM();
    initSession().then(function() {{
      trackLPVisit();
      autoBindCTA();
      autoBindFormStart();
    }});
  }}

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
