import hashlib
from cortexheal.models.incident import Incident
from cortexheal.models.events import RuntimeEvent

def generate_fingerprint(incident: Incident, trigger_event: RuntimeEvent) -> str:
    components = [
        str(trigger_event.framework),
        str(trigger_event.agent_id),
        str(incident.failure_type),
        str(trigger_event.tool) if trigger_event.tool else "None",
        str(trigger_event.arguments_hash) if trigger_event.arguments_hash else "None",
        str(trigger_event.response_hash) if trigger_event.response_hash else "None"
    ]
    raw_string = "|".join(components)
    hash_val = hashlib.sha256(raw_string.encode('utf-8')).hexdigest()
    return f"v1-{hash_val}"
