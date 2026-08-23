"""
Prometheus telemetry instrumentation and histogram registries.
"""

from cortexheal.telemetry.metrics import (
    events_received_total,
    events_processed_total,
    events_dropped_total,
    events_failed_total,
    ingestion_latency,
    queue_depth,
    queue_capacity,
    detections_total,
    incidents_created_total,
    stuck_loop_detections_total,
    budget_exceeded_total,
)

__all__ = [
    "events_received_total",
    "events_processed_total",
    "events_dropped_total",
    "events_failed_total",
    "ingestion_latency",
    "queue_depth",
    "queue_capacity",
    "detections_total",
    "incidents_created_total",
    "stuck_loop_detections_total",
    "budget_exceeded_total",
]
