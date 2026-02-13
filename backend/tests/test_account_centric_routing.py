"""
Tests du routage Account-Centric
Vérifie la hiérarchie: account.crm_routing[product_type] > form.target_crm (override)

Scénarios testés:
1. Routing via config account (PV/PAC/ITE)
2. Override formulaire (form.target_crm prend le dessus)
3. Aucun config → no_crm
4. Account config partielle (certains produits seulement)
5. Form override sans clé API → fallback account
6. Logs de routage complets
"""

import pytest
import httpx
import uuid

API_URL = "https://account-lead-router.preview.emergentagent.com"
CREDENTIALS = {"email": "energiebleuciel@gmail.com", "password": "92Ruemarxdormoy"}


# ==================== SETUP (run once) ====================

_auth_cache = {}

async def get_auth():
    """Cache pour auth token et headers"""
    if "token" not in _auth_cache:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{API_URL}/api/auth/login", json=CREDENTIALS)
            assert r.status_code == 200, f"Login failed: {r.text}"
            _auth_cache["token"] = r.json()["token"]
            _auth_cache["headers"] = {
                "Authorization": f"Bearer {_auth_cache['token']}",
                "Content-Type": "application/json"
            }
            # Get CRM slugs
            r2 = await client.get(f"{API_URL}/api/crms", headers=_auth_cache["headers"])
            crms = r2.json().get("crms", [])
            _auth_cache["crm_slugs"] = {c["slug"]: c["id"] for c in crms}
    return _auth_cache["headers"], _auth_cache["crm_slugs"]


# ==================== HELPERS ====================

async def create_test_account(headers, crm_id, crm_routing=None, suffix=""):
    """Crée un compte de test avec routing optionnel"""
    async with httpx.AsyncClient(timeout=30) as client:
        payload = {
            "name": f"Test Account Routing {suffix} {uuid.uuid4().hex[:6]}",
            "crm_id": crm_id,
        }
        if crm_routing:
            payload["crm_routing"] = crm_routing
        r = await client.post(f"{API_URL}/api/accounts", json=payload, headers=headers)
        assert r.status_code == 200, f"Create account failed: {r.text}"
        return r.json()["account"]


async def create_test_lp_and_form(headers, account_id, product_type, target_crm="", crm_api_key=""):
    """Crée une LP+Form de test"""
    async with httpx.AsyncClient(timeout=30) as client:
        lp_payload = {
            "account_id": account_id,
            "name": f"Test LP {product_type} {uuid.uuid4().hex[:6]}",
            "url": "https://test-lp.example.com",
            "product_type": product_type,
            "crm_api_key": crm_api_key,
        }
        r = await client.post(f"{API_URL}/api/lps", json=lp_payload, headers=headers)
        assert r.status_code == 200, f"Create LP failed: {r.text}"
        data = r.json()
        lp = data["lp"]
        form = data["form"]

        # Si override CRM, mettre à jour le form
        if target_crm or crm_api_key:
            update = {}
            if target_crm:
                update["target_crm"] = target_crm
            if crm_api_key:
                update["crm_api_key"] = crm_api_key
            r2 = await client.put(f"{API_URL}/api/forms/{form['id']}", json=update, headers=headers)
            assert r2.status_code == 200, f"Update form failed: {r2.text}"
            form = r2.json()["form"]

        return lp, form


async def submit_test_lead(form_code, phone=None, dept="75"):
    """Soumet un lead de test"""
    async with httpx.AsyncClient(timeout=30) as client:
        # Créer une session
        session_r = await client.post(f"{API_URL}/api/public/track/session", json={
            "form_code": form_code,
        })
        session_id = session_r.json()["session_id"]

        # Soumettre le lead
        lead_payload = {
            "session_id": session_id,
            "form_code": form_code,
            "phone": phone or f"06{uuid.uuid4().hex[:8][:8].replace('a','1').replace('b','2').replace('c','3').replace('d','4').replace('e','5').replace('f','6')}",
            "nom": "TestRouting",
            "prenom": "Lead",
            "email": "test@routing.com",
            "departement": dept,
        }
        r = await client.post(f"{API_URL}/api/public/leads", json=lead_payload)
        assert r.status_code == 200, f"Submit lead failed: {r.text}"
        return r.json()


async def get_lead(headers, lead_id):
    """Récupère un lead par ID"""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{API_URL}/api/leads/{lead_id}", headers=headers)
        if r.status_code == 200:
            return r.json()
        return None


async def cleanup_account(headers, account_id):
    """Nettoie un compte de test et ses entités liées"""
    async with httpx.AsyncClient(timeout=30) as client:
        # Supprimer forms
        forms_r = await client.get(f"{API_URL}/api/forms?account_id={account_id}", headers=headers)
        for f in forms_r.json().get("forms", []):
            await client.delete(f"{API_URL}/api/forms/{f['id']}", headers=headers)
        # Supprimer LPs
        lps_r = await client.get(f"{API_URL}/api/lps?account_id={account_id}", headers=headers)
        for lp in lps_r.json().get("lps", []):
            await client.delete(f"{API_URL}/api/lps/{lp['id']}", headers=headers)
        # Supprimer account
        await client.delete(f"{API_URL}/api/accounts/{account_id}", headers=headers)


# ==================== TESTS ====================


@pytest.mark.asyncio
async def test_1_account_routing_pv():
    """
    Test 1: Routing via account.crm_routing pour PV
    Config: account.crm_routing.PV = zr7, form.target_crm = vide
    Attendu: routing_source = account_routing, target_crm = zr7
    """
    headers, crm_slugs = await get_auth()
    zr7_id = crm_slugs.get("zr7", list(crm_slugs.values())[0])

    account = await create_test_account(headers, zr7_id, crm_routing={
        "PV": {"target_crm": "zr7", "api_key": "test_key_pv_zr7", "delivery_mode": "api"}
    }, suffix="PV")

    try:
        _, form = await create_test_lp_and_form(headers, account["id"], "PV")
        result = await submit_test_lead(form["code"])

        assert result["success"] is True
        assert result["lead_id"]

        lead = await get_lead(headers, result["lead_id"])
        assert lead is not None
        assert lead.get("routing_source") == "account_routing"
        assert lead.get("account_id") == account["id"]
        assert lead.get("product_type") == "PV"
        print(f"  [PASS] PV routing via account: target={lead.get('target_crm')}, source={lead.get('routing_source')}")
    finally:
        await cleanup_account(headers, account["id"])


@pytest.mark.asyncio
async def test_2_account_routing_pac(headers, crm_slugs):
    """
    Test 2: Routing via account.crm_routing pour PAC
    Config: account.crm_routing.PAC = mdl
    """
    crm_id = list(crm_slugs.values())[0]

    account = await create_test_account(headers, crm_id, crm_routing={
        "PAC": {"target_crm": "mdl", "api_key": "test_key_pac_mdl", "delivery_mode": "api"}
    }, suffix="PAC")

    try:
        _, form = await create_test_lp_and_form(headers, account["id"], "PAC")
        result = await submit_test_lead(form["code"])

        lead = await get_lead(headers, result["lead_id"])
        assert lead.get("routing_source") == "account_routing"
        assert lead.get("product_type") == "PAC"
        print(f"  [PASS] PAC routing via account: target={lead.get('target_crm')}, source={lead.get('routing_source')}")
    finally:
        await cleanup_account(headers, account["id"])


@pytest.mark.asyncio
async def test_3_account_routing_ite(headers, crm_slugs):
    """
    Test 3: Routing via account.crm_routing pour ITE
    """
    crm_id = list(crm_slugs.values())[0]

    account = await create_test_account(headers, crm_id, crm_routing={
        "ITE": {"target_crm": "zr7", "api_key": "test_key_ite_zr7", "delivery_mode": "api"}
    }, suffix="ITE")

    try:
        _, form = await create_test_lp_and_form(headers, account["id"], "ITE")
        result = await submit_test_lead(form["code"])

        lead = await get_lead(headers, result["lead_id"])
        assert lead.get("routing_source") == "account_routing"
        assert lead.get("product_type") == "ITE"
        print(f"  [PASS] ITE routing via account: target={lead.get('target_crm')}, source={lead.get('routing_source')}")
    finally:
        await cleanup_account(headers, account["id"])


@pytest.mark.asyncio
async def test_4_form_override(headers, crm_slugs):
    """
    Test 4: Override formulaire prend le dessus sur account
    Config: account.crm_routing.PV = zr7, form.target_crm = mdl
    Attendu: routing_source = form_override, target_crm = mdl
    """
    crm_id = list(crm_slugs.values())[0]

    account = await create_test_account(headers, crm_id, crm_routing={
        "PV": {"target_crm": "zr7", "api_key": "test_key_account", "delivery_mode": "api"}
    }, suffix="Override")

    try:
        _, form = await create_test_lp_and_form(
            headers, account["id"], "PV",
            target_crm="mdl", crm_api_key="test_key_form_override"
        )
        result = await submit_test_lead(form["code"])

        lead = await get_lead(headers, result["lead_id"])
        assert lead.get("routing_source") == "form_override"
        print(f"  [PASS] Form override: target={lead.get('target_crm')}, source={lead.get('routing_source')}")
    finally:
        await cleanup_account(headers, account["id"])


@pytest.mark.asyncio
async def test_5_no_config_no_crm(headers, crm_slugs):
    """
    Test 5: Ni account ni form n'ont de config CRM
    Attendu: status = no_crm, routing_source = none
    """
    crm_id = list(crm_slugs.values())[0]

    account = await create_test_account(headers, crm_id, suffix="NoCRM")

    try:
        _, form = await create_test_lp_and_form(headers, account["id"], "PV")
        result = await submit_test_lead(form["code"])

        lead = await get_lead(headers, result["lead_id"])
        assert lead.get("routing_source") == "none"
        assert lead.get("api_status") in ["no_crm", "no_api_key"]
        print(f"  [PASS] No config: status={lead.get('api_status')}, source={lead.get('routing_source')}")
    finally:
        await cleanup_account(headers, account["id"])


@pytest.mark.asyncio
async def test_6_partial_account_config(headers, crm_slugs):
    """
    Test 6: Account a config pour PV mais pas PAC
    Attendu: PV → account_routing, PAC → no_crm
    """
    crm_id = list(crm_slugs.values())[0]

    account = await create_test_account(headers, crm_id, crm_routing={
        "PV": {"target_crm": "zr7", "api_key": "test_key_pv_only", "delivery_mode": "api"}
    }, suffix="Partial")

    try:
        # PV form - devrait router via account
        _, form_pv = await create_test_lp_and_form(headers, account["id"], "PV")
        result_pv = await submit_test_lead(form_pv["code"])
        lead_pv = await get_lead(headers, result_pv["lead_id"])
        assert lead_pv.get("routing_source") == "account_routing"

        # PAC form - pas de config → no_crm
        _, form_pac = await create_test_lp_and_form(headers, account["id"], "PAC")
        result_pac = await submit_test_lead(form_pac["code"])
        lead_pac = await get_lead(headers, result_pac["lead_id"])
        assert lead_pac.get("routing_source") == "none"
        assert lead_pac.get("api_status") in ["no_crm", "no_api_key"]

        print(f"  [PASS] Partial config: PV={lead_pv.get('routing_source')}, PAC={lead_pac.get('routing_source')}")
    finally:
        await cleanup_account(headers, account["id"])


@pytest.mark.asyncio
async def test_7_form_override_partial(headers, crm_slugs):
    """
    Test 7: Form a target_crm mais PAS de crm_api_key → fallback vers account
    Attendu: routing_source = account_routing (car override incomplet)
    """
    crm_id = list(crm_slugs.values())[0]

    account = await create_test_account(headers, crm_id, crm_routing={
        "PV": {"target_crm": "zr7", "api_key": "test_key_account_fb", "delivery_mode": "api"}
    }, suffix="PartialOverride")

    try:
        # Form avec target_crm mais sans clé API
        _, form = await create_test_lp_and_form(
            headers, account["id"], "PV",
            target_crm="mdl"  # Pas de crm_api_key
        )
        result = await submit_test_lead(form["code"])

        lead = await get_lead(headers, result["lead_id"])
        # Override incomplet (pas de clé) → fallback sur account
        assert lead.get("routing_source") == "account_routing"
        print(f"  [PASS] Partial override fallback: source={lead.get('routing_source')}")
    finally:
        await cleanup_account(headers, account["id"])


@pytest.mark.asyncio
async def test_8_update_account_routing(headers, crm_slugs):
    """
    Test 8: Mise à jour du crm_routing via PUT /accounts/:id
    """
    crm_id = list(crm_slugs.values())[0]

    account = await create_test_account(headers, crm_id, suffix="UpdateRouting")

    try:
        # Vérifier qu'il n'y a pas de routing
        assert account.get("crm_routing") == {} or account.get("crm_routing") is None

        # Mettre à jour le routing
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.put(
                f"{API_URL}/api/accounts/{account['id']}",
                json={
                    "crm_routing": {
                        "PV": {"target_crm": "zr7", "api_key": "new_key_pv", "delivery_mode": "api"},
                        "PAC": {"target_crm": "mdl", "api_key": "new_key_pac", "delivery_mode": "api"},
                        "ITE": {"target_crm": "zr7", "api_key": "new_key_ite", "delivery_mode": "api"},
                    }
                },
                headers=headers,
            )
            assert r.status_code == 200, f"Update account failed: {r.text}"
            updated = r.json()["account"]

        assert "crm_routing" in updated
        assert updated["crm_routing"]["PV"]["target_crm"] == "zr7"
        assert updated["crm_routing"]["PAC"]["target_crm"] == "mdl"
        assert updated["crm_routing"]["ITE"]["target_crm"] == "zr7"
        print(f"  [PASS] Account routing updated: {list(updated['crm_routing'].keys())}")
    finally:
        await cleanup_account(headers, account["id"])


@pytest.mark.asyncio
async def test_9_multi_product_account(headers, crm_slugs):
    """
    Test 9: Un compte avec config complète PV/PAC/ITE vers différents CRM
    Vérifie que chaque produit route vers le bon CRM
    """
    crm_id = list(crm_slugs.values())[0]

    account = await create_test_account(headers, crm_id, crm_routing={
        "PV": {"target_crm": "zr7", "api_key": "key_pv", "delivery_mode": "api"},
        "PAC": {"target_crm": "mdl", "api_key": "key_pac", "delivery_mode": "api"},
        "ITE": {"target_crm": "zr7", "api_key": "key_ite", "delivery_mode": "api"},
    }, suffix="MultiProduct")

    try:
        results = {}
        for pt in ["PV", "PAC", "ITE"]:
            _, form = await create_test_lp_and_form(headers, account["id"], pt)
            result = await submit_test_lead(form["code"], dept=f"{30 + ['PV','PAC','ITE'].index(pt)}")
            lead = await get_lead(headers, result["lead_id"])
            results[pt] = {
                "routing_source": lead.get("routing_source"),
                "product_type": lead.get("product_type"),
            }
            assert lead.get("routing_source") == "account_routing"
            assert lead.get("product_type") == pt

        print(f"  [PASS] Multi-product routing: {results}")
    finally:
        await cleanup_account(headers, account["id"])


@pytest.mark.asyncio
async def test_10_lead_has_routing_source_field(headers, crm_slugs):
    """
    Test 10: Vérifier que le champ routing_source est bien présent dans le lead
    """
    crm_id = list(crm_slugs.values())[0]

    account = await create_test_account(headers, crm_id, crm_routing={
        "PV": {"target_crm": "zr7", "api_key": "test_field_check", "delivery_mode": "api"}
    }, suffix="FieldCheck")

    try:
        _, form = await create_test_lp_and_form(headers, account["id"], "PV")
        result = await submit_test_lead(form["code"])

        lead = await get_lead(headers, result["lead_id"])
        # Vérifier tous les champs de routage
        assert "routing_source" in lead, "routing_source manquant dans le lead"
        assert "routing_reason" in lead, "routing_reason manquant dans le lead"
        assert "target_crm" in lead, "target_crm manquant dans le lead"
        assert "account_id" in lead, "account_id manquant dans le lead"
        assert "product_type" in lead, "product_type manquant dans le lead"
        print(f"  [PASS] Tous les champs de routage sont présents")
    finally:
        await cleanup_account(headers, account["id"])
