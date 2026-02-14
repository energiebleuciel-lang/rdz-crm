"""
RDZ CRM — Phone Normalization Tests
Tests: normalize_phone_fr + integration with public lead submission.
Run: cd /app/backend && pytest tests/test_phone_normalization.py -v
"""

import pytest
import httpx
import uuid
import os
import sys
sys.path.insert(0, "/app/backend")

from config import normalize_phone_fr, validate_phone_fr

API_URL = ""
with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            API_URL = line.split("=", 1)[1].strip()
            break

PASSWORD = "RdzTest2026!"


# ═══════════════════════════════════════════════════════════════
# 1. NORMALIZATION PIPELINE
# ═══════════════════════════════════════════════════════════════

class TestNormalizationPipeline:
    """Tests for the normalize_phone_fr function."""

    # --- MUST PASS (valid phones) ---

    def test_standard_mobile(self):
        """0612345679 — standard mobile (not the blocked 0612345678)."""
        s, n, q = normalize_phone_fr("0612345679")
        assert s == "valid"
        assert n == "0612345679"
        assert q == "valid"

    def test_with_spaces(self):
        """06 12 34 56 79 — spaces stripped."""
        s, n, q = normalize_phone_fr("06 12 34 56 79")
        assert s == "valid"
        assert n == "0612345679"

    def test_plus33_mobile(self):
        """+33612345679 — +33 prefix normalized."""
        s, n, q = normalize_phone_fr("+33612345679")
        assert s == "valid"
        assert n == "0612345679"

    def test_33_prefix_11_digits(self):
        """33612345679 — 33 prefix (11 digits) normalized."""
        s, n, q = normalize_phone_fr("33612345679")
        assert s == "valid"
        assert n == "0612345679"

    def test_0033_prefix(self):
        """0033612345679 — 0033 prefix normalized."""
        s, n, q = normalize_phone_fr("0033612345679")
        assert s == "valid"
        assert n == "0612345679"

    def test_9_digits_mobile(self):
        """612345679 — 9 digits, mobile prefix → add 0."""
        s, n, q = normalize_phone_fr("612345679")
        assert s == "valid"
        assert n == "0612345679"

    def test_9_digits_mobile_7(self):
        """712345679 — 9 digits starting with 7."""
        s, n, q = normalize_phone_fr("712345679")
        assert s == "valid"
        assert n == "0712345679"

    def test_landline(self):
        """0145678901 — landline (01)."""
        s, n, q = normalize_phone_fr("0145678901")
        assert s == "valid"
        assert n == "0145678901"
        assert q == "valid"

    def test_with_dashes(self):
        """06-12-34-56-79 — dashes stripped."""
        s, n, q = normalize_phone_fr("06-12-34-56-79")
        assert s == "valid"
        assert n == "0612345679"

    def test_with_dots(self):
        """06.12.34.56.79 — dots stripped."""
        s, n, q = normalize_phone_fr("06.12.34.56.79")
        assert s == "valid"
        assert n == "0612345679"

    def test_with_parentheses(self):
        """(06) 12 34 56 79 — parentheses stripped."""
        s, n, q = normalize_phone_fr("(06) 12 34 56 79")
        assert s == "valid"
        assert n == "0612345679"

    def test_plus33_with_spaces(self):
        """+33 6 12 34 56 79 — +33 with spaces."""
        s, n, q = normalize_phone_fr("+33 6 12 34 56 79")
        assert s == "valid"
        assert n == "0612345679"

    # --- MUST FAIL (invalid phones) ---

    def test_too_short(self):
        """123456 — too short."""
        s, n, q = normalize_phone_fr("123456")
        assert s == "invalid"
        assert q == "invalid"

    def test_us_number(self):
        """+12025550199 — US number, not FR."""
        s, n, q = normalize_phone_fr("+12025550199")
        assert s == "invalid"

    def test_letters(self):
        """abcdef — no digits."""
        s, n, q = normalize_phone_fr("abcdef")
        assert s == "invalid"

    def test_empty(self):
        """Empty string."""
        s, n, q = normalize_phone_fr("")
        assert s == "invalid"

    def test_blocked_all_zeros(self):
        """0000000000 — all same digits."""
        s, n, q = normalize_phone_fr("0000000000")
        assert s == "invalid"

    def test_blocked_all_ones(self):
        """1111111111 — all same digits."""
        s, n, q = normalize_phone_fr("1111111111")
        assert s == "invalid"

    def test_blocked_sequence_0123(self):
        """0123456789 — sequential."""
        s, n, q = normalize_phone_fr("0123456789")
        assert s == "invalid"

    def test_blocked_sequence_1234(self):
        """1234567890 — sequential."""
        s, n, q = normalize_phone_fr("1234567890")
        assert s == "invalid"

    def test_blocked_reverse_0987(self):
        """0987654321 — reverse sequential."""
        s, n, q = normalize_phone_fr("0987654321")
        assert s == "invalid"

    def test_blocked_test_number(self):
        """0612345678 — ultra common test number."""
        s, n, q = normalize_phone_fr("0612345678")
        assert s == "invalid"

    def test_blocked_all_fives(self):
        """5555555555 — all same digits."""
        s, n, q = normalize_phone_fr("5555555555")
        assert s == "invalid"


# ═══════════════════════════════════════════════════════════════
# 2. QUALITY DETECTION
# ═══════════════════════════════════════════════════════════════

class TestPhoneQuality:
    """Tests for phone_quality field."""

    def test_normal_phone_valid(self):
        """Normal phone → quality=valid."""
        s, n, q = normalize_phone_fr("0698765432")
        assert q == "valid"

    def test_suspicious_alternating(self):
        """0606060606 — alternating pattern → suspicious."""
        s, n, q = normalize_phone_fr("0606060606")
        assert s == "valid"  # Accepted
        assert q == "suspicious"

    def test_suspicious_many_same(self):
        """0611111111 — 7+ same digits → suspicious."""
        s, n, q = normalize_phone_fr("0611111111")
        assert s == "valid"  # Accepted
        assert q == "suspicious"

    def test_suspicious_not_blocked(self):
        """Suspicious phones are accepted (not rejected)."""
        s, n, q = normalize_phone_fr("0678787878")
        assert s == "valid"
        assert q == "suspicious"

    def test_landline_valid_quality(self):
        """Landline → quality=valid (not suspicious)."""
        s, n, q = normalize_phone_fr("0145234567")
        assert q == "valid"


# ═══════════════════════════════════════════════════════════════
# 3. LEGACY WRAPPER
# ═══════════════════════════════════════════════════════════════

class TestLegacyWrapper:
    """validate_phone_fr backward compat."""

    def test_valid(self):
        ok, result = validate_phone_fr("0698765432")
        assert ok is True
        assert result == "0698765432"

    def test_invalid(self):
        ok, result = validate_phone_fr("abcdef")
        assert ok is False

    def test_plus33(self):
        ok, result = validate_phone_fr("+33698765432")
        assert ok is True
        assert result == "0698765432"


# ═══════════════════════════════════════════════════════════════
# 4. API INTEGRATION (E2E)
# ═══════════════════════════════════════════════════════════════

class TestAPIIntegration:
    """Phone normalization applied at API level."""

    def test_lead_plus33_normalized(self):
        """+33 phone normalized before storage."""
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{API_URL}/api/public/leads", json={
                "session_id": str(uuid.uuid4()),
                "form_code": "TEST",
                "phone": "+33698765432",
                "nom": "PlusTest",
                "departement": "75",
                "entity": "ZR7",
                "produit": "PV",
            })
            assert r.status_code == 200
            data = r.json()
            assert data["success"] is True
            # Lead should NOT be invalid — +33 is now handled
            assert data["status"] != "invalid", f"Phone +33 should be accepted, got {data}"

    def test_lead_blocked_phone_invalid(self):
        """Blocked phone: status=invalid."""
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{API_URL}/api/public/leads", json={
                "session_id": str(uuid.uuid4()),
                "form_code": "TEST",
                "phone": "0000000000",
                "nom": "BlockedTest",
                "departement": "75",
                "entity": "ZR7",
                "produit": "PV",
            })
            assert r.status_code == 200
            assert r.json()["status"] == "invalid"

    def test_lead_suspicious_accepted(self):
        """Suspicious phone: lead accepted (not rejected)."""
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{API_URL}/api/public/leads", json={
                "session_id": str(uuid.uuid4()),
                "form_code": "TEST",
                "phone": "0606060606",
                "nom": "SuspiciousTest",
                "departement": "75",
                "entity": "ZR7",
                "produit": "PV",
            })
            assert r.status_code == 200
            data = r.json()
            assert data["success"] is True
            # Suspicious = accepted, not invalid
            assert data["status"] != "invalid"

    def test_lead_0033_normalized(self):
        """0033 prefix normalized."""
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{API_URL}/api/public/leads", json={
                "session_id": str(uuid.uuid4()),
                "form_code": "TEST",
                "phone": "0033698765432",
                "nom": "Prefix0033",
                "departement": "13",
                "entity": "ZR7",
                "produit": "PAC",
            })
            assert r.status_code == 200
            assert r.json()["status"] != "invalid"

    def test_lead_test_number_blocked(self):
        """0612345678 (test number) blocked."""
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{API_URL}/api/public/leads", json={
                "session_id": str(uuid.uuid4()),
                "form_code": "TEST",
                "phone": "0612345678",
                "nom": "TestNum",
                "departement": "75",
                "entity": "ZR7",
                "produit": "PV",
            })
            assert r.status_code == 200
            assert r.json()["status"] == "invalid"
