from fastapi import FastAPI, HTTPException, Depends, Security, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader
from sse_starlette.sse import EventSourceResponse
import asyncio
from contextlib import asynccontextmanager

from cortexheal.storage.postgres import (
    get_incidents, get_incident, get_all_runs, get_run,
    get_events_for_run, get_audit_events_for_run, get_recovery_plan_by_incident
)
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
# Dictionary mapping run_id -> set of client queues
SSE_CLIENTS = {}

async def poll_db_for_updates():
    try:
        last_incident_count = len(get_incidents())
        last_run_count = len(get_all_runs())
    except Exception:
        last_incident_count = 0
        last_run_count = 0
        
    while True:
        await asyncio.sleep(2)
        if not SSE_CLIENTS:
            continue
        try:
            current_incidents = get_incidents()
            current_runs = get_all_runs()
            if len(current_incidents) > last_incident_count or len(current_runs) > last_run_count:
                last_incident_count = len(current_incidents)
                last_run_count = len(current_runs)
                
                # In V1, we just notify all connected queues that *something* updated
                # if they are subscribed. For true run-isolation, we would need to check
                # exactly which runs updated. For now, we notify all active clients.
                for run_id, queues in list(SSE_CLIENTS.items()):
                    for q in list(queues):
                        try:
                            q.put_nowait("update")
                        except asyncio.QueueFull:
                            pass
        except Exception as e:
            logger.error(f"SSE DB Polling error: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    polling_task = asyncio.create_task(poll_db_for_updates())
    yield
    # Shutdown
    polling_task.cancel()

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
        raise HTTPException(status_code=429, detail="Too Many Requests")
        
    RATE_LIMIT_STORE[client_ip].append(now)

app.router.dependencies.append(Depends(rate_limit))

# --- AUTHENTICATION & AUTHORIZATION ---
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

# Simple V1 Token-based Auth configured via ENV
VIEWER_TOKENS = settings.get_viewer_tokens()
OPERATOR_TOKENS = settings.get_operator_tokens()
ADMIN_TOKENS = settings.get_admin_tokens()

class User:
    def __init__(self, username: str, role: str):
        self.username = username
        self.role = role

def get_current_user(api_key: str = Security(api_key_header)):
    if api_key in ADMIN_TOKENS:
        return User(username="admin_user", role="ADMIN")
    elif api_key in OPERATOR_TOKENS:
        return User(username="operator_user", role="OPERATOR")
    elif api_key in VIEWER_TOKENS:
        return User(username="viewer_user", role="VIEWER")
    else:
        raise HTTPException(status_code=403, detail="Invalid API Key")

def require_operator(user: User = Depends(get_current_user)):
    if user.role not in ["OPERATOR", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Requires OPERATOR or ADMIN role")
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
        
    return {"status": "success", "message": "Plan executed successfully"}

@app.post("/api/incidents/{incident_id}/plan/reject")
def api_reject_recovery_plan(incident_id: str, user: User = Depends(require_operator)):
    plan = get_recovery_plan_by_incident(incident_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    success = recovery_executor.reject_plan(plan, user.role, user.username)
    if not success:
        raise HTTPException(status_code=400, detail="Could not reject plan")
        
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
                    # Wait for an update signal from the global poller
                    await asyncio.wait_for(client_queue.get(), timeout=5.0)
                    yield {
                        "event": "update",
                        "data": "new_data_available"
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
