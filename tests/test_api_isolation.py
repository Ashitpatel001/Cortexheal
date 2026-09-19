import pytest
from fastapi.testclient import TestClient
import uuid
import time
from datetime import datetime, timezone
import json

from cortexheal.server.api import app
from cortexheal.storage.postgres import get_connection, init_db
from cortexheal.models.auth import hash_key

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown():
    init_db()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM recovery_outcomes;")
            cur.execute("DELETE FROM incidents;")
            cur.execute("DELETE FROM events;")
            cur.execute("DELETE FROM runs;")
            cur.execute("DELETE FROM api_keys;")
        conn.commit()
    yield
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM recovery_outcomes;")
            cur.execute("DELETE FROM incidents;")
            cur.execute("DELETE FROM events;")
            cur.execute("DELETE FROM runs;")
            cur.execute("DELETE FROM api_keys;")
        conn.commit()

def seed_org_data(org_id: str) -> str:
    raw_key = f"ctx_viewer_{org_id}_test"
    k_hash = hash_key(raw_key)
    prefix = raw_key[:16] + "..."
    
    run_id = f"test_run_{org_id}_{uuid.uuid4().hex[:8]}"
    incident_id = str(uuid.uuid4())
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO api_keys (key_id, key_hash, key_prefix, name, org_id, role, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (str(uuid.uuid4()), k_hash, prefix, f"{org_id} Key", org_id, "VIEWER", datetime.now(timezone.utc)))
            
            cur.execute('''
                INSERT INTO runs (run_id, agent_id, status, start_time, org_id, framework)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (run_id, "test_agent", "running", datetime.now(timezone.utc), org_id, "custom"))
            
            cur.execute('''
                INSERT INTO incidents (incident_id, run_id, agent_id, failure_type, severity, status, detector, detector_version, trigger_event_id, triggered_at, evidence, observed_value, threshold, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (incident_id, run_id, "test_agent", "STUCK_LOOP", "CRITICAL", "OPEN", "stuck_loop_detector", "1.0", str(uuid.uuid4()), datetime.now(timezone.utc), json.dumps({}), json.dumps(5), json.dumps(5), "Test Incident"))
        conn.commit()
        
    return raw_key

def test_api_incidents_and_runs_org_isolation():
    """
    Negative isolation test: org_a cannot see org_b's runs or incidents.
    This explicitly prevents the global leak bug.
    """
    key_a = seed_org_data("org_a")
    key_b = seed_org_data("org_b")
    
    # 1. Test /api/incidents
    res_a_incidents = client.get("/api/incidents", headers={"X-API-Key": key_a})
    assert res_a_incidents.status_code == 200
    data_a_incidents = res_a_incidents.json()["data"]
    
    res_b_incidents = client.get("/api/incidents", headers={"X-API-Key": key_b})
    assert res_b_incidents.status_code == 200
    data_b_incidents = res_b_incidents.json()["data"]
    
    # Assertions for incidents:
    assert len(data_a_incidents) == 1, "org_a should see exactly 1 incident"
    assert len(data_b_incidents) == 1, "org_b should see exactly 1 incident"
    # Ensure they are disjoint
    assert data_a_incidents[0]["run_id"].startswith("test_run_org_a_")
    assert data_b_incidents[0]["run_id"].startswith("test_run_org_b_")
    
    # 2. Test /api/runs
    res_a_runs = client.get("/api/runs", headers={"X-API-Key": key_a})
    assert res_a_runs.status_code == 200
    data_a_runs = res_a_runs.json()["data"]
    
    res_b_runs = client.get("/api/runs", headers={"X-API-Key": key_b})
    assert res_b_runs.status_code == 200
    data_b_runs = res_b_runs.json()["data"]
    
    # Assertions for runs:
    assert len(data_a_runs) == 1, "org_a should see exactly 1 run"
    assert len(data_b_runs) == 1, "org_b should see exactly 1 run"
    assert data_a_runs[0]["run_id"].startswith("test_run_org_a_")
    assert data_b_runs[0]["run_id"].startswith("test_run_org_b_")
