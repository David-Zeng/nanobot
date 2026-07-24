# WhatsApp Channel Setup (Docker / Raspberry Pi)

This guide covers setting up the WhatsApp channel when running nanobot in Docker.

> **Migration note (July 2026):** WhatsApp used to run through a Node.js/Baileys
> bridge (`bridge/`) that this fork patched and auto-started from `entrypoint.sh`.
> Upstream removed that bridge entirely and reimplemented WhatsApp natively in
> Python using [neonize](https://github.com/krypton-byte/neonize)
> (`nanobot/channels/whatsapp.py`). There is no more `bridge/` directory and no
> `bridge-token` file. The `nanobot channels login whatsapp` command still
> exists — it now drives neonize directly (`WhatsAppChannel.login()`) instead
> of the old bridge process. See `docs/DOCKER_UPDATE_GUIDE.md` for what
> changes on rebuild.

## Prerequisites

- nanobot running in Docker with the `whatsapp` extra installed (see
  `NANOBOT_EXTRAS` in the `Dockerfile`)
- A WhatsApp account on your phone

## Step 1 — Configure

Add the WhatsApp channel to `~/.nanobot/config.json`:

```json
{
  "channels": {
    "whatsapp": {
      "enabled": true,
      "allowFrom": ["61433674165"],
      "groupPolicy": "open",
      "dmPolicy": "mention"
    }
  }
}
```

> **Important:** Use your number **without** the `+` prefix (e.g. `61433674165`,
> not `+61433674165`).

`groupPolicy` defaults to `"open"` (reply to every group message); set it to
`"mention"` to only reply when the bot is @-mentioned or replied to.
`dmPolicy` also defaults to `"open"`; set it to `"mention"` to ignore
unsolicited direct messages while accepting mentions and replies to the bot.

One-to-one chats cannot produce a genuine WhatsApp @mention, so under
`dmPolicy: "mention"` a new conversation is started by beginning the message
with the `mentionKeyword` text trigger (default `"@nanobot"`, case-insensitive,
stripped before the agent sees the message). Set `mentionKeyword` to `""` to
require a reply to the bot instead.

## Step 2 — Link Your Device (Scan QR Code)

**Option A — via the running gateway.** Start (or restart) the container and
watch the logs:

```bash
docker compose up -d
docker logs -f nanobot
```

An ASCII QR code prints directly to the log output when no session exists yet.
Open WhatsApp on your phone: **Settings → Linked Devices → Link a Device** →
scan it.

**Option B — standalone interactive login**, without needing the gateway
running or tailing logs:

```bash
docker exec -it nanobot nanobot channels login whatsapp
# or, to discard an existing session and force a fresh QR:
docker exec -it nanobot nanobot channels login whatsapp --force
```

Either way, the session is saved to `~/.nanobot/whatsapp-auth/neonize.db` on
the host and persists across container restarts via the volume mount — you
should only need to scan once, unless the device gets unlinked from the phone
side or the auth DB is deleted.

## Step 3 — How to Message Nanobot

Send a WhatsApp message from your phone (or another account in `allowFrom`)
to the linked number, or add nanobot to a group.

With the default `"open"` policies every permitted message gets a reply. Under
a `"mention"` policy (verified on the Pi deployment, 2026-07-24), a message is
handled only when it addresses the bot in one of three ways:

| How to address the bot | DMs | Groups |
|---|---|---|
| Start the message with `@nanobot ` (the `mentionKeyword`) | ✅ | ✅ |
| Reply to one of Nanobot's messages | ✅ | ✅ |
| Genuine WhatsApp @mention (picked from the popup) | n/a — not possible in 1:1 chats | ✅ |

Keyword rules, as implemented and tested:

- The message must **start** with the keyword — `@nanobot hello` works;
  `hello @nanobot` and `@nanobots hello` do not.
- Matching is case-insensitive and tolerates leading whitespace.
- The keyword is stripped before the agent sees the text (the agent receives
  `hello`).
- A bare `@nanobot` with no other text and no media is dropped.
- The keyword is how a **new** DM conversation starts under
  `dmPolicy: "mention"`; once Nanobot has replied, replying to its messages
  needs no keyword.
- `mentionKeyword` does **not** bypass `allowFrom` — an unlisted sender is
  dropped no matter what they type.

> **Self-messaging works.** Messaging your own linked number from another
> device (the chat labeled "You") reaches the bot; this fork restores the
> behavior the old bridge provided. The bot's own outbound replies are
> deduplicated so they are not re-processed as inbound messages.

## Troubleshooting

### "Access denied for sender" in logs

The `allowFrom` number doesn't match the resolved sender ID. Check the logs
for the exact ID nanobot resolved (phone number preferred, falling back to
WhatsApp's internal LID if the phone number isn't yet known):

```
Access denied for sender 61433674165. Add them to allowFrom list in config to grant access.
```

Use that exact value (without `+`) in `allowFrom`.

### QR code doesn't appear in `docker logs`

The QR renders as ASCII art via `segno` right after `Scan the WhatsApp QR
code with Linked Devices` in the log stream — it can lag the log line by a
few seconds. Re-run `docker logs -f nanobot` and wait a moment, or `docker
logs nanobot` (non-follow) after a short pause.

### No reply in a DM and nothing in the logs

Under `dmPolicy: "mention"` an unaddressed direct message is dropped
**silently, before any log line** — this is by design. Check, in order:

1. The message starts with the exact `mentionKeyword` (default `@nanobot`,
   `@` included, followed by a space) — or is a reply to a Nanobot message.
2. The sender's number is in `allowFrom` in international format without `+`
   (e.g. an Australian mobile `0433322885` must be listed as `61433322885`).
   A sender that passes the keyword gate but fails `allowFrom` logs
   `Ignoring unauthorized WhatsApp sender ...`; a message that fails the
   keyword gate logs nothing at all.
3. The message was sent **after** the container started — messages older than
   channel startup are ignored, so anything sent during a restart window is
   never replayed.

### Messages received but no reply

Check that your configured model (`agents.defaults.model` in
`~/.nanobot/config.json`) is valid for your provider and that the provider
API key is set correctly.
