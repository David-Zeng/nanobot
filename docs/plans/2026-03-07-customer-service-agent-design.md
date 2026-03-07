# Beauty Salon Customer Service Agent System

> **This document has been superseded.**
>
> The design has been split into focused files for easier navigation.
> See the full design in: [`docs/plans/beauty-salon-agent/`](./beauty-salon-agent/)

## Document Index

| File | Contents |
|------|----------|
| [00-overview.md](./beauty-salon-agent/00-overview.md) | System summary, architecture diagram, key design decisions |
| [01-nanobot-mechanics.md](./beauty-salon-agent/01-nanobot-mechanics.md) | How nanobot works — workspace files, sessions, memory, heartbeat, cron |
| [02-database-schema.md](./beauty-salon-agent/02-database-schema.md) | PostgreSQL schema — all tables with SQL |
| [03-agent-configs.md](./beauty-salon-agent/03-agent-configs.md) | SOUL.md, AGENTS.md, HEARTBEAT.md, config.json per agent |
| [04-message-flow.md](./beauty-salon-agent/04-message-flow.md) | Message pipeline, IM resolution, context loading, booking flow |
| [05-background-agent.md](./beauty-salon-agent/05-background-agent.md) | Background Agent — summarisation, reminders, daily report, cleanup |
| [06-security.md](./beauty-salon-agent/06-security.md) | Guardrails, rate limiting, access control, audit trail |
| [07-docker-deployment.md](./beauty-salon-agent/07-docker-deployment.md) | docker-compose.yml, folder structure, env vars, backup/restore |
| [08-roadmap.md](./beauty-salon-agent/08-roadmap.md) | Implementation phases, task checklist, key risks |
