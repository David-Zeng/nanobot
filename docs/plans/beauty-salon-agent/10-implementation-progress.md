# Beauty Salon Agent — Implementation Progress

> Last updated: 2026-03-08

---

## Status: Phase 1 complete — system is live on RPI

All three agents are running on `pi@10.1.1.234`. The customer bot (@DJBeautySalonBot) is responding via Telegram.

---

## What's Done

### nanobot core (branch: `beauty_salon`)

Two new features added, both committed and tested:

#### 1. `tools.disabled` (commit `633ccf2`)

Allows any agent config to exclude specific default tools from registration.

**Files changed:**
- `nanobot/config/schema.py` — added `disabled: list[str]` field to `ToolsConfig`
- `nanobot/agent/loop.py` — added `disabled_tools: set[str]` param, skip logic in `_register_default_tools()`
- `nanobot/cli/commands.py` — threads `config.tools.disabled` into both `AgentLoop` instantiations
- `tests/test_tools_disabled.py` — 11 tests, all passing

**Usage in config JSON:**
```json
"tools": { "disabled": ["write_file", "edit_file", "exec", "cron", "spawn"] }
```

#### 2. `fallbackModels` (commit `29cff08`)

On `RateLimitError` (HTTP 429) or capacity-exceeded errors, `CustomProvider.chat()` retries with each model in `fallbackModels` in order.

**Files changed:**
- `nanobot/config/schema.py` — added `fallback_models: list[str]` to `AgentDefaults`
- `nanobot/agent/loop.py` — added `fallback_models` param, passed to `provider.chat()`
- `nanobot/providers/base.py` — added `fallback_models` to abstract `chat()` signature
- `nanobot/providers/custom_provider.py` — implemented retry loop with `RateLimitError` catch + capacity phrase detection
- `nanobot/cli/commands.py` — threads `config.agents.defaults.fallback_models` into `AgentLoop`

**Usage in config JSON:**
```json
"agents": { "defaults": { "model": "primary/model", "fallbackModels": ["fallback/model-1", "fallback/model-2"] } }
```

---

### beauty-salon-agent project

Full project created at `/Volumes/WD_mini_2TB/git_repo/beauty-salon-agent/` and deployed to `pi@10.1.1.234:/home/pi/beauty-salon-agent/`.

#### Database (`sql/init.sql`)
- 6 enums: `task_status`, `task_type`, `appointment_status`, `reminder_channel`, `reminder_status`, `user_role`
- 9 tables: `users`, `customers`, `customer_memory`, `background_tasks`, `services`, `appointments`, `reminders`, `operation_history`, `settings`
- 15+ indexes on FK columns and common query patterns
- Trigger: `trg_customer_duplicate` — blocks duplicate IM account IDs or mobile numbers
- Seed data: 1 admin user, 6 services, 11 settings rows

#### Agent configs (`config/`)

| File | Model | Channel | Disabled tools |
|------|-------|---------|----------------|
| `customer-agent.json` | Kimi-K2.5-TEE | Telegram (`allowFrom: ["*"]`) | write_file, edit_file, exec, cron, spawn |
| `admin-agent.json` | GLM-5-TEE | Telegram (`allowFrom: ["${ADMIN_TELEGRAM_ID}"]`) | none |
| `background-agent.json` | MiniMax-M2.5-TEE | none (heartbeat every 300s) | none |

Fallback chain for customer agent: `Kimi-K2.5-TEE → MiniMax-M2.5-TEE → GLM-5-TEE`

LLM provider: chutes.ai (`https://llm.chutes.ai/v1`) — all TEE models.

#### Workspace docs (`data/`)
- `customer-workspace/AGENTS.md` — topic guardrail, language, booking enquiry workflow (no DB access, info-only)
- `customer-workspace/SOUL.md` — persona: warm, professional, trilingual (Cantonese/English/Mandarin)
- `customer-workspace/IDENTITY.md` — static placeholder (DB-backed identity deferred to Phase 2)
- `admin-workspace/AGENTS.md` — admin capabilities (view appointments, update settings)
- `background-workspace/AGENTS.md` — task processing workflow
- `background-workspace/HEARTBEAT.md` — 3 heartbeat checklist items

#### Docker (`Dockerfile.agent`, `docker-compose.yml`)
- Shared base image: `python:3.12-slim` + `postgresql-client` + `gettext-base`
- Installs nanobot from **local wheel** (`nanobot_ai-0.1.4.post3-py3-none-any.whl`) — not PyPI
- Entrypoint: `envsubst < /app/config.json > ~/.nanobot/config.json && nanobot gateway`
- 3 services: customer (port 18790), admin (port 18791), background (no port)
- No postgres service — uses external PG at `10.1.1.102:5433`

#### Tests
- Layer 2 (config): 61 tests — validate JSON structure, workspace docs, docker-compose
- Layer 4 (docker): 25 tests — static docker-compose structure checks
- Layer 3 (tools.disabled): 11 tests in nanobot repo
- Layer 1 (SQL): written, requires `pytest-postgresql` with live PG

---

## Known Issues / Deferred

| Item | Status |
|------|--------|
| Customer agent DB access (bookings) | Deferred — `exec` disabled, need dedicated booking tool or re-enable exec |
| IDENTITY.md written per customer | Deferred — requires write_file or DB-backed identity tool |
| Admin bot testing | Not yet tested |
| Background agent task processing | Heartbeat running, no tasks queued yet |
| Cron jobs (daily report, nightly cleanup) | Config exists, not wired into background agent yet |
| Layer 1 SQL tests on CI | Needs pytest-postgresql setup |

---

## Deployment Cheatsheet

```bash
# Rebuild wheel after nanobot changes
cd /Volumes/WD_mini_2TB/git_repo/nanobot
python -m build --wheel
cp dist/nanobot_ai-0.1.4.post3-py3-none-any.whl ../beauty-salon-agent/

# Sync and rebuild on RPI
cd /Volumes/WD_mini_2TB/git_repo/beauty-salon-agent
rsync -av --exclude='.git' --exclude='*.pyc' . pi@10.1.1.234:/home/pi/beauty-salon-agent/
ssh pi@10.1.1.234 "cd /home/pi/beauty-salon-agent && docker compose build && docker compose up -d"

# View logs
ssh pi@10.1.1.234 "docker logs beauty-salon-customer-agent-1 --tail 30 -f"
```

---

## Next Steps (Phase 2)

1. **Customer DB access** — decide: re-enable `exec` for bookings, or build a dedicated booking tool in nanobot
2. **Test admin bot** — message @DJSalonAdminBot, verify it responds with admin capabilities
3. **Background agent tasks** — verify heartbeat processes idle customer sessions
4. **Cron jobs** — wire `cron-jobs.json` into the background agent container
5. **Push nanobot `beauty_salon` branch** to GitHub remote
6. **Push beauty-salon-agent** to GitHub
