# CortexHeal Launch Readiness

## Known Items
- Status visibility lag under heavy concurrent load has been observed up to 500ms+ in stress conditions; typical measured latency is p95 ~94ms. Not yet confirmed whether this affects live Fleet view responsiveness under realistic production concurrency.

- **Demo Runner Supervision**: cron_demo_runner.py currently has zero supervision. It must not be run raw in production; it requires a restart policy (e.g., via a docker-compose service or systemd unit) before handling public-facing demo traffic.
- **Webhook Dispatch Blocking**: Webhook dispatch is currently synchronous, which blocks the telemetry worker. This poses a latency risk during incident bursts when reliable alerting is most critical.
- **SSE Fanout Architecture**: Server-Sent Events (SSE) fanout is currently implemented in-process. This works for a single backend replica but will silently break (causing dropped live updates) if the backend is horizontally scaled to multiple replicas.