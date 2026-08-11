from typing import Optional, Dict
from cortexheal.models.events import RuntimeEvent
from cortexheal.detection.base import BaseDetector, DetectionResult

class BudgetConfig:
    enabled: bool = True
    max_cost_usd: float = 1.00

class BudgetDetector(BaseDetector):
    def __init__(self, config: BudgetConfig = BudgetConfig()):
        self.config = config
        self._cumulative: Dict[str, float] = {}

    @property
    def name(self) -> str:
        return "budget_detector"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, event: RuntimeEvent) -> Optional[DetectionResult]:
        if not self.config.enabled:
            return None
            
        if event.cost is None:
            return None
            
        run_id = event.run_id
        current_cost = self._cumulative.get(run_id, 0.0) + event.cost
        self._cumulative[run_id] = current_cost
        
        if current_cost >= self.config.max_cost_usd:
            return DetectionResult(
                matched=True,
                failure_type="BUDGET_EXCEEDED",
                severity="HIGH",
                evidence={
                    "event_cost": event.cost,
                    "cumulative_cost": current_cost,
                    "currency": "USD"
                },
                observed_value=current_cost,
                threshold=self.config.max_cost_usd,
                description=f"Cumulative run cost (${current_cost:.4f}) exceeded budget threshold (${self.config.max_cost_usd:.4f}).",
                trigger_event_id=event.event_id
            )
            
        return None
