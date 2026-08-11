import pytest
from unittest.mock import patch, MagicMock

from cortexheal.models.incident import Incident
from cortexheal.models.events import RuntimeEvent
from cortexheal.models.learning import PatternRecord, RecoveryOutcome
from cortexheal.learning.fingerprint import generate_fingerprint
from cortexheal.learning.pattern import PatternEngine
from cortexheal.learning.trust import TrustEngine
from cortexheal.learning.ranking import RankingEngine

@pytest.fixture
def dummy_incident():
    return Incident(
        run_id="run-123",
        agent_id="agent-456",
        failure_type="STUCK_LOOP",
        severity="HIGH",
        detector="test",
        detector_version="1.0",
        trigger_event_id="evt-001",
        evidence={},
        observed_value=5,
        threshold=3,
        description="test incident"
    )

@pytest.fixture
def dummy_event():
    return RuntimeEvent(
        run_id="run-123",
        agent_id="agent-456",
        event_type="RUN_FAILED",
        status="failed",
        sequence_number=1,
        framework="cortex",
        idempotency_key="key",
        tool="SearchTool",
        arguments_hash="hash_args",
        response_hash="hash_resp"
    )

def test_generate_fingerprint_deterministic(dummy_incident, dummy_event):
    fp1 = generate_fingerprint(dummy_incident, dummy_event)
    fp2 = generate_fingerprint(dummy_incident, dummy_event)
    assert fp1 == fp2
    assert fp1.startswith("v1-")

@patch('cortexheal.learning.pattern.get_pattern_by_fingerprint')
@patch('cortexheal.learning.pattern.save_pattern_record')
def test_pattern_engine_create_new(mock_save, mock_get, dummy_incident, dummy_event):
    mock_get.return_value = None
    engine = PatternEngine()
    pattern = engine.get_or_create_pattern(dummy_incident, dummy_event)
    assert pattern.occurrences == 1
    mock_save.assert_called_once()
    assert pattern.fingerprint.startswith("v1-")

@patch('cortexheal.learning.pattern.get_pattern_by_fingerprint')
@patch('cortexheal.learning.pattern.save_pattern_record')
def test_pattern_engine_update_existing(mock_save, mock_get, dummy_incident, dummy_event):
    existing = PatternRecord(
        pattern_id="p-1",
        framework="cortex",
        agent_id="agent-456",
        failure_type="STUCK_LOOP",
        fingerprint="v1-xyz",
        fingerprint_version="v1",
        occurrences=5
    )
    mock_get.return_value = existing
    
    engine = PatternEngine()
    pattern = engine.get_or_create_pattern(dummy_incident, dummy_event)
    assert pattern.occurrences == 6
    mock_save.assert_called_once()
    assert pattern.pattern_id == "p-1"

@patch('cortexheal.learning.trust.get_outcomes_for_pattern')
def test_trust_engine_calculate_trust(mock_get_outcomes):
    mock_get_outcomes.return_value = [
        RecoveryOutcome(run_id="r1", incident_id="i1", pattern_id="p1", action_type="RESUME", execution_result="EXECUTED", verification_result="VERIFIED_SUCCESS"),
        RecoveryOutcome(run_id="r2", incident_id="i2", pattern_id="p1", action_type="RESUME", execution_result="EXECUTED", verification_result="VERIFIED_SUCCESS"),
        RecoveryOutcome(run_id="r3", incident_id="i3", pattern_id="p1", action_type="RESUME", execution_result="EXECUTED", verification_result="VERIFIED_FAILURE"),
        RecoveryOutcome(run_id="r4", incident_id="i4", pattern_id="p1", action_type="RESUME", execution_result="EXECUTED", verification_result="UNVERIFIED"),
        RecoveryOutcome(run_id="r5", incident_id="i5", pattern_id="p1", action_type="KEEP_PAUSED", execution_result="EXECUTED", verification_result="VERIFIED_SUCCESS"),
    ]
    
    engine = TrustEngine()
    evidence = engine.calculate_trust("p1")
    
    assert evidence.occurrences == 5
    assert "RESUME" in evidence.actions
    resume_stats = evidence.actions["RESUME"]
    assert resume_stats.attempted == 4
    assert resume_stats.verified_success == 2
    assert resume_stats.verified_failure == 1
    assert resume_stats.success_rate == 2/3
    assert resume_stats.trust_score == 2/3
    assert resume_stats.risk_level == "MEDIUM"
    
    keep_paused_stats = evidence.actions["KEEP_PAUSED"]
    assert keep_paused_stats.attempted == 1
    assert keep_paused_stats.verified_success == 1
    assert keep_paused_stats.verified_failure == 0
    assert keep_paused_stats.success_rate == 1.0
    assert keep_paused_stats.trust_score == 0.0  # <3 attempts means 0.0 trust
    assert keep_paused_stats.risk_level == "UNKNOWN"

@patch('cortexheal.learning.trust.get_outcomes_for_pattern')
@patch('cortexheal.learning.ranking.SUPPORTED_CAPABILITIES', {"cortex": ["RESUME"]})
def test_ranking_engine(mock_get_outcomes):
    mock_get_outcomes.return_value = [
        RecoveryOutcome(run_id="r1", incident_id="i1", pattern_id="p1", action_type="RESUME", execution_result="EXECUTED", verification_result="VERIFIED_SUCCESS"),
        RecoveryOutcome(run_id="r2", incident_id="i2", pattern_id="p1", action_type="RESUME", execution_result="EXECUTED", verification_result="VERIFIED_SUCCESS"),
        RecoveryOutcome(run_id="r3", incident_id="i3", pattern_id="p1", action_type="RESUME", execution_result="EXECUTED", verification_result="VERIFIED_SUCCESS"),
        RecoveryOutcome(run_id="r4", incident_id="i4", pattern_id="p1", action_type="KEEP_PAUSED", execution_result="EXECUTED", verification_result="VERIFIED_SUCCESS"),
        RecoveryOutcome(run_id="r5", incident_id="i5", pattern_id="p1", action_type="KEEP_PAUSED", execution_result="EXECUTED", verification_result="VERIFIED_SUCCESS"),
        RecoveryOutcome(run_id="r6", incident_id="i6", pattern_id="p1", action_type="KEEP_PAUSED", execution_result="EXECUTED", verification_result="VERIFIED_SUCCESS"),
    ]
    
    pattern = PatternRecord(
        pattern_id="p1",
        framework="cortex",
        agent_id="agent-456",
        failure_type="STUCK_LOOP",
        fingerprint="v1-xyz",
        fingerprint_version="v1"
    )
    
    engine = RankingEngine()
    recommendations = engine.rank_actions(pattern)
    
    # KEEP_PAUSED is filtered out as it's not in the mock SUPPORTED_CAPABILITIES
    assert len(recommendations) == 1
    assert recommendations[0].action_type == "RESUME"
    assert recommendations[0].trust_level == "HIGH"
