# Updating Nanobot (Docker / Raspberry Pi)

This guide covers how to pull upstream changes and rebuild the Docker image,
including known issues encountered on Raspberry Pi.

## Standard Update Flow

```bash
cd ~/git_repo/nanobot

# 1. Pull upstream changes into your branch
git fetch origin
git merge origin/main --no-edit

# 2. Rebuild the image (use explicit path, not '.')
docker build -t nanobot /home/pi/git_repo/nanobot

# 3. Recreate the container
docker stop nanobot && docker rm nanobot
docker run -d \
  --name nanobot \
  --restart always \
  -p 18790:18790 \
  -v /home/pi/.nanobot:/home/nanobot/.nanobot \
  nanobot gateway
```

## Known Issues

### `docker build .` fails with "requires 1 argument"

When running `docker build .` via SSH or a script, the `.` argument can be
silently dropped. Always use the **explicit absolute path** instead:

```bash
# Wrong (may fail over SSH)
docker build -t nanobot .

# Correct
docker build -t nanobot /home/pi/git_repo/nanobot
```

### Volume mount path mismatch (`No API key configured`)

The container runs as user `nanobot` with `HOME=/home/nanobot`. The config
must be mounted to `/home/nanobot/.nanobot`, not `/root/.nanobot`:

```bash
# Wrong
-v /home/pi/.nanobot:/root/.nanobot

# Correct
-v /home/pi/.nanobot:/home/nanobot/.nanobot
```

### Permission denied on `workspace/cron/jobs.json`

Files created by earlier container runs (or the `onboard` step) may be owned
by `root`. Fix before starting the container:

```bash
sudo chown -R $(id -u):$(id -g) ~/.nanobot
```

The `setup_nanobot_rpi.sh` script does this automatically.

### WhatsApp bridge removed upstream (neonize migration)

As of the July 2026 upstream merge, the Node.js/Baileys `bridge/` directory
(and its entrypoint auto-start block) is gone. WhatsApp now runs natively in
Python via the `neonize` library (`nanobot/channels/whatsapp.py`) — no
separate bridge process, no `npm install -g` build step for it.

The old Baileys auth session (`creds.json`, `app-state-sync-key-*.json`,
`bridge-token` in `~/.nanobot/whatsapp-auth/`) is **not compatible** with
neonize's expected format (`neonize.db`). After merging this change and
rebuilding, WhatsApp will disconnect and print a QR code to the container
logs (`docker logs -f nanobot`) — re-scan it from Linked Devices on your
phone. This is a one-time migration cost, not a per-rebuild issue.

If you previously patched `bridge/src/whatsapp.ts` (read receipts, LID group
mentions, reply-to-bot detection), those patches are obsolete — the upstream
Python implementation (`_send_read_receipt`, `_was_mentioned`,
`_is_reply_to_bot` in `nanobot/channels/whatsapp.py`) already covers the same
ground natively. The one patch that did **not** carry forward is the `fromMe`
self-message override: `_handle_neonize_message` unconditionally drops
messages where `source.IsFromMe` is true, so "message your own linked number"
no longer reaches the bot. See `docs/WHATSAPP_DOCKER_SETUP.md` (updated for
the neonize flow) for setup and this specific gap.

### `NANOBOT_EXTRAS` build arg controls which channels actually work

The Dockerfile only installs the Python extras listed in the `NANOBOT_EXTRAS`
build arg (`ARG NANOBOT_EXTRAS=whatsapp,weixin,telegram`, set once near the
top of the Python install stage). A channel can be `"enabled": true` in
`config.json` with a valid token and still silently fail to start with
`No module named 'telegram'` (or similar) in `docker logs` if its extra
isn't in that list — the failure is a `WARNING`, not a crash, so the
container looks healthy.

When enabling a new channel in `config.json`, check whether its extra
(see `[project.optional-dependencies]` in `pyproject.toml`) is already in
`NANOBOT_EXTRAS`; if not, add it there and rebuild.

### Model not supported error

After an upstream merge, verify your model name is still valid for your
provider. Check available models:

```bash
docker exec nanobot python3 -c "
import httpx, asyncio, json
async def list_models():
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.get('https://nano-gpt.com/api/v1/models',
            headers={'Authorization': 'Bearer YOUR_API_KEY'})
        for m in json.loads(r.text).get('data', []):
            print(m['id'])
asyncio.run(list_models())
"
```

## Checking the Running Version

```bash
docker logs nanobot 2>&1 | grep "Starting nanobot"
# 🐈 Starting nanobot gateway version 0.1.5.post1 on port 18790...
```
