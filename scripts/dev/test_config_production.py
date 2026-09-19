
import os
import sys

# Test 1: Production with default password should fail
os.environ["ENVIRONMENT"] = "production"
os.environ["DATABASE_URL"] = "postgresql://cortexheal:cortexpassword@localhost:5432/cortexheal_db"

print("Running Test 1: Default database URL in production...")
try:
    from cortexheal.config import Settings
    settings = Settings()
    print("FAIL: Settings loaded successfully when it should have raised an error.")
    sys.exit(1)
except ValueError as e:
    print(f"PASS: Caught expected ValueError: {e}")

# Test 2: Production with custom password should succeed
os.environ["DATABASE_URL"] = "postgresql://cortexheal:secure_prod_password@postgres:5432/cortexheal_db"
# Override the tokens as well, otherwise it fails on those
os.environ["ADMIN_TOKENS"] = "real-admin-key"
os.environ["OPERATOR_TOKENS"] = "real-op-key"

print("\nRunning Test 2: Custom database URL in production...")
try:
    from cortexheal.config import Settings
    settings = Settings()
    print(f"PASS: Settings loaded successfully. db_url={settings.DATABASE_URL}")
except Exception as e:
    print(f"FAIL: Unexpected error: {e}")
    sys.exit(1)

