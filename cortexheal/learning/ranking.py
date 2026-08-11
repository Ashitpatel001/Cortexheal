from typing import List
from cortexheal.learning.trust import TrustEngine
from cortexheal.models.learning import RankedRecommendation, PatternRecord
try:
    from cortexheal.recovery.capabilities import SUPPORTED_CAPABILITIES
except ImportError:
    SUPPORTED_CAPABILITIES = {
        "cortex": ["KEEP_PAUSED", "RESUME", "REVERT_STATE"],
        "langgraph": ["KEEP_PAUSED", "RESUME"],
        "autogen": ["KEEP_PAUSED"]
    }

class RankingEngine:
    def __init__(self):
        self.trust_engine = TrustEngine()
        
    def rank_actions(self, pattern: PatternRecord) -> List[RankedRecommendation]:
        evidence = self.trust_engine.calculate_trust(pattern.pattern_id)
        
        framework = pattern.framework
        supported_actions = SUPPORTED_CAPABILITIES.get(framework, [])
        
        recommendations = []
        for action_type, stats in evidence.actions.items():
            if action_type not in supported_actions:
                continue
                
            verified_attempts = stats.verified_success + stats.verified_failure
            
            if verified_attempts < 3:
                trust_level = "INSUFFICIENT_EVIDENCE"
            else:
                if stats.trust_score >= 0.8:
                    trust_level = "HIGH"
                elif stats.trust_score >= 0.5:
                    trust_level = "MEDIUM"
                else:
                    trust_level = "LOW"
                    
            recommendations.append(
                RankedRecommendation(
                    action_type=action_type,
                    historical_success_rate=stats.success_rate,
                    verified_attempts=verified_attempts,
                    risk_level=stats.risk_level,
                    trust_level=trust_level,
                    is_supported=True
                )
            )
            
        recommendations.sort(key=lambda x: (x.historical_success_rate, x.verified_attempts), reverse=True)
        return recommendations
