# Safety Model

## Intervention Tiers

1.  **SAFE (PAUSE)**
    *   **Description:** Safely suspends the agent's execution without destroying state.
    *   **Trigger:** May automatically fire based on deterministic Policy Engine rules (e.g., Budget Exceeded).
    *   **Reversibility:** Fully reversible.
    
2.  **REVIEW (RESUME)**
    *   **Description:** Controlled continuation of a paused run.
    *   **Trigger:** Executed explicitly via Human-In-The-Loop (HITL) approval, or injected via policy relaxation.
    
3.  **BLOCK (KILL)**
    *   **Description:** Destructive termination of the agent run.
    *   **Trigger:** **REQUIRES HUMAN APPROVAL.** No automatic destructive actions in V1.

## Core Safety Principles

*   **Fail-Safe Behavior:** If the internal CortexHeal Policy Engine is unavailable, unreachable, or errors out, the SDK adapter MUST **DEFAULT TO SAFE PAUSE**. Never silently continue a potentially unsafe execution.
*   **Policy Evaluation:** Policies are evaluated synchronously on critical events (e.g., before tool execution) to prevent out-of-band runaway.
*   **Audit Requirements:** Every intervention (PAUSE, RESUME, KILL) must be logged to PostgreSQL with an immutable `idempotency_key`, timestamp, and the identity of the human approver (for RESUME/KILL).
*   **Approval Expiration:** Human approval requests (e.g., via Slack) automatically expire after a configured timeout (e.g., 60 minutes), resulting in a permanent KILL to free resources.
*   **Duplicate-Event Protection:** Idempotency keys prevent replay attacks or network retries from triggering multiple interventions for the same event.
