"""
Tests unitaires pour la logique LB Target Dynamique
"""
import pytest
from math import ceil


def compute_lb_needed(lb_target_pct: float, delivered_units: int, lb_delivered: int) -> int:
    """Mirror of routing_engine.compute_lb_needed"""
    if lb_target_pct <= 0:
        return 0
    return ceil(lb_target_pct * (delivered_units + 1)) - lb_delivered


class TestComputeLbNeeded:
    """Tests pour la formule lb_needed = ceil(target * (delivered + 1)) - lb_delivered"""

    def test_target_zero(self):
        """target=0 -> never need LB"""
        assert compute_lb_needed(0, 0, 0) == 0
        assert compute_lb_needed(0, 100, 0) == 0
        assert compute_lb_needed(0, 100, 50) == 0

    def test_first_delivery_with_20pct(self):
        """Start of week, 20% target: first delivery should be fresh"""
        # delivered=0, lb=0 -> lb_needed = ceil(0.20 * 1) - 0 = 1
        assert compute_lb_needed(0.20, 0, 0) == 1

    def test_convergence_20pct(self):
        """Simulate 10 deliveries at 20% target: ~2 should be LB"""
        target = 0.20
        delivered = 0
        lb = 0
        lb_picks = 0
        
        for _ in range(10):
            lb_needed = compute_lb_needed(target, delivered, lb)
            if lb_needed > 0:
                lb += 1
                lb_picks += 1
            delivered += 1
        
        # 20% of 10 = 2
        assert lb_picks == 2, f"Expected 2 LB picks, got {lb_picks}"

    def test_convergence_50_units_20pct(self):
        """Test 1: Commande quota=100, target=0.20, simulate 50 units -> LB ~10"""
        target = 0.20
        delivered = 0
        lb = 0
        lb_picks = 0
        
        for _ in range(50):
            lb_needed = compute_lb_needed(target, delivered, lb)
            if lb_needed > 0:
                lb += 1
                lb_picks += 1
            delivered += 1
        
        assert lb_picks == 10, f"Expected 10 LB picks for 50 units at 20%, got {lb_picks}"

    def test_low_volume_20pct(self):
        """Test 2: Commande quota=500, target=0.20, only 200 delivered -> LB ~40"""
        target = 0.20
        delivered = 0
        lb = 0
        lb_picks = 0
        
        for _ in range(200):
            lb_needed = compute_lb_needed(target, delivered, lb)
            if lb_needed > 0:
                lb += 1
                lb_picks += 1
            delivered += 1
        
        assert lb_picks == 40, f"Expected 40 LB picks for 200 units at 20%, got {lb_picks}"

    def test_30pct_target(self):
        """Test 3: 30% target, 100 units"""
        target = 0.30
        delivered = 0
        lb = 0
        lb_picks = 0
        
        for _ in range(100):
            lb_needed = compute_lb_needed(target, delivered, lb)
            if lb_needed > 0:
                lb += 1
                lb_picks += 1
            delivered += 1
        
        assert lb_picks == 30, f"Expected 30 LB picks at 30%, got {lb_picks}"

    def test_already_delivered_with_lb(self):
        """When resuming with existing accepted deliveries"""
        # 10 already delivered (2 LB), target 20%
        # lb_needed = ceil(0.20 * 11) - 2 = ceil(2.2) - 2 = 3 - 2 = 1
        assert compute_lb_needed(0.20, 10, 2) == 1
        
        # 10 already delivered (3 LB), target 20%
        # lb_needed = ceil(0.20 * 11) - 3 = 3 - 3 = 0
        assert compute_lb_needed(0.20, 10, 3) == 0

    def test_lb_surplus(self):
        """When more LB than needed already"""
        # 10 delivered, 5 LB, target 20%
        # lb_needed = ceil(0.20 * 11) - 5 = 3 - 5 = -2
        assert compute_lb_needed(0.20, 10, 5) == -2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
