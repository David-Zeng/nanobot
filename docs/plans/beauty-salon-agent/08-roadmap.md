# Implementation Roadmap

---

## Phases

```mermaid
gantt
    title Implementation Roadmap
    dateFormat  YYYY-MM-DD

    section Phase 0 - nanobot Feature
    tools.disabled in config.json    :a0, 2026-03-07, 1d

    section Phase 1 - Foundation
    DB schema + init.sql             :a1, after a0, 2d
    Docker Compose + health checks   :a2, after a1, 2d
    Workspace files for all 3 agents :a3, after a2, 2d

    section Phase 2 - Customer Agent
    Telegram channel + basic reply   :b1, after a3, 2d
    IM resolution + new customer reg :b2, after b1, 3d
    IDENTITY.md injection mechanism  :b3, after b2, 2d
    Service query                    :b4, after b3, 2d
    Booking flow                     :b5, after b4, 3d
    Appointment modification         :b6, after b5, 2d

    section Phase 3 - Background Agent
    Heartbeat + idle detection       :c1, after b6, 2d
    Conversation summarisation       :c2, after c1, 3d
    Reminder delivery                :c3, after c2, 2d
    Daily report                     :c4, after c3, 2d
    Nightly cleanup                  :c5, after c4, 1d

    section Phase 4 - Admin Agent
    Admin Telegram channel           :d1, after c5, 2d
    Customer + appointment mgmt      :d2, after d1, 3d
    Settings management              :d3, after d2, 2d
    Backup and restore               :d4, after d3, 2d

    section Phase 5 - Additional Channels
    WhatsApp integration             :e1, after d4, 3d
    Discord integration              :e2, after e1, 2d

    section Phase 6 - Polish
    Guardrail tuning                 :f1, after e2, 2d
    End-to-end testing               :f2, after f1, 3d
    Documentation                    :f3, after f2, 2d
```

---

## Phase 0 — nanobot Feature: `tools.disabled`

**Goal:** Hard-enforce tool restrictions per agent instance via config, so the LLM cannot call disallowed tools regardless of what it's instructed to do.

```mermaid
flowchart LR
    A[Add disabled list to ToolsConfig<br/>in config/schema.py] --> B[Skip disabled tools<br/>in _register_default_tools]
    B --> C[tools.get_definitions excludes them<br/>LLM never sees them]
    C --> D[customer-agent config.json<br/>disabled: write_file, edit_file, exec, cron]
    D --> E[Verify: LLM cannot write files<br/>even if prompted to]
```

**Why:** `allowFrom` only controls who can send messages. Once a message reaches the agent loop, all tools are available to the LLM. A jailbreak or hallucination could cause the Customer Agent to call `write_file` or `exec`. With `tools.disabled`, those tools are never registered — they don't exist from the LLM's perspective.

**nanobot changes required:**

1. `nanobot/config/schema.py` — add `disabled: list[str]` to `ToolsConfig`
2. `nanobot/agent/loop.py` — pass `disabled` into `AgentLoop.__init__`, skip disabled tools in `_register_default_tools`

**Customer Agent `config.json` addition:**

```json
"tools": {
  "disabled": ["write_file", "edit_file", "exec", "cron", "spawn"]
}
```

This leaves the Customer Agent with only: `read_file`, `list_dir`, `web_search`, `web_fetch`, `message`.

- [ ] Add `disabled: list[str]` to `ToolsConfig` in `nanobot/config/schema.py`
- [ ] Read `disabled` in `AgentLoop._register_default_tools` and skip those tools
- [ ] Add `tools.disabled` to customer-agent `config.json`
- [ ] Verify: attempt to call `write_file` from customer-agent returns tool-not-found error

**Done when:** Customer Agent cannot write or execute anything, even if the LLM tries.

---

## Phase 1 — Foundation

**Goal:** Running infra with empty agents.

```mermaid
flowchart LR
    A[Write init.sql<br/>schema + seed data] --> B[Write docker-compose.yml<br/>with health checks]
    B --> C[Create workspace files<br/>SOUL, AGENTS, USER per agent]
    C --> D[Pre-seed cron/jobs.json<br/>for background-agent]
    D --> E{docker compose up}
    E -->|4 containers healthy| F[Done]
    E -->|Error| G[Fix + retry]
```

- [ ] Write `init.sql` with full schema (all tables, enums, indexes, trigger, seed data)
- [ ] Write `docker-compose.yml` with health checks
- [ ] Create workspace directories and initial workspace files for all 3 agents
  - `SOUL.md`, `AGENTS.md`, `USER.md` per agent
  - `HEARTBEAT.md` for background-agent
  - Pre-seeded `cron/jobs.json` for background-agent
- [ ] Verify all 3 containers start and connect to postgres

**Done when:** `docker compose up` starts all 4 containers with no errors.

---

## Phase 2 — Customer Agent

**Goal:** Customer can book an appointment end-to-end via Telegram.

```mermaid
flowchart TD
    A[Telegram channel<br/>responds to messages] --> B[IM resolution<br/>lookup or create customer]
    B --> C[New customer registration<br/>ask name + mobile]
    C --> D[IDENTITY.md injection<br/>customer record + memory per message]
    D --> E[Service query<br/>list from DB]
    E --> F[Booking flow<br/>check availability + confirm + INSERT]
    F --> G[last_message_at updated<br/>after every response]
    G --> H[Appointment modification<br/>reschedule or cancel]
    H --> I[Operation history<br/>logged for all actions]
```

- [ ] Telegram channel responds to messages
- [ ] IM resolution: lookup customer by telegram_id, create new record if not found
- [ ] Ask new customer for name + mobile, update DB
- [ ] IDENTITY.md injection: write customer record + memory before each message
- [ ] Service query: list services from DB
- [ ] Booking flow: check availability, confirm, INSERT appointment, INSERT reminder
- [ ] `last_message_at` updated after every response
- [ ] Appointment modification: reschedule or cancel
- [ ] Operation history logged for all booking actions

**Done when:** A new Telegram user can go from first message → registered customer → confirmed appointment.

---

## Phase 3 — Background Agent

**Goal:** Conversations are summarised, reminders are sent.

```mermaid
flowchart TD
    A[Heartbeat fires every 5 min] --> B[Idle detection<br/>customers inactive over 15 min]
    B --> C[Summarisation<br/>read JSONL + LLM + INSERT customer_memory]
    C --> D[Verify: IDENTITY.md injection<br/>correct in next conversation]
    D --> E[Reminders<br/>find due + send via message tool]
    E --> F[Daily report<br/>generate + deliver to admin]
    F --> G[Nightly cleanup<br/>old appointments + failed tasks]
```

- [ ] Heartbeat fires every 5 min and processes `HEARTBEAT.md` tasks
- [ ] Idle detection query finds customers inactive > 15 min
- [ ] Summarisation: reads session JSONL, generates summary, inserts `customer_memory`
- [ ] Customer Agent injects latest `customer_memory` into IDENTITY.md correctly
- [ ] Reminders: finds due reminders, sends via `message` tool, updates status
- [ ] Daily report: generates and delivers to admin Telegram channel
- [ ] Nightly cleanup: removes old cancelled appointments and failed tasks

**Done when:** After a test conversation, the session is summarised within 20 min and the summary appears correctly in the next conversation's IDENTITY.md.

---

## Phase 4 — Admin Agent

**Goal:** Owner can manage the system via Telegram.

```mermaid
flowchart TD
    A[Admin Telegram channel<br/>restricted to owner only] --> B[Customer management<br/>list, view, update, soft-delete]
    B --> C[Appointment management<br/>today schedule + cancel/modify]
    C --> D[Settings management<br/>read + update settings table]
    D --> E[Operation history<br/>audit trail + reports]
    E --> F[Manual backup trigger<br/>via admin command]
    F --> G[Daily report acknowledgement<br/>from Background Agent]
```

- [ ] Admin Telegram channel responds (allowFrom restricted to owner)
- [ ] Customer management: list, view, update, soft-delete customers
- [ ] Appointment management: view today's schedule, cancel/modify on behalf of customer
- [ ] Settings: read and update `settings` table values
- [ ] View operation history and audit trail
- [ ] Trigger backup manually
- [ ] Receive and acknowledge daily reports from Background Agent

**Done when:** Owner can view today's appointments and cancel one via Telegram.

---

## Phase 5 — Additional Channels

**Goal:** WhatsApp and Discord customers work the same as Telegram.

```mermaid
flowchart TD
    A[WhatsApp<br/>nanobot channels login] --> B[IM resolution<br/>whatsapp_id lookup]
    B --> C[Booking flow<br/>same as Telegram]
    D[Discord<br/>bot invited to server] --> E[Mention-based interaction<br/>discord_id lookup]
    E --> C
    C --> F[Cross-channel identity<br/>mobile number deduplication]
    F --> G[Admin daily report<br/>shows all channels]
```

- [ ] WhatsApp: link device (`nanobot channels login`), test IM resolution and booking
- [ ] Discord: bot invited to server, mention-based interaction, booking flow
- [ ] Cross-channel identity: if a WhatsApp customer also connects via Telegram, they are recognised as the same customer by mobile number

**Done when:** A booking made via WhatsApp shows up in the admin's daily report alongside Telegram bookings.

---

## Phase 6 — Polish

**Goal:** System is production-ready.

```mermaid
flowchart TD
    A[Guardrail tuning<br/>Cantonese/English edge cases] --> B[Rate limiting<br/>rapid-fire message test]
    B --> C[Error handling<br/>psql failure + LLM error scenarios]
    C --> D[Load test<br/>10 concurrent customers]
    D --> E[Backup/restore drill<br/>drop table + restore + verify]
    E --> F[Documentation update<br/>findings from implementation]
    F --> G[Production ready]
```

- [ ] Guardrail tuning: test edge cases (mixed Cantonese/English, ambiguous messages)
- [ ] Rate limiting: test with rapid-fire messages
- [ ] Error handling: what happens if psql fails? If LLM returns error?
- [ ] Load test: simulate 10 concurrent customers
- [ ] Backup/restore drill: backup, drop a table, restore, verify
- [ ] Documentation: update this design with anything discovered during implementation

---

## Key Risks

| Risk | Mitigation |
|------|-----------|
| `IDENTITY.md` write race condition | nanobot serialises processing via `_processing_lock`; only one message processed at a time per agent instance |
| Background Agent reads stale session file | `last_message_at` DB field is the idle signal — always accurate regardless of session file state |
| psql not available in nanobot image | Add `postgresql-client` to Dockerfile; or use Python `psycopg2` via `exec` |
| LLM generates invalid SQL | Agent uses parameterised queries as much as possible; critical paths have confirmation steps |
| WhatsApp session expires | `nanobot channels login` must be re-run; document the recovery procedure |
| Reminder delivery fails | Retry not implemented in Phase 1 — failed reminders are logged and surfaced in daily report |
