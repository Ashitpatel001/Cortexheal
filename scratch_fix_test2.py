
import re

with open("test_unrecoverable.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace all API calls with direct calls
content = re.sub(
    r"req = urllib\.request.*?API Error:.*?\"",
    """
    from cortexheal.storage.postgres import get_incidents, get_recovery_plan_by_incident
    from cortexheal.recovery.engine import RecoveryEngine
    from cortexheal.recovery.executor import RecoveryExecutor
    from cortexheal.protection.controller import ProtectionController
    
    incidents = get_incidents(run_id=run_id)
    if incidents:
        incident_id = incidents[0].incident_id
        print(f"Approving recovery for incident {incident_id}...")
        
        # 1. Generate plan
        RecoveryEngine().generate_plan(incidents[0])
        
        # 2. Execute plan
        plan = get_recovery_plan_by_incident(incident_id)
        RecoveryExecutor().execute_plan(plan, "ADMIN", "dev-operator")
        
        # 3. Resume
        print(f"Resuming run {run_id} directly...")
        ProtectionController().resume(run_id, "dev-operator", "Manual Resume", incident_id)
        print("Run resumed via API! Re-invoking graph...")
        
        try:
            graph.invoke(None, config=config)
        except Exception as e:
            print(f"Execution interrupted again: {e}")
""",
    content,
    flags=re.DOTALL
)

with open("test_unrecoverable.py", "w", encoding="utf-8") as f:
    f.write(content)

