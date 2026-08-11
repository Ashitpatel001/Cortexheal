from typing import Dict, Any
from cortexheal.models.incident import Incident
from cortexheal.models.learning import RecoveryOutcome

class InsufficientData(Exception):
    pass

class MLDatasetBuilder:
    @staticmethod
    def extract_features(incident: Incident, outcome: RecoveryOutcome) -> Dict[str, Any]:
        """
        Extracts sanitized features for ML training.
        Ensures raw tokens and sensitive data from evidence are not leaked.
        """
        framework = incident.evidence.get("framework", "unknown")
        token_cost = incident.evidence.get("token_cost", 0)
        
        success = (outcome.verification_result == "VERIFIED_SUCCESS")
        
        return {
            "framework": framework,
            "failure_type": incident.failure_type,
            "action_type": outcome.action_type,
            "token_cost": token_cost,
            "success": success
        }

class RecoveryPredictor:
    ML_STATUS = "PREPARED / INSUFFICIENT_DATA"
    
    def predict_success(self, incident: Incident, action: str) -> float:
        """
        Predicts the probability of success for a given action.
        Returns a neutral score (float) or raises InsufficientData.
        MUST never directly return an ActionType. MUST NOT modify PolicyEngine rules.
        """
        if self.ML_STATUS == "PREPARED / INSUFFICIENT_DATA":
            raise InsufficientData("Not enough historical data to make ML predictions.")
        
        # When sufficient data is available, return a probability score
        return 0.5
