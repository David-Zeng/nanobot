# Message Flow & Processing

---

## 1. Full Message Pipeline

Everything runs inside the nanobot agent loop. There is no separate guardrail service — all filtering, customer lookup, and context injection happen within the Customer Agent via instructions in `AGENTS.md` and the `IDENTITY.md` mechanism.

```mermaid
sequenceDiagram
    participant U as Customer (TG/WA/DC)
    participant CA as Customer Agent (nanobot)
    participant FS as Session File (shared volume)
    participant DB as PostgreSQL

    U->>CA: Message arrives via channel
    CA->>DB: Lookup customer by IM ID
    alt New customer
        CA->>DB: INSERT customers (IM ID only)
        CA->>CA: Ask for name + mobile
        CA->>DB: UPDATE customers SET name, mobile
    end
    CA->>DB: SELECT latest customer_memory
    CA->>CA: Write IDENTITY.md with customer record + memory summary
    CA->>FS: Load session file (channel:chat_id.jsonl)
    CA->>CA: Build system prompt: identity + SOUL + AGENTS + USER + IDENTITY + memory
    CA->>CA: Guardrail check (LLM classifies message topic)
    alt Off-topic
        CA-->>U: "I am the Beauty Salon assistant..."
    else On-topic
        CA->>CA: Rate limit check (count recent messages in session file)
        alt Rate limited
            CA-->>U: "Please slow down..."
        else
            CA->>CA: Generate response (booking / query / modification)
            CA->>DB: Execute DB operations (booking, update, etc.)
            CA->>DB: INSERT operation_history
            CA->>DB: UPDATE customers SET last_message_at = NOW()
            CA->>FS: Save turn to session file
            CA-->>U: Response
        end
    end
```

---

## 2. IM Account Resolution

```mermaid
flowchart TD
    A[Message arrives] --> B{Which channel?}
    B -->|telegram| C[WHERE telegram_id = sender_id]
    B -->|whatsapp| D[WHERE whatsapp_id = sender_id]
    B -->|discord| E[WHERE discord_id = sender_id]

    C --> F{Customer found?}
    D --> F
    E --> F

    F -->|Yes| G[Load customer record]
    F -->|No| H[INSERT customer with IM ID only]
    H --> I[Ask: name and mobile number?]
    I --> J[UPDATE customer with name + mobile]
    J --> G

    G --> K[SELECT latest customer_memory summary]
    K --> L[Write IDENTITY.md to workspace]
    L --> M[Load session file for this channel:chat_id]
    M --> N[Process with agent]
```

---

## 3. Customer Context Loading

Context is loaded in two layers on every message:

**Layer 1 — Long-term memory (DB)**
The latest `customer_memory` summary is fetched and written to `IDENTITY.md` before the agent loop starts. This gives the agent the customer's history, preferences, and past appointment patterns.

**Layer 2 — Current session (JSONL file)**
nanobot automatically loads the session file for `channel:chat_id` and injects recent turns into the message history. This gives the agent the live conversation context.

Together: the agent always has both a long-term view (from DB) and the current conversation (from session file).

```
System prompt contains:
  └── IDENTITY.md  ← customer record + latest DB memory summary

Message history contains:
  └── sessions/telegram_123456789.jsonl  ← current conversation turns
```

---

## 4. IDENTITY.md Injection Mechanism

The `IDENTITY.md` file is part of nanobot's bootstrap file list (`ContextBuilder.BOOTSTRAP_FILES`). It is loaded into the system prompt automatically if it exists in the workspace.

Before each customer message is processed, a wrapper script (or the agent itself, on first message) overwrites `IDENTITY.md` with the current customer's data:

```
1. Receive message from channel (channel, sender_id, content)
2. Query DB: SELECT * FROM customers WHERE <channel>_id = sender_id
3. Query DB: SELECT summary FROM customer_memory WHERE customer_id = X ORDER BY created_at DESC LIMIT 1
4. Query DB: SELECT * FROM appointments WHERE customer_id = X AND status != 'cancelled' ORDER BY appointment_time
5. Write IDENTITY.md to workspace with above data
6. Route message to nanobot gateway (normal flow)
```

**Important:** Only one customer is active per message turn. `IDENTITY.md` is written atomically before the message is processed. Since nanobot serialises message processing via `_processing_lock`, there is no race condition.

---

## 5. Rate Limiting

Rate limiting is enforced via `AGENTS.md` instructions — no DB queries per-message.

The agent uses the `exec` tool to count recent messages in the session JSONL file when it suspects rate abuse:

```bash
# Count customer messages in the last 60 seconds
grep -c '"role": "user"' sessions/telegram_123456789.jsonl
```

For normal conversations this check is skipped entirely (no overhead). It is only triggered when the agent notices rapid successive messages — the LLM decides when to check based on the AGENTS.md instructions.

Configurable limits stored in the `settings` table:
- `rate_limit_per_minute`: 10 (default)
- `rate_limit_per_hour`: 50 (default)

---

## 6. Booking Flow

```mermaid
sequenceDiagram
    participant U as Customer
    participant CA as Customer Agent
    participant DB as PostgreSQL

    U->>CA: "I want to book a haircut"
    CA->>DB: SELECT * FROM services WHERE is_active = true
    DB-->>CA: Service list
    CA->>U: "When would you like to come in?"
    U->>CA: "Tomorrow at 2pm"
    CA->>DB: Check conflicts (appointments at that time ± buffer)
    DB-->>CA: No conflict
    CA->>U: "Confirm: Haircut tomorrow at 2pm?"
    U->>CA: "Yes"
    CA->>DB: INSERT INTO appointments
    CA->>DB: INSERT INTO reminders (24h before, session_key)
    CA->>DB: INSERT INTO operation_history (booking_create)
    CA->>DB: UPDATE customers SET last_message_at = NOW()
    CA->>U: "Booked! Appointment #123 confirmed for tomorrow at 2pm."
```

The reminder row in the `reminders` table includes `session_key` (e.g. `telegram:123456789`) so the Background Agent knows where to deliver it.

---

## 7. Appointment Modification

```
Customer: "I need to reschedule my appointment"
Agent: Queries appointments for this customer_id
Agent: "Your appointment is tomorrow at 2pm for a haircut. What would you like to change?"
Customer: "Change to 4pm"
Agent: Checks availability at 4pm
Agent: "Confirm: change to 4pm tomorrow?"
Customer: "Yes"
Agent: UPDATE appointments SET appointment_time = ..., updated_at = NOW()
Agent: INSERT operation_history (booking_update, old_value, new_value)
Agent: UPDATE reminders SET scheduled_time = ... WHERE appointment_id = X AND status = 'pending'
Agent: "Done! Your appointment is now at 4pm."
```
