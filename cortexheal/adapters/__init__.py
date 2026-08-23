"""
Framework adapters for attaching deterministic CortexHeal safety gates and telemetry observers
to agent frameworks (LangGraph, AutoGen, CrewAI).
"""

from cortexheal.adapters.base import FrameworkAdapter
from cortexheal.adapters.langgraph import LangGraphAdapter
from cortexheal.adapters.autogen import AutoGenAdapter

__all__ = [
    "FrameworkAdapter",
    "LangGraphAdapter",
    "AutoGenAdapter",
]
