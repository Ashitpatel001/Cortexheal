
with open("cortexheal/server/api.py", "r", encoding="utf-8") as f:
    content = f.read()

import re

old_block = """    plan = get_recovery_plan_by_incident(incident_id)
    if not plan:
        incident = get_incident(incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        plan = recovery_engine.generate_plan(incident)
    return plan.model_dump()"""

new_block = """    plan = get_recovery_plan_by_incident(incident_id)
    incident = get_incident(incident_id)
    if not plan:
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        plan = recovery_engine.generate_plan(incident)
        
    plan_dict = plan.model_dump()
    if incident:
        try:
            from cortexheal.storage.postgres import get_events_for_run
            from cortexheal.learning.pattern import PatternEngine
            from cortexheal.learning.trust import TrustEngine
            
            events = get_events_for_run(incident.run_id)
            trigger_event = next((e for e in events if e.event_id == incident.trigger_event_id), events[-1] if events else None)
            if trigger_event:
                pattern = PatternEngine().get_or_create_pattern(incident, trigger_event)
                evidence = TrustEngine().calculate_trust(pattern.pattern_id)
                if evidence.occurrences > 0:
                    actions_summary = []
                    for action, stats in evidence.actions.items():
                        actions_summary.append({
                            "action": action,
                            "attempted": stats.attempted,
                            "verified_success": stats.verified_success,
                            "verified_failure": stats.verified_failure,
                            "success_rate": stats.success_rate,
                            "trust_score": stats.trust_score,
                            "risk_level": stats.risk_level
                        })
                    plan_dict["pattern_trust"] = {
                        "occurrences": evidence.occurrences,
                        "actions": actions_summary
                    }
        except Exception as e:
            pass
            
    return plan_dict"""

content = content.replace(old_block, new_block)

with open("cortexheal/server/api.py", "w", encoding="utf-8") as f:
    f.write(content)

