# Deployment Guide

This guide covers deploying nanobot on **AMD VPS with 2GB RAM**.

## Feasibility Confirmation

**Yes, 2GB RAM is sufficient.**

- **Core memory footprint**: ~150MB (estimated from Docker image size and dependencies)
- **Peak usage**: ~300MB with active chat
- **Remaining**: ~1.7GB for system, channels, and background processes

nanobot is intentionally ultra-lightweight — this deployment is **fully supported**.

## Prerequisites

| Option | Requirement |
|--------|-------------|
| **Docker** (Recommended) | Docker Engine 20.10+ |
| **Bare Metal** | Python 3.11+ (or 3.12+ recommended) |

### Installing Docker on AMD VPS

```bash
# Debian/Ubuntu
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Log out and back in for group changes to take effect
```

## Docker Deployment (Recommended)

### Build the Image

```bash
docker build -t nanobot .
```

### First-Time Setup

```bash
# Initialize config (creates ~/.nanobot/)
docker run -v ~/.nanobot:/root/.nanobot --rm nanobot onboard
```

### Configure API Keys

Edit `~/.nanobot/config.json`:

```json
{
  "providers": {
    "openrouter": {
      "apiKey": "sk-or-v1-xxx"
    }
  },
  "agents": {
    "defaults": {
      "model": "anthropic/claude-opus-4-5"
    }
  }
}
```

### Run Gateway

```bash
docker run -d \
  --restart always \
  -p 18790:18790 \
  -v ~/.nanobot:/root/.nanobot \
  nanobot gateway
```

**Flags explained:**
- `-d`: Run in background
- `--restart always`: Auto-restart on crash or reboot
- `-p 18790:18790`: Expose port (gateway default)
- `-v ~/.nanobot:/root/.nanobot`: Persist config and workspace

### Verify Running

```bash
docker ps
docker logs nanobot
```

### Run Commands Directly

```bash
# Chat with agent
docker run -v ~/.nanobot:/root/.nanobot --rm nanobot agent -m "Hello!"

# Check status
docker run -v ~/.nanobot:/root/.nanobot --rm nanobot status

# Check channel connections
docker run -v ~/.nanobot:/root/.nanobot --rm nanobot channels status
```

## Systemd (Bare Metal)

### Install Python Dependencies

```bash
pip install -e ".[dev]"  # Includes dev dependencies, still minimal
```

### Create Service File

Create `/etc/systemd/system/nanobot.service`:

```ini
[Unit]
Description=Nanobot Gateway
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/nanobot
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/nanobot gateway
Restart=always
RestartSec=10

# Memory limits for 2GB VPS
MemoryLimit=2G
MemorySwapMax=1G

[Install]
WantedBy=multi-user.target
```

### Enable and Start

```bash
sudo systemctl daemon-reload
sudo systemctl enable nanobot
sudo systemctl start nanobot
sudo systemctl status nanobot
```

### Check Logs

```bash
sudo journalctl -u nanobot -f
```

## Low-Resource Tips

### 1. Use Remote Providers (Recommended)

Local LLMs (Ollama, vLLM) require significant RAM (4GB-32GB depending on model).

**Use remote providers instead:**

| Provider | Memory Cost | Cost |
|----------|-------------|------|
| OpenRouter | ~0MB | Per-token |
| Anthropic | ~0MB | Per-token |
| Groq | ~0MB | Per-token (free tier available) |

```json
{
  "providers": {
    "openrouter": {
      "apiKey": "sk-or-v1-xxx"
    }
  },
  "agents": {
    "defaults": {
      "model": "anthropic/claude-opus-4-5"
    }
  }
}
```

### 2. Add Swap File (If Running Other Services)

If your VPS runs other services, add swap to prevent OOM kills:

```bash
# Create 1GB swap file
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make it persistent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Verify
free -h
```

### 3. Disable Unused Channels

Each channel has a memory footprint. Disable what you don't use.

**WhatsApp bridge** (optional, requires Node.js ≥18):

```bash
# In config.json, disable if not needed:
{
  "channels": {
    "whatsapp": {
      "enabled": false  // Set to false
    }
  }
}
```

**Disable all unused channels:**
- Telegram: `enabled: true/false`
- Discord: `enabled: true/false`
- WhatsApp: `enabled: true/false`
- Feishu: `enabled: true/false`
- Mochat: `enabled: true/false`
- DingTalk: `enabled: true/false`
- Slack: `enabled: true/false`
- Email: `enabled: true/false`
- QQ: `enabled: true/false`

### 4. Optional: Reduce Log Level

In `~/.nanobot/config.json`:

```json
{
  "logLevel": "WARNING"  // Default is INFO
}
```

## Monitoring Resources

### Docker

```bash
# Check memory usage
docker stats nanobot

# Check logs
docker logs nanobot --tail 100
```

### Systemd

```bash
# Check memory usage
systemctl show nanobot --property=MemoryCurrent,MemoryLimit

# Check logs
journalctl -u nanobot --since today
```

## Troubleshooting

### Out of Memory (OOM)

If nanobot gets killed by the kernel:

1. **Check OOM logs:**
   ```bash
   dmesg | grep -i "killed process"
   ```

2. **Increase swap** (see tip #2 above)

3. **Disable channels** you don't use

4. **Use a lighter model** in config:
   ```json
   {
     "agents": {
       "defaults": {
         "model": "deepseek/deepseek-chat"  // ~8x cheaper than Claude
       }
     }
   }
   ```

### Gateway Won't Start

1. **Check port is free:**
   ```bash
   sudo netstat -tlnp | grep 18790
   ```

2. **Check config validity:**
   ```bash
   docker run -v ~/.nanobot:/root/.nanobot --rm nanobot onboard
   ```

3. **Review logs:**
   ```bash
   docker logs nanobot
   ```

### Channel Connection Issues

1. **Check channel status:**
   ```bash
   docker run -v ~/.nanobot:/root/.nanobot --rm nanobot channels status
   ```

2. **Verify API keys** are set correctly

3. **Check network/firewall** allows outbound connections to channel APIs

## Upgrading

### Docker

```bash
# Stop and remove old container
docker stop nanobot
docker rm nanobot

# Pull latest image (or rebuild)
docker build -t nanobot .

# Restart with same flags
docker run -d --restart always -p 18790:18790 -v ~/.nanobot:/root/.nanobot nanobot gateway
```

### Bare Metal

```bash
# Pull latest changes
git pull
pip install -e ".[dev]"

# Restart systemd service
sudo systemctl restart nanobot
```

## Further Reading

- [Main README](README.md) - Full feature list and setup
- [Configuration](https://github.com/HKUDS/nanobot#configuration) - Detailed config options
- [CLI Reference](https://github.com/HKUDS/nanobot#cli-reference) - All available commands
