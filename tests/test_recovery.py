import pytest
from unittest.mock import patch
from cortexheal.models.recovery import RecoveryPlan, RecoveryAction
from cortexheal.models.incident import Incident
from cortexheal.models.run import AgentRun
from cortexheal.recovery.engine import RecoveryEngine
from cortexheal.recovery.policy import PolicyEngine
from cortexheal.recovery.executor import RecoveryExecutor
import uuid

def test_recovery_engine_deterministic():
    engine = RecoveryEngine()
    incident = Incident(
        run_id=str(uuid.uuid4()),
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
    
    with patch('cortexheal.recovery.engine.get_recovery_plan_by_incident', return_value=None):
        with patch('cortexheal.recovery.engine.get_run', return_value=AgentRun(framework="langgraph", run_id="run1", agent_id="agent1", status="paused", start_time="2026-08-08T00:00:00Z", last_updated="2026-08-08T00:00:00Z")):
            with patch('cortexheal.recovery.engine.get_events_for_run', return_value=[]):
                with patch('cortexheal.recovery.engine.save_audit_event'):
                    with patch('cortexheal.recovery.policy.get_audit_events_for_run', return_value=[]):
                        with patch('cortexheal.recovery.engine.save_recovery_plan'):
                            with patch('cortexheal.recovery.engine.RecoveryExecutor.execute_plan') as mock_exec:
                                plan = engine.generate_plan(incident)
            
    assert plan.diagnosis == "The agent appears to be repeatedly invoking the same tool without observable progress."
    assert plan.planner_type == "AI_ASSISTED"
    assert plan.proposed_actions[0].action_type == "KEEP_PAUSED"

def test_policy_engine():
    policy = PolicyEngine()
    plan = RecoveryPlan(
        incident_id="inc1",
        run_id="run1",
        diagnosis="test",
        proposed_actions=[
            RecoveryAction(run_id="run1", incident_id="inc1", action_type="KEEP_PAUSED", reason="test")
        ]
    )
    
    # Viewer cannot approve
    assert not policy.evaluate_plan(plan, "VIEWER")
    
    # Operator can approve
    assert policy.evaluate_plan(plan, "OPERATOR")
    
    # Admin can approve
    assert policy.evaluate_plan(plan, "ADMIN")
    
    # Invalid action
    plan.proposed_actions.append(
        RecoveryAction.model_construct(run_id="run1", incident_id="inc1", action_type="INVALID_ACTION", reason="test")
    )
    assert not policy.evaluate_plan(plan, "OPERATOR")

@patch('cortexheal.recovery.executor.save_recovery_plan')
@patch('cortexheal.recovery.executor.save_recovery_action')
@patch('cortexheal.recovery.executor.save_audit_event')
@patch('cortexheal.recovery.executor.save_recovery_outcome')
@patch('cortexheal.recovery.executor.get_incident', return_value=Incident(run_id="run1", agent_id="test", failure_type="STUCK_LOOP", description="test", evidence={}, severity="HIGH", detector="test", detector_version="test", trigger_event_id="test", observed_value=3, threshold=3))
@patch('cortexheal.recovery.executor.PatternEngine.get_or_create_pattern')
@patch('cortexheal.recovery.executor.ProtectionController')
@patch('cortexheal.recovery.executor.get_run', return_value=AgentRun(framework="langgraph", run_id="run1", agent_id="agent1", status="paused", start_time="2026-08-08T00:00:00Z", last_updated="2026-08-08T00:00:00Z"))
@patch('cortexheal.recovery.executor.get_events_for_run', return_value=[])
def test_executor_approve(mock_events, mock_get_run, mock_pc_cls, mock_pattern, mock_incident, mock_save_outcome, mock_audit, mock_save_act, mock_save_plan):
    mock_pc = mock_pc_cls.return_value
    executor = RecoveryExecutor()
    
    plan = RecoveryPlan(
        incident_id="inc1",
        run_id="run1",
        diagnosis="test",
        proposed_actions=[
            RecoveryAction(run_id="run1", incident_id="inc1", action_type="RESUME", reason="test")
        ],
        snapshot_run_status="paused",
        snapshot_sequence_number=0
    )
    
    success = executor.execute_plan(plan, "OPERATOR", "test_user")
    assert success
    assert plan.status == "COMPLETED"
    
    # Verify protection controller was called
    mock_pc.resume.assert_called_once_with("run1", actor_id="test_user", reason="test", incident_id="inc1")

@patch('cortexheal.recovery.executor.save_recovery_plan')
@patch('cortexheal.recovery.executor.save_audit_event')
@patch('cortexheal.recovery.executor.save_recovery_outcome', return_value=None)
@patch('cortexheal.recovery.executor.get_incident', return_value=Incident(run_id="run1", agent_id="test", failure_type="STUCK_LOOP", description="test", evidence={}, severity="HIGH", detector="test", detector_version="test", trigger_event_id="test", observed_value=3, threshold=3))
@patch('cortexheal.recovery.executor.get_events_for_run', return_value=[])
@patch('cortexheal.recovery.executor.PatternEngine.get_or_create_pattern')
def test_executor_reject(mock_pattern, mock_events, mock_incident, mock_save_outcome, mock_audit, mock_save_plan):
    executor = RecoveryExecutor()
    plan = RecoveryPlan(
        incident_id="inc1",
        run_id="run1",
        diagnosis="test",
        proposed_actions=[]
    )
    
    # Reject works for OPERATOR
    success = executor.reject_plan(plan, "OPERATOR", "test_user")
    assert success
    assert plan.status == "REJECTED"
    
    # Cannot approve after reject
    success = executor.execute_plan(plan, "OPERATOR", "test_user")
    assert not success

