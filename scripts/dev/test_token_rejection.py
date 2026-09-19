
import os
import sys

# Test: Production with real default token (dev-admin-key) should fail
os.environ["ENVIRONMENT"] = "production"
os.environ["DATABASE_URL"] = "postgresql://cortexheal:secure_prod_password@postgres:5432/cortexheal_db"
os.environ["ADMIN_TOKENS"] = "dev-admin-key"

print("Running Test: dev-admin-key in production...")
try:
    from cortexheal.config import Settings
    settings = Settings()
    print("FAIL: Settings loaded successfully when it should have raised an error.")
    sys.exit(1)
except ValueError as e:
    print(f"PASS: Caught expected ValueError: {e}")

