import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager
from typing import List, Optional, Any
import json
import logging
import threading

from cortexheal.config import settings
from cortexheal.models.events import RuntimeEvent
from cortexheal.models.run import AgentRun
from cortexheal.models.incident import Incident
from cortexheal.models.protection import AuditEvent

logger = logging.getLogger(__name__)

# Global connection pool
_pool = None

def init_pool():
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.SimpleConnectionPool(
            1,
            settings.DB_POOL_SIZE,
            settings.DATABASE_URL
        )
        logger.info(f"Initialized PostgreSQL connection pool (max={settings.DB_POOL_SIZE})")

_pool_lock = threading.Lock()

@contextmanager
def get_connection():
    with _pool_lock:
        if _pool is None:
            init_pool()
        conn = _pool.getconn()
    try:
        yield conn
    finally:
        with _pool_lock:
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
                cur.execute("ALTER TABLE runs ADD COLUMN IF NOT EXISTS protection_mode VARCHAR(20) DEFAULT 'DISABLED'")
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
            
            # Indexes
            cur.execute("CREATE INDEX IF NOT EXISTS idx_patterns_fingerprint ON pattern_records(fingerprint)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_pattern ON recovery_outcomes(pattern_id)")
            
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
                    status = EXCLUDED.status,
                    end_time = EXCLUDED.end_time,
                    total_tokens = EXCLUDED.total_tokens,
                    total_cost = EXCLUDED.total_cost,
                    failure_reason = EXCLUDED.failure_reason,
                    protection_mode = EXCLUDED.protection_mode
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

def update_run_status(run_id: str, new_status: str) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
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
        row['triggered_at'] = row['triggered_at'].isoformat()
        incidents.append(Incident(**row))
    return incidents

def get_incident(incident_id: str) -> Optional[Incident]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM incidents WHERE incident_id = %s", (incident_id,))
            row = cur.fetchone()
            
    if not row: return None
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
