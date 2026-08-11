from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from cortexheal.models.events import RuntimeEvent

class FrameworkAdapter(ABC):
    """
    Base contract for all framework adapters (LangGraph, AutoGen, etc.).
    Adapters are responsible for intercepting framework-specific lifecycle
    events and normalizing them into CortexHeal RuntimeEvents.
    """
    
    @property
    @abstractmethod
    def framework_name(self) -> str:
        """Returns the name of the framework (e.g., 'LangGraph', 'AutoGen')."""
        pass
        
    @abstractmethod
    def get_safety_gate(self) -> Any:
        """
        Returns the framework-specific hook, node, or middleware 
        that enforces the CortexHeal protection (pause/resume) boundary.
        """
        pass
        
    @abstractmethod
    def get_telemetry_callback(self) -> Any:
        """
        Returns the framework-specific callback handler or hook
        used to observe events and emit RuntimeEvents.
        """
        pass
