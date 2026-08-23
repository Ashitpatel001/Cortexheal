from datetime import datetime, timezone
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
import uuid

class WebhookConfig(BaseModel):
    webhook_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    org_id: str
    target_type: Literal["slack", "generic_webhook", "pagerduty", "opsgenie"] = "slack"
    url: str
    enabled: bool = True
    secret_token: Optional[str] = None
    min_severity: Literal["HIGH", "CRITICAL"] = "HIGH"
    escalation_timeout_minutes: int = 15
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class WebhookCreateRequest(BaseModel):
    url: str = Field(..., description="Target webhook URL (e.g. Slack incoming webhook)")
    target_type: Literal["slack", "generic_webhook", "pagerduty", "opsgenie"] = "slack"
    min_severity: Literal["HIGH", "CRITICAL"] = "HIGH"
    escalation_timeout_minutes: int = Field(default=15, ge=1, le=1440)
    secret_token: Optional[str] = None

class NotificationRecord(BaseModel):
    notification_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    org_id: str
    incident_id: str
    run_id: str
    notification_type: Literal["INITIAL_ALERT", "ESCALATION"]
    target_url: str
    payload: Dict[str, Any]
    status: Literal["SUCCESS", "FAILED"]
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    sent_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
