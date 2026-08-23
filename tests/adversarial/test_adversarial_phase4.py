"""
ADVERSARIAL ROBUSTNESS VALIDATION — PHASE 4: API/AUTH, PHASE 5: SSE, PHASE 6: CHAOS
Uses FastAPI TestClient (no live server needed).
"""
import sys, os, json, uuid, time, threading, traceback, asyncio, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from unittest.mock import patch, MagicMock
from cortexheal.models.run import AgentRun
from cortexheal.models.incident import Incident
from cortexheal.models.recovery import RecoveryPlan, RecoveryAction

MOCK_RUNS = {
    "run_1": AgentRun(framework="langgraph", run_id="run_1", agent_id="agent1",
                      status="paused", start_time="2026-01-01T00:00:00Z",
                      last_updated="2026-01-01T00:00:00Z"),
    "run_2": AgentRun(framework="langgraph", run_id="run_2", agent_id="agent1",
                      status="running", start_time="2026-01-01T00:00:00Z",
                      last_updated="2026-01-01T00:00:00Z"),
}

MOCK_INCIDENTS = [
    Incident(run_id="run_1", agent_id="agent1", failure_type="STUCK_LOOP",
             severity="CRITICAL", status="OPEN", detector="stuck_loop_detector",
             detector_version="1.0", trigger_event_id="ev1",
             evidence={"tool": "search"}, observed_value=5, threshold=5,
             description="Stuck loop detected")
]
MOCK_PLANS = {}

def mock_get_run(run_id): return MOCK_RUNS.get(run_id)
def mock_get_all_runs(): return list(MOCK_RUNS.values())
def mock_get_incidents(): return MOCK_INCIDENTS
def mock_get_incident(incident_id):
    return next((i for i in MOCK_INCIDENTS if i.incident_id == incident_id), None)
def mock_get_events(run_id): return []
def mock_get_audits(run_id): return []
def mock_get_plan(incident_id): return MOCK_PLANS.get(incident_id)
def mock_save_plan(plan): MOCK_PLANS[plan.incident_id] = plan
def mock_noop(*args, **kwargs): return True

patches = [
    patch('cortexheal.server.api.get_run', side_effect=mock_get_run),
    patch('cortexheal.server.api.get_all_runs', side_effect=mock_get_all_runs),
    patch('cortexheal.server.api.get_incidents', side_effect=mock_get_incidents),
    patch('cortexheal.server.api.get_incident', side_effect=mock_get_incident),
    patch('cortexheal.server.api.get_events_for_run', side_effect=mock_get_events),
    patch('cortexheal.server.api.get_audit_events_for_run', side_effect=mock_get_audits),
    patch('cortexheal.server.api.get_recovery_plan_by_incident', side_effect=mock_get_plan),
    patch('cortexheal.protection.controller.get_run', side_effect=mock_get_run),
    patch('cortexheal.protection.controller.update_run_status', side_effect=mock_noop),
    patch('cortexheal.protection.controller.save_audit_event', side_effect=mock_noop),
    patch('cortexheal.recovery.executor.get_run', side_effect=mock_get_run),
    patch('cortexheal.recovery.executor.get_events_for_run', side_effect=mock_get_events),
    patch('cortexheal.recovery.executor.get_incident', side_effect=lambda i: mock_get_incident(i)),
    patch('cortexheal.recovery.executor.save_recovery_plan', side_effect=mock_save_plan),
    patch('cortexheal.recovery.executor.save_recovery_action', side_effect=mock_noop),
    patch('cortexheal.recovery.executor.save_audit_event', side_effect=mock_noop),
    patch('cortexheal.recovery.executor.save_recovery_outcome', side_effect=mock_noop),
    patch('cortexheal.recovery.engine.get_recovery_plan_by_incident', side_effect=mock_get_plan),
    patch('cortexheal.recovery.engine.save_recovery_plan', side_effect=mock_save_plan),
    patch('cortexheal.recovery.engine.get_run', side_effect=mock_get_run),
    patch('cortexheal.recovery.engine.get_events_for_run', side_effect=mock_get_events),
    patch('cortexheal.recovery.engine.save_audit_event', side_effect=mock_noop),
    patch('cortexheal.recovery.policy.get_audit_events_for_run', side_effect=mock_get_audits),
    patch('cortexheal.storage.postgres.get_connection', side_effect=Exception("No DB")),
]

@pytest.fixture(scope="module", autouse=True)
def manage_patches():
    for p in patches:
        p.start()
    yield
    for p in reversed(patches):
        p.stop()

from fastapi.testclient import TestClient
from cortexheal.server.api import app, RATE_LIMIT_STORE
from cortexheal.config import settings

# Bump rate limit so tests don't interfere with each other
settings.API_RATE_LIMIT_PER_MIN = 5000

client = TestClient(app)

RESULTS = []

def record(test_id, description, passed, raw_output, verdict_type="PASS"):
    status = (verdict_type if verdict_type != "PASS" else "PASS") if passed else "FAIL"
    RESULTS.append({"id": test_id, "desc": description, "status": status, "raw": raw_output})
    print(f"  [{status}] {test_id}: {description}")
    if status == "FAIL":
        print(f"       RAW: {raw_output[:600]}")

VIEWER = settings.get_viewer_tokens()[0]
OPERATOR = settings.get_operator_tokens()[0]
ADMIN = settings.get_admin_tokens()[0]

def rl_clear():
    RATE_LIMIT_STORE.clear()

# ============================================================
# PHASE 4: API / AUTH
# ============================================================

def test_p4_1_viewer_on_mutating():
    print("\n=== P4-1: VIEWER token on mutating endpoints ===")
    rl_clear()
    inc_id = MOCK_INCIDENTS[0].incident_id
    
    r = client.post(f"/api/runs/run_1/resume", headers={"X-API-Key": VIEWER})
    raw = f"POST /api/runs/run_1/resume with VIEWER: status={r.status_code}, body={r.text}"
    record("P4-1a", "Resume with VIEWER token returns 403", r.status_code == 403, raw)
    
    # Create a plan
    from cortexheal.recovery.engine import RecoveryEngine
    plan = RecoveryEngine().generate_plan(MOCK_INCIDENTS[0])
    MOCK_PLANS[inc_id] = plan
    
    r = client.post(f"/api/incidents/{inc_id}/plan/approve", headers={"X-API-Key": VIEWER})
    raw = f"POST approve with VIEWER: status={r.status_code}, body={r.text}"
    record("P4-1b", "Approve with VIEWER token returns 403", r.status_code == 403, raw)
    
    plan.status = "PROPOSED"
    MOCK_PLANS[inc_id] = plan
    r = client.post(f"/api/incidents/{inc_id}/plan/reject", headers={"X-API-Key": VIEWER})
    raw = f"POST reject with VIEWER: status={r.status_code}, body={r.text}"
    record("P4-1c", "Reject with VIEWER token returns 403", r.status_code == 403, raw)

def test_p4_2_auth_variations():
    print("\n=== P4-2: Auth variations ===")
    rl_clear()
    
    # No token
    r = client.get("/api/runs")
    raw = f"GET /api/runs NO token: status={r.status_code}, body={r.text[:200]}"
    record("P4-2a", f"No API key returns {r.status_code} (expect 403)", r.status_code == 403, raw)
    
    # Empty token
    r = client.get("/api/runs", headers={"X-API-Key": ""})
    raw = f"GET /api/runs empty token: status={r.status_code}, body={r.text[:200]}"
    record("P4-2b", f"Empty API key returns {r.status_code} (expect 403)", r.status_code == 403, raw)
    
    # Malformed 5000-char token
    r = client.get("/api/runs", headers={"X-API-Key": "x" * 5000})
    raw = f"GET /api/runs 5000-char token: status={r.status_code}, body={r.text[:200]}"
    record("P4-2c", f"5000-char token returns {r.status_code}", r.status_code == 403, raw)
    
    # Unknown token
    r = client.get("/api/runs", headers={"X-API-Key": "unknown-key-abc"})
    raw = f"GET /api/runs unknown token: status={r.status_code}, body={r.text[:200]}"
    record("P4-2d", f"Unknown token returns {r.status_code}", r.status_code == 403, raw)

def test_p4_3_sqli():
    print("\n=== P4-3: SQL injection payloads ===")
    rl_clear()
    
    payloads = [
        "'; DROP TABLE runs; --",
        "1 OR 1=1",
        "run_1' UNION SELECT * FROM pg_catalog.pg_tables--",
    ]
    
    for i, payload in enumerate(payloads):
        r = client.get(f"/api/runs/{payload}", headers={"X-API-Key": VIEWER})
        raw = f"GET /api/runs/{payload}: status={r.status_code}, body={r.text[:200]}"
        # These run_ids don't exist in MOCK_RUNS, so should be 404
        record(f"P4-3-{i}", f"SQLi '{payload[:30]}' returns {r.status_code} (expect 404, not 500)",
               r.status_code == 404, raw)
    
    # Oversized
    big_id = "A" * 10000
    r = client.get(f"/api/runs/{big_id}", headers={"X-API-Key": VIEWER})
    raw = f"GET /api/runs/{'A'*20}...(10KB): status={r.status_code}, body={r.text[:200]}"
    record("P4-3-big", f"10KB run_id returns {r.status_code} (expect 404)",
           r.status_code == 404, raw)

def test_p4_4_pagination():
    print("\n=== P4-4: Pagination abuse ===")
    rl_clear()
    
    # Negative skip
    r = client.get("/api/runs?skip=-1", headers={"X-API-Key": VIEWER})
    raw = f"skip=-1: status={r.status_code}, body={r.text[:300]}"
    record("P4-4a", f"skip=-1 returns {r.status_code} (expect 422)", r.status_code == 422, raw)
    
    # limit > 100
    r = client.get("/api/runs?limit=999", headers={"X-API-Key": VIEWER})
    raw = f"limit=999: status={r.status_code}, body={r.text[:300]}"
    record("P4-4b", f"limit=999 returns {r.status_code} (expect 422)", r.status_code == 422, raw)
    
    # limit=0
    r = client.get("/api/runs?limit=0", headers={"X-API-Key": VIEWER})
    raw = f"limit=0: status={r.status_code}, body={r.text[:300]}"
    record("P4-4c", f"limit=0 returns {r.status_code} (expect 422)", r.status_code == 422, raw)
    
    # Non-integer skip
    r = client.get("/api/runs?skip=abc", headers={"X-API-Key": VIEWER})
    raw = f"skip=abc: status={r.status_code}, body={r.text[:300]}"
    record("P4-4d", f"skip=abc returns {r.status_code} (expect 422)", r.status_code == 422, raw)

def test_p4_5_error_shapes():
    print("\n=== P4-5: Error response shapes ===")
    rl_clear()
    
    # 403 shape
    r = client.get("/api/runs", headers={"X-API-Key": "bad-key"})
    raw = f"403 shape: {json.dumps(r.json())}"
    record("P4-5a", "403 error shape documented", r.status_code == 403, raw)
    
    # 404 shape
    r = client.get("/api/runs/nonexistent", headers={"X-API-Key": VIEWER})
    raw = f"404 shape: {json.dumps(r.json())}"
    record("P4-5b", "404 error shape documented", r.status_code == 404, raw)
    
    # 422 shape
    r = client.get("/api/runs?skip=-1", headers={"X-API-Key": VIEWER})
    raw = f"422 shape: {json.dumps(r.json(), indent=2)[:500]}"
    record("P4-5c", "422 error shape documented", r.status_code == 422, raw)
    
    # Extra fields on POST (resume takes no body)
    r = client.post("/api/runs/run_1/resume", headers={"X-API-Key": OPERATOR},
                    json={"garbage": "value", "sql": "'; DROP TABLE;"})
    raw = f"POST resume with extra body: status={r.status_code}, body={r.text[:300]}"
    record("P4-5d", f"Extra body fields on resume: status={r.status_code} (accepted/ignored)",
           r.status_code == 200, raw)

def test_p4_6_rate_limit():
    print("\n=== P4-6: Rate limiting ===")
    rl_clear()
    
    # Temporarily lower rate limit for test
    original_limit = settings.API_RATE_LIMIT_PER_MIN
    settings.API_RATE_LIMIT_PER_MIN = 10
    
    statuses = []
    for i in range(15):
        r = client.get("/health")
        statuses.append(r.status_code)
    
    count_429 = sum(1 for s in statuses if s == 429)
    count_200 = sum(1 for s in statuses if s == 200)
    
    raw = f"Sent 15 reqs, limit=10. 200s={count_200}, 429s={count_429}, statuses={statuses}"
    record("P4-6a", f"Rate limit fires: {count_429} rejections", count_429 > 0, raw)
    
    # Check 429 response for Retry-After header
    if count_429 > 0:
        # Find a 429 response
        rl_clear()
        settings.API_RATE_LIMIT_PER_MIN = 10
        for i in range(15):
            r = client.get("/health")
            if r.status_code == 429:
                break
        
        has_retry = "Retry-After" in r.headers or "retry-after" in r.headers
        raw = f"429 headers: {dict(r.headers)}"
        record("P4-6b", f"429 includes Retry-After header: {has_retry}",
               has_retry,
               raw + " | BUG: No Retry-After header. RFC 6585 recommends it.")
    
    # Check /health without API key
    rl_clear()
    settings.API_RATE_LIMIT_PER_MIN = 5000
    r = client.get("/health")
    raw = f"GET /health no API key: status={r.status_code}, body={r.text[:200]}"
    record("P4-6c", f"/health without API key: {r.status_code}", r.status_code == 200, raw)
    
    # Restore
    settings.API_RATE_LIMIT_PER_MIN = original_limit

# ============================================================
# PHASE 5: SSE
# ============================================================

def test_p5():
    print("\n=== P5: SSE analysis ===")
    from cortexheal.server.api import SSE_CLIENTS
    
    # SSE event types analysis (code review)
    raw = ("SSE emits only 2 event types: 'update' (generic, data='new_data_available') and "
           "'heartbeat' (data='ping'). No specific types for incident_created, run_paused, "
           "run_resumed, plan_approved, plan_rejected, recovery_executed, recovery_verified. "
           "Client must poll REST API after 'update' to learn what changed.")
    record("P5-3", "SSE lacks specific event types (only generic 'update' + heartbeat)",
           False,
           raw + " | FINDING: SSE is a notification bell, not a proper event stream. "
           "Frontend must still poll REST after every notification.")
    
    # SSE cleanup code review
    import inspect
    from cortexheal.server.api import api_stream
    src = inspect.getsource(api_stream)
    has_finally = "finally:" in src
    has_discard = "discard" in src
    raw2 = f"finally_block={has_finally}, discard_call={has_discard}"
    record("P5-2", "SSE cleanup code exists", has_finally and has_discard, raw2)

# ============================================================
# PHASE 6: CHAOS
# ============================================================

def test_p6_1_fail_open():
    print("\n=== P6-1: Fail-open on DB failure ===")
    from cortexheal.runtime.collector import RuntimeCollector
    from cortexheal.models.events import RuntimeEvent
    
    with patch('cortexheal.runtime.collector.get_run', side_effect=Exception("DB DEAD")), \
         patch('cortexheal.runtime.collector.save_run', side_effect=Exception("DB DEAD")), \
         patch('cortexheal.runtime.collector.save_event', side_effect=Exception("DB DEAD")), \
         patch('cortexheal.runtime.collector.save_incident', side_effect=Exception("DB DEAD")):
        
        c = RuntimeCollector(max_queue_size=100)
        ev = RuntimeEvent(
            framework="langgraph", run_id="fail_open", agent_id="test",
            event_type="TOOL_CALL_COMPLETED", status="success", sequence_number=1,
            idempotency_key=str(uuid.uuid4()), tool="t", arguments_hash="h1", response_hash="h2"
        )
        try:
            c.ingest_event(ev)
            c._queue.join()
            time.sleep(0.3)
            crashed = False
        except Exception:
            crashed = True
        c.shutdown(timeout=2)
    
    record("P6-1", "Fail-open: collector does not crash on DB failure",
           not crashed, f"crashed={crashed}")

def test_p6_3_queue_overflow():
    print("\n=== P6-3: Queue overflow ===")
    from cortexheal.runtime.collector import RuntimeCollector
    from cortexheal.models.events import RuntimeEvent
    import queue as q
    
    with patch('cortexheal.runtime.collector.get_run', return_value=None), \
         patch('cortexheal.runtime.collector.save_run', side_effect=mock_noop), \
         patch('cortexheal.runtime.collector.save_event', side_effect=mock_noop), \
         patch('cortexheal.runtime.collector.save_incident', side_effect=mock_noop):
        
        # Pause the worker so queue fills up
        c = RuntimeCollector(max_queue_size=5)
        c._shutdown_event.set()  # Stop the worker
        time.sleep(0.2)
        
        accepted = 0
        dropped = 0
        for i in range(50):
            ev = RuntimeEvent(
                framework="langgraph", run_id="overflow", agent_id="test",
                event_type="TOOL_CALL_COMPLETED", status="success", sequence_number=i+1,
                idempotency_key=str(uuid.uuid4()), tool="t", arguments_hash="h", response_hash="r"
            )
            try:
                c._queue.put_nowait(ev)
                accepted += 1
            except q.Full:
                dropped += 1
        
    raw = f"queue_size=5, sent=50, accepted={accepted}, dropped={dropped}"
    record("P6-3", f"Queue overflow: {dropped}/50 dropped", dropped > 0, raw)

def test_p6_api_resume_nonexistent():
    print("\n=== P6-extra: API resume for non-existent run ===")
    rl_clear()
    r = client.post("/api/runs/FAKE_RUN/resume", headers={"X-API-Key": OPERATOR})
    raw = f"POST /api/runs/FAKE_RUN/resume: status={r.status_code}, body={r.text}"
    record("P6-api-a", f"Resume non-existent: status={r.status_code} (expect 404)",
           r.status_code == 404, raw)

def test_p6_double_approve():
    print("\n=== P6-extra: Double approve via API ===")
    rl_clear()
    inc_id = MOCK_INCIDENTS[0].incident_id
    
    from cortexheal.recovery.engine import RecoveryEngine
    plan = RecoveryEngine().generate_plan(MOCK_INCIDENTS[0])
    plan.status = "PROPOSED"
    MOCK_PLANS[inc_id] = plan
    
    r1 = client.post(f"/api/incidents/{inc_id}/plan/approve", headers={"X-API-Key": OPERATOR})
    status_after = MOCK_PLANS.get(inc_id, MagicMock()).status
    r2 = client.post(f"/api/incidents/{inc_id}/plan/approve", headers={"X-API-Key": OPERATOR})
    
    raw = (f"1st approve: {r1.status_code} {r1.text[:100]} | plan status after 1st: {status_after} | "
           f"2nd approve: {r2.status_code} {r2.text[:100]}")
    record("P6-dbl", f"Double approve: 1st={r1.status_code}, 2nd={r2.status_code}",
           r1.status_code == 200 and r2.status_code == 400, raw)

def test_p6_approve_then_reject():
    print("\n=== P6-extra: Approve then reject ===")
    rl_clear()
    inc_id = MOCK_INCIDENTS[0].incident_id
    
    from cortexheal.recovery.engine import RecoveryEngine
    plan = RecoveryEngine().generate_plan(MOCK_INCIDENTS[0])
    plan.status = "PROPOSED"
    MOCK_PLANS[inc_id] = plan
    
    r1 = client.post(f"/api/incidents/{inc_id}/plan/approve", headers={"X-API-Key": OPERATOR})
    r2 = client.post(f"/api/incidents/{inc_id}/plan/reject", headers={"X-API-Key": OPERATOR})
    final = MOCK_PLANS.get(inc_id, MagicMock()).status
    
    raw = f"approve={r1.status_code}, reject={r2.status_code}, final_plan_status={final}"
    record("P6-ar", f"Approve then reject: approve={r1.status_code}, reject={r2.status_code}, final={final}",
           r1.status_code == 200 and r2.status_code == 400, raw)

# ============================================================
# RUN ALL TESTS
# ============================================================
if __name__ == "__main__":
    print("=" * 70)
    print("ADVERSARIAL ROBUSTNESS VALIDATION — PHASES 4-6")
    print("=" * 70)
    
    test_p4_1_viewer_on_mutating()
    test_p4_2_auth_variations()
    test_p4_3_sqli()
    test_p4_4_pagination()
    test_p4_5_error_shapes()
    test_p4_6_rate_limit()
    test_p5()
    test_p6_1_fail_open()
    test_p6_3_queue_overflow()
    test_p6_api_resume_nonexistent()
    test_p6_double_approve()
    test_p6_approve_then_reject()
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passes = sum(1 for r in RESULTS if r["status"] == "PASS")
    fails = sum(1 for r in RESULTS if r["status"] == "FAIL")
    design = sum(1 for r in RESULTS if r["status"] == "DESIGN-BOUNDARY")
    print(f"PASS: {passes}  FAIL: {fails}  DESIGN-BOUNDARY: {design}  TOTAL: {len(RESULTS)}")
    for r in RESULTS:
        print(f"  [{r['status']}] {r['id']}: {r['desc']}")
    
    with open("adversarial_p4_p6_raw.json", "w") as f:
        json.dump(RESULTS, f, indent=2, default=str)
    
    print(f"\nRaw results written to adversarial_p4_p6_raw.json")
    
    for p in patches:
        try: p.stop()
        except: pass
