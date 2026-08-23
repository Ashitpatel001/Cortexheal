from datetime import datetime, timezone
from typing import Optional, Literal
from pydantic import BaseModel, Field
import uuid
import secrets
import hashlib

def hash_key(raw_key: str) -> str:
    """Compute SHA-256 hash of plaintext API key."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

def generate_raw_key(role: str) -> str:
    """Generate cryptographically secure API key with cosmetic role prefix."""
    token_hex = secrets.token_hex(24)
    return f"ctx_{role.lower()}_{token_hex}"

class ApiKey(BaseModel):
    key_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    key_hash: str
    key_prefix: str
    name: str
    org_id: str
    role: Literal["VIEWER", "OPERATOR", "ADMIN"]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None

class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Human-readable name or purpose for this key")
    role: Literal["VIEWER", "OPERATOR", "ADMIN"] = Field(..., description="Role assigned to this key")

class ApiKeyResponse(BaseModel):
    key_id: str
    key_prefix: str
    name: str
    org_id: str
    role: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None

class ApiKeyCreatedResponse(ApiKeyResponse):
    raw_key: str = Field(..., description="Plaintext secret key. Displayed exactly once.")
