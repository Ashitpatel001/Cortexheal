# CortexHeal 

CortexHeal is a deterministic detection engine and self-healing platform for AI Agents. It provides a modular, safe, and observable control plane for your autonomous systems.

## Getting Started

### 1. Installation

Install CortexHeal using pip (along with the framework adapter of your choice):

```bash
pip install cortexheal[langgraph]
# OR
pip install cortexheal[autogen]
```

### 2. Configuration

CortexHeal uses environment variables for configuration. Create a `.env` file in your working directory:

```env
DATABASE_URL=postgresql://cortexheal:cortexpassword@localhost:5432/cortexheal_db
CORTEXHEAL_VIEWER_TOKENS=viewer-key
CORTEXHEAL_OPERATOR_TOKENS=operator-key
CORTEXHEAL_ADMIN_TOKENS=admin-key
ENVIRONMENT=development
```

### 3. Initialize the Database

Make sure you have PostgreSQL running, then apply migrations:

```bash
alembic upgrade head
```

*(Note: For testing, you can also run `python init_db.py` to create tables directly.)*

### 4. Integration (SDK)

Integrate CortexHeal into your agent in ~5 minutes:

**LangGraph Example:**

```python
from cortexheal import CortexHeal
from cortexheal.adapters.langgraph import LangGraphAdapter

# Initialize CortexHeal with the LangGraph adapter
adapter = LangGraphAdapter(agent_id="my_agent")
cortex = CortexHeal(adapter=adapter)

# Add protection to your LangGraph StateGraph
graph_builder.add_node("safety_gate", cortex.safety_gate)

# When compiling, inject the telemetry callback
graph = graph_builder.compile()
graph.invoke(input_data, config={"callbacks": [cortex.telemetry]})
```

**AutoGen Example:**

```python
from cortexheal import CortexHeal
from cortexheal.adapters.autogen import AutoGenAdapter
from autogen import ConversableAgent

# Initialize CortexHeal with the AutoGen adapter
adapter = AutoGenAdapter(agent_id="my_agent")
cortex = CortexHeal(adapter=adapter)

agent = ConversableAgent(name="assistant", ...)

# Automatically injects safety hooks and telemetry
protected_agent = cortex.protect(agent)
```

### 5. Running the Control Plane

Start the Control Plane API to monitor your agents and review incidents:

```bash
uvicorn cortexheal.server.api:app --host 0.0.0.0 --port 8000
```

Access the dashboard at `http://localhost:8000/static/index.html`.

## Production Hardening (Phase 9)

CortexHeal is designed for production:
- **Connection Pooling**: PostgreSQL connections are efficiently managed.
- **Structured Logging**: All logs are JSON-formatted for aggregation (Datadog/Splunk).
- **Control Plane API**: Protected by Rate Limiting, RBAC, and Pagination.
- **Real-Time UI**: Features Server-Sent Events (SSE) for instant dashboard updates.
- **Docker Ready**: A `Dockerfile` is provided for containerized deployments.

For detailed architecture, see `docs/PHASE_9_AUDIT.md`.