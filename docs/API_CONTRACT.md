# CortexHeal API & SSE Contract Specification (Locked)

This specification defines the locked backend API contract for CortexHeal Control Plane. It outlines all REST endpoints, authentication and authorization roles, request/response schemas, and Server-Sent Events (SSE).

---

## 1. Authentication & Authorization

All API endpoints (except `/health`, `/readiness`, and `/metrics`) require an API key passed in the `X-API-Key` HTTP header.

### Roles & Permissions:
- **VIEWER**:
  - Read-only access to runs, incidents, timeline, plans, and SSE stream.
  - Allowed Tokens configured via `VIEWER_TOKENS` (default: `dev-viewer-key`).
- **OPERATOR**:
  - Full VIEWER access plus approval/rejection of recovery plans and resuming runs.
  - Allowed Tokens configured via `OPERATOR_TOKENS` (default: `dev-operator-key`).
- **ADMIN**:
  - Full system administrative access.
  - Allowed Tokens configured via `ADMIN_TOKENS` (default: `dev-admin-key`).

---

## 2. REST Endpoints

### 2.1 System & Health

#### `GET /health`
- **Auth**: None
- **Response**: `200 OK`

#### `GET /api/whoami`
- **Auth**: Required (`X-API-Key`)
- **Response**: `200 OK`
  ```json
  {
    "role": "VIEWER", // Or "OPERATOR" / "ADMIN"
    "org_id": "org_123"
  }
  ```

### 2.2 Authentication & API Key Management (ADMIN Only)

#### `POST /api/keys`
- **Auth**: Required (`ADMIN` role)
- **Request Body**:
  ```json
  {
    "name": "Production Worker",
    "role": "OPERATOR" // "VIEWER" | "OPERATOR" | "ADMIN"
  }
  ```
- **Response**: `200 OK` (Includes `raw_key` shown exactly once)
  ```json
  {
    "key_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "key_prefix": "ctx_operator_a1b...",
    "name": "Production Worker",
    "org_id": "org_123",
    "role": "OPERATOR",
    "created_at": "2026-08-22T21:00:00Z",
    "last_used_at": null,
    "revoked_at": null,
    "raw_key": "ctx_operator_a1b2c3d4..."
  }
  ```

#### `GET /api/keys`
- **Auth**: Required (`ADMIN` role)
- **Response**: `200 OK` (Returns only keys belonging to caller's `org_id`)
  ```json
  [
    {
      "key_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "key_prefix": "ctx_operator_a1b...",
      "name": "Production Worker",
      "org_id": "org_123",
      "role": "OPERATOR",
      "created_at": "2026-08-22T21:00:00Z",
      "last_used_at": "2026-08-22T21:05:00Z",
      "revoked_at": null
    }
  ]
  ```

#### `POST /api/keys/{key_id}/revoke`
- **Auth**: Required (`ADMIN` role)
- **Response**: `200 OK` (or `404 Not Found` if `key_id` does not exist in caller's `org_id`)
  ```json
  {
    "status": "success",
    "message": "API key 3fa85f64-5717-4562-b3fc-2c963f66afa6 revoked"
  }
  ```

#### `GET /readiness`
- **Auth**: None
- **Response**: `200 OK` (or `503 Service Unavailable` if database is down)
```json
{
  "status": "HEALTHY"
}
```

#### `GET /metrics`
- **Auth**: None
- **Description**: Prometheus scrape endpoint yielding standard Prometheus text exposition format metrics.

---

### 2.2 Incidents

#### `GET /api/incidents`
- **Auth**: `VIEWER`, `OPERATOR`, `ADMIN`
- **Query Parameters**:
  - `skip` (integer, default 0, ge 0)
  - `limit` (integer, default 50, ge 1, le 100)
- **Response**: `200 OK`
```json
{
  "data": [
    {
      "incident_id": "9780bb1a-6763-4509-a13d-999af27656ae",
      "run_id": "1faa03f5-50f6-45ff-909c-3d8fb207f323",
      "agent_id": "test_agent",
      "failure_type": "STUCK_LOOP",
      "severity": "HIGH",
      "status": "OPEN",
      "detector": "stuck_loop_detector",
      "detector_version": "1.0",
      "trigger_event_id": "c1f73ec2-9e90-482a-a9a7-ba5d45d8b8e0",
      "evidence": {
        "tool": "failing_tool",
        "consecutive_repetitions": 5,
        "arguments_hash": "a1b2c3...",
        "response_hash": "d4e5f6..."
      },
      "observed_value": 5.0,
      "threshold": 5.0,
      "description": "Tool 'failing_tool' repeated 5 consecutive times with identical signature",
      "triggered_at": "2026-08-20T19:34:50.123456Z",
      "run_status": "paused",
      "protection_mode": "ACTIVE"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 50
}
```

#### `GET /api/incidents/{incident_id}`
- **Auth**: `VIEWER`, `OPERATOR`, `ADMIN`
- **Response**: `200 OK`
```json
{
  "incident_id": "9780bb1a-6763-4509-a13d-999af27656ae",
  "run_id": "1faa03f5-50f6-45ff-909c-3d8fb207f323",
  "agent_id": "test_agent",
  "failure_type": "STUCK_LOOP",
  "severity": "HIGH",
  "status": "OPEN",
  "detector": "stuck_loop_detector",
  "detector_version": "1.0",
  "trigger_event_id": "c1f73ec2-9e90-482a-a9a7-ba5d45d8b8e0",
  "evidence": {
    "tool": "failing_tool",
    "consecutive_repetitions": 5
  },
  "observed_value": 5.0,
  "threshold": 5.0,
  "description": "Tool 'failing_tool' repeated 5 consecutive times with identical signature",
  "triggered_at": "2026-08-20T19:34:50.123456Z",
  "run_status": "paused",
  "protection_mode": "ACTIVE"
}
```

#### `GET /api/incidents/{incident_id}/plan`
- **Auth**: `VIEWER`, `OPERATOR`, `ADMIN`
- **Description**: Retrieves existing plan or generates a deterministic recovery plan (with AI provider analysis when configured).
- **Response**: `200 OK`
```json
{
  "plan_id": "f5b84c8a-c40d-4b8f-8d96-857cb315c1e0",
  "incident_id": "9780bb1a-6763-4509-a13d-999af27656ae",
  "run_id": "1faa03f5-50f6-45ff-909c-3d8fb207f323",
  "status": "PROPOSED",
  "risk_level": "LOW",
  "diagnosis": "Deterministic stuck loop on failing_tool.",
  "proposed_actions": [
    {
      "action_id": "b1e9c80a-9d6a-4d7a-8f51-7f8e36781290",
      "run_id": "1faa03f5-50f6-45ff-909c-3d8fb207f323",
      "incident_id": "9780bb1a-6763-4509-a13d-999af27656ae",
      "action_type": "RESUME",
      "reason": "Resume agent execution following operator review",
      "status": "PENDING"
    }
  ],
  "planner_type": "DETERMINISTIC",
  "verification_status": "RECOVERY_UNVERIFIED",
  "snapshot_run_status": "paused",
  "snapshot_sequence_number": 5,
  "created_at": "2026-08-20T19:34:52.000000Z"
}
```

#### `POST /api/incidents/{incident_id}/plan/approve`
- **Auth**: `OPERATOR`, `ADMIN`
- **Response**: `200 OK`
```json
{
  "status": "success",
  "message": "Plan executed successfully"
}
```

#### `POST /api/incidents/{incident_id}/plan/reject`
- **Auth**: `OPERATOR`, `ADMIN`
- **Response**: `200 OK`
```json
{
  "status": "success",
  "message": "Plan rejected"
}
```

---

### 2.3 Agent Runs

#### `GET /api/runs`
- **Auth**: `VIEWER`, `OPERATOR`, `ADMIN`
- **Query Parameters**:
  - `skip` (integer, default 0)
  - `limit` (integer, default 50)
- **Response**: `200 OK`
```json
{
  "data": [
    {
      "run_id": "1faa03f5-50f6-45ff-909c-3d8fb207f323",
      "agent_id": "test_agent",
      "framework": "langgraph",
      "status": "paused",
      "protection_mode": "ACTIVE",
      "start_time": "2026-08-20T19:34:45.000000Z",
      "last_updated": "2026-08-20T19:34:50.000000Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 50
}
```

#### `GET /api/runs/{run_id}`
- **Auth**: `VIEWER`, `OPERATOR`, `ADMIN`
- **Response**: `200 OK`
```json
{
  "run_id": "1faa03f5-50f6-45ff-909c-3d8fb207f323",
  "agent_id": "test_agent",
  "framework": "langgraph",
  "status": "paused",
  "protection_mode": "ACTIVE",
  "start_time": "2026-08-20T19:34:45.000000Z",
  "last_updated": "2026-08-20T19:34:50.000000Z"
}
```

#### `GET /api/runs/{run_id}/timeline`
- **Auth**: `VIEWER`, `OPERATOR`, `ADMIN`
- **Description**: Returns chronological timeline containing raw runtime events, audit log state transitions, and incident triggers.
- **Response**: `200 OK`
```json
[
  {
    "type": "event",
    "timestamp": "2026-08-20T19:34:45.000000Z",
    "data": {
      "run_id": "1faa03f5-50f6-45ff-909c-3d8fb207f323",
      "event_type": "RUN_STARTED",
      "sequence_number": 1
    }
  },
  {
    "type": "incident",
    "timestamp": "2026-08-20T19:34:50.000000Z",
    "data": {
      "incident_id": "9780bb1a-6763-4509-a13d-999af27656ae",
      "failure_type": "STUCK_LOOP"
    }
  },
  {
    "type": "audit",
    "timestamp": "2026-08-20T19:34:50.100000Z",
    "data": {
      "action": "PAUSE_REQUESTED",
      "actor_type": "SYSTEM",
      "result": "SUCCESS"
    }
  }
]
```

#### `POST /api/runs/{run_id}/resume`
- **Auth**: `OPERATOR`, `ADMIN`
- **Response**: `200 OK`
```json
{
  "status": "success",
  "message": "Resume requested for run 1faa03f5-50f6-45ff-909c-3d8fb207f323"
}
```

### 2.6 Outbound Alerting & Webhooks

#### `POST /api/webhooks`
- **Auth**: `ADMIN`
- **Description**: Registers a new outbound alert webhook destination for the caller's organization.
- **Request Body**:
  ```json
  {
    "url": "https://hooks.slack.com/services/T000/B000/XXXX",
    "target_type": "slack", // "slack" | "generic_webhook" | "pagerduty" | "opsgenie"
    "min_severity": "HIGH", // "HIGH" | "CRITICAL"
    "escalation_timeout_minutes": 15,
    "secret_token": "optional-bearer-token"
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "webhook_id": "98a74bcb-d3d8-4130-800a-13ec9255af65",
    "org_id": "org_123",
    "target_type": "slack",
    "url": "https://hooks.slack.com/services/T000/B000/XXXX",
    "enabled": true,
    "secret_token": null,
    "min_severity": "HIGH",
    "escalation_timeout_minutes": 15,
    "created_at": "2026-08-23T15:00:00Z"
  }
  ```

#### `GET /api/webhooks`
- **Auth**: `ADMIN`
- **Description**: Lists all registered webhooks for the caller's organization.
- **Response**: `200 OK` (Array of WebhookConfig objects)

#### `DELETE /api/webhooks/{webhook_id}`
- **Auth**: `ADMIN`
- **Description**: Deletes a registered webhook belonging to the caller's organization.
- **Response**: `200 OK` (`{"status": "success", "message": "Webhook <id> deleted"}`)

#### `GET /api/notifications`
- **Auth**: `OPERATOR`, `ADMIN`
- **Description**: Retrieves audit history of all dispatched notifications (initial alerts and escalations).
- **Query Parameters**:
  - `limit` (optional int, default 50, max 200)
- **Response**: `200 OK`
  ```json
  [
    {
      "notification_id": "2e7b9be8-ea5d-4b63-b7b1-ae9e2fd486c3",
      "org_id": "org_123",
      "incident_id": "0720f987-ddc4-4391-bd03-1098310a5fed",
      "run_id": "run_live_123",
      "notification_type": "INITIAL_ALERT", // "INITIAL_ALERT" | "ESCALATION"
      "target_url": "https://hooks.slack.com/services/...",
      "payload": { ... },
      "status": "SUCCESS", // "SUCCESS" | "FAILED"
      "status_code": 200,
      "response_body": "{\"status\":\"ok\"}",
      "sent_at": "2026-08-23T15:07:10Z"
    }
  ]
  ```

### 2.7 Compliance & Audit Export

#### `GET /api/audit/export`
- **Auth**: `OPERATOR`, `ADMIN`
- **Description**: Generates an end-to-end deterministic safety and compliance audit export containing safety incidents, recovery plans, and system/human verification actions.
- **Query Parameters**:
  - `format` (string, `json` | `csv`, default `json`)
  - `from_date` (optional string, ISO 8601 timestamp)
  - `to_date` (optional string, ISO 8601 timestamp)
  - `agent_id` (optional string)
  - `failure_type` (optional string, e.g. `STUCK_LOOP`, `BUDGET_EXCEEDED`)
- **Response**:
  - When `format=json`: `200 OK` (`application/json`) with metadata headers and array of structured incident/audit records.
  - When `format=csv`: `200 OK` (`text/csv`) with `Content-Disposition: attachment; filename="cortexheal_audit_export_YYYY-MM-DD.csv"`.

---

## 3. Server-Sent Events (SSE) Stream

### `GET /api/stream`
- **Auth**: `VIEWER`, `OPERATOR`, `ADMIN`
- **Query Parameters**:
  - `run_id` (optional string): Filter stream to a specific agent run ID. If omitted, connects to the `global` stream channel and receives events across all runs.
- **Headers**:
  - `Accept: text/event-stream`
  - `X-API-Key: <token>`
- **Wire Format**: Standard SSE protocol. All event payloads in the `data` field are JSON-serialized strings (except heartbeat `ping`).

---

### 3.1 Typed SSE Events & Payload Specifications

#### 1. `event: run_status_changed`
Emitted by the background reconciliation loop whenever an agent run transitions lifecycle status (e.g., `running` → `pause_requested` → `paused` → `resume_requested` → `running` → `completed`).
- **Channel**: `global` and `<run_id>`
- **Wire Payload**:
  ```http
  event: run_status_changed
  data: {"run_id": "1faa03f5-50f6-45ff-909c-3d8fb207f323", "old_status": "paused", "new_status": "resume_requested"}
  ```
- **JSON Schema**:
  ```json
  {
    "run_id": "string",
    "old_status": "string",
    "new_status": "string"
  }
  ```

#### 2. `event: incident_created`
Emitted when a safety detector (e.g., `stuck_loop_detector`, `budget_detector`) triggers and persists a new incident.
- **Channel**: `global` and `<run_id>`
- **Wire Payload**:
  ```http
  event: incident_created
  data: {"incident_id": "9780bb1a-6763-4509-a13d-999af27656ae", "run_id": "1faa03f5-50f6-45ff-909c-3d8fb207f323", "failure_type": "STUCK_LOOP", "severity": "HIGH"}
  ```
- **JSON Schema**:
  ```json
  {
    "incident_id": "string",
    "run_id": "string",
    "failure_type": "STUCK_LOOP | BUDGET_EXCEEDED",
    "severity": "LOW | MEDIUM | HIGH | CRITICAL"
  }
  ```

#### 3. `event: run_resumed`
Emitted in real-time when an operator or admin executes `POST /api/runs/{run_id}/resume`.
- **Channel**: `global` and `<run_id>`
- **Wire Payload**:
  ```http
  event: run_resumed
  data: {"run_id": "1faa03f5-50f6-45ff-909c-3d8fb207f323", "actor": "operator_user"}
  ```
- **JSON Schema**:
  ```json
  {
    "run_id": "string",
    "actor": "string"
  }
  ```

#### 4. `event: plan_approved`
Emitted in real-time when an operator or admin executes `POST /api/incidents/{incident_id}/plan/approve`.
- **Channel**: `global` and `<run_id>`
- **Wire Payload**:
  ```http
  event: plan_approved
  data: {"incident_id": "9780bb1a-6763-4509-a13d-999af27656ae", "plan_id": "f5b84c8a-c40d-4b8f-8d96-857cb315c1e0", "actor": "operator_user"}
  ```
- **JSON Schema**:
  ```json
  {
    "incident_id": "string",
    "plan_id": "string",
    "actor": "string"
  }
  ```

#### 5. `event: plan_rejected`
Emitted in real-time when an operator or admin executes `POST /api/incidents/{incident_id}/plan/reject`.
- **Channel**: `global` and `<run_id>`
- **Wire Payload**:
  ```http
  event: plan_rejected
  data: {"incident_id": "9780bb1a-6763-4509-a13d-999af27656ae", "plan_id": "f5b84c8a-c40d-4b8f-8d96-857cb315c1e0", "actor": "operator_user"}
  ```
- **JSON Schema**:
  ```json
  {
    "incident_id": "string",
    "plan_id": "string",
    "actor": "string"
  }
  ```

#### 6. `event: heartbeat`
Emitted every 5 seconds over active SSE connections for HTTP keep-alive.
- **Channel**: All connected clients
- **Wire Payload**:
  ```http
  event: heartbeat
  data: ping
  ```

---

### 3.2 Frontend Consumption Example (JavaScript / TypeScript)

```typescript
const eventSource = new EventSource('/api/stream?run_id=1faa03f5-50f6-45ff-909c-3d8fb207f323', {
  headers: { 'X-API-Key': 'dev-viewer-key' }
});

// 1. Status Transition Handling & Animation
eventSource.addEventListener('run_status_changed', (e: MessageEvent) => {
  const { run_id, old_status, new_status } = JSON.parse(e.data);
  console.log(`Run ${run_id} transitioned: ${old_status} -> ${new_status}`);
  // Animate UI badge: e.g. "paused" -> "resume_requested" -> "running"
  updateRunStatusBadge(run_id, old_status, new_status);
});

// 2. Incident Queue Real-time Ingestion
eventSource.addEventListener('incident_created', (e: MessageEvent) => {
  const incident = JSON.parse(e.data);
  console.log('New Incident Detected:', incident);
  prependIncidentQueue(incident);
});

// 3. Plan Approval / Execution
eventSource.addEventListener('plan_approved', (e: MessageEvent) => {
  const { incident_id, plan_id, actor } = JSON.parse(e.data);
  markPlanApproved(incident_id, actor);
});

// 4. Plan Rejection
eventSource.addEventListener('plan_rejected', (e: MessageEvent) => {
  const { incident_id, plan_id, actor } = JSON.parse(e.data);
  markPlanRejected(incident_id, actor);
});
```

