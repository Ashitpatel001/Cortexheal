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

---

## Phase 3 � Reverse Proxy & TLS (Caddy)

Caddy serves as the edge router. It terminates TLS automatically and routes traffic to the local Docker containers.

### Installing and Configuring Caddy

Run these commands as root on the server:

\\\ash
# 1. Install Caddy (Debian/Ubuntu)
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy

# 2. Copy the Caddyfile to the system directory
# IMPORTANT: Edit /opt/cortexheal/repo/deploy/Caddyfile to replace YOURDOMAIN.com first!
sudo cp /opt/cortexheal/repo/deploy/Caddyfile /etc/caddy/Caddyfile

# 3. Reload Caddy to apply changes and provision TLS certificates
sudo systemctl reload caddy
\\\

> [!NOTE]
> Caddy naturally supports HTTP/2 and Server-Sent Events (SSE). No explicit buffering directives are needed for /api/stream to function correctly.

---

## Phase 4 � Process Supervision (Docker & Systemd)

The \docker-compose.prod.yml\ file defines \
estart: always\ for all services (Postgres, API, and the Demo Runner). 
The Demo Runner is fully containerized and managed by Docker, eliminating the need for raw Python processes.

To ensure the entire stack survives a bare-metal server reboot, enable the Docker daemon to start on boot:

\\\ash
# Run on the server:
sudo systemctl enable docker
\\\


---

## Phase 6 � Deployment & Verification

After completing the Prerequisites and Phase 2 host directory setup, follow these exact steps to deploy the application.

### 1. Clone the Repository
\\\ash
cd /opt/cortexheal
git clone https://github.com/YOUR_ORG/CortexHeal.git repo
cd repo
\\\

### 2. Configure Production Secrets
\\\ash
cp .env.production.example .env.production
nano .env.production
\\\
*(Fill in all CHANGE_ME_REAL_PASSWORD and YOURDOMAIN placeholders with actual secure values)*

### 3. Start the Application Stack
\\\ash
docker compose -f docker-compose.prod.yml up -d --build
\\\

### 4. Run Database Migrations
\\\ash
# The API container has alembic installed. Execute the migration inside it:
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
\\\

### 5. Verify Health
Wait 30 seconds for services to fully start, then verify the backend is healthy:
\\\ash
curl -f https://api.YOURDOMAIN.com/health
\\\

Verify authentication rejection (ensures API keys are required):
\\\ash
curl -f https://api.YOURDOMAIN.com/api/whoami
# Should return HTTP 403 Forbidden
\\\


