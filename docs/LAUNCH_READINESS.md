# CortexHeal Architecture & Operations Readiness

**Deterministic Safety & Circuit-Breaker Control Plane for AI Agents**  
*Document Version:* 1.0.0  
*Status:* **PRODUCTION READY**

---

## 1. System Architecture & Core Invariants

**CortexHeal** is an application-layer safety and circuit-breaker control plane designed for autonomous AI agents (LangGraph, AutoGen, and custom runtime loops). It intercepts runtime telemetry in real time and automatically trips circuit breakers when an agent loop becomes pathological (e.g. repeated identical tool calls or budget ceiling breaches).

```
   ┌─────────────────────────────────────────────────────────┐
   │                    Agent Application                    │
   │  ┌───────────────┐   (in-graph node)   ┌─────────────┐  │
   │  │   LLM Step    │ ──► [Safety Gate] ─►│  Tool Call  │  │
   │  └───────┬───────┘          ▲          └──────┬──────┘  │
   └──────────┼──────────────────┼─────────────────┼─────────┘
              │ (telemetry)      │ (pause signal)  │
              ▼                  │                 ▼
   ┌─────────────────────────────┴───────────────────────────┐
   │                    CortexHeal Core                      │
   │  ┌──────────────────┐   ┌────────────────────────────┐  │
   │  │ RuntimeCollector │──►│   Deterministic Engine     │  │
   │  └──────────────────┘   │ • Exact SHA-256 Fingerprint│  │
   │                         │ • Sliding Cost Bounds      │  │
   │                         └─────────────┬──────────────┘  │
   │                                       ▼                 │
   │                         ┌────────────────────────────┐  │
   │                         │    ProtectionController    │  │
   │                         │ • Thread-Safe Interrupt    │  │
   │                         │ • Circuit Breaker Trip     │  │
   │                         └─────────────┬──────────────┘  │
   └───────────────────────────────────────┼─────────────────┘
                                           ▼
                             ┌───────────────────────────┐
                             │ Human Operator & Alerting │
                             │ • Async Webhook Outbound  │
                             │ • Real-time SSE Dashboard │
                             │ • Plan Review & Resume    │
                             └───────────────────────────┘
```

### Architectural Non-Negotiables
1. **Zero LLMs in the Safety-Decision Path**: Every safety decision (loop detection, budget threshold trip, circuit break) is 100% deterministic (canonical SHA-256 argument/response hashing and exact mathematical threshold bounding). No secondary LLM evaluator is ever consulted to decide whether an agent should be paused.
2. **Deterministic Fingerprinting**: Tool arguments and outputs are normalized (recursive key sorting, numeric coercion, strict JSON serialization) before computing SHA-256 hashes, preventing false positives from dictionary key ordering.
3. **Multi-Tenant Isolation**: Every API key, agent run, incident queue item, outbound webhook alert, and compliance export is partitioned strictly by `org_id` derived from caller authentication tokens.
4. **Decoupled Asynchronous Telemetry**: Ingestion and outbound webhook dispatching are non-blocking and decoupled from agent execution paths via thread pool executors and buffered queues.

---

## 2. Platform Capabilities

### A. Real-Time Deterministic Detection
- **Stuck Loop Detector**: Computes deterministic sliding window signatures over `(tool, arguments_hash, response_hash)`. Consecutive identical tool executions trigger immediate circuit breaks.
- **Budget Threshold Detector**: Tracks cumulative micro-costs across LLM invocations and tool calls. Once the configured ceiling is breached, pause requests are dispatched to prevent runaway billing.

### B. In-Graph Protection & Circuit Breaking
- **LangGraph & AutoGen Adapters**: Lightweight interceptors attachable to graph workflows as a native node (`SafetyGate`).
- **Idempotent Pause & Resume**: State transitions (`running` -> `pause_requested` -> `paused` -> `resumed`) are guarded by optimistic concurrency controls in PostgreSQL.

### C. Multi-Tenant Role-Based Access Control (RBAC)
- **Roles**:
  - `VIEWER`: Read-only access to runs, incidents, and audit logs. Mutating endpoints return `403 Forbidden`.
  - `OPERATOR`: Ability to approve/reject recovery plans, pause runs, and trigger compliance exports.
  - `ADMIN`: Full operational authority, including API key generation, key revocation, and webhook configuration.
- **Storage**: Keys are stored using standard SHA-256 hashing; raw keys are revealed only once upon creation.

### D. Outbound Alerting & Escalation
- **Webhook Dispatch**: Asynchronous delivery to Slack (Block Kit), PagerDuty, or generic JSON endpoints on `HIGH` and `CRITICAL` incidents.
- **Escalation Engine**: Background poller that monitors unacknowledged incidents exceeding defined SLA windows and dispatches secondary notifications.
- **Audit Logging**: Every outbound notification attempt (status code, payload, response body, latency) is permanently logged in `notification_records`.

### E. Compliance & Audit Export
- **Export Formats**: Standardized JSON array and streaming CSV exports via `GET /api/audit/export`.
- **Query Filters**: Supports filtering by `start_time`, `end_time`, `run_id`, and `actor_type`.

---

## 3. Deliberate Architectural Boundaries

To preserve low latency, operational stability, and deterministic guarantees, the following mechanisms were intentionally excluded:

1. **No LLM Judges in Critical Paths**:
   - Secondary LLM judges introduce hundreds of milliseconds of variable latency, token costs, and probabilistic hallucinations. CortexHeal strictly uses deterministic mathematical validation.
2. **No Unchecked Autonomous State Mutation**:
   - Automated remediation without human oversight introduces cascading loop risks. CortexHeal requires operator review or explicit policy approval before state recovery.
3. **No Kernel / eBPF Probes**:
   - Agent loops occur at the application orchestration layer. Kernel-level tracing adds operational overhead without improving agent semantic visibility.
4. **No Container-Level Pod Killing**:
   - Terminating agent containers causes crash loops and drops in-flight transactions. CortexHeal pauses execution graphs gracefully at state check boundaries.

---

## 4. Operational Scale Benchmarks

The following metrics represent verified performance under concurrent load (55 concurrent LangGraph agents with active SafetyGates and persistent SSE streaming connections):

| Metric | Target SLA | Measured Performance |
| :--- | :--- | :--- |
| **Telemetry Handover Latency** | < 1.0 ms | **0.15 ms** (in-process queue enqueue) |
| **Pipeline Latency (p50)** | < 50.0 ms | **~26.5 ms** (ingest to pause signal) |
| **Pipeline Latency (p95)** | < 150.0 ms | **~94.0 ms** |
| **Pipeline Latency (p99)** | < 300.0 ms | **~240.0 ms** |
| **Circuit Breaker Accuracy** | 100.0% | **100.0%** (55/55 pathological runs paused) |
| **Event Loss Rate** | 0.00% | **0.00%** (zero dropped events) |

---

## 5. Deployment & Configuration Reference

### Environment Variables
| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | String | `postgresql://postgres:postgres@localhost:5432/cortexheal` | PostgreSQL connection URI |
| `ALLOW_DEV_TOKENS` | Boolean | `false` | Accepts dev keys (`dev-admin-key`, etc.) for local tests |
| `MAX_WORKERS` | Integer | `20` | Thread pool size for outbound alert dispatchers |
| `ESCALATION_CHECK_INTERVAL_SECONDS` | Integer | `60` | Frequency of unacknowledged incident scans |

### Recommended Infrastructure
- **PostgreSQL**: Version 14+ with connection pooling enabled.
- **FastAPI / Uvicorn Server**: Deployed behind a reverse proxy (e.g. Nginx or Cloudflare) with SSE streaming timeouts disabled (`proxy_read_timeout 3600s;`).
- **Dashboard UI**: Static single-page application (React + Vite) served from CDN or static web host.
