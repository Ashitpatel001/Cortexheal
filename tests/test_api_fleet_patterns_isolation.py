import pytest
from fastapi.testclient import TestClient
import uuid
from datetime import datetime, timezone

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
            cur.execute("DELETE FROM pattern_records;")
        conn.commit()
    yield
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM recovery_outcomes;")
            cur.execute("DELETE FROM incidents;")
            cur.execute("DELETE FROM events;")
            cur.execute("DELETE FROM runs;")
            cur.execute("DELETE FROM api_keys;")
            cur.execute("DELETE FROM pattern_records;")
        conn.commit()

def seed_fleet_and_patterns(org_id: str) -> str:
    raw_key = f"ctx_viewer_{org_id}_fleet"
    k_hash = hash_key(raw_key)
    prefix = raw_key[:16] + "..."
    
    agent_id = f"agent_{org_id}_{uuid.uuid4().hex[:4]}"
    run_id = f"run_{org_id}_{uuid.uuid4().hex[:4]}"
    pattern_id = f"p_{org_id}_{uuid.uuid4().hex[:4]}"
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Insert Key
            cur.execute('''
                INSERT INTO api_keys (key_id, key_hash, key_prefix, name, org_id, role, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (str(uuid.uuid4()), k_hash, prefix, f"{org_id} Key", org_id, "VIEWER", datetime.now(timezone.utc)))
            
            # Insert Run (Fleet will aggregate this)
            cur.execute('''
                INSERT INTO runs (run_id, agent_id, status, start_time, end_time, org_id, framework)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (run_id, agent_id, "completed", datetime.now(timezone.utc), datetime.now(timezone.utc), org_id, "test_framework"))
            
            # Insert Pattern
            cur.execute('''
                INSERT INTO pattern_records (pattern_id, framework, agent_id, failure_type, fingerprint, fingerprint_version, occurrences, org_id, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (pattern_id, "test_framework", agent_id, "STUCK_LOOP", f"fingerprint_{org_id}", "v1", 1, org_id, datetime.now(timezone.utc), datetime.now(timezone.utc)))
            
        conn.commit()
    return raw_key

def test_fleet_and_patterns_org_isolation():
    key_a = seed_fleet_and_patterns("org_a")
    key_b = seed_fleet_and_patterns("org_b")
    
    # Test Fleet - returns a direct JSON array
    res_a_fleet = client.get("/api/fleet", headers={"X-API-Key": key_a})
    assert res_a_fleet.status_code == 200
    fleet_a = res_a_fleet.json()
    
    res_b_fleet = client.get("/api/fleet", headers={"X-API-Key": key_b})
    assert res_b_fleet.status_code == 200
    fleet_b = res_b_fleet.json()
    
    assert len(fleet_a) == 1
    assert len(fleet_b) == 1
    assert "agent_org_a_" in fleet_a[0]["agent_id"]
    assert "agent_org_b_" in fleet_b[0]["agent_id"]
    
    # Test Patterns - returns {"data": [...]}
    res_a_patterns = client.get("/api/patterns", headers={"X-API-Key": key_a})
    assert res_a_patterns.status_code == 200
    patterns_a = res_a_patterns.json()["data"]
    
    res_b_patterns = client.get("/api/patterns", headers={"X-API-Key": key_b})
    assert res_b_patterns.status_code == 200
    patterns_b = res_b_patterns.json()["data"]
    
    assert len(patterns_a) == 1
    assert len(patterns_b) == 1
    assert "fingerprint_org_a" in patterns_a[0]["fingerprint"]
    assert "fingerprint_org_b" in patterns_b[0]["fingerprint"]
