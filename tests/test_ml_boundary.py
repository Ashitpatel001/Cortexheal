import pytest
from cortexheal.learning.ml import MLDatasetBuilder, RecoveryPredictor, InsufficientData
from cortexheal.models.incident import Incident
from cortexheal.models.learning import RecoveryOutcome

def test_ml_dataset_builder_does_not_leak_raw_tokens():
    evidence = {
        "framework": "langgraph",
        "token_cost": 420,
        "raw_prompt": "You are a helpful assistant...",
        "api_key": "sk-secret"
    }
    
    incident = Incident(
        run_id="run-123",
        agent_id="agent-abc",
        failure_type="STUCK_LOOP",
        severity="HIGH",
        detector="stuck_detector",
        detector_version="1.0",
        trigger_event_id="evt-1",
        evidence=evidence,
        observed_value=0,
        threshold=0,
        description="Agent stuck"
    )
    
    outcome = RecoveryOutcome(
        run_id="run-123",
        incident_id=incident.incident_id,
        pattern_id="pat-1",
        action_type="RESUME",
        execution_result="EXECUTED",
        verification_result="VERIFIED_SUCCESS"
    )
    
    features = MLDatasetBuilder.extract_features(incident, outcome)
    
    # Assert expected sanitized features
    assert features["framework"] == "langgraph"
    assert features["token_cost"] == 420
    assert features["failure_type"] == "STUCK_LOOP"
    assert features["action_type"] == "RESUME"
    assert features["success"] is True
    
    # Assert sensitive / raw data is not leaked
    assert "raw_prompt" not in features
    assert "api_key" not in features
    assert "evidence" not in features

def test_predict_success_insufficient_data():
    predictor = RecoveryPredictor()
    incident = Incident(
        run_id="run-1",
        agent_id="agent-1",
        failure_type="STUCK_LOOP",
        severity="MEDIUM",
        detector="det",
        detector_version="1",
        trigger_event_id="evt-2",
        evidence={},
        observed_value=0,
        threshold=0,
        description="test"
    )
    
    with pytest.raises(InsufficientData):
        predictor.predict_success(incident, "RESUME")

def test_ml_safety_boundary():
    # Test that ML output must never directly return ActionType and must return float
    predictor = RecoveryPredictor()
    predictor.ML_STATUS = "READY_FOR_PREDICTION"
    
    incident = Incident(
        run_id="run-1",
        agent_id="agent-1",
        failure_type="STUCK_LOOP",
        severity="MEDIUM",
        detector="det",
        detector_version="1",
        trigger_event_id="evt-2",
        evidence={},
        observed_value=0,
        threshold=0,
        description="test"
    )
    
    score = predictor.predict_success(incident, "KEEP_PAUSED")
    
    # Must return a float (probability), never an ActionType string directly
    assert isinstance(score, float)
    assert not isinstance(score, str)
    
    # The policy engine is isolated from this predictor, fulfilling the constraint
    # that ML must not modify PolicyEngine rules.
