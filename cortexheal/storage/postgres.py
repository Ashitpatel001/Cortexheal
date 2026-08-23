import os
import time
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager
from typing import List, Optional, Any, Dict
import json
import logging
import threading

from cortexheal.config import settings
from cortexheal.models.events import RuntimeEvent
from cortexheal.models.run import AgentRun
from cortexheal.models.incident import Incident
from cortexheal.models.protection import AuditEvent
from cortexheal.models.auth import ApiKey
from cortexheal.models.alerting import WebhookConfig, NotificationRecord

logger = logging.getLogger(__name__)

# Global connection pool
_pool = None

def init_pool():
    global _pool
    if _pool is None:
        max_conn = max(100, settings.DB_POOL_SIZE * 10)
        _pool = psycopg2.pool.ThreadedConnectionPool(
            1,
            max_conn,
            settings.DATABASE_URL
        )
        logger.info(f"Initialized PostgreSQL ThreadedConnectionPool (max={max_conn})")

_pool_lock = threading.Lock()

@contextmanager
def get_connection():
    conn = None
    start_wait = time.time()
    while conn is None:
        with _pool_lock:
            if _pool is None:
                init_pool()
            try:
                conn = _pool.getconn()
            except psycopg2.pool.PoolError:
                if time.time() - start_wait > 5.0:
                    raise
        if conn is None:
            time.sleep(0.01)  # Wait 10ms for connection to return to pool
            
    try:
        yield conn
    finally:
        with _pool_lock:
            if _pool and conn:
                _pool.putconn(conn)

def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Runs table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id VARCHAR(36) PRIMARY KEY,
                    agent_id VARCHAR(255) NOT NULL,
                    framework VARCHAR(50),
                    model VARCHAR(100),
                    provider VARCHAR(100),
                    status VARCHAR(50),
                    start_time TIMESTAMP WITH TIME ZONE,
                    end_time TIMESTAMP WITH TIME ZONE,
                    total_tokens INTEGER DEFAULT 0,
                    total_cost DOUBLE PRECISION,
                    failure_reason TEXT
                )
            """)
            try:
                cur.execute("ALTER TABLE runs ADD COLUMN IF NOT EXISTS protection_mode VARCHAR(20) DEFAULT 'ACTIVE'")
            except Exception:
                pass 
            
            # Events table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id VARCHAR(36) PRIMARY KEY,
                    run_id VARCHAR(36) REFERENCES runs(run_id),
                    agent_id VARCHAR(255),
                    parent_run_id VARCHAR(36),
                    timestamp TIMESTAMP WITH TIME ZONE,
                    event_type VARCHAR(50),
                    tool VARCHAR(255),
                    arguments_hash VARCHAR(64),
                    response_hash VARCHAR(64),
                    tokens_prompt INTEGER,
                    tokens_completion INTEGER,
                    tokens_total INTEGER,
                    cost DOUBLE PRECISION,
                    latency_ms INTEGER,
                    state_hash VARCHAR(64),
                    status VARCHAR(50),
                    sequence_number INTEGER,
                    framework VARCHAR(50),
                    model VARCHAR(100),
                    provider VARCHAR(100),
                    trace_id VARCHAR(100),
                    span_id VARCHAR(100),
                    idempotency_key VARCHAR(100) UNIQUE,
                    environment VARCHAR(50),
                    policy_version VARCHAR(50),
                    detector_version VARCHAR(50)
                )
            """)
            
            # Indexes for queries
            cur.execute("CREATE INDEX IF NOT EXISTS idx_events_run_id ON events(run_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_events_agent_id ON events(agent_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)")
            
            # Incidents table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id VARCHAR(36) PRIMARY KEY,
                    run_id VARCHAR(36) REFERENCES runs(run_id),
                    agent_id VARCHAR(255),
                    failure_type VARCHAR(50),
                    severity VARCHAR(20),
                    status VARCHAR(20),
                    detector VARCHAR(50),
                    detector_version VARCHAR(20),
                    trigger_event_id VARCHAR(36),
                    triggered_at TIMESTAMP WITH TIME ZONE,
                    evidence JSONB,
                    observed_value JSONB,
                    threshold JSONB,
                    description TEXT,
                    UNIQUE(run_id, failure_type, detector_version)
                )
            """)
            
            # Audit Events table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id VARCHAR(36) PRIMARY KEY,
                    run_id VARCHAR(36),
                    incident_id VARCHAR(36),
                    timestamp TIMESTAMP WITH TIME ZONE,
                    action VARCHAR(50),
                    actor VARCHAR(50), -- deprecated
                    result VARCHAR(50),
                    reason TEXT,
                    policy_version VARCHAR(20)
                )
            """)
            try:
                cur.execute("ALTER TABLE audit_events ADD COLUMN IF NOT EXISTS actor_type VARCHAR(20) DEFAULT 'SYSTEM'")
                cur.execute("ALTER TABLE audit_events ADD COLUMN IF NOT EXISTS actor_id VARCHAR(100) DEFAULT 'SYSTEM'")
            except Exception:
                pass
                
            cur.execute("""
                CREATE TABLE IF NOT EXISTS recovery_plans (
                    plan_id VARCHAR(36) PRIMARY KEY,
                    incident_id VARCHAR(36),
                    run_id VARCHAR(36),
                    diagnosis TEXT,
                    confidence FLOAT,
                    proposed_actions JSONB,
                    risk_level VARCHAR(20),
                    created_at TIMESTAMP WITH TIME ZONE,
                    planner_type VARCHAR(50),
                    status VARCHAR(20),
                    snapshot_run_status VARCHAR(50) DEFAULT 'unknown',
                    snapshot_sequence_number INTEGER DEFAULT 0,
                    ai_analysis JSONB,
                    verification_status VARCHAR(50)
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS recovery_actions (
                    action_id VARCHAR(36) PRIMARY KEY,
                    run_id VARCHAR(36),
                    incident_id VARCHAR(36),
                    action_type VARCHAR(50),
                    reason TEXT,
                    parameters JSONB,
                    risk_level VARCHAR(20),
                    created_at TIMESTAMP WITH TIME ZONE,
                    status VARCHAR(20)
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS pattern_records (
                    pattern_id VARCHAR(36) PRIMARY KEY,
                    framework VARCHAR(50),
                    agent_id VARCHAR(255),
                    failure_type VARCHAR(50),
                    fingerprint VARCHAR(64) UNIQUE,
                    fingerprint_version VARCHAR(20),
                    occurrences INTEGER DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE,
                    updated_at TIMESTAMP WITH TIME ZONE,
                    is_promotion_candidate BOOLEAN DEFAULT FALSE
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS recovery_outcomes (
                    outcome_id VARCHAR(36) PRIMARY KEY,
                    run_id VARCHAR(36),
                    incident_id VARCHAR(36),
                    pattern_id VARCHAR(36) REFERENCES pattern_records(pattern_id),
                    action_type VARCHAR(50),
                    ai_recommendation VARCHAR(50),
                    human_decision VARCHAR(50),
                    approval_actor VARCHAR(100),
                    execution_result VARCHAR(50),
                    verification_result VARCHAR(50),
                    timestamp TIMESTAMP WITH TIME ZONE
                )
            """)
            
            # API Keys table (Multi-tenant)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    key_id VARCHAR(36) PRIMARY KEY,
                    key_hash VARCHAR(64) UNIQUE NOT NULL,
                    key_prefix VARCHAR(32) NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    org_id VARCHAR(100) NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    last_used_at TIMESTAMP WITH TIME ZONE,
                    revoked_at TIMESTAMP WITH TIME ZONE
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_org ON api_keys(org_id)")
            
            # Webhook configurations table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS webhook_configs (
                    webhook_id VARCHAR(36) PRIMARY KEY,
                    org_id VARCHAR(100) NOT NULL,
                    target_type VARCHAR(50) NOT NULL,
                    url TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT TRUE,
                    secret_token TEXT,
                    min_severity VARCHAR(20) DEFAULT 'HIGH',
                    escalation_timeout_minutes INTEGER DEFAULT 15,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_webhook_configs_org ON webhook_configs(org_id)")

            # Notification audit records table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS notification_records (
                    notification_id VARCHAR(36) PRIMARY KEY,
                    org_id VARCHAR(100) NOT NULL,
                    incident_id VARCHAR(36) NOT NULL,
                    run_id VARCHAR(36) NOT NULL,
                    notification_type VARCHAR(50) NOT NULL,
                    target_url TEXT NOT NULL,
                    payload JSONB NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    status_code INTEGER,
                    response_body TEXT,
                    sent_at TIMESTAMP WITH TIME ZONE NOT NULL
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_notifications_org ON notification_records(org_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_notifications_incident ON notification_records(incident_id)")

            conn.commit()

def save_run(run: AgentRun):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO runs (
                    run_id, agent_id, framework, model, provider, status, 
                    start_time, end_time, total_tokens, total_cost, failure_reason, protection_mode
                ) VALUES (
                    %(run_id)s, %(agent_id)s, %(framework)s, %(model)s, %(provider)s, %(status)s,
                    %(start_time)s, %(end_time)s, %(total_tokens)s, %(total_cost)s, %(failure_reason)s, %(protection_mode)s
                ) ON CONFLICT (run_id) DO UPDATE SET
                    status = CASE 
                        WHEN runs.status IN ('pause_requested', 'paused') AND EXCLUDED.status = 'running' THEN runs.status
                        ELSE EXCLUDED.status
                    END,
                    end_time = COALESCE(EXCLUDED.end_time, runs.end_time),
                    total_tokens = EXCLUDED.total_tokens,
                    total_cost = EXCLUDED.total_cost,
                    failure_reason = COALESCE(EXCLUDED.failure_reason, runs.failure_reason),
                    protection_mode = COALESCE(EXCLUDED.protection_mode, runs.protection_mode)
            """, run.model_dump())
            conn.commit()

def save_event(event: RuntimeEvent) -> bool:
    """Saves an event. Returns True if inserted, False if it was a duplicate."""
    dump = event.model_dump()
    dump["tokens_prompt"] = dump["tokens"]["prompt"] if dump.get("tokens") else None
    dump["tokens_completion"] = dump["tokens"]["completion"] if dump.get("tokens") else None
    dump["tokens_total"] = dump["tokens"]["total"] if dump.get("tokens") else None
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                if 'status' not in dump:
                    logger.error(f"DUMP MISSING STATUS! Keys: {dump.keys()}")
                cur.execute("""
                    INSERT INTO events (
                        event_id, run_id, agent_id, parent_run_id, timestamp, event_type,
                        tool, arguments_hash, response_hash, tokens_prompt, tokens_completion, tokens_total,
                        cost, latency_ms, state_hash, status, sequence_number, framework,
                        model, provider, trace_id, span_id, idempotency_key, environment,
                        policy_version, detector_version
                    ) VALUES (
                        %(event_id)s, %(run_id)s, %(agent_id)s, %(parent_run_id)s, %(timestamp)s, %(event_type)s,
                        %(tool)s, %(arguments_hash)s, %(response_hash)s, %(tokens_prompt)s, %(tokens_completion)s, %(tokens_total)s,
                        %(cost)s, %(latency_ms)s, %(state_hash)s, %(status)s, %(sequence_number)s, %(framework)s,
                        %(model)s, %(provider)s, %(trace_id)s, %(span_id)s, %(idempotency_key)s, %(environment)s,
                        %(policy_version)s, %(detector_version)s
                    ) ON CONFLICT (idempotency_key) DO NOTHING
                """, dump)
                inserted = cur.rowcount > 0
                conn.commit()
                return inserted
            except Exception as e:
                conn.rollback()
                raise e

def save_incident(incident: Incident) -> bool:
    dump = incident.model_dump()
    dump['evidence'] = json.dumps(dump['evidence'])
    dump['observed_value'] = json.dumps(dump['observed_value'])
    dump['threshold'] = json.dumps(dump['threshold'])
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO incidents (
                        incident_id, run_id, agent_id, failure_type, severity, status,
                        detector, detector_version, trigger_event_id, triggered_at,
                        evidence, observed_value, threshold, description
                    ) VALUES (
                        %(incident_id)s, %(run_id)s, %(agent_id)s, %(failure_type)s, %(severity)s, %(status)s,
                        %(detector)s, %(detector_version)s, %(trigger_event_id)s, %(triggered_at)s,
                        %(evidence)s, %(observed_value)s, %(threshold)s, %(description)s
                    ) ON CONFLICT (run_id, failure_type, detector_version) DO NOTHING
                """, dump)
                inserted = cur.rowcount > 0
                conn.commit()
                return inserted
            except Exception as e:
                conn.rollback()
                raise e

def get_run(run_id: str) -> Optional[AgentRun]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM runs WHERE run_id = %s", (run_id,))
            row = cur.fetchone()
            
    if not row:
        return None
        
    if row.get('start_time'): row['start_time'] = row['start_time'].isoformat()
    if row.get('end_time'): row['end_time'] = row['end_time'].isoformat()
    return AgentRun(**row)

def update_run_status(run_id: str, new_status: str, expected_statuses: Optional[List[str]] = None) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            if expected_statuses:
                cur.execute(
                    "UPDATE runs SET status = %s WHERE run_id = %s AND status = ANY(%s)", 
                    (new_status, run_id, expected_statuses)
                )
            else:
                cur.execute("UPDATE runs SET status = %s WHERE run_id = %s", (new_status, run_id))
            updated = cur.rowcount > 0
            conn.commit()
            return updated

def update_run_protection_mode(run_id: str, new_mode: str) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE runs SET protection_mode = %s WHERE run_id = %s", (new_mode, run_id))
            updated = cur.rowcount > 0
            conn.commit()
            return updated

def save_audit_event(event: Any) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO audit_events (
                    event_id, run_id, incident_id, timestamp, action, actor_type, actor_id, result, reason, policy_version
                ) VALUES (
                    %(event_id)s, %(run_id)s, %(incident_id)s, %(timestamp)s, %(action)s, %(actor_type)s, %(actor_id)s, %(result)s, %(reason)s, %(policy_version)s
                )
            """, event.model_dump())
            conn.commit()

def save_recovery_plan(plan: Any) -> None:
    data = plan.model_dump()
    data['proposed_actions'] = json.dumps(data['proposed_actions'])
    if data['ai_analysis']:
        data['ai_analysis'] = json.dumps(data['ai_analysis'])
        
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO recovery_plans (
                    plan_id, incident_id, run_id, diagnosis, confidence, proposed_actions, risk_level, 
                    created_at, planner_type, status, snapshot_run_status, snapshot_sequence_number,
                    ai_analysis, verification_status
                ) VALUES (
                    %(plan_id)s, %(incident_id)s, %(run_id)s, %(diagnosis)s, %(confidence)s, %(proposed_actions)s, %(risk_level)s, 
                    %(created_at)s, %(planner_type)s, %(status)s, %(snapshot_run_status)s, %(snapshot_sequence_number)s,
                    %(ai_analysis)s, %(verification_status)s
                )
                ON CONFLICT (plan_id) DO UPDATE SET 
                    status = EXCLUDED.status,
                    verification_status = EXCLUDED.verification_status
            """, data)
            conn.commit()

def get_recovery_plan_by_incident(incident_id: str) -> Optional[Any]:
    from cortexheal.models.recovery import RecoveryPlan
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM recovery_plans WHERE incident_id = %s ORDER BY created_at DESC LIMIT 1", (incident_id,))
            row = cur.fetchone()
            
    if not row:
        return None
    row['created_at'] = row['created_at'].isoformat()
    if isinstance(row['proposed_actions'], str):
        row['proposed_actions'] = json.loads(row['proposed_actions'])
    if row.get('ai_analysis') and isinstance(row['ai_analysis'], str):
        row['ai_analysis'] = json.loads(row['ai_analysis'])
    return RecoveryPlan(**row)

def save_recovery_action(action: Any) -> None:
    data = action.model_dump()
    data['parameters'] = json.dumps(data['parameters'])
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO recovery_actions (
                    action_id, run_id, incident_id, action_type, reason, parameters, risk_level, created_at, status
                ) VALUES (
                    %(action_id)s, %(run_id)s, %(incident_id)s, %(action_type)s, %(reason)s, %(parameters)s, %(risk_level)s, %(created_at)s, %(status)s
                )
                ON CONFLICT (action_id) DO UPDATE SET status = EXCLUDED.status
            """, data)
            conn.commit()

def get_events_for_run(run_id: str) -> List[RuntimeEvent]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM events WHERE run_id = %s ORDER BY sequence_number ASC", (run_id,))
            rows = cur.fetchall()
            
    events = []
    for row in rows:
        if row.get('timestamp'): row['timestamp'] = row['timestamp'].isoformat()
        if row.get('tokens_total') is not None:
            row['tokens'] = {
                "prompt": row.get('tokens_prompt', 0),
                "completion": row.get('tokens_completion', 0),
                "total": row.get('tokens_total', 0)
            }
        events.append(RuntimeEvent(**row))
    return events

def get_incidents() -> List[Incident]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM incidents ORDER BY triggered_at DESC")
            rows = cur.fetchall()
            
    incidents = []
    for row in rows:
        if hasattr(row.get('triggered_at'), 'isoformat'):
            row['triggered_at'] = row['triggered_at'].isoformat()
        incidents.append(Incident(**row))
    return incidents

def get_incident(incident_id: str) -> Optional[Incident]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM incidents WHERE incident_id = %s", (incident_id,))
            row = cur.fetchone()
            
    if not row: return None
    if hasattr(row.get('triggered_at'), 'isoformat'):
        row['triggered_at'] = row['triggered_at'].isoformat()
    return Incident(**row)

def get_all_runs() -> List[AgentRun]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM runs ORDER BY start_time DESC")
            rows = cur.fetchall()
            
    runs = []
    for row in rows:
        if row.get('start_time'): row['start_time'] = row['start_time'].isoformat()
        if row.get('end_time'): row['end_time'] = row['end_time'].isoformat()
        runs.append(AgentRun(**row))
    return runs

def get_audit_events_for_run(run_id: str) -> List[AuditEvent]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM audit_events WHERE run_id = %s ORDER BY timestamp ASC", (run_id,))
            rows = cur.fetchall()
            
    audits = []
    for row in rows:
        if row.get('timestamp'): row['timestamp'] = row['timestamp'].isoformat()
        audits.append(AuditEvent(**row))
    return audits

def save_pattern_record(pattern: Any) -> None:
    data = pattern.model_dump()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO pattern_records (
                    pattern_id, framework, agent_id, failure_type, fingerprint, 
                    fingerprint_version, occurrences, created_at, updated_at, is_promotion_candidate
                ) VALUES (
                    %(pattern_id)s, %(framework)s, %(agent_id)s, %(failure_type)s, %(fingerprint)s,
                    %(fingerprint_version)s, %(occurrences)s, %(created_at)s, %(updated_at)s, %(is_promotion_candidate)s
                )
                ON CONFLICT (fingerprint) DO UPDATE SET 
                    occurrences = EXCLUDED.occurrences,
                    updated_at = EXCLUDED.updated_at,
                    is_promotion_candidate = EXCLUDED.is_promotion_candidate
            """, data)
            conn.commit()

def get_pattern_by_fingerprint(fingerprint: str) -> Optional[Any]:
    from cortexheal.models.learning import PatternRecord
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM pattern_records WHERE fingerprint = %s", (fingerprint,))
            row = cur.fetchone()
            
    if not row: return None
    row['created_at'] = row['created_at'].isoformat()
    row['updated_at'] = row['updated_at'].isoformat()
    return PatternRecord(**row)

def save_recovery_outcome(outcome: Any) -> None:
    data = outcome.model_dump()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO recovery_outcomes (
                    outcome_id, run_id, incident_id, pattern_id, action_type, ai_recommendation,
                    human_decision, approval_actor, execution_result, verification_result, timestamp
                ) VALUES (
                    %(outcome_id)s, %(run_id)s, %(incident_id)s, %(pattern_id)s, %(action_type)s, %(ai_recommendation)s,
                    %(human_decision)s, %(approval_actor)s, %(execution_result)s, %(verification_result)s, %(timestamp)s
                )
            """, data)
            conn.commit()

def get_outcomes_for_pattern(pattern_id: str) -> List[Any]:
    from cortexheal.models.learning import RecoveryOutcome
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM recovery_outcomes WHERE pattern_id = %s ORDER BY timestamp DESC", (pattern_id,))
            rows = cur.fetchall()
            
    outcomes = []
    for row in rows:
        row['timestamp'] = row['timestamp'].isoformat()
        outcomes.append(RecoveryOutcome(**row))
    return outcomes

_API_KEY_CACHE = {}  # key_hash -> (ApiKey, timestamp)
_API_KEY_CACHE_LOCK = threading.Lock()
_CACHE_TTL = 30.0  # seconds

_LAST_USED_THROTTLE = {}  # key_id -> last_updated_time
_LAST_USED_LOCK = threading.Lock()

def save_api_key(api_key: ApiKey) -> ApiKey:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO api_keys (
                    key_id, key_hash, key_prefix, name, org_id, role, created_at, last_used_at, revoked_at
                ) VALUES (
                    %(key_id)s, %(key_hash)s, %(key_prefix)s, %(name)s, %(org_id)s, %(role)s,
                    %(created_at)s, %(last_used_at)s, %(revoked_at)s
                ) ON CONFLICT (key_id) DO UPDATE SET
                    last_used_at = EXCLUDED.last_used_at,
                    revoked_at = EXCLUDED.revoked_at
            """, api_key.model_dump())
            conn.commit()
    with _API_KEY_CACHE_LOCK:
        _API_KEY_CACHE[api_key.key_hash] = (api_key, time.time())
    return api_key

def get_api_key_by_hash(key_hash: str) -> Optional[ApiKey]:
    now = time.time()
    with _API_KEY_CACHE_LOCK:
        if key_hash in _API_KEY_CACHE:
            cached_key, cached_at = _API_KEY_CACHE[key_hash]
            if now - cached_at < _CACHE_TTL:
                return cached_key

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM api_keys WHERE key_hash = %s", (key_hash,))
            row = cur.fetchone()
    if not row:
        return None
    api_key = ApiKey(**row)
    with _API_KEY_CACHE_LOCK:
        _API_KEY_CACHE[key_hash] = (api_key, now)
    return api_key

def get_api_keys_by_org(org_id: str) -> List[ApiKey]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM api_keys WHERE org_id = %s ORDER BY created_at DESC", (org_id,))
            rows = cur.fetchall()
    return [ApiKey(**row) for row in rows]

def get_api_key_by_id_and_org(key_id: str, org_id: str) -> Optional[ApiKey]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM api_keys WHERE key_id = %s AND org_id = %s", (key_id, org_id))
            row = cur.fetchone()
    if not row:
        return None
    return ApiKey(**row)

def revoke_api_key(key_id: str, org_id: str) -> bool:
    """Revoke API key if it belongs to org_id. Returns True if revoked, False if not found."""
    from datetime import datetime, timezone
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE api_keys 
                SET revoked_at = %s 
                WHERE key_id = %s AND org_id = %s AND revoked_at IS NULL
            """, (datetime.now(timezone.utc), key_id, org_id))
            conn.commit()
            success = cur.rowcount > 0

    with _API_KEY_CACHE_LOCK:
        _API_KEY_CACHE.clear()
    return success

def update_api_key_last_used(key_id: str) -> None:
    now = time.time()
    with _LAST_USED_LOCK:
        last_ts = _LAST_USED_THROTTLE.get(key_id, 0)
        if now - last_ts < 5.0:  # Update DB at most once every 5 seconds per key
            return
        _LAST_USED_THROTTLE[key_id] = now
        
    from datetime import datetime, timezone
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE api_keys SET last_used_at = %s WHERE key_id = %s", (datetime.now(timezone.utc), key_id))
                conn.commit()
    except Exception as e:
        logger.warning(f"Failed to update last_used_at for key {key_id}: {e}")

# -----------------------------------------------------------------------------
# Alerting & Webhook Management
# -----------------------------------------------------------------------------

def save_webhook_config(config: WebhookConfig) -> WebhookConfig:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO webhook_configs (
                    webhook_id, org_id, target_type, url, enabled, secret_token,
                    min_severity, escalation_timeout_minutes, created_at
                ) VALUES (
                    %(webhook_id)s, %(org_id)s, %(target_type)s, %(url)s, %(enabled)s, %(secret_token)s,
                    %(min_severity)s, %(escalation_timeout_minutes)s, %(created_at)s
                ) ON CONFLICT (webhook_id) DO UPDATE SET
                    target_type = EXCLUDED.target_type,
                    url = EXCLUDED.url,
                    enabled = EXCLUDED.enabled,
                    secret_token = EXCLUDED.secret_token,
                    min_severity = EXCLUDED.min_severity,
                    escalation_timeout_minutes = EXCLUDED.escalation_timeout_minutes
            """, config.model_dump())
            conn.commit()
    return config

def get_webhook_configs_by_org(org_id: str) -> List[WebhookConfig]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM webhook_configs WHERE org_id = %s ORDER BY created_at DESC", (org_id,))
            rows = cur.fetchall()
    return [WebhookConfig(**row) for row in rows]

def get_active_webhook_configs_by_org(org_id: str) -> List[WebhookConfig]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM webhook_configs WHERE org_id = %s AND enabled = TRUE", (org_id,))
            rows = cur.fetchall()
    return [WebhookConfig(**row) for row in rows]

def get_webhook_config_by_id_and_org(webhook_id: str, org_id: str) -> Optional[WebhookConfig]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM webhook_configs WHERE webhook_id = %s AND org_id = %s", (webhook_id, org_id))
            row = cur.fetchone()
    if not row:
        return None
    return WebhookConfig(**row)

def delete_webhook_config(webhook_id: str, org_id: str) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM webhook_configs WHERE webhook_id = %s AND org_id = %s", (webhook_id, org_id))
            conn.commit()
            return cur.rowcount > 0

# -----------------------------------------------------------------------------
# Notification History
# -----------------------------------------------------------------------------

def save_notification_record(record: NotificationRecord) -> NotificationRecord:
    data = record.model_dump()
    data["payload"] = Json(data["payload"])
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO notification_records (
                        notification_id, org_id, incident_id, run_id, notification_type,
                        target_url, payload, status, status_code, response_body, sent_at
                    ) VALUES (
                        %(notification_id)s, %(org_id)s, %(incident_id)s, %(run_id)s, %(notification_type)s,
                        %(target_url)s, %(payload)s, %(status)s, %(status_code)s, %(response_body)s, %(sent_at)s
                    )
                """, data)
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
    return record

def get_notifications_for_incident(incident_id: str) -> List[NotificationRecord]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM notification_records WHERE incident_id = %s ORDER BY sent_at DESC", (incident_id,))
            rows = cur.fetchall()
    return [NotificationRecord(**row) for row in rows]

def get_notifications_by_org(org_id: str, limit: int = 100) -> List[NotificationRecord]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM notification_records WHERE org_id = %s ORDER BY sent_at DESC LIMIT %s", (org_id, limit))
            rows = cur.fetchall()
    return [NotificationRecord(**row) for row in rows]

# -----------------------------------------------------------------------------
# Compliance & Audit Export Query
# -----------------------------------------------------------------------------

def get_audit_export_records(
    org_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    agent_id: Optional[str] = None,
    failure_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    query = """
        SELECT 
            i.incident_id,
            i.triggered_at,
            i.run_id,
            i.agent_id,
            COALESCE(r.framework, 'unknown') AS framework,
            r.model,
            r.provider,
            COALESCE(r.status, 'unknown') AS run_status,
            COALESCE(r.protection_mode, 'ACTIVE') AS protection_mode,
            i.failure_type,
            i.severity,
            i.status AS incident_status,
            i.detector,
            i.detector_version,
            i.observed_value,
            i.threshold,
            i.description,
            i.evidence,
            p.plan_id,
            p.diagnosis AS recovery_diagnosis,
            p.proposed_actions,
            p.status AS plan_status,
            p.verification_status,
            a.event_id AS audit_event_id,
            a.timestamp AS audit_timestamp,
            a.action AS audit_action,
            a.actor_type AS audit_actor_type,
            a.actor_id AS audit_actor_id,
            a.result AS audit_result,
            a.reason AS audit_reason,
            a.policy_version AS audit_policy_version
        FROM incidents i
        LEFT JOIN runs r ON i.run_id = r.run_id
        LEFT JOIN recovery_plans p ON i.incident_id = p.incident_id
        LEFT JOIN audit_events a ON i.incident_id = a.incident_id
        WHERE 1=1
    """
    params = []
    if from_date:
        query += " AND i.triggered_at >= %s"
        params.append(from_date)
    if to_date:
        query += " AND i.triggered_at <= %s"
        params.append(to_date)
    if agent_id:
        query += " AND i.agent_id = %s"
        params.append(agent_id)
    if failure_type:
        query += " AND i.failure_type = %s"
        params.append(failure_type)

    query += " ORDER BY i.triggered_at DESC, a.timestamp ASC"

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()

    formatted_rows = []
    for row in rows:
        row_dict = dict(row)
        for ts_field in ['triggered_at', 'audit_timestamp']:
            if hasattr(row_dict.get(ts_field), 'isoformat'):
                row_dict[ts_field] = row_dict[ts_field].isoformat()
        if isinstance(row_dict.get('evidence'), str):
            try:
                row_dict['evidence'] = json.loads(row_dict['evidence'])
            except Exception:
                pass
        if isinstance(row_dict.get('proposed_actions'), str):
            try:
                row_dict['proposed_actions'] = json.loads(row_dict['proposed_actions'])
            except Exception:
                pass
        formatted_rows.append(row_dict)
    return formatted_rows




