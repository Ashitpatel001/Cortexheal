# CortexHeal Test Agents

These are local, mocked LangGraph agents designed to test CortexHeal's Detection and Recovery engines deterministically without requiring external API calls or real LLM executions.

## Running the tests

Ensure the CortexHeal database and API server are running first.

1. **Test A - Recoverable Loop**
   ```bash
   python examples/manual_recoverable_loop.py
   ```
   This agent triggers a STUCK_LOOP, gets paused by CortexHeal, gets resumed via the API, and then successfully transitions its state to SUCCESS to prove recovery behavior.

2. **Test B - Unrecoverable Loop**
   ```bash
   python examples/manual_unrecoverable_loop.py
   ```
   This agent triggers a STUCK_LOOP, gets paused, gets resumed, but intentionally continues its failing loop to trigger CortexHeal's RECOVERY_REPEATED_FAILURE safeguard.
