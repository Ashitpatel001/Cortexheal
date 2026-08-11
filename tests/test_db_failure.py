import pytest
import time
from unittest.mock import patch, MagicMock
from cortexheal.runtime.collector import RuntimeCollector
from cortexheal.models.events import RuntimeEvent
from cortexheal.telemetry import metrics

def test_telemetry_backpressure_and_db_failure():
    # Create a collector with a tiny queue for testing
    collector = RuntimeCollector(max_queue_size=5)
    
    # Mock sync_process_event to simulate DB failure
    with patch.object(collector, '_sync_process_event', side_effect=Exception("DB Unreachable")):
        # 1. Test queue fills up but doesn't block
        for i in range(10):
            event = RuntimeEvent(framework="langgraph", run_id="r1", agent_id="a1", event_type="RUN_STARTED", status="success", sequence_number=i, idempotency_key=f"k{i}")
            collector.ingest_event(event)
        
        # Wait for the background worker to try processing
        time.sleep(0.5)
        
        # DB is failing, so events will error out inside the worker, but ingest_event never blocked!
        assert metrics.events_received_total._value.get() >= 10
        
        # Wait, if sync_process_event raises an exception, the event is removed from the queue
        # Let's mock a slow DB instead
        
def test_slow_db_queue_full():
    collector = RuntimeCollector(max_queue_size=2)
    
    def slow_db(event):
        time.sleep(0.5)
        
    with patch.object(collector, '_sync_process_event', side_effect=slow_db):
        event = RuntimeEvent(framework="langgraph", run_id="r1", agent_id="a1", event_type="RUN_STARTED", status="success", sequence_number=1, idempotency_key="k1")
        
        # Enqueue 1 (gets pulled by worker immediately)
        collector.ingest_event(event)
        
        # Enqueue 2 & 3 (fills queue)
        collector.ingest_event(event)
        collector.ingest_event(event)
        
        initial_dropped = metrics.events_dropped_total._value.get()
        # Enqueue many to guarantee overflow
        for _ in range(5):
            collector.ingest_event(event)
    
        assert metrics.events_dropped_total._value.get() > initial_dropped
        
    collector.shutdown()
