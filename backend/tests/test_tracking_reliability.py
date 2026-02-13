"""
RDZ Tracking Layer v2.1 - Tests de Fiabilité Production
========================================================

Tests:
1. 10 LP visits → 10 reçues backend
2. Multi-tab → session unique
3. CTA spam clicks → événement unique
4. Full funnel (LP → CTA → Form → Submit) × 100
5. Fallback fetch (simulation adblock)
"""

import asyncio
import aiohttp
import json
import uuid
import os
from datetime import datetime

API_URL = os.environ.get("API_URL", "https://delivery-pipeline-1.preview.emergentagent.com")
BASE_URL = f"{API_URL}/api/public"

# Compteurs globaux
results = {
    "test_1_lp_visits": {"sent": 0, "received": 0, "duplicates": 0},
    "test_2_multi_tab": {"sessions_created": 0, "unique_sessions": set()},
    "test_3_cta_spam": {"clicks_sent": 0, "events_recorded": 0, "duplicates": 0},
    "test_4_funnel": {"started": 0, "completed": 0, "leads_created": 0, "errors": []},
    "test_5_fallback": {"beacon_simulated": 0, "fetch_fallback": 0, "success": 0}
}


async def test_1_lp_visits(session):
    """Test 1: 10 LP visits avec 10 sessions différentes → 10 events reçus"""
    print("\n" + "="*60)
    print("TEST 1: 10 LP Visits → 10 Events Backend")
    print("="*60)
    
    for i in range(10):
        # Créer une session unique
        session_data = {
            "lp_code": f"LP-TEST-{i+1:03d}",
            "form_code": "PV-TEST-001",
            "utm_campaign": f"test_visit_{i+1}"
        }
        
        async with session.post(f"{BASE_URL}/track/session", json=session_data) as resp:
            data = await resp.json()
            session_id = data.get("session_id")
            
            if session_id:
                results["test_1_lp_visits"]["sent"] += 1
                
                # Envoyer lp-visit
                visit_data = {
                    "session_id": session_id,
                    "lp_code": f"LP-TEST-{i+1:03d}",
                    "utm_campaign": f"test_visit_{i+1}"
                }
                
                # Simuler sendBeacon (text/plain)
                async with session.post(
                    f"{BASE_URL}/track/lp-visit",
                    data=json.dumps(visit_data),
                    headers={"Content-Type": "text/plain;charset=UTF-8"}
                ) as visit_resp:
                    visit_result = await visit_resp.json()
                    
                    if visit_result.get("success"):
                        if visit_result.get("duplicate"):
                            results["test_1_lp_visits"]["duplicates"] += 1
                        else:
                            results["test_1_lp_visits"]["received"] += 1
                        print(f"  ✓ Visit {i+1}: session={session_id[:8]}... event={visit_result.get('event_id', 'N/A')[:8]}...")
    
    sent = results["test_1_lp_visits"]["sent"]
    received = results["test_1_lp_visits"]["received"]
    print(f"\n  Résultat: {received}/{sent} events reçus")
    return received == sent


async def test_2_multi_tab(session):
    """Test 2: Simulation multi-tab avec même visitor_id → session unique réutilisée"""
    print("\n" + "="*60)
    print("TEST 2: Multi-Tab → Session Unique")
    print("="*60)
    
    # Simuler un visitor_id fixe (comme un cookie)
    visitor_id = str(uuid.uuid4())
    lp_code = "LP-MULTITAB-TEST"
    
    # Simuler 5 "onglets" ouvrant la même LP rapidement
    for tab in range(5):
        session_data = {
            "lp_code": lp_code,
            "form_code": "PV-MULTITAB",
            "utm_campaign": "multitab_test"
        }
        
        # Le backend vérifie visitor_id via cookie, simulons avec header custom pour test
        async with session.post(
            f"{BASE_URL}/track/session",
            json=session_data,
            cookies={"_rdz_vid": visitor_id}
        ) as resp:
            data = await resp.json()
            session_id = data.get("session_id")
            reused = data.get("reused", False)
            
            results["test_2_multi_tab"]["sessions_created"] += 1
            results["test_2_multi_tab"]["unique_sessions"].add(session_id)
            
            status = "REUSED" if reused else "NEW"
            print(f"  Tab {tab+1}: session={session_id[:8]}... ({status})")
    
    unique = len(results["test_2_multi_tab"]["unique_sessions"])
    total = results["test_2_multi_tab"]["sessions_created"]
    print(f"\n  Résultat: {unique} session(s) unique(s) pour {total} requêtes")
    
    # Le backend devrait réutiliser la session dans les 30 minutes
    return unique == 1


async def test_3_cta_spam(session):
    """Test 3: Spam clicks CTA → 1 seul événement enregistré"""
    print("\n" + "="*60)
    print("TEST 3: CTA Spam Clicks → Single Event")
    print("="*60)
    
    # Créer une session
    session_data = {
        "lp_code": "LP-SPAM-TEST",
        "form_code": "PV-SPAM-TEST"
    }
    
    async with session.post(f"{BASE_URL}/track/session", json=session_data) as resp:
        data = await resp.json()
        session_id = data.get("session_id")
    
    print(f"  Session créée: {session_id[:8]}...")
    
    # Simuler 20 clicks rapides (spam)
    for click in range(20):
        event_data = {
            "session_id": session_id,
            "event_type": "cta_click",
            "lp_code": "LP-SPAM-TEST"
        }
        
        async with session.post(
            f"{BASE_URL}/track/event",
            data=json.dumps(event_data),
            headers={"Content-Type": "text/plain"}
        ) as resp:
            result = await resp.json()
            results["test_3_cta_spam"]["clicks_sent"] += 1
            
            if result.get("success"):
                if result.get("duplicate"):
                    results["test_3_cta_spam"]["duplicates"] += 1
                else:
                    results["test_3_cta_spam"]["events_recorded"] += 1
    
    sent = results["test_3_cta_spam"]["clicks_sent"]
    recorded = results["test_3_cta_spam"]["events_recorded"]
    duplicates = results["test_3_cta_spam"]["duplicates"]
    
    print(f"  Clicks envoyés: {sent}")
    print(f"  Events enregistrés: {recorded}")
    print(f"  Duplicates rejetés: {duplicates}")
    print(f"\n  Résultat: {recorded} event(s) pour {sent} clicks")
    
    return recorded == 1 and duplicates == sent - 1


async def test_4_full_funnel(session, iterations=100):
    """Test 4: Full funnel LP → CTA → Form → Submit × 100"""
    print("\n" + "="*60)
    print(f"TEST 4: Full Funnel × {iterations} Iterations")
    print("="*60)
    
    for i in range(iterations):
        results["test_4_funnel"]["started"] += 1
        
        try:
            # 1. Créer session (LP)
            session_data = {
                "lp_code": f"LP-FUNNEL-{i+1:03d}",
                "form_code": f"PV-FUNNEL-{i+1:03d}",
                "liaison_code": f"LP-FUNNEL-{i+1:03d}_PV-FUNNEL-{i+1:03d}",
                "utm_campaign": f"funnel_test_{i+1}",
                "utm_source": "test",
                "utm_medium": "reliability"
            }
            
            async with session.post(f"{BASE_URL}/track/session", json=session_data) as resp:
                data = await resp.json()
                session_id = data.get("session_id")
                if not session_id:
                    results["test_4_funnel"]["errors"].append(f"Iteration {i+1}: No session_id")
                    continue
            
            # 2. LP Visit
            visit_data = {
                "session_id": session_id,
                "lp_code": f"LP-FUNNEL-{i+1:03d}",
                "utm_campaign": f"funnel_test_{i+1}"
            }
            async with session.post(
                f"{BASE_URL}/track/lp-visit",
                data=json.dumps(visit_data),
                headers={"Content-Type": "text/plain"}
            ) as resp:
                lp_result = await resp.json()
                if not lp_result.get("success"):
                    results["test_4_funnel"]["errors"].append(f"Iteration {i+1}: LP visit failed")
                    continue
            
            # 3. CTA Click
            cta_data = {
                "session_id": session_id,
                "event_type": "cta_click",
                "lp_code": f"LP-FUNNEL-{i+1:03d}"
            }
            async with session.post(
                f"{BASE_URL}/track/event",
                data=json.dumps(cta_data),
                headers={"Content-Type": "text/plain"}
            ) as resp:
                cta_result = await resp.json()
                if not cta_result.get("success"):
                    results["test_4_funnel"]["errors"].append(f"Iteration {i+1}: CTA click failed")
                    continue
            
            # 4. Form Start
            form_start_data = {
                "session_id": session_id,
                "event_type": "form_start",
                "form_code": f"PV-FUNNEL-{i+1:03d}"
            }
            async with session.post(
                f"{BASE_URL}/track/event",
                data=json.dumps(form_start_data),
                headers={"Content-Type": "text/plain"}
            ) as resp:
                form_result = await resp.json()
                if not form_result.get("success"):
                    results["test_4_funnel"]["errors"].append(f"Iteration {i+1}: Form start failed")
                    continue
            
            # 5. Submit Lead
            lead_data = {
                "session_id": session_id,
                "form_code": f"PV-FUNNEL-{i+1:03d}",
                "lp_code": f"LP-FUNNEL-{i+1:03d}",
                "liaison_code": f"LP-FUNNEL-{i+1:03d}_PV-FUNNEL-{i+1:03d}",
                "utm_campaign": f"funnel_test_{i+1}",
                "phone": f"06{i:08d}",  # Numéros uniques
                "nom": f"TestFunnel{i+1}",
                "prenom": "Reliability",
                "departement": "75",
                "email": f"test{i+1}@reliability.test"
            }
            
            async with session.post(f"{BASE_URL}/leads", json=lead_data) as resp:
                lead_result = await resp.json()
                if lead_result.get("success"):
                    results["test_4_funnel"]["leads_created"] += 1
                    results["test_4_funnel"]["completed"] += 1
                else:
                    results["test_4_funnel"]["errors"].append(f"Iteration {i+1}: Lead failed - {lead_result}")
        
        except Exception as e:
            results["test_4_funnel"]["errors"].append(f"Iteration {i+1}: Exception - {str(e)}")
        
        # Progress
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i+1}/{iterations} ({results['test_4_funnel']['completed']} completed)")
    
    started = results["test_4_funnel"]["started"]
    completed = results["test_4_funnel"]["completed"]
    leads = results["test_4_funnel"]["leads_created"]
    errors = len(results["test_4_funnel"]["errors"])
    
    print(f"\n  Started: {started}")
    print(f"  Completed: {completed}")
    print(f"  Leads created: {leads}")
    print(f"  Errors: {errors}")
    
    if errors > 0:
        print(f"\n  First 5 errors:")
        for err in results["test_4_funnel"]["errors"][:5]:
            print(f"    - {err}")
    
    success_rate = (completed / started) * 100 if started > 0 else 0
    print(f"\n  Success Rate: {success_rate:.1f}%")
    
    return completed == started


async def test_5_fallback_fetch(session):
    """Test 5: Fallback fetch quand sendBeacon échoue (simulation adblock)"""
    print("\n" + "="*60)
    print("TEST 5: Fallback Fetch (Adblock Simulation)")
    print("="*60)
    
    # Créer une session
    session_data = {
        "lp_code": "LP-FALLBACK-TEST",
        "form_code": "PV-FALLBACK-TEST"
    }
    
    async with session.post(f"{BASE_URL}/track/session", json=session_data) as resp:
        data = await resp.json()
        session_id = data.get("session_id")
    
    print(f"  Session créée: {session_id[:8]}...")
    
    # Test avec différents Content-Types (simulation de ce que les navigateurs peuvent envoyer)
    content_types = [
        ("text/plain;charset=UTF-8", "sendBeacon default"),
        ("text/plain", "sendBeacon variant"),
        ("application/json", "fetch standard"),
    ]
    
    for ct, description in content_types:
        # Créer une nouvelle session pour chaque test (éviter les duplicates)
        session_data_ct = {
            "lp_code": f"LP-FALLBACK-{ct.replace('/', '-').replace(';', '')}",
            "form_code": "PV-FALLBACK-TEST"
        }
        async with session.post(f"{BASE_URL}/track/session", json=session_data_ct) as resp:
            data = await resp.json()
            test_session_id = data.get("session_id")
        
        event_data = {
            "session_id": test_session_id,
            "event_type": "cta_click",
            "lp_code": f"LP-FALLBACK-{ct.replace('/', '-').replace(';', '')}"
        }
        
        headers = {"Content-Type": ct}
        
        try:
            async with session.post(
                f"{BASE_URL}/track/event",
                data=json.dumps(event_data),
                headers=headers
            ) as resp:
                text = await resp.text()
                try:
                    result = json.loads(text)
                except:
                    result = {"success": False, "raw": text}
                
                results["test_5_fallback"]["fetch_fallback"] += 1
                
                if result.get("success"):
                    results["test_5_fallback"]["success"] += 1
                    status = "✓"
                else:
                    status = "✗"
                
                print(f"  {description} ({ct}): {status}")
        except Exception as e:
            print(f"  {description} ({ct}): ✗ Exception: {e}")
            results["test_5_fallback"]["fetch_fallback"] += 1
    
    success = results["test_5_fallback"]["success"]
    total = results["test_5_fallback"]["fetch_fallback"]
    print(f"\n  Résultat: {success}/{total} réussis")
    
    return success == total


async def run_all_tests():
    """Exécuter tous les tests"""
    print("\n" + "="*60)
    print("RDZ TRACKING LAYER v2.1 - RELIABILITY TESTS")
    print(f"API: {API_URL}")
    print(f"Started: {datetime.now().isoformat()}")
    print("="*60)
    
    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        test_results = {}
        
        # Test 1: LP Visits
        test_results["test_1"] = await test_1_lp_visits(session)
        
        # Test 2: Multi-tab
        test_results["test_2"] = await test_2_multi_tab(session)
        
        # Test 3: CTA Spam
        test_results["test_3"] = await test_3_cta_spam(session)
        
        # Test 4: Full Funnel (100 iterations)
        test_results["test_4"] = await test_4_full_funnel(session, iterations=100)
        
        # Test 5: Fallback
        test_results["test_5"] = await test_5_fallback_fetch(session)
        
        # Résumé final
        print("\n" + "="*60)
        print("RÉSUMÉ FINAL")
        print("="*60)
        
        all_passed = True
        for test_name, passed in test_results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {test_name}: {status}")
            if not passed:
                all_passed = False
        
        print("\n" + "="*60)
        if all_passed:
            print("🎉 TOUS LES TESTS PASSÉS - v2.1 PRODUCTION-READY")
        else:
            print("⚠️  CERTAINS TESTS ONT ÉCHOUÉ - INVESTIGATION REQUISE")
        print("="*60)
        
        return test_results


if __name__ == "__main__":
    asyncio.run(run_all_tests())
