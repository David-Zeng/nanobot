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
      "groupPolicy": "open"
    }
  }
}
```

> **Important:** Use your number **without** the `+` prefix (e.g. `61433674165`,
> not `+61433674165`).

`groupPolicy` defaults to `"open"` (reply to every group message); set it to
`"mention"` to only reply when the bot is @-mentioned or replied to.

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

> **Known gap — self-messaging is not supported.** The previous bridge patched
> out Baileys' `fromMe` filter so you could message the bot by sending a
> WhatsApp message **to your own number** (appears as "You"). The new neonize
> implementation has no such option: `nanobot/channels/whatsapp.py` unconditionally
> drops messages where `source.IsFromMe` is true
> (`_handle_neonize_message`). If your workflow depends on self-messaging,
> this will not receive replies until either an upstream toggle is added or
> this fork reintroduces the override. Message from a second number/device in
> the meantime.

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

### Messages received but no reply

Check that your configured model (`agents.defaults.model` in
`~/.nanobot/config.json`) is valid for your provider and that the provider
API key is set correctly.
