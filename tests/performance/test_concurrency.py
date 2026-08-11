import time
import pytest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from cortexheal.runtime.collector import RuntimeCollector
from cortexheal.models.events import RuntimeEvent
from cortexheal.telemetry import metrics

def simulate_agent_run(run_id, num_events, collector):
    for i in range(num_events):
        collector.ingest_event(RuntimeEvent(
            framework="langgraph",
            run_id=f"run_{run_id}",
            agent_id="perf_agent",
            event_type="TOOL_CALL_COMPLETED",
            status="success",
            sequence_number=i,
            idempotency_key=f"idem_{run_id}_{i}",
            tool="tool_X"
        ))

@patch('cortexheal.runtime.collector.save_event', return_value=True)
@patch('cortexheal.runtime.collector.save_run', return_value=True)
@patch('cortexheal.runtime.collector.get_run', return_value=None)
@patch('cortexheal.detection.engine.DetectionEngine.evaluate', return_value=[])
@pytest.mark.parametrize("num_runs", [10, 50, 100])
def test_concurrent_agent_runs(mock_eval, mock_get, mock_save_run, mock_save_event, num_runs):
    collector = RuntimeCollector(max_queue_size=20000)
    events_per_run = 100
    
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=num_runs) as executor:
        for i in range(num_runs):
            executor.submit(simulate_agent_run, i, events_per_run, collector)
            
    collector._queue.join()
    collector.shutdown()
    
    duration = time.time() - start_time
    total_events = num_runs * events_per_run
    
    print(f"\n--- Concurrency: {num_runs} Runs ---")
    print(f"Total Events: {total_events}")
    print(f"Duration: {duration:.2f}s")
    print(f"Throughput: {total_events/duration:.0f} events/sec")
    
    assert mock_save_event.call_count == total_events
