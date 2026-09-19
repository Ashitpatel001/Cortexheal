
import os
import sys

def test_config(test_name, env_vars, expect_failure):
    # Clear environment variables first to avoid state leaking between tests
    for key in ["ENVIRONMENT", "DATABASE_URL", "ADMIN_TOKENS", "OPERATOR_TOKENS", "VIEWER_TOKENS"]:
        if key in os.environ:
            del os.environ[key]
            
    # Apply test variables
    for k, v in env_vars.items():
        os.environ[k] = v

    print(f"\nRunning Test: {test_name}")
    try:
        from cortexheal.config import Settings
        settings = Settings()
        if expect_failure:
            print("FAIL: Settings loaded successfully when it should have raised an error.")
            sys.exit(1)
        else:
            print("PASS: Settings loaded successfully without false positives.")
    except ValueError as e:
        if expect_failure:
            print(f"PASS: Caught expected ValueError: {e}")
        else:
            print(f"FAIL: Unexpected ValueError: {e}")
            sys.exit(1)

# Base safe environment
base_env = {
    "ENVIRONMENT": "production",
    "DATABASE_URL": "postgresql://cortexheal:secure_prod_password@postgres:5432/cortexheal_db",
    "ADMIN_TOKENS": "safe-admin-key",
    "OPERATOR_TOKENS": "safe-op-key",
    "VIEWER_TOKENS": "safe-viewer-key"
}

# Test 1: dev-operator-key should fail
test1_env = base_env.copy()
test1_env["OPERATOR_TOKENS"] = "dev-operator-key"
test_config("dev-operator-key in production", test1_env, expect_failure=True)

# Test 2: dev-viewer-key should fail
test2_env = base_env.copy()
test2_env["VIEWER_TOKENS"] = "dev-viewer-key"
test_config("dev-viewer-key in production", test2_env, expect_failure=True)

# Test 3: Real custom tokens should succeed
test3_env = {
    "ENVIRONMENT": "production",
    "DATABASE_URL": "postgresql://cortexheal:secure_prod_password@postgres:5432/cortexheal_db",
    "ADMIN_TOKENS": "prod-custom-admin-key-99",
    "OPERATOR_TOKENS": "prod-custom-op-key-88",
    "VIEWER_TOKENS": "prod-custom-view-key-77"
}
test_config("Real custom tokens in production", test3_env, expect_failure=False)

