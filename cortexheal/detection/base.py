from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from cortexheal.models.events import RuntimeEvent

class DetectionResult(BaseModel):
    matched: bool
    failure_type: str
    severity: str
    evidence: Dict[str, Any]
    observed_value: Any
    threshold: Any
    description: str
    trigger_event_id: str

class BaseDetector:
    """Base interface for deterministic detectors."""
    
    @property
    def name(self) -> str:
        raise NotImplementedError
        
    @property
    def version(self) -> str:
        raise NotImplementedError

    def evaluate(self, event: RuntimeEvent) -> Optional[DetectionResult]:
        """
        Evaluates an incoming event against the run state.
        Returns a DetectionResult if a failure is detected, None otherwise.
        """
        raise NotImplementedError
