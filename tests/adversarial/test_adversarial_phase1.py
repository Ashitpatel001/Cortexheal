"""
ADVERSARIAL ROBUSTNESS VALIDATION — PHASE 1: STUCK_LOOP DETECTOR
Exercises edge cases in hashing, threshold boundaries, and concurrency.
"""
import sys, os, json, hashlib, uuid, time, threading, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from cortexheal.detection.stuck_loop import StuckLoopDetector, Config
from cortexheal.detection.budget import BudgetDetector, BudgetConfig
from cortexheal.detection.engine import DetectionEngine
from cortexheal.models.events import RuntimeEvent
from cortexheal.runtime.hashing import deterministic_hash, serialize

RESULTS = []

def record(test_id, description, passed, raw_output):
    status = "PASS" if passed else "FAIL"
    RESULTS.append({"id": test_id, "desc": description, "status": status, "raw": raw_output})
    print(f"  [{status}] {test_id}: {description}")
    if not passed:
        print(f"       RAW: {raw_output[:500]}")

def make_event(run_id, tool, args_hash, resp_hash, seq=1, cost=None, event_type='TOOL_CALL_COMPLETED'):
    return RuntimeEvent(
        framework="langgraph", run_id=run_id, agent_id="test_agent",
        event_type=event_type, status="success", sequence_number=seq,
        idempotency_key=str(uuid.uuid4()), tool=tool,
        arguments_hash=args_hash, response_hash=resp_hash, cost=cost
    )

# ============================================================
# P1-1: Near-duplicate calls (single character difference)
# ============================================================
def test_p1_1_near_duplicate():
    print("\n=== P1-1: Near-duplicate calls ===")
    detector = StuckLoopDetector(Config())
    detector.config.repetition_threshold = 5
    
    # 5 calls where arguments_hash differs by 1 char each time
    results_list = []
    for i in range(5):
        args_hash = f"abc{i}def"  # abc0def, abc1def, abc2def...
        ev = make_event("near_dup_run", "search_tool", args_hash, "same_resp", seq=i+1)
        result = detector.evaluate(ev)
        results_list.append(result)
    
    # None should trigger because each args_hash differs
    triggered = [r for r in results_list if r and r.matched]
    raw = f"results={[str(r) for r in results_list]}, triggered_count={len(triggered)}"
    record("P1-1", "Near-duplicate calls (1-char diff in args_hash) should NOT trigger", 
           len(triggered) == 0, raw)

# ============================================================
# P1-2: Key-order normalization ({"a":1,"b":2} vs {"b":2,"a":1})
# ============================================================
def test_p1_2_key_order_normalization():
    print("\n=== P1-2: Key-order normalization ===")
    hash1 = deterministic_hash({"a": 1, "b": 2})
    hash2 = deterministic_hash({"b": 2, "a": 1})
    
    ser1 = serialize({"a": 1, "b": 2})
    ser2 = serialize({"b": 2, "a": 1})
    
    raw = f"hash1={hash1}, hash2={hash2}, ser1={ser1}, ser2={ser2}, equal={hash1 == hash2}"
    record("P1-2", "Key-sorted dicts should produce identical hashes",
           hash1 == hash2, raw)

# ============================================================
# P1-2b: NOTE — hashing is done by the SDK BEFORE reaching the detector.
# The detector compares pre-computed arguments_hash strings.
# So key-order normalization must happen at SDK level.
# Test whether the detector itself just compares raw hash strings.
# ============================================================
def test_p1_2b_detector_uses_prehashed():
    print("\n=== P1-2b: Detector compares pre-hashed strings ===")
    detector = StuckLoopDetector(Config())
    detector.config.repetition_threshold = 3
    
    # If SDK sends different hash strings for same semantic content, detector WON'T catch it
    results = []
    for i in range(3):
        ev = make_event("prehash_run", "tool", "HASH_A", "HASH_R", seq=i+1)
        results.append(detector.evaluate(ev))
    
    triggered = results[-1] and results[-1].matched
    raw = f"last_result={results[-1]}, triggered={triggered}"
    record("P1-2b", "Detector triggers when pre-hashed strings are identical",
           triggered, raw)
    
    # Now test: if SDK sends DIFFERENT hash strings for same semantic args, detector misses
    detector2 = StuckLoopDetector(Config())
    detector2.config.repetition_threshold = 3
    results2 = []
    for i in range(5):
        # Simulate SDK NOT normalizing key order — different hash each time
        args_hash = deterministic_hash({"key": i % 2, "val": "same"})  # alternates
        ev = make_event("prehash_miss_run", "tool", args_hash, "HASH_R", seq=i+1)
        results2.append(detector2.evaluate(ev))
    
    triggered2 = any(r and r.matched for r in results2)
    raw2 = f"results={[str(r) for r in results2]}, any_triggered={triggered2}"
    record("P1-2b-miss", "Detector MISSES loop if SDK sends alternating different hashes",
           not triggered2, raw2)

# ============================================================
# P1-3: Non-deterministic tool responses
# ============================================================
def test_p1_3_nondeterministic_responses():
    print("\n=== P1-3: Non-deterministic tool responses ===")
    detector = StuckLoopDetector(Config())
    detector.config.repetition_threshold = 5
    
    results = []
    for i in range(10):
        # Same tool & args, but response contains a UUID (non-deterministic)
        resp_hash = deterministic_hash({"result": "ok", "trace_id": str(uuid.uuid4())})
        ev = make_event("nondet_run", "search", "SAME_ARGS", resp_hash, seq=i+1)
        results.append(detector.evaluate(ev))
    
    triggered = any(r and r.matched for r in results)
    raw = f"results_count={len(results)}, any_triggered={triggered}"
    
    # This SHOULD fail to trigger because response_hash changes each time
    record("P1-3", "Non-deterministic responses prevent stuck loop detection — GAP",
           not triggered,
           raw + " | VERDICT: Detector cannot detect loops where response varies. "
           "This is a REAL GAP for the product's value proposition (agent calls same "
           "tool with same args in a loop but gets different error messages each time).")

# ============================================================
# P1-4: Hash collision / serialization weakness
# ============================================================
def test_p1_4_hash_collision():
    print("\n=== P1-4: Hash collision / serialization weaknesses ===")
    
    # 4a: float vs int
    h_int = deterministic_hash({"value": 1})
    h_float = deterministic_hash({"value": 1.0})
    ser_int = serialize({"value": 1})
    ser_float = serialize({"value": 1.0})
    raw_a = f"int_ser={ser_int}, float_ser={ser_float}, int_hash={h_int}, float_hash={h_float}, same={h_int == h_float}"
    # In Python json.dumps, 1 and 1.0 serialize differently: "1" vs "1.0"
    record("P1-4a", "int(1) vs float(1.0) produce different hashes (potential false negative)",
           h_int != h_float,
           raw_a + " | If an API returns 1 as int sometimes and 1.0 as float other times, "
           "the hashes will differ, breaking loop detection.")
    
    # 4b: Unicode normalization (é vs e + combining acute)
    h_nfc = deterministic_hash({"name": "\u00e9"})  # precomposed é
    h_nfd = deterministic_hash({"name": "e\u0301"})  # decomposed e + combining acute
    ser_nfc = serialize({"name": "\u00e9"})
    ser_nfd = serialize({"name": "e\u0301"})
    raw_b = f"nfc_ser={repr(ser_nfc)}, nfd_ser={repr(ser_nfd)}, nfc_hash={h_nfc}, nfd_hash={h_nfd}, same={h_nfc == h_nfd}"
    record("P1-4b", "Unicode NFC vs NFD produce different hashes (potential false negative)",
           h_nfc != h_nfd,
           raw_b + " | No unicode normalization is applied before hashing.")
    
    # 4c: Nested dict key order
    h1 = deterministic_hash({"outer": {"z": 1, "a": 2}})
    h2 = deterministic_hash({"outer": {"a": 2, "z": 1}})
    raw_c = f"h1={h1}, h2={h2}, same={h1 == h2}"
    record("P1-4c", "Nested dict key order is normalized (good)",
           h1 == h2, raw_c)
    
    # 4d: Boolean vs int collision
    h_true = deterministic_hash({"flag": True})
    h_one = deterministic_hash({"flag": 1})
    ser_true = serialize({"flag": True})
    ser_one = serialize({"flag": 1})
    raw_d = f"true_ser={ser_true}, one_ser={ser_one}, true_hash={h_true}, one_hash={h_one}, same={h_true == h_one}"
    record("P1-4d", "Boolean True vs int 1 hash collision check",
           True,  # Just recording the result
           raw_d)

# ============================================================
# P1-5: Threshold boundary testing
# ============================================================
def test_p1_5_threshold_boundary():
    print("\n=== P1-5: Threshold boundary ===")
    
    # 5a: threshold-1 should NOT trigger
    detector = StuckLoopDetector(Config())
    detector.config.repetition_threshold = 5
    results_4 = []
    for i in range(4):
        ev = make_event("boundary_run_4", "tool_x", "args_x", "resp_x", seq=i+1)
        results_4.append(detector.evaluate(ev))
    triggered_4 = any(r and r.matched for r in results_4)
    raw_4 = f"4_reps: triggered={triggered_4}, results={[str(r) for r in results_4]}"
    record("P1-5a", "threshold-1 (4) repetitions should NOT trigger",
           not triggered_4, raw_4)
    
    # 5b: exact threshold SHOULD trigger
    detector2 = StuckLoopDetector(Config())
    detector2.config.repetition_threshold = 5
    results_5 = []
    for i in range(5):
        ev = make_event("boundary_run_5", "tool_x", "args_x", "resp_x", seq=i+1)
        results_5.append(detector2.evaluate(ev))
    triggered_5 = results_5[-1] and results_5[-1].matched
    raw_5 = f"5_reps: last_triggered={triggered_5}, results={[str(r) for r in results_5]}"
    record("P1-5b", "exact threshold (5) repetitions SHOULD trigger",
           triggered_5, raw_5)
    
    # 5c: threshold+50 rapid-fire — should not crash, double-fire, or create issues
    detector3 = StuckLoopDetector(Config())
    detector3.config.repetition_threshold = 5
    results_55 = []
    for i in range(55):
        ev = make_event("boundary_run_55", "tool_x", "args_x", "resp_x", seq=i+1)
        results_55.append(detector3.evaluate(ev))
    
    triggered_count = sum(1 for r in results_55 if r and r.matched)
    # Every call from 5 onward should trigger (count starts at 5th)
    raw_55 = f"55_reps: trigger_count={triggered_count}, expected=51 (reps 5..55)"
    record("P1-5c", "threshold+50 rapid-fire does not crash and triggers consistently",
           triggered_count == 51, raw_55)
    
    # 5d: Check deduplication in DetectionEngine (only 1 incident, not 51)
    # NOTE: DetectionEngine deduplicates via _emitted dict
    print("  [INFO] P1-5d: DetectionEngine dedup check...")
    engine = DetectionEngine()
    engine.detectors[0].config.repetition_threshold = 3
    incidents_all = []
    for i in range(20):
        ev = make_event("dedup_run", "tool_x", "args_x", "resp_x", seq=i+1)
        incidents = engine.evaluate(ev)
        incidents_all.extend(incidents)
    
    raw_dedup = f"total_incidents_returned={len(incidents_all)}, expected=1"
    record("P1-5d", "DetectionEngine should return only 1 incident for repeated triggers (dedup)",
           len(incidents_all) == 1, raw_dedup)

# ============================================================
# P1-6: Concurrent runs
# ============================================================
def test_p1_6_concurrent_runs():
    print("\n=== P1-6: Concurrent runs (20 simultaneous) ===")
    detector = StuckLoopDetector(Config())
    detector.config.repetition_threshold = 3
    
    errors = []
    results_by_run = {}
    lock = threading.Lock()
    
    def run_agent(run_idx):
        try:
            run_id = f"concurrent_run_{run_idx}"
            local_results = []
            for i in range(5):
                ev = make_event(run_id, "tool_x", "args_x", "resp_x", seq=i+1)
                result = detector.evaluate(ev)
                local_results.append(result)
            with lock:
                results_by_run[run_id] = local_results
        except Exception as e:
            with lock:
                errors.append(f"run_{run_idx}: {traceback.format_exc()}")
    
    threads = [threading.Thread(target=run_agent, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    
    # Check: each run should have triggered independently
    trigger_counts = {}
    for run_id, results in results_by_run.items():
        trigger_counts[run_id] = sum(1 for r in results if r and r.matched)
    
    # Each run has 5 events with threshold 3, so triggers at event 3,4,5 = 3 triggers
    all_correct = all(c == 3 for c in trigger_counts.values())
    
    raw = (f"runs_completed={len(results_by_run)}, errors={errors}, "
           f"trigger_counts={trigger_counts}")
    
    if errors:
        record("P1-6", "Concurrent runs: no errors", False, raw)
    elif not all_correct:
        record("P1-6", "Concurrent runs: each run triggers independently", False, raw)
    else:
        record("P1-6", "Concurrent runs: 20 runs, each triggers at threshold, no cross-contamination", 
               True, raw)

    # Check for cross-contamination in internal state
    state_runs = set(detector._state.keys())
    expected_runs = {f"concurrent_run_{i}" for i in range(20)}
    cross = state_runs - expected_runs
    raw_cross = f"state_keys={state_runs}, unexpected={cross}"
    record("P1-6b", "No cross-contamination in detector state", len(cross) == 0, raw_cross)

# ============================================================
# PHASE 2: BUDGET DETECTOR
# ============================================================
def test_p2_1_concurrent_cost():
    print("\n=== P2-1: Concurrent cost accumulation ===")
    detector = BudgetDetector(BudgetConfig())
    detector.config.max_cost_usd = 1.00
    
    errors = []
    trigger_count = [0]
    lock = threading.Lock()
    
    def add_cost(thread_idx):
        try:
            for i in range(100):
                ev = make_event(
                    "budget_concurrent", "tool", "args", "resp", 
                    seq=thread_idx*100+i+1, cost=0.001
                )
                result = detector.evaluate(ev)
                if result and result.matched:
                    with lock:
                        trigger_count[0] += 1
        except Exception as e:
            with lock:
                errors.append(traceback.format_exc())
    
    threads = [threading.Thread(target=add_cost, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    
    final_cost = detector._cumulative.get("budget_concurrent", 0)
    expected = 10 * 100 * 0.001  # 1.0
    
    raw = (f"final_cost={final_cost}, expected={expected}, "
           f"trigger_count={trigger_count[0]}, errors={errors}")
    
    # Due to race conditions in += on float, cost may be wrong
    is_exact = abs(final_cost - expected) < 0.0001
    record("P2-1", f"Concurrent cost accumulation: final={final_cost:.6f} vs expected={expected:.6f}",
           is_exact, raw + 
           " | BudgetDetector._cumulative uses unsynchronized dict+=. "
           "Under GIL this MAY work but is not guaranteed correct.")

def test_p2_2_negative_zero_missing_cost():
    print("\n=== P2-2: Negative, zero, missing, and malformed cost ===")
    detector = BudgetDetector(BudgetConfig())
    detector.config.max_cost_usd = 1.00
    
    # 2a: None cost
    ev_none = make_event("cost_none", "tool", "args", "resp", seq=1, cost=None)
    result_none = detector.evaluate(ev_none)
    raw_none = f"cost=None, result={result_none}, cumulative={detector._cumulative.get('cost_none', 'not_set')}"
    record("P2-2a", "None cost is skipped (not accumulated)", 
           result_none is None, raw_none)
    
    # 2b: Zero cost
    ev_zero = make_event("cost_zero", "tool", "args", "resp", seq=1, cost=0.0)
    result_zero = detector.evaluate(ev_zero)
    cumulative_zero = detector._cumulative.get("cost_zero", "not_set")
    raw_zero = f"cost=0.0, result={result_zero}, cumulative={cumulative_zero}"
    record("P2-2b", "Zero cost is accumulated but should not trigger",
           result_zero is None and cumulative_zero == 0.0, raw_zero)
    
    # 2c: Negative cost — should now be REJECTED by Pydantic ge=0.0 constraint
    try:
        ev_neg = make_event("cost_neg", "tool", "args", "resp", seq=1, cost=-0.50)
        # If we get here, validation didn't catch it
        result_neg = detector.evaluate(ev_neg)
        cumulative_neg = detector._cumulative.get("cost_neg", "not_set")
        raw_neg = f"cost=-0.50, result={result_neg}, cumulative={cumulative_neg}"
        record("P2-2c", "Negative cost is rejected (FIXED)",
               False,
               raw_neg + " | BUG STILL PRESENT: negative cost was accepted")
    except Exception as e:
        raw_neg = f"Pydantic correctly rejected negative cost: {type(e).__name__}: {e}"
        record("P2-2c", "Negative cost is rejected by Pydantic validation (FIXED)",
               True, raw_neg)
    
    # 2d: String cost — will Pydantic reject it?
    try:
        ev_str = make_event("cost_str", "tool", "args", "resp", seq=1, cost="not_a_number")
        raw_str = f"Pydantic ACCEPTED string cost! event.cost={ev_str.cost}"
        record("P2-2d", "String cost should be rejected by Pydantic validation",
               False, raw_str)
    except Exception as e:
        raw_str = f"Pydantic correctly rejected string cost: {type(e).__name__}: {e}"
        record("P2-2d", "String cost rejected by Pydantic validation", True, raw_str)

def test_p2_3_threshold_boundary():
    print("\n=== P2-3: Budget threshold boundary ===")
    
    # 3a: One cent under
    detector_under = BudgetDetector(BudgetConfig())
    detector_under.config.max_cost_usd = 1.00
    ev_under = make_event("budget_under", "tool", "args", "resp", seq=1, cost=0.99)
    result_under = detector_under.evaluate(ev_under)
    raw_under = f"cost=0.99, threshold=1.00, result={result_under}"
    record("P2-3a", "Cost $0.99 (1 cent under $1.00 threshold) should NOT trigger",
           result_under is None, raw_under)
    
    # 3b: Exact threshold
    detector_exact = BudgetDetector(BudgetConfig())
    detector_exact.config.max_cost_usd = 1.00
    ev_exact = make_event("budget_exact", "tool", "args", "resp", seq=1, cost=1.00)
    result_exact = detector_exact.evaluate(ev_exact)
    triggered_exact = result_exact and result_exact.matched
    raw_exact = f"cost=1.00, threshold=1.00, result={result_exact}, triggered={triggered_exact}"
    record("P2-3b", "Cost exactly at $1.00 threshold SHOULD trigger (uses >=)",
           triggered_exact, raw_exact)
    
    # 3c: One cent over
    detector_over = BudgetDetector(BudgetConfig())
    detector_over.config.max_cost_usd = 1.00
    ev_over = make_event("budget_over", "tool", "args", "resp", seq=1, cost=1.01)
    result_over = detector_over.evaluate(ev_over)
    triggered_over = result_over and result_over.matched
    raw_over = f"cost=1.01, threshold=1.00, result={result_over}, triggered={triggered_over}"
    record("P2-3c", "Cost $1.01 (1 cent over threshold) SHOULD trigger",
           triggered_over, raw_over)

# ============================================================
# PHASE 3: LIFECYCLE STATE MACHINE ABUSE
# ============================================================
def test_p3_1_double_approve():
    print("\n=== P3-1: Double approve ===")
    from cortexheal.recovery.executor import RecoveryExecutor
    from cortexheal.models.recovery import RecoveryPlan, RecoveryAction
    from unittest.mock import patch, MagicMock
    from cortexheal.models.run import AgentRun
    
    executor = RecoveryExecutor()
    plan = RecoveryPlan(
        incident_id="inc_double", run_id="run_double", diagnosis="test",
        proposed_actions=[RecoveryAction(run_id="run_double", incident_id="inc_double", 
                                         action_type="RESUME", reason="test")],
        snapshot_run_status="paused", snapshot_sequence_number=0, status="PROPOSED"
    )
    
    mock_run = AgentRun(framework="langgraph", run_id="run_double", agent_id="a1",
                        status="paused", start_time="2026-01-01T00:00:00Z",
                        last_updated="2026-01-01T00:00:00Z")
    
    with patch('cortexheal.recovery.executor.get_run', return_value=mock_run), \
         patch('cortexheal.recovery.executor.get_events_for_run', return_value=[]), \
         patch('cortexheal.recovery.executor.save_recovery_plan'), \
         patch('cortexheal.recovery.executor.save_recovery_action'), \
         patch('cortexheal.recovery.executor.save_audit_event'), \
         patch('cortexheal.recovery.executor.save_recovery_outcome'), \
         patch('cortexheal.recovery.executor.get_incident', return_value=MagicMock()), \
         patch('cortexheal.recovery.executor.ProtectionController') as mock_pc:
        
        # First approve
        result1 = executor.execute_plan(plan, "OPERATOR", "user1")
        status_after_first = plan.status
        
        # Second approve — plan.status is now COMPLETED, not PROPOSED
        result2 = executor.execute_plan(plan, "OPERATOR", "user1")
        status_after_second = plan.status
    
    raw = (f"first_approve={result1}, status_after_first={status_after_first}, "
           f"second_approve={result2}, status_after_second={status_after_second}")
    record("P3-1", "Double approve: second approve returns False (plan not PROPOSED)",
           result1 == True and result2 == False, raw)

def test_p3_3_resume_not_paused():
    print("\n=== P3-3: Resume a run that was never paused ===")
    from cortexheal.protection.controller import ProtectionController
    from cortexheal.models.run import AgentRun
    from unittest.mock import patch, MagicMock
    
    pc = ProtectionController()
    mock_run = AgentRun(framework="langgraph", run_id="run_never_paused", agent_id="a1",
                        status="running", start_time="2026-01-01T00:00:00Z",
                        last_updated="2026-01-01T00:00:00Z")
    
    with patch('cortexheal.protection.controller.get_run', return_value=mock_run) as mock_get, \
         patch('cortexheal.protection.controller.save_audit_event') as mock_audit, \
         patch('cortexheal.protection.controller.update_run_status') as mock_update:
        
        pc.resume("run_never_paused", actor_id="user1")
        
        # Should NOT call update_run_status because status is 'running'
        update_called = mock_update.called
        audit_called = mock_audit.called
        
        if audit_called:
            audit_args = mock_audit.call_args
            audit_event = audit_args[0][0] if audit_args[0] else None
            audit_result = audit_event.result if audit_event else "unknown"
        else:
            audit_result = "not_called"
    
    raw = f"update_called={update_called}, audit_called={audit_called}, audit_result={audit_result}"
    record("P3-3", "Resume non-paused run: should not call update, should log IDEMPOTENT",
           not update_called and audit_result == "IDEMPOTENT", raw)

def test_p3_6_resume_nonexistent():
    print("\n=== P3-6: Resume non-existent run ===")
    from cortexheal.protection.controller import ProtectionController
    from unittest.mock import patch
    
    pc = ProtectionController()
    
    with patch('cortexheal.protection.controller.get_run', return_value=None) as mock_get, \
         patch('cortexheal.protection.controller.save_audit_event') as mock_audit, \
         patch('cortexheal.protection.controller.update_run_status') as mock_update:
        
        # Should silently return without updating or auditing
        pc.resume("DOES_NOT_EXIST_12345", actor_id="user1")
        
        update_called = mock_update.called
        audit_called = mock_audit.called
    
    raw = f"update_called={update_called}, audit_called={audit_called}"
    # BUG: resume silently returns None without any audit when run doesn't exist
    record("P3-6", "Resume non-existent run: silently returns (no error, no audit log)",
           not update_called and not audit_called,
           raw + " | BUG: No feedback to caller. The API returns 404 but the "
           "controller itself silently swallows the missing run.")

def test_p3_7_concurrent_resume():
    print("\n=== P3-7: 100 concurrent resume requests ===")
    from cortexheal.protection.controller import ProtectionController
    from cortexheal.models.run import AgentRun
    from unittest.mock import patch, MagicMock
    
    update_count = [0]
    lock = threading.Lock()
    
    def mock_update_status(run_id, status):
        with lock:
            update_count[0] += 1
        return True
    
    mock_run = AgentRun(framework="langgraph", run_id="concurrent_resume", agent_id="a1",
                        status="paused", start_time="2026-01-01T00:00:00Z",
                        last_updated="2026-01-01T00:00:00Z")
    
    errors = []
    
    def do_resume(idx):
        try:
            pc = ProtectionController()
            with patch('cortexheal.protection.controller.get_run', return_value=mock_run), \
                 patch('cortexheal.protection.controller.update_run_status', side_effect=mock_update_status), \
                 patch('cortexheal.protection.controller.save_audit_event'):
                pc.resume("concurrent_resume", actor_id=f"user_{idx}")
        except Exception as e:
            with lock:
                errors.append(traceback.format_exc())
    
    threads = [threading.Thread(target=do_resume, args=(i,)) for i in range(100)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    
    raw = f"update_count={update_count[0]}, errors={len(errors)}, error_samples={errors[:3]}"
    # BUG: All 100 see status='paused' and ALL call update_run_status.
    # There's no lock or CAS operation. This is a TOCTOU race.
    record("P3-7", f"100 concurrent resumes: {update_count[0]} updates executed (expected 1, got {update_count[0]})",
           update_count[0] == 1,
           raw + " | BUG: TOCTOU race — get_run() returns 'paused' for all 100 threads, "
           "so all 100 call update_run_status. No atomic compare-and-swap.")

# ============================================================
# RUN ALL TESTS
# ============================================================
if __name__ == "__main__":
    print("=" * 70)
    print("ADVERSARIAL ROBUSTNESS VALIDATION — PHASES 1-3")
    print("=" * 70)
    
    test_p1_1_near_duplicate()
    test_p1_2_key_order_normalization()
    test_p1_2b_detector_uses_prehashed()
    test_p1_3_nondeterministic_responses()
    test_p1_4_hash_collision()
    test_p1_5_threshold_boundary()
    test_p1_6_concurrent_runs()
    test_p2_1_concurrent_cost()
    test_p2_2_negative_zero_missing_cost()
    test_p2_3_threshold_boundary()
    test_p3_1_double_approve()
    test_p3_3_resume_not_paused()
    test_p3_6_resume_nonexistent()
    test_p3_7_concurrent_resume()
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passes = sum(1 for r in RESULTS if r["status"] == "PASS")
    fails = sum(1 for r in RESULTS if r["status"] == "FAIL")
    print(f"PASS: {passes}  FAIL: {fails}  TOTAL: {len(RESULTS)}")
    print()
    for r in RESULTS:
        print(f"  [{r['status']}] {r['id']}: {r['desc']}")
    
    # Write raw results to file
    with open("adversarial_p1_p3_raw.json", "w") as f:
        json.dump(RESULTS, f, indent=2, default=str)
    
    print(f"\nRaw results written to adversarial_p1_p3_raw.json")
