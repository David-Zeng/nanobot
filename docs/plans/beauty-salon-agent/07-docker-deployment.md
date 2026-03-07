# Docker Deployment

---

## 1. Folder Structure

```
beauty-salon-agent/
├── docker-compose.yml
├── Dockerfile
├── .env                          # secrets — gitignored
├── init.sql                      # DB schema + seed data
├── config/
│   ├── customer-agent/
│   │   └── config.json
│   ├── admin-agent/
│   │   └── config.json
│   └── background-agent/
│       └── config.json
└── data/
    ├── customer-agent/
    │   └── workspace/
    │       ├── SOUL.md
    │       ├── AGENTS.md
    │       ├── USER.md
    │       ├── TOOLS.md
    │       ├── HEARTBEAT.md      # empty (heartbeat disabled)
    │       ├── memory/
    │       │   └── MEMORY.md
    │       ├── sessions/         # auto-managed by nanobot
    │       └── cron/
    │           └── jobs.json     # empty (no scheduled jobs)
    ├── admin-agent/
    │   └── workspace/
    │       ├── SOUL.md
    │       ├── AGENTS.md
    │       ├── USER.md
    │       ├── memory/
    │       └── sessions/
    ├── background-agent/
    │   └── workspace/
    │       ├── SOUL.md
    │       ├── AGENTS.md
    │       ├── HEARTBEAT.md      # active tasks
    │       ├── memory/
    │       ├── sessions/
    │       └── cron/
    │           └── jobs.json     # pre-seeded daily + cleanup jobs
    ├── backups/
    │   ├── database/
    │   └── configs/
    └── logs/
```

---

## 2. docker-compose.yml

```yaml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: nanobot_db
      POSTGRES_USER: nanobot
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    networks:
      - nanobot-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nanobot -d nanobot_db"]
      interval: 10s
      timeout: 5s
      retries: 5

  customer-agent:
    image: ghcr.io/hkuds/nanobot:latest
    command: nanobot gateway -w /app/workspace -c /app/config/config.json -p 18790
    volumes:
      - ./data/customer-agent/workspace:/app/workspace
      - ./config/customer-agent:/app/config
      - ./data/backups:/app/backups
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - CUSTOMER_TELEGRAM_TOKEN=${CUSTOMER_TELEGRAM_TOKEN}
      - DISCORD_TOKEN=${DISCORD_TOKEN}
      - DATABASE_URL=postgresql://nanobot:${DB_PASSWORD}@postgres:5432/nanobot_db
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - nanobot-net

  admin-agent:
    image: ghcr.io/hkuds/nanobot:latest
    command: nanobot gateway -w /app/workspace -c /app/config/config.json -p 18791
    volumes:
      - ./data/admin-agent/workspace:/app/workspace
      - ./config/admin-agent:/app/config
      - ./data/backups:/app/backups
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - ADMIN_TELEGRAM_TOKEN=${ADMIN_TELEGRAM_TOKEN}
      - ADMIN_TELEGRAM_USER_ID=${ADMIN_TELEGRAM_USER_ID}
      - DATABASE_URL=postgresql://nanobot:${DB_PASSWORD}@postgres:5432/nanobot_db
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - nanobot-net

  background-agent:
    image: ghcr.io/hkuds/nanobot:latest
    command: nanobot gateway -w /app/workspace -c /app/config/config.json -p 18792
    volumes:
      - ./data/background-agent/workspace:/app/workspace
      - ./data/customer-agent/workspace:/app/customer-workspace:ro
      - ./config/background-agent:/app/config
      - ./data/backups:/app/backups
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - ADMIN_TELEGRAM_TOKEN=${ADMIN_TELEGRAM_TOKEN}
      - ADMIN_TELEGRAM_CHAT_ID=${ADMIN_TELEGRAM_CHAT_ID}
      - DATABASE_URL=postgresql://nanobot:${DB_PASSWORD}@postgres:5432/nanobot_db
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - nanobot-net

networks:
  nanobot-net:
    driver: bridge

volumes:
  postgres_data:
```

Key points:
- `customer-agent/workspace` is mounted **read-only** into `background-agent` at `/app/customer-workspace` — so the Background Agent can read session files without risk of modifying them
- No `version:` key — deprecated in Compose v2
- `depends_on` with `condition: service_healthy` ensures postgres is ready before agents start
- All agents use `restart: unless-stopped` for production resilience

---

## 3. .env File

```bash
# LLM
ANTHROPIC_API_KEY=sk-ant-...

# Customer channels
CUSTOMER_TELEGRAM_TOKEN=...
DISCORD_TOKEN=...

# Admin channel
ADMIN_TELEGRAM_TOKEN=...
ADMIN_TELEGRAM_USER_ID=123456789
ADMIN_TELEGRAM_CHAT_ID=123456789

# Database
DB_PASSWORD=change-me-before-deploy
```

This file must be gitignored:

```bash
echo ".env" >> .gitignore
```

---

## 4. Dockerfile

nanobot publishes an official Docker image. If using the published image no custom Dockerfile is needed. If building from source:

```dockerfile
FROM python:3.11-slim

# Install psql client for DB access from agent
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
RUN pip install -e .

COPY nanobot/ nanobot/

ENTRYPOINT ["nanobot"]
```

---

## 5. Shared Volume Details

The Background Agent mounts the Customer Agent workspace read-only:

```
background-agent container sees:
  /app/workspace          → background-agent's own workspace (read/write)
  /app/customer-workspace → customer-agent's workspace (read-only)
    └── sessions/         → customer JSONL session files
```

The Background Agent reads session files from `/app/customer-workspace/sessions/` to detect idle conversations and generate summaries.

---

## 6. Backup & Restore

### Backup script

Triggered by the Admin Agent on demand, or by the Background Agent on a schedule.

```bash
#!/bin/bash
# backup.sh — run inside the postgres container or from a host with psql access
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/app/backups

pg_dump -h postgres -U nanobot -Fc nanobot_db > "$BACKUP_DIR/database/backup_$DATE.dump"
tar -czf "$BACKUP_DIR/configs/config_$DATE.tar.gz" /app/config/

# Keep only last 7 days
find "$BACKUP_DIR" -type f -mtime +7 -delete

echo "Backup completed: $DATE"
```

### Restore script

```bash
#!/bin/bash
# restore.sh
BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: ./restore.sh <backup_date e.g. 20260307_090000>"
    exit 1
fi

pg_restore -h postgres -U nanobot -d nanobot_db \
    --clean --if-exists \
    "/app/backups/database/backup_$BACKUP_FILE.dump"

tar -xzf "/app/backups/configs/config_$BACKUP_FILE.tar.gz" -C /

echo "Restore completed from $BACKUP_FILE"
```
