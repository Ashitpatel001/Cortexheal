
from fastapi.testclient import TestClient
from cortexheal.server.api import app, get_current_user, User

client = TestClient(app)

def mock_auth_org_a():
    return User(username="user_a", role="ADMIN", org_id="org_a")

def mock_auth_org_b():
    return User(username="user_b", role="ADMIN", org_id="org_b")

print("--- Testing API with org_a ---")
app.dependency_overrides[get_current_user] = mock_auth_org_a
resp_a = client.get("/api/fleet")
print(resp_a.json())

print("\n--- Testing API with org_b ---")
app.dependency_overrides[get_current_user] = mock_auth_org_b
resp_b = client.get("/api/fleet")
print(resp_b.json())

