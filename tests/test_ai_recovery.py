import pytest
from unittest.mock import patch, MagicMock
from cortexheal.models.recovery import RecoveryPlan, RecoveryAction, RecoveryAnalysis
from cortexheal.models.incident import Incident
from cortexheal.models.run import AgentRun
from cortexheal.models.events import RuntimeEvent
from cortexheal.recovery.engine import RecoveryEngine
from cortexheal.recovery.policy import PolicyEngine
from cortexheal.recovery.executor import RecoveryExecutor
from cortexheal.recovery.ai_provider import MockAIProvider
import uuid

@pytest.fixture
def mock_postgres():
    with patch('cortexheal.recovery.engine.get_recovery_plan_by_incident', return_value=None), \
         patch('cortexheal.recovery.engine.get_run', return_value=AgentRun(framework="langgraph", run_id="run1", agent_id="agent1", status="paused", start_time="2026-08-08T00:00:00Z", last_updated="2026-08-08T00:00:00Z")), \
         patch('cortexheal.recovery.engine.get_events_for_run', return_value=[RuntimeEvent.model_construct(framework="langgraph", run_id="run1", agent_id="agent1", event_type="PAUSED", sequence_number=10, timestamp="2026-08-08T00:00:00Z")]), \
         patch('cortexheal.recovery.engine.save_recovery_plan'), \
         patch('cortexheal.recovery.engine.save_audit_event'), \
         patch('cortexheal.recovery.policy.get_audit_events_for_run', return_value=[]), \
         patch('cortexheal.recovery.executor.get_run', return_value=AgentRun.model_construct(framework="langgraph", run_id="run1", agent_id="agent1", status="paused", start_time="2026-08-08T00:00:00Z", last_updated="2026-08-08T00:00:00Z")), \
         patch('cortexheal.recovery.executor.get_events_for_run', return_value=[RuntimeEvent.model_construct(framework="langgraph", run_id="run1", agent_id="agent1", event_type="PAUSED", sequence_number=10, timestamp="2026-08-08T00:00:00Z")]), \
         patch('cortexheal.recovery.executor.save_recovery_plan'), \
         patch('cortexheal.recovery.executor.save_recovery_action'), \
         patch('cortexheal.recovery.executor.save_audit_event'), \
         patch('cortexheal.recovery.executor.ProtectionController'):
        yield

def test_ai_assisted_planning(mock_postgres):
    ai_provider = MockAIProvider()
    engine = RecoveryEngine(ai_provider=ai_provider)
    incident = Incident(
        run_id="run1",
        agent_id="test",
        failure_type="STUCK_LOOP",
        description="Loop detected",
        evidence={},
        severity="HIGH",
        detector="stuck_loop",
        detector_version="1.0",
        trigger_event_id=str(uuid.uuid4()),
        observed_value=3,
        threshold=3
    )
    
    plan = engine.generate_plan(incident)
    
    assert plan.planner_type == "AI_ASSISTED"
    assert plan.ai_analysis is not None
    assert plan.ai_analysis["confidence"] == 0.91
    assert plan.snapshot_run_status == "paused"
    assert plan.snapshot_sequence_number == 10

def test_plan_staleness_protection(mock_postgres):
    executor = RecoveryExecutor()
    plan = RecoveryPlan(
        incident_id="inc1",
        run_id="run1",
        diagnosis="test",
        proposed_actions=[RecoveryAction.model_construct(run_id="run1", incident_id="inc1", action_type="RESUME", reason="test")],
        snapshot_run_status="paused",
        snapshot_sequence_number=5 # Mismatch! Current is 10
    )
    
    success = executor.execute_plan(plan, "OPERATOR", "user1")
    assert not success
    assert plan.status == "PLAN_STALE"

def test_verification_status_update(mock_postgres):
    executor = RecoveryExecutor()
    plan = RecoveryPlan(
        incident_id="inc1",
        run_id="run1",
        diagnosis="test",
        proposed_actions=[RecoveryAction.model_construct(run_id="run1", incident_id="inc1", action_type="RESUME", reason="test", status="PENDING")],
        snapshot_run_status="paused",
        snapshot_sequence_number=10
    )
    
    success = executor.execute_plan(plan, "OPERATOR", "user1")
    assert success
    assert plan.verification_status == "RECOVERY_UNVERIFIED"
    assert plan.status == "COMPLETED"

def test_ai_graceful_degradation():
    class BrokenAIProvider(MockAIProvider):
        def analyze_incident(self, incident, run, events):
            raise Exception("AI API Error")
            
    engine = RecoveryEngine(ai_provider=BrokenAIProvider())
    incident = Incident(run_id="run1", agent_id="test", failure_type="STUCK_LOOP", description="test", evidence={}, severity="HIGH", detector="stuck_loop", detector_version="1.0", trigger_event_id="test", observed_value=3, threshold=3)
    
    with patch('cortexheal.recovery.engine.get_recovery_plan_by_incident', return_value=None), \
         patch('cortexheal.recovery.engine.get_run', return_value=None), \
         patch('cortexheal.recovery.engine.get_events_for_run', return_value=[]), \
         patch('cortexheal.recovery.engine.save_audit_event'), \
         patch('cortexheal.recovery.policy.get_audit_events_for_run', return_value=[]), \
         patch('cortexheal.recovery.engine.save_recovery_plan'):
        plan = engine.generate_plan(incident)
        
    assert plan.planner_type == "DETERMINISTIC"
    assert plan.ai_analysis is None
