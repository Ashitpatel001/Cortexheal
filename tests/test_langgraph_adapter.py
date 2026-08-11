import pytest
import time
from unittest.mock import patch, MagicMock

from cortexheal.adapters.langgraph import CortexHealLangGraphCallback
from langchain_core.outputs import LLMResult, Generation
from cortexheal.models.events import RuntimeEvent

@pytest.fixture
def callback():
    return CortexHealLangGraphCallback(agent_id="test_agent")

@patch('cortexheal.adapters.langgraph.collector')
def test_on_chain_start_emits_run_started(mock_collector, callback):
    callback.on_chain_start({}, {})
    assert mock_collector.ingest_event.call_count == 1
    event = mock_collector.ingest_event.call_args[0][0]
    assert event.event_type == 'RUN_STARTED'
    assert event.sequence_number == 1

@patch('cortexheal.adapters.langgraph.collector')
def test_on_llm_cycle(mock_collector, callback):
    callback._ensure_run_started()
    mock_collector.reset_mock()
    
    # LLM Start
    callback.on_llm_start({}, ["Test prompt"], run_id="llm1")
    assert mock_collector.ingest_event.call_count == 1
    start_event = mock_collector.ingest_event.call_args[0][0]
    assert start_event.event_type == 'LLM_CALL_STARTED'
    assert start_event.sequence_number == 1
    
    # LLM End
    time.sleep(0.01)
    llm_result = LLMResult(
        generations=[[Generation(text="Test response")]],
        llm_output={"token_usage": {"total_tokens": 10, "prompt_tokens": 5, "completion_tokens": 5}}
    )
    callback.on_llm_end(llm_result, run_id="llm1")
    
    assert mock_collector.ingest_event.call_count == 2
    end_event = mock_collector.ingest_event.call_args[0][0]
    assert end_event.event_type == 'LLM_CALL_COMPLETED'
    assert end_event.tokens.total == 10
    assert end_event.latency_ms is not None
    assert end_event.latency_ms > 0

@patch('cortexheal.adapters.langgraph.collector')
def test_fail_open_telemetry(mock_collector, callback):
    # Simulate Postgres failure by making ingest_event raise Exception
    mock_collector.ingest_event.side_effect = Exception("DB Connection Failed")
    
    # This should NOT raise an exception, allowing the agent to continue
    try:
        callback.on_chain_start({}, {})
        passed = True
    except Exception:
        passed = False
        
    assert passed == True
