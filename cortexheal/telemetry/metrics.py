from prometheus_client import Counter, Histogram, Gauge

# --- RUNTIME METRICS ---
events_received_total = Counter(
    "cortexheal_events_received_total", "Total telemetry events received"
)
events_processed_total = Counter(
    "cortexheal_events_processed_total", "Total telemetry events successfully processed"
)
events_dropped_total = Counter(
    "cortexheal_events_dropped_total", "Total telemetry events dropped due to queue overflow"
)
events_failed_total = Counter(
    "cortexheal_events_failed_total", "Total telemetry events failed during DB insertion"
)
ingestion_latency = Histogram(
    "cortexheal_ingestion_latency_seconds", "Latency of event DB ingestion"
)
queue_depth = Gauge(
    "cortexheal_queue_depth", "Current number of events in the ingestion queue"
)
queue_capacity = Gauge(
    "cortexheal_queue_capacity", "Maximum capacity of the ingestion queue"
)

# --- DETECTION METRICS ---
detections_total = Counter(
    "cortexheal_detections_total", "Total detections triggered", ["detector_name"]
)
incidents_created_total = Counter(
    "cortexheal_incidents_created_total", "Total incidents created"
)
stuck_loop_detections_total = Counter(
    "cortexheal_stuck_loop_detections_total", "Total stuck loop detections"
)
budget_exceeded_total = Counter(
    "cortexheal_budget_exceeded_total", "Total budget exceeded detections"
)

# --- PROTECTION METRICS ---
pause_requests_total = Counter(
    "cortexheal_pause_requests_total", "Total pause requests sent to agents"
)
pauses_successful_total = Counter(
    "cortexheal_pauses_successful_total", "Total successful agent pauses"
)
pauses_failed_total = Counter(
    "cortexheal_pauses_failed_total", "Total failed agent pauses"
)
protection_degraded_total = Counter(
    "cortexheal_protection_degraded_total", "Total times protection was degraded"
)

# --- RECOVERY METRICS ---
recovery_plans_created_total = Counter(
    "cortexheal_recovery_plans_created_total", "Total recovery plans generated"
)
recovery_approved_total = Counter(
    "cortexheal_recovery_approved_total", "Total recovery plans approved"
)
recovery_rejected_total = Counter(
    "cortexheal_recovery_rejected_total", "Total recovery plans rejected"
)
recovery_executed_total = Counter(
    "cortexheal_recovery_executed_total", "Total recovery plans executed"
)
recovery_verified_total = Counter(
    "cortexheal_recovery_verified_total", "Total recovery plans successfully verified"
)
recovery_failed_total = Counter(
    "cortexheal_recovery_failed_total", "Total recovery plans failed execution"
)
recovery_repeated_failure_total = Counter(
    "cortexheal_recovery_repeated_failure_total", "Total repeated failures after recovery"
)

# --- AI METRICS ---
ai_analysis_total = Counter(
    "cortexheal_ai_analysis_total", "Total AI analysis requests"
)
ai_analysis_success_total = Counter(
    "cortexheal_ai_analysis_success_total", "Total successful AI analysis requests"
)
ai_analysis_failure_total = Counter(
    "cortexheal_ai_analysis_failure_total", "Total failed AI analysis requests"
)
ai_fallback_total = Counter(
    "cortexheal_ai_fallback_total", "Total AI fallback generations"
)
ai_latency = Histogram(
    "cortexheal_ai_latency_seconds", "Latency of AI analysis generation"
)
ai_cost = Counter(
    "cortexheal_ai_cost_dollars", "Estimated cost of AI operations in USD"
)

# --- API METRICS ---
api_request_count = Counter(
    "cortexheal_api_request_count", "Total API requests", ["method", "endpoint", "http_status"]
)
api_request_latency = Histogram(
    "cortexheal_api_request_latency_seconds", "API Request Latency", ["method", "endpoint"]
)
api_rate_limit_rejections = Counter(
    "cortexheal_api_rate_limit_rejections", "Total API rate limit rejections"
)

# --- DATABASE METRICS ---
db_query_latency = Histogram(
    "cortexheal_db_query_latency_seconds", "Database query execution latency", ["operation"]
)
db_connection_failures = Counter(
    "cortexheal_db_connection_failures", "Database connection pool exhaustion or failures"
)
