from cortexheal.mcp_server import list_open_incidents, get_incident_details, get_run_timeline
import json

print("--- Calling list_open_incidents ---")
incidents_json = list_open_incidents()
print(incidents_json)
inc_data = json.loads(incidents_json)

if inc_data:
    inc_id = inc_data[0]["incident_id"]
    print(f"\n--- Calling get_incident_details({inc_id}) ---")
    details = get_incident_details(inc_id)
    print(details)
    
    # Get run id from details
    det_data = json.loads(details)
    run_id = det_data["run_id"]
    print(f"\n--- Calling get_run_timeline({run_id}) ---")
    timeline = get_run_timeline(run_id)
    print(timeline)
else:
    print("No open incidents found in DB.")
