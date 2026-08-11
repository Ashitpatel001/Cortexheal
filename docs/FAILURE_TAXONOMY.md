# Failure Taxonomy

## P0: STUCK_LOOP
*   **Signal:** repeated tool signature: tool + arguments hash + response hash combined with lack of meaningful state change.
*   **Evidence:** The agent is repeatedly calling the same tool with the same arguments, receiving the same response, but failing to progress its internal state or reasoning.
*   **False-Positive Risks:** Paginating through large datasets using the same tool (requires tracking pagination cursors as state changes).
*   **Detector Input:** Stream of Normalized Runtime Events (specifically tool calls and state hashes).
*   **Detector Output:** `Incident(type=STUCK_LOOP, confidence=1.0)`
*   **Severity:** CRITICAL
*   **Safe Action:** PAUSE
*   **Human Action:** REVIEW -> KILL or RESUME (with injected context).
*   **Future Extension:** Detecting semantic loops (conceptually repeating the same mistakes with different wording).

## P1: BUDGET_EXCEEDED
*   **Signal:** cumulative run cost >= configured budget.
*   **Evidence:** Token usage metadata parsed from the LLM provider responses multiplied by model costs exceeds the allowed USD threshold.
*   **False-Positive Risks:** Misconfigured pricing models or delayed token reporting.
*   **Detector Input:** Normalized Runtime Events (specifically `tokens` and `cost` fields).
*   **Detector Output:** `Incident(type=BUDGET_EXCEEDED, confidence=1.0)`
*   **Severity:** HIGH
*   **Safe Action:** PAUSE
*   **Human Action:** REVIEW -> Approve budget increase (RESUME) or KILL.
*   **Future Extension:** Granular budgets (per-tool, per-sub-agent) and rate-limiting.

## P2: EXECUTION_TIMEOUT
*   **Status:** DEFERRED (V2+)

## P3: DEPENDENCY_LOOP
*   **Status:** DEFERRED (V2+)

## P4: SEMANTIC_DRIFT
*   **Status:** DEFERRED (V2+)
