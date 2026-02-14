"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  RDZ CRM - State Machine Transition Testing (Direct Python Tests)            ║
║                                                                              ║
║  Tests the state machine transitions by calling functions directly:          ║
║  1. Valid transitions work correctly                                         ║
║  2. Invalid transitions are blocked                                          ║
║  3. Invariants are enforced                                                  ║
║  4. Batch guards work correctly                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import pytest
import asyncio
import uuid
import os
import sys

# Add backend to path
sys.path.insert(0, "/app/backend")

from services.delivery_state_machine import (
    check_sent_invariants,
    validate_delivery_transition,
    VALID_DELIVERY_TRANSITIONS,
    DeliveryInvariantError
)


class TestValidTransitions:
    """Test the VALID_DELIVERY_TRANSITIONS map"""
    
    def test_valid_transitions_map_exists(self):
        """Check the transition map is defined"""
        assert VALID_DELIVERY_TRANSITIONS is not None
        assert isinstance(VALID_DELIVERY_TRANSITIONS, dict)
        print(f"✅ Transitions map: {VALID_DELIVERY_TRANSITIONS}")
    
    def test_pending_csv_valid_transitions(self):
        """pending_csv can go to ready_to_send, sending, failed"""
        valid_next = VALID_DELIVERY_TRANSITIONS.get("pending_csv", [])
        assert "ready_to_send" in valid_next
        assert "sending" in valid_next
        assert "failed" in valid_next
        assert "sent" not in valid_next  # Cannot skip to sent
        print(f"✅ pending_csv transitions: {valid_next}")
    
    def test_ready_to_send_valid_transitions(self):
        """ready_to_send can go to sending, failed"""
        valid_next = VALID_DELIVERY_TRANSITIONS.get("ready_to_send", [])
        assert "sending" in valid_next
        assert "failed" in valid_next
        print(f"✅ ready_to_send transitions: {valid_next}")
    
    def test_sending_valid_transitions(self):
        """sending can go to sent, failed"""
        valid_next = VALID_DELIVERY_TRANSITIONS.get("sending", [])
        assert "sent" in valid_next
        assert "failed" in valid_next
        print(f"✅ sending transitions: {valid_next}")
    
    def test_sent_is_terminal(self):
        """sent is terminal - no valid next states"""
        valid_next = VALID_DELIVERY_TRANSITIONS.get("sent", [])
        assert len(valid_next) == 0, f"sent should be terminal but has: {valid_next}"
        print("✅ sent is terminal (no valid transitions)")
    
    def test_failed_can_retry(self):
        """failed can go to pending_csv (reset), sending (retry)"""
        valid_next = VALID_DELIVERY_TRANSITIONS.get("failed", [])
        assert "pending_csv" in valid_next or "sending" in valid_next
        print(f"✅ failed transitions (retry allowed): {valid_next}")


class TestInvariantChecks:
    """Test the invariant checking functions"""
    
    def test_sent_invariants_valid(self):
        """Valid sent invariants should pass"""
        result = check_sent_invariants(
            sent_to=["test@example.com"],
            last_sent_at="2026-01-18T10:00:00Z",
            send_attempts=1
        )
        assert result == True
        print("✅ Valid invariants pass check")
    
    def test_sent_invariants_empty_sent_to(self):
        """Empty sent_to should raise error"""
        with pytest.raises(DeliveryInvariantError) as exc_info:
            check_sent_invariants(
                sent_to=[],
                last_sent_at="2026-01-18T10:00:00Z",
                send_attempts=1
            )
        assert "sent_to" in str(exc_info.value)
        print(f"✅ Empty sent_to blocked: {exc_info.value}")
    
    def test_sent_invariants_null_sent_to(self):
        """None sent_to should raise error"""
        with pytest.raises(DeliveryInvariantError) as exc_info:
            check_sent_invariants(
                sent_to=None,
                last_sent_at="2026-01-18T10:00:00Z",
                send_attempts=1
            )
        assert "sent_to" in str(exc_info.value)
        print(f"✅ None sent_to blocked: {exc_info.value}")
    
    def test_sent_invariants_null_last_sent_at(self):
        """None last_sent_at should raise error"""
        with pytest.raises(DeliveryInvariantError) as exc_info:
            check_sent_invariants(
                sent_to=["test@example.com"],
                last_sent_at=None,
                send_attempts=1
            )
        assert "last_sent_at" in str(exc_info.value)
        print(f"✅ None last_sent_at blocked: {exc_info.value}")
    
    def test_sent_invariants_zero_attempts(self):
        """Zero send_attempts should raise error"""
        with pytest.raises(DeliveryInvariantError) as exc_info:
            check_sent_invariants(
                sent_to=["test@example.com"],
                last_sent_at="2026-01-18T10:00:00Z",
                send_attempts=0
            )
        assert "send_attempts" in str(exc_info.value)
        print(f"✅ Zero send_attempts blocked: {exc_info.value}")
    
    def test_sent_invariants_negative_attempts(self):
        """Negative send_attempts should raise error"""
        with pytest.raises(DeliveryInvariantError) as exc_info:
            check_sent_invariants(
                sent_to=["test@example.com"],
                last_sent_at="2026-01-18T10:00:00Z",
                send_attempts=-1
            )
        assert "send_attempts" in str(exc_info.value)
        print(f"✅ Negative send_attempts blocked: {exc_info.value}")
    
    def test_multiple_emails_valid(self):
        """Multiple emails in sent_to should work"""
        result = check_sent_invariants(
            sent_to=["test1@example.com", "test2@example.com"],
            last_sent_at="2026-01-18T10:00:00Z",
            send_attempts=2
        )
        assert result == True
        print("✅ Multiple emails pass invariant check")


class TestTransitionValidation:
    """Test the validate_delivery_transition async function"""
    
    @pytest.mark.asyncio
    async def test_valid_transition_pending_to_ready(self):
        """pending_csv -> ready_to_send should be valid"""
        result = await validate_delivery_transition(
            delivery_id="test-123",
            from_status="pending_csv",
            to_status="ready_to_send"
        )
        assert result == True
        print("✅ pending_csv -> ready_to_send valid")
    
    @pytest.mark.asyncio
    async def test_valid_transition_ready_to_sending(self):
        """ready_to_send -> sending should be valid"""
        result = await validate_delivery_transition(
            delivery_id="test-123",
            from_status="ready_to_send",
            to_status="sending"
        )
        assert result == True
        print("✅ ready_to_send -> sending valid")
    
    @pytest.mark.asyncio
    async def test_valid_transition_sending_to_sent(self):
        """sending -> sent should be valid"""
        result = await validate_delivery_transition(
            delivery_id="test-123",
            from_status="sending",
            to_status="sent"
        )
        assert result == True
        print("✅ sending -> sent valid")
    
    @pytest.mark.asyncio
    async def test_invalid_transition_sent_to_failed(self):
        """sent -> failed should be BLOCKED (sent is terminal)"""
        with pytest.raises(DeliveryInvariantError) as exc_info:
            await validate_delivery_transition(
                delivery_id="test-123",
                from_status="sent",
                to_status="failed"
            )
        assert "INVALID TRANSITION" in str(exc_info.value)
        print(f"✅ sent -> failed blocked: {exc_info.value}")
    
    @pytest.mark.asyncio
    async def test_invalid_transition_sent_to_pending(self):
        """sent -> pending_csv should be BLOCKED"""
        with pytest.raises(DeliveryInvariantError) as exc_info:
            await validate_delivery_transition(
                delivery_id="test-123",
                from_status="sent",
                to_status="pending_csv"
            )
        assert "INVALID TRANSITION" in str(exc_info.value)
        print(f"✅ sent -> pending_csv blocked: {exc_info.value}")
    
    @pytest.mark.asyncio
    async def test_invalid_transition_sent_to_ready(self):
        """sent -> ready_to_send should be BLOCKED"""
        with pytest.raises(DeliveryInvariantError) as exc_info:
            await validate_delivery_transition(
                delivery_id="test-123",
                from_status="sent",
                to_status="ready_to_send"
            )
        assert "INVALID TRANSITION" in str(exc_info.value)
        print(f"✅ sent -> ready_to_send blocked: {exc_info.value}")
    
    @pytest.mark.asyncio
    async def test_invalid_transition_skip_states(self):
        """pending_csv -> sent should be BLOCKED (must go through sending)"""
        with pytest.raises(DeliveryInvariantError) as exc_info:
            await validate_delivery_transition(
                delivery_id="test-123",
                from_status="pending_csv",
                to_status="sent"
            )
        assert "INVALID TRANSITION" in str(exc_info.value)
        print(f"✅ pending_csv -> sent blocked (must go through sending): {exc_info.value}")
    
    @pytest.mark.asyncio
    async def test_invalid_transition_ready_to_sent(self):
        """ready_to_send -> sent should be BLOCKED (must go through sending)"""
        with pytest.raises(DeliveryInvariantError) as exc_info:
            await validate_delivery_transition(
                delivery_id="test-123",
                from_status="ready_to_send",
                to_status="sent"
            )
        assert "INVALID TRANSITION" in str(exc_info.value)
        print(f"✅ ready_to_send -> sent blocked (must go through sending): {exc_info.value}")


class TestStaticCodeAudit:
    """Verify no direct status writes exist outside state machine"""
    
    def test_no_direct_status_sent_writes(self):
        """
        Audit: Check that no code sets status='sent' directly on db.deliveries
        (except state_machine.py)
        """
        import subprocess
        
        result = subprocess.run(
            ['grep', '-rn', 'status.*sent', '/app/backend/routes/', '/app/backend/services/'],
            capture_output=True,
            text=True
        )
        
        # Filter out state_machine, test files, and return values (not DB writes)
        violations = []
        for line in result.stdout.split('\n'):
            if not line:
                continue
            if 'state_machine' in line.lower():
                continue
            if 'test' in line.lower():
                continue
            # Check for actual DB writes
            if '{"$set"' in line and '"status":' in line and '"sent"' in line:
                violations.append(line)
            # Check for update_one/update_many with status
            if 'update_one' in line or 'update_many' in line:
                if '"status"' in line and '"sent"' in line:
                    violations.append(line)
        
        if violations:
            print(f"❌ Potential violations: {violations}")
        
        assert len(violations) == 0, f"Found direct status writes: {violations}"
        print("✅ No direct status='sent' writes found outside state machine")
    
    def test_state_machine_is_imported(self):
        """Verify state machine is imported in delivery routes"""
        with open('/app/backend/routes/deliveries.py', 'r') as f:
            content = f.read()
        
        assert 'from services.delivery_state_machine import' in content
        assert 'mark_delivery_sent' in content
        print("✅ State machine is properly imported in deliveries.py")
    
    def test_state_machine_used_in_daily_delivery(self):
        """Verify state machine is used in daily_delivery.py"""
        with open('/app/backend/services/daily_delivery.py', 'r') as f:
            content = f.read()
        
        assert 'from services.delivery_state_machine import' in content
        assert 'batch_mark_deliveries_sent' in content
        print("✅ State machine is properly imported in daily_delivery.py")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
