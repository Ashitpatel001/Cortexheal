import pytest
from unittest.mock import patch, MagicMock
from cortexheal.runtime.collector import collector
from cortexheal.models.events import RuntimeEvent, TokenUsage
from cortexheal.models.run import AgentRun

@patch('cortexheal.runtime.collector.get_run')
@patch('cortexheal.runtime.collector.save_run')
@patch('cortexheal.runtime.collector.save_event')
def test_collector_ingest_event(mock_save_event, mock_save_run, mock_get_run):
    # Mock run not existing yet
    mock_get_run.return_value = None
    
    event = RuntimeEvent(framework="langgraph", 
        run_id="run_1",
        agent_id="agent_1",
        event_type="LLM_CALL_COMPLETED",
        status="success",
        sequence_number=1,
        idempotency_key="id_1",
        tokens=TokenUsage(total=15, prompt=10, completion=5),
        cost=0.02
    )
    
    collector.ingest_event(event)
    collector._queue.join()
    
    # Assert run was created and saved twice (creation + update)
    assert mock_save_run.call_count == 2
    saved_run = mock_save_run.call_args[0][0]
    assert saved_run.total_tokens == 15
    assert saved_run.total_cost == 0.02
    
    # Assert event was saved
    assert mock_save_event.call_count == 1
    assert mock_save_event.call_args[0][0] == event

@patch('cortexheal.runtime.collector.get_run')
@patch('cortexheal.runtime.collector.save_run')
@patch('cortexheal.runtime.collector.save_event')
def test_collector_run_completed(mock_save_event, mock_save_run, mock_get_run):
    existing_run = AgentRun(framework="langgraph", run_id="run_1", agent_id="agent_1", status="running")
    mock_get_run.return_value = existing_run
    
    event = RuntimeEvent(framework="langgraph", 
        run_id="run_1",
        agent_id="agent_1",
        event_type="RUN_COMPLETED",
        status="success",
        sequence_number=2,
        idempotency_key="id_2",
    )
    
    collector.ingest_event(event)
    collector._queue.join()
    
    saved_run = mock_save_run.call_args[0][0]
    assert saved_run.status == "completed"
    assert saved_run.end_time is not None
