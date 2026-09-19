from cortexheal.models.learning import PatternRecord
from cortexheal.models.incident import Incident
from cortexheal.models.events import RuntimeEvent
from cortexheal.storage.postgres import save_pattern_record, get_pattern_by_fingerprint
from cortexheal.learning.fingerprint import generate_fingerprint

class PatternEngine:
    def get_or_create_pattern(self, incident: Incident, trigger_event: RuntimeEvent, org_id: str) -> PatternRecord:
        fingerprint = generate_fingerprint(incident, trigger_event)
        
        existing = get_pattern_by_fingerprint(org_id, fingerprint)
        if existing:
            existing.occurrences += 1
            save_pattern_record(existing)
            return existing
            
        new_pattern = PatternRecord(
            framework=trigger_event.framework,
            agent_id=trigger_event.agent_id,
            org_id=org_id,
            failure_type=incident.failure_type,
            fingerprint=fingerprint,
            fingerprint_version="v1",
            occurrences=1
        )
        save_pattern_record(new_pattern)
        return new_pattern
