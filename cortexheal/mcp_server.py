import asyncio
import json
from typing import Any, List, Dict
from mcp.server.mcpserver import MCPServer

# CortexHeal storage imports
from cortexheal.storage.postgres import (
    get_incidents,
    get_incident,
    get_run,
    get_events_for_run
)

# Initialize MCPServer
mcp = MCPServer("CortexHeal MCP Server")

@mcp.tool()
def list_open_incidents() -> str:
    """List all currently open incidents in CortexHeal."""
    incidents = [i for i in get_incidents() if i.status == "OPEN"]
    data = [
        {
            "incident_id": i.incident_id,
            "agent_id": i.agent_id,
            "failure_type": i.failure_type,
            "severity": i.severity,
            "triggered_at": str(i.triggered_at) if i.triggered_at else None
        } for i in incidents
    ]
    return json.dumps(data, indent=2)

@mcp.tool()
def get_incident_details(incident_id: str) -> str:
    """Get detailed information and evidence for a specific incident by ID.
    Args:
        incident_id: The UUID of the incident
    """
    incident = get_incident(incident_id)
    if not incident:
        return f"Error: Incident {incident_id} not found"
        
    run = get_run(incident.run_id)
    data = incident.model_dump()
    data['run_status'] = run.status if run else "unknown"
    if data.get('triggered_at'):
        data['triggered_at'] = str(data['triggered_at'])
        
    return json.dumps(data, indent=2)

@mcp.tool()
def get_run_timeline(run_id: str) -> str:
    """Get the execution timeline (tool calls, LLM responses) for a specific run.
    Args:
        run_id: The UUID of the run
    """
    events = get_events_for_run(run_id)
    timeline = []
    for e in events:
        entry = e.model_dump()
        if entry.get('timestamp'):
            entry['timestamp'] = str(entry['timestamp'])
        timeline.append(entry)
        
    return json.dumps(timeline, indent=2)

def main():
    """Run the MCP server over stdio."""
    mcp.run()

if __name__ == "__main__":
    main()

