# CortexHeal — Bare-Metal Deployment Runbook

> **Audience**: Human operator with SSH access to the target Linux server.
> This document was prepared locally — the agent has zero SSH access.
> Every server-side command is listed explicitly for copy-paste execution.

---

## Prerequisites

| Requirement | Minimum |
|---|---|
| Linux server | Ubuntu 22.04+ / Debian 12+ (any systemd-based distro) |
| Docker Engine | 24.0+ with `docker compose` v2 plugin |
| Caddy | 2.7+ (installed in Phase 3) |
| RAM | 2 GB+ |
| Disk | 20 GB+ free for data + backups |
| DNS | A records for `app.<domain>`, `api.<domain>`, `<domain>` pointing at server IP |

> [!IMPORTANT]
> **Confirm DNS propagation before starting.** Run `dig +short app.YOURDOMAIN.com`
> from a machine outside the server. If it doesn't return your server IP, stop —
> TLS provisioning (Caddy) will fail silently.

---

## Phase 2 — Persistent Storage Setup

### Host directories that must exist before first run

Create the following directories on the server. Docker will NOT create bind-mount
source directories automatically — the compose file will fail if these are missing.

```bash
# Run on the server:
sudo mkdir -p /opt/cortexheal/data/postgres
sudo mkdir -p /opt/cortexheal/backups
sudo mkdir -p /opt/cortexheal/repo

# Postgres data dir must be owned by UID 999 (the postgres user inside the container)
sudo chown -R 999:999 /opt/cortexheal/data/postgres

# Backups dir owned by root (the backup script runs as root via crontab)
sudo chown root:root /opt/cortexheal/backups
sudo chmod 750 /opt/cortexheal/backups
```

### Directory layout after setup

```
/opt/cortexheal/
├── repo/                    # Git clone of CortexHeal
│   ├── docker-compose.prod.yml
│   ├── .env.production      # Real secrets — NEVER committed
│   ├── scripts/
│   │   └── backup_postgres.sh
│   └── ...
├── data/
│   └── postgres/            # Bind-mounted Postgres data (survives container rebuilds)
└── backups/
    └── cortexheal_db_20260914_030000.sql.gz   # Timestamped dumps
```

### Scheduled backups

The backup script runs `pg_dump` inside the Postgres container, gzips the output
to `/opt/cortexheal/backups/`, and prunes dumps older than 30 days.

```bash
# Run on the server — add this crontab entry:
sudo crontab -e

# Add this line (daily at 03:00 server time):
0 3 * * * /opt/cortexheal/repo/scripts/backup_postgres.sh >> /opt/cortexheal/backups/backup.log 2>&1
```

> [!NOTE]
> The backup script expects the Postgres container to be named `cortexheal-postgres-1`
> (the default when running `docker compose -f docker-compose.prod.yml up`).
> If you override the project name, update `CONTAINER_NAME` in the script.

---

*Phases 3–6 will be appended to this document as they are completed.*
