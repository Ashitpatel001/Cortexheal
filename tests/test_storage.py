import pytest
import pytest
from unittest.mock import patch, MagicMock

from cortexheal.models.events import RuntimeEvent
from cortexheal.models.run import AgentRun
from cortexheal.storage.postgres import save_run, save_event, get_run, get_events_for_run

@pytest.fixture(autouse=True)
def mock_db():
    with patch('cortexheal.storage.postgres.get_connection') as mock_conn:
        yield mock_conn

def test_save_and_get_run(mock_db):
    mock_conn = MagicMock()
    mock_db.return_value.__enter__.return_value = mock_conn
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    
    run_id = "test_run_123"
    run = AgentRun(framework="langgraph", run_id=run_id, agent_id="agent_1")

    # Test saving (should not raise)
    save_run(run)
    assert mock_cur.execute.call_count > 0

    # Test getting (mocking fetchone)
    mock_cur.fetchone.return_value = {
        "run_id": run_id, "agent_id": "agent_1", "status": "running", "framework": "langgraph"
    }
    retrieved = get_run(run_id)
    assert retrieved.run_id == run_id
    assert retrieved.status == "running"

def test_save_and_get_events(mock_db):
    mock_conn = MagicMock()
    mock_db.return_value.__enter__.return_value = mock_conn
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    
    run_id = "test_run_456"

    event1 = RuntimeEvent(framework="langgraph",
        run_id=run_id,
        agent_id="agent_2",
        event_type="RUN_STARTED",
        status="success",
        sequence_number=1,
        idempotency_key="event1_idem"
    )

    # Test saving
    mock_cur.rowcount = 1
    assert save_event(event1) == True

    # Test deduplication
    mock_cur.rowcount = 0
    assert save_event(event1) == False

    # Test getting
    mock_cur.fetchall.return_value = [
        {"run_id": run_id, "agent_id": "agent_2", "event_id": event1.event_id, "event_type": "RUN_STARTED", "status": "success", "sequence_number": 1, "idempotency_key": "event1_idem", "framework": "langgraph"}
    ]
    events = get_events_for_run(run_id)
    assert len(events) == 1
    assert events[0].sequence_number == 1
