#!/bin/bash
set -euo pipefail

# ==============================================================================
# nanobot Update Helper
#
# Updates the running nanobot container when code changes.
#
# Usage:
#   ./update_nanobot.sh     # Pull git changes and update container
#   ./update_nanobot.sh rpi # Update RPi container
#   ./update_nanobot.sh amd # Update AMD container
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$HOME/.nanobot"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}   nanobot Update                       ${NC}"
echo -e "${GREEN}=========================================${NC}"

# Detect platform if not specified
PLATFORM="${1:-}"

if [[ "$PLATFORM" == "rpi" ]] || [[ "$PLATFORM" == "amd" ]]; then
    SETUP_SCRIPT="$SCRIPT_DIR/setup_nanobot_${PLATFORM}.sh"
elif [[ -f "$SCRIPT_DIR/setup_nanobot_rpi.sh" ]]; then
    # Try to detect platform
    if uname -m | grep -q arm64; then
        SETUP_SCRIPT="$SCRIPT_DIR/setup_nanobot_rpi.sh"
    else
        SETUP_SCRIPT="$SCRIPT_DIR/setup_nanobot_amd_2gb.sh"
    fi
else
    echo -e "${RED}Setup scripts not found. Ensure setup_nanobot_*.sh is in the same directory.${NC}"
    exit 1
fi

if [[ ! -f "$SETUP_SCRIPT" ]]; then
    echo -e "${RED}Setup script not found: $SETUP_SCRIPT${NC}"
    exit 1
fi

# Check if config exists
if [[ ! -f "$CONFIG_DIR/config.json" ]]; then
    echo -e "${RED}Error: Config not found at $CONFIG_DIR${NC}"
    echo -e "${YELLOW}Please run setup script first:${NC}"
    echo -e "  $SETUP_SCRIPT"
    exit 1
fi

# Update logic
echo -e "${YELLOW}Step 1: Updating code from git...${NC}"
git pull

echo -e "${YELLOW}Step 2: Rebuilding container...${NC}"
bash "$SETUP_SCRIPT"

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}   Update Complete!                     ${NC}"
echo -e "${GREEN}=========================================${NC}"
echo -e "Logs:    docker logs -f nanobot"
echo -e "Status:  docker ps | grep nanobot"
echo -e "Config:  $CONFIG_DIR/config.json"
