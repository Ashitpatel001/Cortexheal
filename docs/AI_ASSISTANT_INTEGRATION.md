# AI Assistant Integration (MCP + Context Fallback)

CortexHeal is designed with a strict **Zero-LLM safety boundary**. The detection and pause/resume decisions are 100% deterministic.

However, when an agent is paused by a circuit breaker (e.g., stuck in a loop or exceeding a budget), human engineers often use AI assistants like Cursor, Claude Code, or Windsurf to diagnose and fix the underlying agent logic. To reduce friction during this debugging phase, CortexHeal provides two human-facing convenience layers to export incident data directly into your AI assistant.

**Crucially, this data only flows outward to human tools. It never feeds back into CortexHeal's own detection engine.**

## 1. Model Context Protocol (MCP) Server

CortexHeal ships with an embedded, read-only MCP server. This allows MCP-compatible AI assistants (like Claude Desktop) to query live incident data directly from the CortexHeal control plane without you needing to copy-paste.

### Exposed Tools
- `list_open_incidents`: Returns a list of all currently open incidents, including their IDs, severity, and agent targets.
- `get_incident(incident_id)`: Returns the full deterministic evidence, thresholds, and description for a specific incident.
- `get_run_timeline(run_id)`: Returns the complete chronological timeline (tool calls, state transitions) for the run that triggered the incident.

### How to Start the MCP Server

You can start the MCP server using the CLI:

```bash
cortexheal mcp
```

This launches the server over `stdio`, which is the standard protocol for local MCP communication. 

### Claude Desktop Configuration Example

To connect Claude Desktop to your local CortexHeal instance, add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cortexheal": {
      "command": "cortexheal",
      "args": ["mcp"]
    }
  }
}
```

Once connected, you can ask Claude questions like:
> *"What incident just fired for the support_agent? Fetch the timeline and tell me why it's stuck in a loop."*

## 2. Copy as AI Context (Dashboard Fallback)

For developers using AI assistants that do not yet support MCP, CortexHeal provides a one-click fallback in the dashboard UI.

On any **Incident Detail** screen, click the **"COPY AS AI CONTEXT"** button. This instantly formats the incident details, evidence, and deterministic thresholds into a clean, markdown-friendly text block on your clipboard.

**Example Output:**
```text
CortexHeal Incident Context
ID: inc-8a7b6c5d
Run ID: run-1234-abcd
Agent ID: support_ticket_router
Failure Type: STUCK_LOOP
Severity: HIGH
Status: OPEN

Description:
Agent support_ticket_router is stuck in a repetitive loop...

Evidence:
{
  "tool": "query_customer_crm",
  "arguments_hash": "hash_crm_param_legacy_id",
  ...
}

Observed Value: 4
Threshold Limit: 4
```

You can paste this directly into ChatGPT, Claude, or Cursor as context for diagnosing the failure.
