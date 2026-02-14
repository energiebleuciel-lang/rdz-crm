"""
Test suite for RDZ CRM Month Summary feature
Tests the new GET /api/billing/month-summary endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "energiebleuciel@gmail.com", "password": "92Ruemarxdormoy"}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json().get("token")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get auth headers"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestMonthSummaryEndpoint:
    """Tests for GET /api/billing/month-summary"""
    
    def test_month_summary_returns_200(self, auth_headers):
        """Test endpoint returns 200 with valid month"""
        response = requests.get(
            f"{BASE_URL}/api/billing/month-summary?month=2026-02",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "month" in data
        assert data["month"] == "2026-02"
    
    def test_month_summary_without_month_uses_current(self, auth_headers):
        """Test endpoint uses current month when not specified"""
        response = requests.get(
            f"{BASE_URL}/api/billing/month-summary",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "month" in data
        # Should have YYYY-MM format
        assert len(data["month"]) == 7
        assert "-" in data["month"]
    
    def test_month_summary_has_summary_fields(self, auth_headers):
        """Test summary contains total_leads, total_lb, billable_leads, billable_lb"""
        response = requests.get(
            f"{BASE_URL}/api/billing/month-summary?month=2026-02",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        summary = data.get("summary", {})
        
        # Required fields in summary
        assert "total_leads" in summary
        assert "total_lb" in summary
        assert "billable_leads" in summary
        assert "billable_lb" in summary
        assert "units_delivered" in summary
        assert "units_billable" in summary
        assert "units_non_billable" in summary
        assert "leads_produced" in summary
        
        # All should be integers
        assert isinstance(summary["total_leads"], int)
        assert isinstance(summary["total_lb"], int)
        assert isinstance(summary["billable_leads"], int)
        assert isinstance(summary["billable_lb"], int)
    
    def test_month_summary_has_totals_fields(self, auth_headers):
        """Test totals include units_billable, units_leads, units_lb, net_ht, vat, ttc"""
        response = requests.get(
            f"{BASE_URL}/api/billing/month-summary?month=2026-02",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        totals = data.get("totals", {})
        
        # Required fields in totals
        assert "units_billable" in totals
        assert "units_leads" in totals
        assert "units_lb" in totals
        assert "net_ht" in totals
        assert "vat" in totals
        assert "ttc" in totals
    
    def test_month_summary_has_rows_with_aggregation(self, auth_headers):
        """Test rows are aggregated by client+product with required fields"""
        response = requests.get(
            f"{BASE_URL}/api/billing/month-summary?month=2026-02",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        rows = data.get("rows", [])
        
        # Should have rows if there's billing data
        assert isinstance(rows, list)
        
        if len(rows) > 0:
            row = rows[0]
            # Required fields per row
            assert "client_id" in row
            assert "product_code" in row
            assert "units_billable" in row
            assert "units_leads" in row
            assert "units_lb" in row
            assert "net_total_ht" in row
            assert "vat_amount" in row
            assert "total_ttc" in row
            assert "status" in row
            assert "weeks_count" in row
    
    def test_month_summary_has_interfacturation(self, auth_headers):
        """Test interfacturation array is present"""
        response = requests.get(
            f"{BASE_URL}/api/billing/month-summary?month=2026-02",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "interfacturation" in data
        assert isinstance(data["interfacturation"], list)
    
    def test_month_summary_has_weeks_in_month(self, auth_headers):
        """Test weeks_in_month array shows which weeks are included"""
        response = requests.get(
            f"{BASE_URL}/api/billing/month-summary?month=2026-02",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "weeks_in_month" in data
        assert isinstance(data["weeks_in_month"], list)
        # February 2026 should include at least W07 based on test data
        if len(data["weeks_in_month"]) > 0:
            assert any("W" in w for w in data["weeks_in_month"])
    
    def test_month_summary_has_date_range(self, auth_headers):
        """Test month_start and month_end are present"""
        response = requests.get(
            f"{BASE_URL}/api/billing/month-summary?month=2026-02",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "month_start" in data
        assert "month_end" in data
        assert data["month_start"] == "2026-02-01"
        assert data["month_end"] == "2026-02-28"
    
    def test_month_summary_invalid_month_returns_400(self, auth_headers):
        """Test invalid month format returns 400"""
        response = requests.get(
            f"{BASE_URL}/api/billing/month-summary?month=invalid",
            headers=auth_headers
        )
        assert response.status_code == 400
    
    def test_month_summary_unauthenticated_returns_401(self):
        """Test unauthenticated request returns 401"""
        response = requests.get(f"{BASE_URL}/api/billing/month-summary?month=2026-02")
        assert response.status_code == 401


class TestMonthSummaryDataIntegrity:
    """Tests for data integrity and aggregation logic"""
    
    def test_totals_match_row_sums(self, auth_headers):
        """Verify totals match sum of non-PREPAID rows"""
        response = requests.get(
            f"{BASE_URL}/api/billing/month-summary?month=2026-02",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        totals = data.get("totals", {})
        rows = data.get("rows", [])
        
        # Calculate sums from non-PREPAID rows
        sum_billable = sum(r.get("units_billable", 0) for r in rows if r.get("billing_mode") != "PREPAID")
        sum_leads = sum(r.get("units_leads", 0) for r in rows if r.get("billing_mode") != "PREPAID")
        sum_lb = sum(r.get("units_lb", 0) for r in rows if r.get("billing_mode") != "PREPAID")
        sum_net_ht = sum(r.get("net_total_ht", 0) for r in rows if r.get("billing_mode") != "PREPAID")
        
        # Verify totals
        assert totals.get("units_billable", 0) == sum_billable
        assert totals.get("units_leads", 0) == sum_leads
        assert totals.get("units_lb", 0) == sum_lb
        assert abs(totals.get("net_ht", 0) - sum_net_ht) < 0.01  # Float tolerance
    
    def test_rows_have_weeks_count(self, auth_headers):
        """Verify each row has weeks_count showing how many weeks were aggregated"""
        response = requests.get(
            f"{BASE_URL}/api/billing/month-summary?month=2026-02",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        rows = data.get("rows", [])
        
        for row in rows:
            assert "weeks_count" in row
            assert isinstance(row["weeks_count"], int)
            assert row["weeks_count"] >= 1
    
    def test_rows_have_status(self, auth_headers):
        """Verify each row has aggregated status"""
        response = requests.get(
            f"{BASE_URL}/api/billing/month-summary?month=2026-02",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        rows = data.get("rows", [])
        
        valid_statuses = ["not_invoiced", "invoiced", "paid", "overdue"]
        for row in rows:
            assert "status" in row
            assert row["status"] in valid_statuses


class TestMonthNavigation:
    """Tests for month navigation edge cases"""
    
    def test_january_month(self, auth_headers):
        """Test January returns correct date range"""
        response = requests.get(
            f"{BASE_URL}/api/billing/month-summary?month=2026-01",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["month_start"] == "2026-01-01"
        assert data["month_end"] == "2026-01-31"
    
    def test_december_month(self, auth_headers):
        """Test December returns correct date range"""
        response = requests.get(
            f"{BASE_URL}/api/billing/month-summary?month=2025-12",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["month_start"] == "2025-12-01"
        assert data["month_end"] == "2025-12-31"
    
    def test_leap_year_february(self, auth_headers):
        """Test February in leap year (2024) returns 29 days"""
        response = requests.get(
            f"{BASE_URL}/api/billing/month-summary?month=2024-02",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["month_start"] == "2024-02-01"
        assert data["month_end"] == "2024-02-29"  # Leap year
