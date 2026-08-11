import logging
from typing import Any, Optional

from cortexheal.config import settings
from cortexheal.adapters.base import FrameworkAdapter

logger = logging.getLogger(__name__)

class CortexHeal:
    """
    Public Developer API for CortexHeal Platform.
    """
    def __init__(
        self, 
        adapter: FrameworkAdapter, 
        auto_ingest: bool = True
    ):
        self.adapter = adapter
        self.auto_ingest = auto_ingest
        self._safety_gate = adapter.get_safety_gate()
        self._telemetry = adapter.get_telemetry_callback()
        
        logger.info(f"Initialized CortexHeal with adapter: {self.adapter.framework_name}")

    def protect(self, agent_graph: Any) -> Any:
        """
        Wraps/protects an agent graph depending on the framework.
        
        For LangGraph: 
        This is a no-op structurally, because LangGraph requires you to add
        `cortex.safety_gate` to your StateGraph manually.
        However, you can configure your graph callbacks to use `cortex.telemetry`.
        
        For AutoGen:
        This injects the before_send hooks automatically into the agent.
        """
        if self.adapter.framework_name == "LangGraph":
            logger.info("LangGraph detected. Please ensure `cortex.safety_gate` is added as a node in your StateGraph, and `cortex.telemetry` is passed as a callback.")
            return agent_graph
            
        elif self.adapter.framework_name == "AutoGen":
            logger.info("AutoGen detected. Injecting protection hooks directly into agent.")
            return self.adapter.register_agent(agent_graph)
            
        return agent_graph
        
    @property
    def safety_gate(self) -> Any:
        """Returns the framework-specific safety gate node or hook."""
        return self._safety_gate
        
    @property
    def telemetry(self) -> Any:
        """Returns the framework-specific telemetry callback handler."""
        return self._telemetry
