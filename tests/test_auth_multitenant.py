import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import uuid

from cortexheal.server.api import app
from cortexheal.config import settings
from cortexheal.models.auth import ApiKey, hash_key, generate_raw_key
from cortexheal.storage.postgres import save_api_key, init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

def create_test_key(org_id: str, role: str, name: str) -> tuple[str, ApiKey]:
    raw_key = generate_raw_key(role)
    k_hash = hash_key(raw_key)
    prefix = raw_key[:16] + "..."
    api_key = ApiKey(
        key_id=str(uuid.uuid4()),
        key_hash=k_hash,
        key_prefix=prefix,
        name=name,
        org_id=org_id,
        role=role
    )
    saved = save_api_key(api_key)
    return raw_key, saved

def test_dev_tokens_rejected_when_bypass_disabled():
    """Shared dev tokens must be rejected when ALLOW_DEV_TOKENS=False."""
    with patch.object(settings, "ALLOW_DEV_TOKENS", False):
        res_admin = client.get("/api/whoami", headers={"X-API-Key": "dev-admin-key"})
        assert res_admin.status_code == 403
        assert res_admin.json()["detail"] == "Invalid API Key"

        res_op = client.get("/api/whoami", headers={"X-API-Key": "dev-operator-key"})
        assert res_op.status_code == 403

        res_vw = client.get("/api/whoami", headers={"X-API-Key": "dev-viewer-key"})
        assert res_vw.status_code == 403

def test_dev_tokens_accepted_when_bypass_enabled():
    """Shared dev tokens function when ALLOW_DEV_TOKENS=True."""
    with patch.object(settings, "ALLOW_DEV_TOKENS", True):
        res_admin = client.get("/api/whoami", headers={"X-API-Key": "dev-admin-key"})
        assert res_admin.status_code == 200
        assert res_admin.json() == {"role": "ADMIN", "org_id": "default_org"}

        res_op = client.get("/api/whoami", headers={"X-API-Key": "dev-operator-key"})
        assert res_op.status_code == 200
        assert res_op.json() == {"role": "OPERATOR", "org_id": "default_org"}

def test_api_key_creation_and_usage():
    """Admin can generate a key, which can immediately authenticate."""
    raw_admin_key, admin_key_obj = create_test_key(org_id="org_alpha", role="ADMIN", name="Alpha Admin")
    
    # 1. Admin creates an Operator key
    payload = {"name": "Worker Node 1", "role": "OPERATOR"}
    res = client.post("/api/keys", json=payload, headers={"X-API-Key": raw_admin_key})
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Worker Node 1"
    assert data["role"] == "OPERATOR"
    assert data["org_id"] == "org_alpha"
    assert "raw_key" in data
    
    raw_op_key = data["raw_key"]
    
    # 2. Use the new Operator key
    whoami_res = client.get("/api/whoami", headers={"X-API-Key": raw_op_key})
    assert whoami_res.status_code == 200
    assert whoami_res.json() == {"role": "OPERATOR", "org_id": "org_alpha"}

def test_non_admin_cannot_create_or_list_keys():
    """VIEWER and OPERATOR cannot create or list API keys."""
    raw_op_key, _ = create_test_key(org_id="org_beta", role="OPERATOR", name="Beta Operator")
    raw_view_key, _ = create_test_key(org_id="org_beta", role="VIEWER", name="Beta Viewer")

    # Operator creation attempt
    res_op = client.post("/api/keys", json={"name": "Sub key", "role": "VIEWER"}, headers={"X-API-Key": raw_op_key})
    assert res_op.status_code == 403
    assert res_op.json()["detail"] == "Requires ADMIN role"

    # Viewer list attempt
    res_vw = client.get("/api/keys", headers={"X-API-Key": raw_view_key})
    assert res_vw.status_code == 403

def test_key_revocation_rejects_immediately():
    """Revoked key must be immediately rejected on subsequent requests."""
    raw_admin_key, admin_key_obj = create_test_key(org_id="org_gamma", role="ADMIN", name="Gamma Admin")
    
    # Create key
    create_res = client.post("/api/keys", json={"name": "Temporary Key", "role": "VIEWER"}, headers={"X-API-Key": raw_admin_key})
    assert create_res.status_code == 200
    key_id = create_res.json()["key_id"]
    raw_temp_key = create_res.json()["raw_key"]

    # Verify key works
    assert client.get("/api/whoami", headers={"X-API-Key": raw_temp_key}).status_code == 200

    # Revoke key
    revoke_res = client.post(f"/api/keys/{key_id}/revoke", headers={"X-API-Key": raw_admin_key})
    assert revoke_res.status_code == 200
    assert revoke_res.json()["status"] == "success"

    # Verify key is immediately rejected with 403
    rejected_res = client.get("/api/whoami", headers={"X-API-Key": raw_temp_key})
    assert rejected_res.status_code == 403
    assert rejected_res.json()["detail"] == "API Key is revoked"

def test_multi_tenant_isolation():
    """Org A cannot list or revoke Org B's keys."""
    raw_admin_a, _ = create_test_key(org_id="tenant_a", role="ADMIN", name="Admin A")
    raw_admin_b, _ = create_test_key(org_id="tenant_b", role="ADMIN", name="Admin B")

    # Admin A creates Key A
    res_a = client.post("/api/keys", json={"name": "Key Alpha", "role": "OPERATOR"}, headers={"X-API-Key": raw_admin_a})
    key_a_id = res_a.json()["key_id"]
    
    # Admin B creates Key B
    res_b = client.post("/api/keys", json={"name": "Key Beta", "role": "OPERATOR"}, headers={"X-API-Key": raw_admin_b})
    key_b_id = res_b.json()["key_id"]
    raw_key_b = res_b.json()["raw_key"]

    # 1. Admin A lists keys -> must ONLY see tenant_a keys
    list_a = client.get("/api/keys", headers={"X-API-Key": raw_admin_a})
    assert list_a.status_code == 200
    keys_a = list_a.json()
    assert all(k["org_id"] == "tenant_a" for k in keys_a)
    assert any(k["key_id"] == key_a_id for k in keys_a)
    assert not any(k["key_id"] == key_b_id for k in keys_a)

    # 2. Admin A attempts to revoke Key B -> must return 404 (not 403, preventing tenant enumeration)
    cross_revoke = client.post(f"/api/keys/{key_b_id}/revoke", headers={"X-API-Key": raw_admin_a})
    assert cross_revoke.status_code == 404
    assert cross_revoke.json()["detail"] == "API key not found"

    # 3. Key B is NOT revoked and still functions
    assert client.get("/api/whoami", headers={"X-API-Key": raw_key_b}).status_code == 200
