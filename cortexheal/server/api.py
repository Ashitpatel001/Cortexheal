from fastapi import FastAPI, HTTPException, Depends, Security, Request, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
import csv
import io
from typing import List, Optional
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from cortexheal.storage.postgres import (
    get_incidents, get_incident, get_all_runs, get_run,
    get_events_for_run, get_audit_events_for_run, get_recovery_plan_by_incident,
    save_api_key, get_api_key_by_hash, get_api_keys_by_org, revoke_api_key, update_api_key_last_used,
    save_webhook_config, get_webhook_configs_by_org, delete_webhook_config, get_notifications_by_org,
    get_audit_export_records
)
from cortexheal.models.auth import (
    ApiKey, ApiKeyCreateRequest, ApiKeyResponse, ApiKeyCreatedResponse,
    hash_key, generate_raw_key
)
from cortexheal.models.alerting import WebhookConfig, WebhookCreateRequest, NotificationRecord
from cortexheal.alerting.dispatcher import alert_dispatcher
from cortexheal.protection.controller import ProtectionController
from cortexheal.recovery.engine import RecoveryEngine
from cortexheal.recovery.executor import RecoveryExecutor
from cortexheal.config import settings
from cortexheal.logger import setup_logging
import os
import time
from prometheus_client import make_asgi_app
from cortexheal.telemetry import metrics

logger = setup_logging()

# --- SERVER-SENT EVENTS (SSE) STATE ---
# Dictionary mapping subscription_key -> set of client queues
# Each queue receives dicts: {"event": "event_type", "data": {...}}
SSE_CLIENTS = {}

def broadcast_sse_event(event_type: str, data: dict, run_id: str = None):
    """
    Push a typed SSE event to all connected clients.
    If run_id is provided, notifies clients subscribed to that run_id AND 'global'.
    If run_id is None, notifies only 'global' subscribers.
    Thread-safe: uses put_nowait which is safe from non-async threads.
    """
    message = {"event": event_type, "data": data}
    target_keys = ["global"]
    if run_id:
        target_keys.append(run_id)
    
    for key in target_keys:
        if key in SSE_CLIENTS:
            for q in list(SSE_CLIENTS[key]):
                try:
                    q.put_nowait(message)
                except asyncio.QueueFull:
                    pass

async def poll_db_for_updates():
    """
    Background poller that detects new incidents and run status changes.
    Emits typed SSE events: incident_created, run_status_changed.
    Acts as a catch-all for changes not already broadcast by API endpoints.
    """
    try:
        last_incidents = {i.incident_id: i for i in get_incidents()}
        last_runs = {r.run_id: r.status for r in get_all_runs()}
    except Exception:
        last_incidents = {}
        last_runs = {}
        
    while True:
        await asyncio.sleep(2)
        if not SSE_CLIENTS:
            continue
        try:
            current_incidents_list = get_incidents()
            current_runs_list = get_all_runs()
            
            current_incidents = {i.incident_id: i for i in current_incidents_list}
            current_runs = {r.run_id: r.status for r in current_runs_list}
            
            # Detect new incidents
            for iid, incident in current_incidents.items():
                if iid not in last_incidents:
                    broadcast_sse_event("incident_created", {
                        "incident_id": iid,
                        "run_id": incident.run_id,
                        "failure_type": incident.failure_type,
                        "severity": incident.severity,
                    }, run_id=incident.run_id)
            
            # Detect run status changes
            for rid, status in current_runs.items():
                old_status = last_runs.get(rid)
                if old_status is not None and old_status != status:
                    broadcast_sse_event("run_status_changed", {
                        "run_id": rid,
                        "old_status": old_status,
                        "new_status": status,
                    }, run_id=rid)
            
            last_incidents = current_incidents
            last_runs = current_runs
        except Exception as e:
            logger.error(f"SSE DB Polling error: {e}")

async def poll_escalations():
    """Background worker that audits unacknowledged incidents and fires escalations."""
    while True:
        try:
            await asyncio.sleep(15.0)
            await asyncio.to_thread(alert_dispatcher.check_and_dispatch_escalations)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Escalation poller error: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    polling_task = asyncio.create_task(poll_db_for_updates())
    escalation_task = asyncio.create_task(poll_escalations())
    yield
    # Shutdown
    polling_task.cancel()
    escalation_task.cancel()

app = FastAPI(title="CortexHeal Control Plane", lifespan=lifespan)

# --- PROMETHEUS METRICS ---
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# --- RATE LIMITING (In-Memory for V1) ---
RATE_LIMIT_STORE = {}

async def rate_limit(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    if client_ip not in RATE_LIMIT_STORE:
        RATE_LIMIT_STORE[client_ip] = []
    
    # Clean up old requests (older than 1 minute)
    RATE_LIMIT_STORE[client_ip] = [t for t in RATE_LIMIT_STORE[client_ip] if now - t < 60]
    
    if len(RATE_LIMIT_STORE[client_ip]) >= settings.API_RATE_LIMIT_PER_MIN:
        # RFC 6585 §4: 429 SHOULD include Retry-After header
        oldest_request = RATE_LIMIT_STORE[client_ip][0]
        retry_after = max(1, int(60 - (now - oldest_request)))
        raise HTTPException(
            status_code=429,
            detail="Too Many Requests",
            headers={"Retry-After": str(retry_after)}
        )
        
    RATE_LIMIT_STORE[client_ip].append(now)

app.router.dependencies.append(Depends(rate_limit))

# --- AUTHENTICATION & AUTHORIZATION ---
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

# Simple V1 Token-based Auth configured via ENV (used only if ALLOW_DEV_TOKENS=True)
VIEWER_TOKENS = settings.get_viewer_tokens()
OPERATOR_TOKENS = settings.get_operator_tokens()
ADMIN_TOKENS = settings.get_admin_tokens()

class User:
    def __init__(self, username: str, role: str, org_id: str = "default_org", key_id: str = None):
        self.username = username
        self.role = role
        self.org_id = org_id
        self.key_id = key_id

def get_current_user(api_key: str = Security(api_key_header)):
    # 1. Check database for valid hashed API key
    k_hash = hash_key(api_key)
    try:
        db_key = get_api_key_by_hash(k_hash)
        if db_key:
            if db_key.revoked_at is not None:
                raise HTTPException(status_code=403, detail="API Key is revoked")
            # Update last used timestamp
            update_api_key_last_used(db_key.key_id)
            return User(
                username=db_key.name,
                role=db_key.role,
                org_id=db_key.org_id,
                key_id=db_key.key_id
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Error querying API key from DB: {e}")

    # 2. Check local dev bypass tokens if explicitly allowed
    if settings.ALLOW_DEV_TOKENS:
        if api_key in ADMIN_TOKENS:
            return User(username="admin_user", role="ADMIN", org_id="default_org")
        elif api_key in OPERATOR_TOKENS:
            return User(username="operator_user", role="OPERATOR", org_id="default_org")
        elif api_key in VIEWER_TOKENS:
            return User(username="viewer_user", role="VIEWER", org_id="default_org")

    raise HTTPException(status_code=403, detail="Invalid API Key")

def require_operator(user: User = Depends(get_current_user)):
    if user.role not in ["OPERATOR", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Requires OPERATOR or ADMIN role")
    return user

def require_admin(user: User = Depends(get_current_user)):
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Requires ADMIN role")
    return user

# Hardened CORS for Production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("CORTEXHEAL_CORS_ORIGIN", "http://localhost:3000")],
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)

protection_controller = ProtectionController()
recovery_engine = RecoveryEngine()
recovery_executor = RecoveryExecutor()

# --- API ENDPOINTS ---

@app.get("/api/whoami")
def api_whoami(user: User = Depends(get_current_user)):
    """Return the currently authenticated user's role and organization."""
    return {"role": user.role, "org_id": user.org_id}

@app.post("/api/keys", response_model=ApiKeyCreatedResponse)
def api_create_key(
    payload: ApiKeyCreateRequest,
    user: User = Depends(require_admin)
):
    """Generate a new API key for caller's organization. ADMIN only."""
    raw_key = generate_raw_key(payload.role)
    k_hash = hash_key(raw_key)
    prefix = raw_key[:16] + "..."
    
    new_key = ApiKey(
        key_hash=k_hash,
        key_prefix=prefix,
        name=payload.name,
        org_id=user.org_id,  # Strictly bounded to caller's org_id
        role=payload.role
    )
    saved = save_api_key(new_key)
    return ApiKeyCreatedResponse(
        key_id=saved.key_id,
        key_prefix=saved.key_prefix,
        name=saved.name,
        org_id=saved.org_id,
        role=saved.role,
        created_at=saved.created_at,
        last_used_at=saved.last_used_at,
        revoked_at=saved.revoked_at,
        raw_key=raw_key
    )

@app.get("/api/keys", response_model=List[ApiKeyResponse])
def api_list_keys(
    user: User = Depends(require_admin)
):
    """List all API keys for caller's organization. ADMIN only."""
    keys = get_api_keys_by_org(user.org_id)
    return [
        ApiKeyResponse(
            key_id=k.key_id,
            key_prefix=k.key_prefix,
            name=k.name,
            org_id=k.org_id,
            role=k.role,
            created_at=k.created_at,
            last_used_at=k.last_used_at,
            revoked_at=k.revoked_at
        ) for k in keys
    ]

@app.post("/api/keys/{key_id}/revoke")
def api_revoke_key(
    key_id: str,
    user: User = Depends(require_admin)
):
    """Revoke an API key within caller's organization. ADMIN only."""
    revoked = revoke_api_key(key_id, user.org_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"status": "success", "message": f"API key {key_id} revoked"}

# --- OUTBOUND WEBHOOKS & ALERTING ---

@app.post("/api/webhooks", response_model=WebhookConfig)
def api_create_webhook(
    payload: WebhookCreateRequest,
    user: User = Depends(require_admin)
):
    """Register a new outbound alerting webhook for caller's organization. ADMIN only."""
    config = WebhookConfig(
        org_id=user.org_id,
        target_type=payload.target_type,
        url=str(payload.url),
        secret_token=payload.secret_token,
        min_severity=payload.min_severity,
        escalation_timeout_minutes=payload.escalation_timeout_minutes
    )
    return save_webhook_config(config)

@app.get("/api/webhooks", response_model=List[WebhookConfig])
def api_list_webhooks(
    user: User = Depends(require_admin)
):
    """List all registered webhooks for caller's organization. ADMIN only."""
    return get_webhook_configs_by_org(user.org_id)

@app.delete("/api/webhooks/{webhook_id}")
def api_delete_webhook(
    webhook_id: str,
    user: User = Depends(require_admin)
):
    """Delete a registered webhook for caller's organization. ADMIN only."""
    deleted = delete_webhook_config(webhook_id, user.org_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Webhook configuration not found")
    return {"status": "success", "message": f"Webhook {webhook_id} deleted"}

@app.get("/api/notifications", response_model=List[NotificationRecord])
def api_list_notifications(
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(require_operator)
):
    """List recent notification audit logs for caller's organization. OPERATOR/ADMIN."""
    return get_notifications_by_org(user.org_id, limit=limit)

# --- AUDIT & COMPLIANCE EXPORT ---

@app.get("/api/audit/export")
def api_audit_export(
    format: str = Query("json", pattern="^(json|csv)$"),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None),
    failure_type: Optional[str] = Query(None),
    user: User = Depends(require_operator)
):
    """
    Compliance & Safety Audit Export.
    Returns complete deterministic incident, recovery, and audit verification history.
    Accessible to OPERATOR and ADMIN.
    """
    records = get_audit_export_records(
        org_id=user.org_id,
        from_date=from_date,
        to_date=to_date,
        agent_id=agent_id,
        failure_type=failure_type
    )
    
    if format == "json":
        return {
            "total_records": len(records),
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "organization_id": user.org_id,
            "filters": {
                "from_date": from_date,
                "to_date": to_date,
                "agent_id": agent_id,
                "failure_type": failure_type
            },
            "records": records
        }

    # CSV Format
    output = io.StringIO()
    if not records:
        output.write("No audit records found for the specified filters\n")
    else:
        fieldnames = [
            "incident_id", "triggered_at", "run_id", "agent_id", "framework",
            "model", "provider", "run_status", "protection_mode",
            "failure_type", "severity", "incident_status", "detector", "detector_version",
            "observed_value", "threshold", "description", "evidence",
            "plan_id", "recovery_diagnosis", "proposed_actions", "plan_status", "verification_status",
            "audit_event_id", "audit_timestamp", "audit_action", "audit_actor_type",
            "audit_actor_id", "audit_result", "audit_reason", "audit_policy_version"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in records:
            row_copy = dict(r)
            if isinstance(row_copy.get("evidence"), (dict, list)):
                row_copy["evidence"] = json.dumps(row_copy["evidence"])
            if isinstance(row_copy.get("proposed_actions"), (dict, list)):
                row_copy["proposed_actions"] = json.dumps(row_copy["proposed_actions"])
            writer.writerow(row_copy)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"cortexheal_audit_export_{date_str}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@app.get("/api/incidents")
def api_get_incidents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_user)
):
    incidents = get_incidents()
    paginated = incidents[skip : skip + limit]
    
    # Enrich with run status
    result = []
    for inc in paginated:
        run = get_run(inc.run_id)
        inc_dict = inc.model_dump()
        inc_dict['run_status'] = run.status if run else 'unknown'
        inc_dict['protection_mode'] = run.protection_mode if run else 'UNKNOWN'
        result.append(inc_dict)
    
    return {
        "data": result,
        "total": len(incidents),
        "skip": skip,
        "limit": limit
    }

@app.get("/api/incidents/{incident_id}")
def api_get_incident(incident_id: str, user: User = Depends(get_current_user)):
    inc = get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    run = get_run(inc.run_id)
    inc_dict = inc.model_dump()
    inc_dict['run_status'] = run.status if run else 'unknown'
    inc_dict['protection_mode'] = run.protection_mode if run else 'UNKNOWN'
    return inc_dict

@app.get("/api/runs")
def api_get_runs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_user)
):
    runs = get_all_runs()
    return {
        "data": runs[skip : skip + limit],
        "total": len(runs),
        "skip": skip,
        "limit": limit
    }

@app.get("/api/runs/{run_id}")
def api_get_run(run_id: str, user: User = Depends(get_current_user)):
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run

@app.get("/api/runs/{run_id}/timeline")
def api_get_run_timeline(run_id: str, user: User = Depends(get_current_user)):
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    events = get_events_for_run(run_id)
    audits = get_audit_events_for_run(run_id)
    incidents = [i for i in get_incidents() if i.run_id == run_id]
    
    # Merge into a single chronological timeline
    timeline = []
    
    for e in events:
        timeline.append({
            "type": "event",
            "timestamp": e.timestamp,
            "data": e.model_dump()
        })
        
    for a in audits:
        timeline.append({
            "type": "audit",
            "timestamp": a.timestamp,
            "data": a.model_dump()
        })
        
    for i in incidents:
        timeline.append({
            "type": "incident",
            "timestamp": i.triggered_at,
            "data": i.model_dump()
        })
        
    # Sort by timestamp
    timeline.sort(key=lambda x: x["timestamp"])
    return timeline

@app.post("/api/runs/{run_id}/resume")
def api_resume_run(run_id: str, user: User = Depends(require_operator)):
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    if run.protection_mode == 'DISABLED':
        raise HTTPException(status_code=400, detail="Cannot resume a run that is PROTECTION_DISABLED")
        
    try:
        protection_controller.resume(run_id, actor_id=user.username, reason="Resumed via Control Plane")
        broadcast_sse_event("run_resumed", {
            "run_id": run_id,
            "actor": user.username,
        }, run_id=run_id)
        return {"status": "success", "message": f"Resume requested for run {run_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def api_health():
    return {"status": "HEALTHY"}

@app.get("/readiness")
def api_readiness():
    try:
        from cortexheal.storage.postgres import get_connection
        # Fast DB check
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        
        # Fast telemetry check
        from cortexheal.runtime.collector import collector
        if not collector._worker_thread or not collector._worker_thread.is_alive():
            return {"status": "DEGRADED", "reason": "Background telemetry worker is dead"}
            
        return {"status": "HEALTHY"}
    except Exception as e:
        return {"status": "NOT_READY", "reason": f"DB connection failed: {e}"}

@app.get("/api/incidents/{incident_id}/plan")
def api_get_recovery_plan(incident_id: str, user: User = Depends(get_current_user)):
    # Autogenerate or retrieve
    plan = get_recovery_plan_by_incident(incident_id)
    if not plan:
        incident = get_incident(incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        plan = recovery_engine.generate_plan(incident)
    return plan.model_dump()

@app.post("/api/incidents/{incident_id}/plan/approve")
def api_approve_recovery_plan(incident_id: str, user: User = Depends(require_operator)):
    plan = get_recovery_plan_by_incident(incident_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    success = recovery_executor.execute_plan(plan, user.role, user.username)
    if not success:
        raise HTTPException(status_code=400, detail="Plan execution failed or was denied")
    
    broadcast_sse_event("plan_approved", {
        "incident_id": incident_id,
        "plan_id": plan.plan_id,
        "actor": user.username,
    }, run_id=plan.run_id)
    return {"status": "success", "message": "Plan executed successfully"}

@app.post("/api/incidents/{incident_id}/plan/reject")
def api_reject_recovery_plan(incident_id: str, user: User = Depends(require_operator)):
    plan = get_recovery_plan_by_incident(incident_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    success = recovery_executor.reject_plan(plan, user.role, user.username)
    if not success:
        raise HTTPException(status_code=400, detail="Could not reject plan")
    
    broadcast_sse_event("plan_rejected", {
        "incident_id": incident_id,
        "plan_id": plan.plan_id,
        "actor": user.username,
    }, run_id=plan.run_id)
    return {"status": "success", "message": "Plan rejected"}



@app.get("/api/stream")
async def api_stream(request: Request, run_id: str = None, user: User = Depends(get_current_user)):
    """
    Stream real-time updates for the dashboard.
    Scalable: Uses a single global DB polling task and async queues per client.
    """
    client_queue = asyncio.Queue(maxsize=10)
    
    # Track by run_id (or 'global' if not provided)
    sub_key = run_id if run_id else 'global'
    if sub_key not in SSE_CLIENTS:
        SSE_CLIENTS[sub_key] = set()
    SSE_CLIENTS[sub_key].add(client_queue)
    
    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    # Wait for a typed event from the broadcaster
                    message = await asyncio.wait_for(client_queue.get(), timeout=5.0)
                    if isinstance(message, dict):
                        yield {
                            "event": message.get("event", "update"),
                            "data": json.dumps(message.get("data", {}))
                        }
                    else:
                        # Backward compatibility for any plain string messages
                        yield {
                            "event": "update",
                            "data": str(message)
                        }
                except asyncio.TimeoutError:
                    # Send a heartbeat every 5 seconds to keep connection alive
                    yield {
                        "event": "heartbeat",
                        "data": "ping"
                    }
        finally:
            if sub_key in SSE_CLIENTS:
                SSE_CLIENTS[sub_key].discard(client_queue)
                if not SSE_CLIENTS[sub_key]:
                    del SSE_CLIENTS[sub_key]
            
    return EventSourceResponse(event_generator())

# --- STATIC FILES ---
# We serve the frontend directly from a static directory
frontend_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(frontend_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    # Fallback to index.html for SPA routing
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Frontend not built yet. Place index.html in cortexheal/server/static/"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
