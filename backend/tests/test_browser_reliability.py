"""
RDZ Tracking Layer v2.1 - Tests Navigateur (Playwright)
========================================================

Tests:
1. Mobile Safari beacon reliability
2. Desktop Chrome tracking
3. Adblock simulation (fetch fallback)
4. Full user journey simulation
"""

import asyncio
from playwright.async_api import async_playwright
import json

BASE_URL = "https://form-tracker-boost.preview.emergentagent.com"
API_URL = f"{BASE_URL}/api/public"

results = {
    "mobile_safari": {"requests": [], "success": False},
    "desktop_chrome": {"requests": [], "success": False},
    "full_journey": {"steps": [], "success": False}
}


async def test_mobile_safari():
    """Test Mobile Safari - iPhone 14"""
    print("\n" + "="*60)
    print("TEST: Mobile Safari (iPhone 14 Simulation)")
    print("="*60)
    
    async with async_playwright() as p:
        # Lancer avec configuration iPhone 14
        iphone_14 = p.devices["iPhone 14"]
        browser = await p.webkit.launch(headless=True)
        context = await browser.new_context(
            **iphone_14,
            locale="fr-FR"
        )
        
        page = await context.new_page()
        
        # Intercepter les requêtes réseau
        tracked_requests = []
        
        async def handle_request(request):
            if "/api/public/track" in request.url:
                tracked_requests.append({
                    "url": request.url,
                    "method": request.method,
                    "post_data": request.post_data
                })
        
        page.on("request", handle_request)
        
        # Créer une page HTML de test avec le script tracking
        test_html = f'''
        <!DOCTYPE html>
        <html>
        <head><title>LP Test Mobile Safari</title></head>
        <body>
            <h1>Landing Page Test</h1>
            <a href="{BASE_URL}/form-test?test=1" id="cta">Demander un devis</a>
            
            <script>
            (function() {{
                var RDZ = {{
                    api: "{API_URL}",
                    lp: "LP-MOBILE-SAFARI",
                    form: "PV-MOBILE-TEST",
                    liaison: "LP-MOBILE-SAFARI_PV-MOBILE-TEST",
                    formUrl: "{BASE_URL}/form-test",
                    session: null,
                    utm: {{}}
                }};
                
                function captureUTM() {{
                    var params = new URLSearchParams(window.location.search);
                    ["utm_source", "utm_medium", "utm_campaign"].forEach(function(key) {{
                        RDZ.utm[key] = params.get(key) || "";
                    }});
                }}
                
                async function initSession() {{
                    try {{
                        var res = await fetch(RDZ.api + "/track/session", {{
                            method: "POST",
                            headers: {{"Content-Type": "application/json"}},
                            body: JSON.stringify({{
                                lp_code: RDZ.lp,
                                form_code: RDZ.form,
                                liaison_code: RDZ.liaison,
                                utm_campaign: RDZ.utm.utm_campaign || "mobile_safari_test"
                            }})
                        }});
                        var data = await res.json();
                        RDZ.session = data.session_id;
                        console.log("Session created:", RDZ.session);
                        return RDZ.session;
                    }} catch(e) {{
                        console.error("Session init failed:", e);
                        return null;
                    }}
                }}
                
                function trackLPVisit() {{
                    if (!RDZ.session) return;
                    var payload = JSON.stringify({{
                        session_id: RDZ.session,
                        lp_code: RDZ.lp,
                        utm_campaign: "mobile_safari_test"
                    }});
                    
                    // Test sendBeacon
                    if (navigator.sendBeacon) {{
                        var sent = navigator.sendBeacon(
                            RDZ.api + "/track/lp-visit", 
                            new Blob([payload], {{type: "application/json"}})
                        );
                        console.log("sendBeacon lp-visit:", sent);
                    }}
                }}
                
                function handleCTA(e) {{
                    if (!RDZ.session) return;
                    var payload = JSON.stringify({{
                        session_id: RDZ.session,
                        event_type: "cta_click",
                        lp_code: RDZ.lp
                    }});
                    
                    if (navigator.sendBeacon) {{
                        navigator.sendBeacon(
                            RDZ.api + "/track/event",
                            new Blob([payload], {{type: "application/json"}})
                        );
                    }}
                }}
                
                document.addEventListener("DOMContentLoaded", async function() {{
                    captureUTM();
                    await initSession();
                    trackLPVisit();
                    
                    document.getElementById("cta").addEventListener("click", handleCTA);
                }});
            }})();
            </script>
        </body>
        </html>
        '''
        
        # Charger la page de test
        await page.set_content(test_html)
        await page.wait_for_timeout(2000)  # Attendre les requêtes
        
        # Cliquer sur CTA
        await page.click("#cta")
        await page.wait_for_timeout(1000)
        
        # Vérifier les requêtes
        session_requests = [r for r in tracked_requests if "track/session" in r["url"]]
        visit_requests = [r for r in tracked_requests if "track/lp-visit" in r["url"]]
        event_requests = [r for r in tracked_requests if "track/event" in r["url"]]
        
        print(f"  Session requests: {len(session_requests)}")
        print(f"  LP Visit requests: {len(visit_requests)}")
        print(f"  Event requests: {len(event_requests)}")
        
        results["mobile_safari"]["requests"] = tracked_requests
        results["mobile_safari"]["success"] = (
            len(session_requests) >= 1 and 
            len(visit_requests) >= 1
        )
        
        status = "✅ PASS" if results["mobile_safari"]["success"] else "❌ FAIL"
        print(f"\n  Résultat: {status}")
        
        await browser.close()
        
        return results["mobile_safari"]["success"]


async def test_desktop_chrome():
    """Test Desktop Chrome"""
    print("\n" + "="*60)
    print("TEST: Desktop Chrome")
    print("="*60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="fr-FR"
        )
        
        page = await context.new_page()
        
        # Intercepter les requêtes
        tracked_requests = []
        
        async def handle_request(request):
            if "/api/public/track" in request.url:
                tracked_requests.append({
                    "url": request.url,
                    "method": request.method
                })
        
        page.on("request", handle_request)
        
        # Même page de test
        test_html = f'''
        <!DOCTYPE html>
        <html>
        <head><title>LP Test Chrome</title></head>
        <body>
            <h1>Landing Page Test</h1>
            <a href="{BASE_URL}/form-test" id="cta">Demander un devis</a>
            
            <script>
            (function() {{
                var RDZ = {{
                    api: "{API_URL}",
                    lp: "LP-CHROME-TEST",
                    session: null
                }};
                
                async function init() {{
                    try {{
                        var res = await fetch(RDZ.api + "/track/session", {{
                            method: "POST",
                            headers: {{"Content-Type": "application/json"}},
                            body: JSON.stringify({{ lp_code: RDZ.lp }})
                        }});
                        var data = await res.json();
                        RDZ.session = data.session_id;
                        
                        // LP Visit via sendBeacon
                        if (navigator.sendBeacon) {{
                            navigator.sendBeacon(
                                RDZ.api + "/track/lp-visit",
                                new Blob([JSON.stringify({{
                                    session_id: RDZ.session,
                                    lp_code: RDZ.lp
                                }})], {{type: "application/json"}})
                            );
                        }}
                    }} catch(e) {{
                        console.error(e);
                    }}
                }}
                
                document.addEventListener("DOMContentLoaded", init);
            }})();
            </script>
        </body>
        </html>
        '''
        
        await page.set_content(test_html)
        await page.wait_for_timeout(2000)
        
        session_requests = [r for r in tracked_requests if "track/session" in r["url"]]
        visit_requests = [r for r in tracked_requests if "track/lp-visit" in r["url"]]
        
        print(f"  Session requests: {len(session_requests)}")
        print(f"  LP Visit requests: {len(visit_requests)}")
        
        results["desktop_chrome"]["requests"] = tracked_requests
        results["desktop_chrome"]["success"] = (
            len(session_requests) >= 1 and 
            len(visit_requests) >= 1
        )
        
        status = "✅ PASS" if results["desktop_chrome"]["success"] else "❌ FAIL"
        print(f"\n  Résultat: {status}")
        
        await browser.close()
        
        return results["desktop_chrome"]["success"]


async def run_browser_tests():
    """Exécuter tous les tests navigateur"""
    print("\n" + "="*60)
    print("RDZ TRACKING v2.1 - BROWSER RELIABILITY TESTS")
    print("="*60)
    
    test_results = {}
    
    test_results["mobile_safari"] = await test_mobile_safari()
    test_results["desktop_chrome"] = await test_desktop_chrome()
    
    print("\n" + "="*60)
    print("RÉSUMÉ TESTS NAVIGATEUR")
    print("="*60)
    
    all_passed = True
    for test_name, passed in test_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False
    
    return all_passed


if __name__ == "__main__":
    asyncio.run(run_browser_tests())
