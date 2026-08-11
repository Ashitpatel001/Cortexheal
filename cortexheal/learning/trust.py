from typing import Dict
from cortexheal.models.learning import PatternEvidence, ActionStats
from cortexheal.storage.postgres import get_outcomes_for_pattern

class TrustEngine:
    def calculate_trust(self, pattern_id: str) -> PatternEvidence:
        outcomes = get_outcomes_for_pattern(pattern_id)
        
        actions: Dict[str, ActionStats] = {}
        occurrences = len(outcomes)
        
        for outcome in outcomes:
            action = outcome.action_type
            if action not in actions:
                actions[action] = ActionStats()
                
            actions[action].attempted += 1
            
            if outcome.verification_result == 'VERIFIED_SUCCESS':
                actions[action].verified_success += 1
            elif outcome.verification_result == 'VERIFIED_FAILURE':
                actions[action].verified_failure += 1
            # UNVERIFIED outcomes do not affect verified_success or verified_failure
            
        for action, stats in actions.items():
            verified_attempts = stats.verified_success + stats.verified_failure
            if verified_attempts > 0:
                stats.success_rate = stats.verified_success / verified_attempts
            else:
                stats.success_rate = 0.0
                
            if verified_attempts < 3:
                stats.trust_score = 0.0
                stats.risk_level = "UNKNOWN"
            else:
                stats.trust_score = stats.success_rate
                if stats.trust_score >= 0.8:
                    stats.risk_level = "LOW"
                elif stats.trust_score >= 0.5:
                    stats.risk_level = "MEDIUM"
                else:
                    stats.risk_level = "HIGH"
                    
        return PatternEvidence(
            pattern_id=pattern_id,
            occurrences=occurrences,
            actions=actions
        )
