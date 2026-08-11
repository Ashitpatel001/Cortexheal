import os
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from cortexheal.server.api import app
from unittest.mock import patch
from cortexheal.config import settings

def test_api_health_readiness():
    client = TestClient(app)
    
    # 1. Health is simple 200
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "HEALTHY"
    
    # 2. Readiness with DB down
    with patch('cortexheal.storage.postgres.get_connection', side_effect=Exception("DB Down")):
        res = client.get("/readiness")
        assert res.status_code == 200
        assert res.json()["status"] == "NOT_READY"
        
    # 3. Readiness with telemetry worker dead
    with patch('cortexheal.storage.postgres.get_connection'):
        with patch('cortexheal.runtime.collector.collector') as mock_coll:
            mock_coll._worker_thread.is_alive.return_value = False
            res = client.get("/readiness")
            assert res.status_code == 200
            assert res.json()["status"] == "DEGRADED"

def test_config_hardening():
    from cortexheal.config import Settings
    
    with pytest.raises(ValueError, match="Default authentication tokens cannot be used in production"):
        Settings(ENVIRONMENT="production", ADMIN_TOKENS="admin-key", OPERATOR_TOKENS="operator-key", DATABASE_URL="postgresql://cortexheal:cortexpassword@localhost:5432/cortexheal_db")

@patch('cortexheal.server.api.get_incidents', return_value=[])
@patch('cortexheal.server.api.get_run', return_value=None)
def test_api_security(mock_get_run, mock_get_incidents):
    client = TestClient(app)
    
    # Unauthenticated should be 403 or 401 depending on FastAPI version
    res = client.get("/api/incidents")
    assert res.status_code in [401, 403]
    
    # Viewer can list incidents
    res = client.get("/api/incidents", headers={"X-API-Key": settings.get_viewer_tokens()[0]})
    assert res.status_code == 200
    
    # Viewer cannot approve plans
    res = client.post("/api/incidents/123/plan/approve", headers={"X-API-Key": settings.get_viewer_tokens()[0]})
    assert res.status_code == 403
    
    # Operator can approve plans (will return 404 since it doesn't exist, but NOT 403!)
    with patch('cortexheal.server.api.get_recovery_plan_by_incident', return_value=None):
        res = client.post("/api/incidents/123/plan/approve", headers={"X-API-Key": settings.get_operator_tokens()[0]})
        assert res.status_code == 404
