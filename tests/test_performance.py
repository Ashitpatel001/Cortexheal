import pytest
import time
from cortexheal.runtime.hashing import deterministic_hash

def test_hashing_performance():
    # Test serialization cost on a moderately large object
    large_obj = {
        "messages": [{"role": "user", "content": "hello"} for _ in range(100)],
        "metadata": {"session_id": "12345", "user_id": "67890"},
        "nested": [[1, 2, 3], [4, 5, 6]] * 10
    }
    
    start_time = time.time()
    for _ in range(1000):
        deterministic_hash(large_obj)
    end_time = time.time()
    
    duration = end_time - start_time
    avg_ms = (duration / 1000) * 1000
    
    # Hashing should be fast (< 2ms on average for a moderate object)
    print(f"Average deterministic hash time: {avg_ms:.2f} ms")
    assert avg_ms < 5.0
