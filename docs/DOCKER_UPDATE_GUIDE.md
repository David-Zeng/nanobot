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

### WhatsApp bridge loses session after rebuild

The WhatsApp bridge binary is rebuilt into the image, but the **auth session**
lives in `~/.nanobot/whatsapp-auth/` on the host and persists via the volume
mount. You should not need to re-scan the QR code after a rebuild.

However, if the bridge JS was patched (e.g. the `fromMe` self-message fix),
the patch must be reapplied to `bridge/src/whatsapp.ts` before rebuilding,
otherwise self-messaging will stop working again. See `docs/WHATSAPP_DOCKER_SETUP.md`.

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
