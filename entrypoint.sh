#!/bin/sh
dir="$HOME/.nanobot"
if [ -d "$dir" ] && [ ! -w "$dir" ]; then
    owner_uid=$(stat -c %u "$dir" 2>/dev/null || stat -f %u "$dir" 2>/dev/null)
    cat >&2 <<ERRMSG
Error: $dir is not writable (owned by UID $owner_uid, running as UID $(id -u)).

Fix (pick one):
  Host:   sudo chown -R 1000:1000 ~/.nanobot
  Docker: docker run --user \$(id -u):\$(id -g) ...
  Podman: podman run --userns=keep-id ...
ERRMSG
    exit 1
fi

# Auto-start WhatsApp bridge if installed and gateway is being started
if [ "$1" = "gateway" ] && [ -f "$HOME/.nanobot/bridge/dist/index.js" ]; then
    TOKEN_FILE="$HOME/.nanobot/whatsapp-auth/bridge-token"
    AUTH_DIR="$HOME/.nanobot/whatsapp-auth"
    if [ -f "$TOKEN_FILE" ]; then
        BRIDGE_TOKEN=$(cat "$TOKEN_FILE")
        BRIDGE_TOKEN="$BRIDGE_TOKEN" AUTH_DIR="$AUTH_DIR" node "$HOME/.nanobot/bridge/dist/index.js" &
    fi
fi

exec nanobot "$@"
