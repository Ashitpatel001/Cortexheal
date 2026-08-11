import time
import pytest
import numpy as np
import tracemalloc
from cortexheal.runtime.collector import RuntimeCollector
from cortexheal.models.events import RuntimeEvent
from cortexheal.telemetry import metrics
from unittest.mock import patch

def generate_events(num_events, run_id="perf_run"):
    return [RuntimeEvent(
        framework="langgraph",
        run_id=run_id,
        agent_id="perf_agent",
        event_type="TOOL_CALL_COMPLETED",
        status="success",
        sequence_number=i,
        idempotency_key=f"idem_{i}",
        tool="tool_X"
    ) for i in range(num_events)]

def simulated_db_save(*args, **kwargs):
    time.sleep(0.001)  # 1ms latency
    return True

@patch('cortexheal.runtime.collector.save_event', side_effect=simulated_db_save)
@patch('cortexheal.runtime.collector.save_run', side_effect=simulated_db_save)
@patch('cortexheal.runtime.collector.get_run', return_value=None)
@patch('cortexheal.detection.engine.DetectionEngine.evaluate', return_value=[])
def test_queue_memory_and_overflow(mock_eval, mock_get, mock_save_run, mock_save_event):
    tracemalloc.start()
    
    # 1. Test Queue Memory at 100K events
    collector = RuntimeCollector(max_queue_size=150000)
    events_100k = generate_events(100000)
    
    for e in events_100k:
        collector.ingest_event(e)
        
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    print(f"Memory at 100K events in queue: {current_mem / 1024 / 1024:.2f} MB")
    assert current_mem < 500 * 1024 * 1024  # Ensure < 500MB
    collector.shutdown()
    
    # 2. Test Overflow Behavior
    # Use a tiny queue and block the worker so it definitely overflows
    def blocking_save(*args, **kwargs):
        time.sleep(5)
        return True
        
    with patch('cortexheal.runtime.collector.save_event', side_effect=blocking_save):
        overflow_collector = RuntimeCollector(max_queue_size=2)
        initial_dropped = metrics.events_dropped_total._value.get()
        
        # Fill the queue
        overflow_collector.ingest_event(events_100k[0])
        overflow_collector.ingest_event(events_100k[1])
        overflow_collector.ingest_event(events_100k[2])
        overflow_collector.ingest_event(events_100k[3])
        
        # Wait a tiny bit for the worker to pull one item, meaning queue has space for 1 more
        time.sleep(0.1)
        
        # Now blast 5 events, it should definitely drop at least some
        for i in range(5):
            overflow_collector.ingest_event(events_100k[i+4])
        
        assert metrics.events_dropped_total._value.get() > initial_dropped
        overflow_collector.shutdown()
    
    tracemalloc.stop()

@patch('cortexheal.runtime.collector.save_event', side_effect=simulated_db_save)
@patch('cortexheal.runtime.collector.save_run', side_effect=simulated_db_save)
@patch('cortexheal.runtime.collector.get_run', return_value=None)
@patch('cortexheal.detection.engine.DetectionEngine.evaluate', return_value=[])
@pytest.mark.parametrize("num_events", [1000, 10000])
def test_ingestion_benchmarks(mock_eval, mock_get, mock_save_run, mock_save_event, num_events):
    collector = RuntimeCollector(max_queue_size=200000)
    events = generate_events(num_events)
    
    start_time = time.time()
    for e in events:
        collector.ingest_event(e)
    sdk_end = time.time()
    
    collector._queue.join()
    db_end = time.time()
    
    collector.shutdown()
    
    sdk_duration = sdk_end - start_time
    total_duration = db_end - start_time
    throughput = num_events / total_duration
    
    print(f"\n--- {num_events} Events Benchmark ---")
    print(f"SDK Overhead: {sdk_duration:.4f}s")
    print(f"Total Time: {total_duration:.2f}s")
    print(f"Throughput: {throughput:.0f} events/sec")
    
    assert sdk_duration < (num_events / 1000) * 0.5  # Rough non-blocking requirement
