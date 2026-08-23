import time
import tracemalloc
from cortexheal.detection.engine import DetectionEngine
from cortexheal.detection.stuck_loop import Config as SLConfig
from cortexheal.models.events import RuntimeEvent

def test_performance_detector_overhead():
    engine = DetectionEngine()
    
    # Pre-generate events to isolate generation time from processing time
    # Benchmark 1,000,000 events
    event = RuntimeEvent(framework="langgraph", 
        run_id="perf_run",
        agent_id="perf_agent",
        event_type="TOOL_CALL_COMPLETED",
        status="success",
        sequence_number=1,
        idempotency_key="idem",
        tool="tool_X",
        arguments_hash="args_X",
        response_hash="resp_X",
        cost=None
    )
    
    tracemalloc.start()
    start_time = time.time()
    
    # Process 1,000,000 events
    for _ in range(1000000):
        engine.evaluate(event)
        
    end_time = time.time()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    duration = end_time - start_time
    per_event_ms = (duration / 1000000) * 1000
    peak_mb = peak / 1024 / 1024
    
    print(f"Processed 1,000,000 events in {duration:.2f} seconds")
    print(f"Per-event latency: {per_event_ms:.5f} ms")
    print(f"Peak memory usage: {peak_mb:.2f} MB")
    
    # Because it is O(1) in memory and CPU per event:
    assert per_event_ms < 0.5  # Sub-millisecond latency per event
    assert duration < 180.0  # Should be extremely fast, adjusting threshold for slow CI / VM environments
    assert peak_mb < 5.0  # Should barely use any memory since it only stores 1 entry per run_id
