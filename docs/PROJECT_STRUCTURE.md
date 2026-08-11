# CortexHeal Project Structure

CortexHeal is a deterministic Detection Engine and Self-Healing Platform for AI Agents.
The repository has been thoroughly cleaned and stabilized for production usage.

## Core Directories

- **`cortexheal/`**: The core library and application package.
  - **`adapters/`**: Integrations with AI agent frameworks. Supported: LangGraph, AutoGen.
  - **`detection/`**: The deterministic runtime detection engine. Handles budgets, loops, bounds.
  - **`protection/`**: Safely pauses agent execution. The `ProtectionController` provides isolated boundaries.
  - **`recovery/`**: Analyzes incidents and generates verifiable execution plans using AI.
  - **`learning/`**: Phase 10 component mapping incidents to safe recovery patterns via fingerprinting.
  - **`models/`**: Pydantic validation schemas.
  - **`runtime/`**: Event collector and hashing utilities.
  - **`server/`**: FastAPI Control Plane providing SSE streams and API endpoints.
  - **`storage/`**: PostgreSQL interactions and connection pooling.
  - **`telemetry/`**: Prometheus metrics and operational counters.
  - **`config.py`**: Pydantic Settings configuration system.
  - **`client.py`**: Python SDK for programmatic CortexHeal interaction.
- **`tests/`**: Comprehensive E2E, unit, integration, and performance testing suite.
- **`alembic/` & `alembic.ini`**: Database migration tooling and state.
- **`docs/`**: Key architectural, setup, and structural documentation.
- **`dashboard/`**: (If present) React-based Frontend interface for the Control Plane.

## Configuration & Environment

- **`.env.example`**: Reference template for configuring CortexHeal.
- **`.env`**: Local active environment file.
- **`docker-compose.yml`**: Spawns required infrastructure (e.g., PostgreSQL on 5433).
- **`pyproject.toml`**: Python package configuration and dependencies.

## Key Capabilities

1. **Observe**: Captures high-frequency agent actions.
2. **Detect**: Applies deterministic thresholds to catch run-away behavior.
3. **Protect**: Synchronously suspends agents before damage is done.
4. **Control**: Provides human-in-the-loop review queues.
5. **Recover**: Analyzes context to generate verifiable recovery plans.
6. **Learn**: Maps failure fingerprints to successful recovery patterns over time.

## Architecture Guidelines

- Always prefer deterministic execution constraints over AI-generated safety rules.
- Database access MUST flow through the connection pool configured in `cortexheal/storage/postgres.py`.
- Production credentials MUST NOT use the `admin-key` default fallbacks.
- New adapters must inherit from `cortexheal.adapters.base.BaseAdapter`.
