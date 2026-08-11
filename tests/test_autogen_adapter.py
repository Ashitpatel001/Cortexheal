import pytest
from unittest.mock import patch, MagicMock
from cortexheal.adapters.autogen import AutoGenAdapter, AutoGenSafetyGate

def test_autogen_adapter_initialization():
    adapter = AutoGenAdapter("agent1")
    assert adapter.framework_name == "AutoGen"
    assert adapter.agent_id == "agent1"
    
@patch('cortexheal.adapters.autogen.collector')
def test_autogen_telemetry(mock_collector):
    adapter = AutoGenAdapter("agent1")
    telemetry = adapter.get_telemetry_callback()
    
    # RUN Start
    run_id = telemetry.start_run("test_run")
    assert run_id == "test_run"
    assert mock_collector.ingest_event.call_count == 1
    event = mock_collector.ingest_event.call_args[0][0]
    assert event.event_type == "RUN_STARTED"
    assert event.run_id == "test_run"
    
    # LLM Start
    msg_id = telemetry.on_llm_start([{"role": "user", "content": "hi"}])
    assert mock_collector.ingest_event.call_count == 2
    event2 = mock_collector.ingest_event.call_args[0][0]
    assert event2.event_type == "LLM_CALL_STARTED"
    
    # LLM End
    telemetry.on_llm_end(msg_id, "hello")
    assert mock_collector.ingest_event.call_count == 3
    event3 = mock_collector.ingest_event.call_args[0][0]
    assert event3.event_type == "LLM_CALL_COMPLETED"

@patch('cortexheal.storage.postgres.get_run')
@patch('cortexheal.storage.postgres.update_run_status')
@patch('cortexheal.storage.postgres.save_audit_event')
@patch('cortexheal.storage.postgres.update_run_protection_mode')
def test_autogen_safety_gate_pause(mock_update_mode, mock_audit, mock_update, mock_get_run):
    gate = AutoGenSafetyGate("run1")
    
    class MockRun:
        protection_mode = 'ACTIVE'
        status = 'pause_requested'
        
    mock_get_run.return_value = MockRun()
    
    # AutoGen throws InterruptedError when paused
    with pytest.raises(InterruptedError, match="Paused by CortexHeal"):
        gate("msg", "sender", "recipient", False)
        
    mock_update.assert_called_with("run1", "paused")
    assert mock_audit.call_count == 1
