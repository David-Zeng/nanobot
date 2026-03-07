# nanobot Mechanics — How It Works

Understanding nanobot internals is essential before designing the beauty salon system on top of it.

---

## 1. System Prompt Assembly

Every time the agent processes a message, `ContextBuilder` assembles the system prompt in this order:

```mermaid
flowchart TD
    A[Message received] --> B[Build system prompt]
    B --> C[1. Identity block<br/>hardcoded: nanobot identity + workspace path]
    C --> D[2. Bootstrap files<br/>AGENTS.md, SOUL.md, USER.md, TOOLS.md, IDENTITY.md]
    D --> E[3. Memory<br/>memory/MEMORY.md always injected]
    E --> F[4. Always-on skills<br/>skills with always: true]
    F --> G[5. Skills summary<br/>list of on-demand skills]
    G --> H[Prepend runtime context to user message<br/>current time, channel, chat_id]
    H --> I[Send to LLM]
```

**Runtime context** (current time, channel name, chat_id) is prepended to each user message — not the system prompt.

---

## 2. Workspace File Reference

Each nanobot instance has a workspace directory. These files control its behaviour:

| File | Purpose | Who edits it |
|------|---------|--------------|
| `SOUL.md` | Agent personality, values, communication style | Us at deploy time |
| `AGENTS.md` | Operational instructions — how to handle tasks, business rules | Us at deploy time |
| `USER.md` | Profile of the person the agent serves | Us at deploy time (describes the salon, not a customer) |
| `TOOLS.md` | Notes on tool usage constraints | Usually left as default |
| `IDENTITY.md` | Injected per-request for dynamic context | Written programmatically per customer message |
| `memory/MEMORY.md` | Long-term persistent facts (auto-updated by LLM) | Auto-managed by nanobot |
| `memory/HISTORY.md` | Append-only event log, grep-searchable | Auto-managed by nanobot |
| `HEARTBEAT.md` | Periodic task list, checked on heartbeat interval | Us at deploy time + agent can edit |
| `sessions/*.jsonl` | Conversation history per channel:chat_id | Auto-managed by nanobot |
| `cron/jobs.json` | Scheduled cron jobs | Agent via `cron` tool |
| `skills/*/SKILL.md` | Custom skill definitions | Us at deploy time |

---

## 3. Session Storage

Sessions are stored as JSONL files at:

```
workspace/sessions/<channel>_<chat_id>.jsonl
```

Each file contains:
- A metadata line: `{"_type": "metadata", "key": "...", "created_at": "...", "updated_at": "...", "last_consolidated": N}`
- One JSON line per message turn

Session key format: `channel:chat_id` — e.g. `telegram:123456789`

The `updated_at` field in the metadata line is the idle detection signal used by the Background Agent.

```mermaid
flowchart LR
    subgraph "sessions/"
        F1["telegram_123456789.jsonl"]
        F2["whatsapp_6591234567.jsonl"]
        F3["discord_987654321.jsonl"]
    end

    subgraph "JSONL structure"
        M["Line 1: metadata<br/>_type, key, created_at, updated_at, last_consolidated"]
        T1["Line 2: user turn"]
        T2["Line 3: assistant turn"]
        T3["Line N: ..."]
    end

    F1 --> M
    M --> T1
    T1 --> T2
    T2 --> T3
```

---

## 4. Memory Consolidation

When a session exceeds `memory_window` (default 100) unconsolidated messages, nanobot automatically:

1. Takes the old messages
2. Calls the LLM with a `save_memory` tool definition
3. LLM returns: `history_entry` (2-5 sentence summary) + `memory_update` (updated MEMORY.md content)
4. Appends `history_entry` to `memory/HISTORY.md`
5. Overwrites `memory/MEMORY.md` with `memory_update`
6. Updates `session.last_consolidated` pointer

This is automatic — no code needed. The `/new` command triggers it immediately (archive_all mode).

```mermaid
flowchart TD
    A[Session exceeds memory_window] --> B[Collect old messages]
    B --> C[Call LLM with save_memory tool]
    C --> D{LLM returns}
    D --> E[history_entry<br/>2-5 sentence summary]
    D --> F[memory_update<br/>full updated MEMORY.md]
    E --> G[Append to memory/HISTORY.md]
    F --> H[Overwrite memory/MEMORY.md]
    G --> I[Update last_consolidated pointer]
    H --> I
```

**Problem for multi-customer use:** `MEMORY.md` is one file per workspace. All customer memories would merge. Solution: use `customer_memory` DB table + per-request `IDENTITY.md` injection (see §04).

---

## 5. Heartbeat Service

Runs on a configurable interval (default: every 30 minutes).

```mermaid
flowchart TD
    A[Timer fires every N minutes] --> B[Read HEARTBEAT.md]
    B --> C{File exists and has content?}
    C -->|No| D[Skip]
    C -->|Yes| E[Call LLM with heartbeat tool<br/>Are there active tasks?]
    E --> F{LLM decision}
    F -->|action: skip| D
    F -->|action: run| G[Run full agent loop<br/>with task description]
    G --> H[Deliver result to<br/>most recent active channel]
```

**For the Background Agent:** heartbeat interval is set to 5 minutes. `HEARTBEAT.md` contains the idle-check task.

---

## 6. Cron Service

Stores jobs in `workspace/cron/jobs.json`. Supports:

| Schedule type | Example |
|---|---|
| `every` | Every 5 minutes |
| `at` | Once at a specific ISO datetime |
| `cron` | Cron expression with optional IANA timezone |

Jobs have a `payload.message` — this is the task description sent to the agent loop when the job fires. If `deliver: true`, the result is sent to the configured channel + chat_id.

**For appointment reminders:** cron jobs are created by the Customer Agent when a booking is confirmed. Each job has `deliver: true` targeting the customer's channel and chat_id.

---

## 7. Multi-Instance Support

Run multiple nanobot instances with:

```bash
nanobot gateway -w /path/to/workspace -c /path/to/config.json -p PORT
```

```mermaid
graph LR
    subgraph "customer-agent :18790"
        WA1[workspace A]
        CFG1[config A]
    end
    subgraph "admin-agent :18791"
        WA2[workspace B]
        CFG2[config B]
    end
    subgraph "background-agent :18792"
        WA3[workspace C]
        CFG3[config C]
    end

    subgraph "Shared"
        DB[(PostgreSQL)]
        VOL[Shared Volume]
    end

    WA1 <--> DB
    WA2 <--> DB
    WA3 <--> DB
    WA1 --- VOL
    WA3 --- VOL
```

Each instance has completely isolated:
- Workspace (sessions, memory, heartbeat, cron jobs, skills)
- Configuration (channels, model, system prompt files)
- Port

They share nothing by default — shared state goes through PostgreSQL and the mounted volume.

---

## 8. Built-in Tools Available to All Agents

| Tool | What it does |
|------|-------------|
| `read_file` | Read any file in workspace |
| `write_file` | Write/overwrite a file |
| `edit_file` | Edit file with old/new string replacement |
| `list_dir` | List directory contents |
| `exec` | Run shell commands (with safety limits) |
| `web_search` | Search the web (requires Brave API key) |
| `web_fetch` | Fetch a URL |
| `message` | Send a message to a specific channel:chat_id |
| `spawn` | Launch a subagent |
| `cron` | Add/list/remove scheduled jobs |

The `exec` tool is particularly powerful — agents can run `psql` commands to read/write PostgreSQL, grep session files, and run backup scripts.
