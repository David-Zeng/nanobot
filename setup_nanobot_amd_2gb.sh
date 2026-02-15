#!/bin/bash
set -e

# ==============================================================================
# nanobot Setup Script for AMD VPS (2GB RAM)
# 
# This script automates the deployment of nanobot on a fresh Ubuntu VPS.
# It handles:
#   1. System optimization (Swap creation for 2GB RAM stability)
#   2. Dependency installation (Docker)
#   3. Building the application
#   4. Configuration setup
#   5. Container lifecycle management
# ==============================================================================

# Colors for user-friendly output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}   nanobot Setup (AMD 2GB RAM Optimized) ${NC}"
echo -e "${GREEN}=========================================${NC}"

# ------------------------------------------------------------------------------
# STEP 0: Low-RAM Optimization (Swap Creation)
# ------------------------------------------------------------------------------
# Why: 2GB RAM is minimal for modern AI applications. Even though nanobot is light,
# background processes or spikes can cause "Out Of Memory" (OOM) kills.
# Solution: Create a 1GB swap file to act as "emergency RAM".
# ------------------------------------------------------------------------------
if [ $(free -m | grep Swap | awk '{print $2}') -eq 0 ]; then
    echo -e "${YELLOW}Detected 0 swap. Creating 1GB swap file for stability...${NC}"
    
    # create a file of size 1GB
    sudo fallocate -l 1G /swapfile
    # restrict permissions (security best practice)
    sudo chmod 600 /swapfile
    # format as swap
    sudo mkswap /swapfile
    # enable swap immediately
    sudo swapon /swapfile
    # make permanent across reboots by adding to /etc/fstab
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    
    echo -e "${GREEN}Swap created.${NC}"
else
    echo -e "${GREEN}Swap already exists. Good.${NC}"
fi

# ------------------------------------------------------------------------------
# STEP 1: Docker Installation
# ------------------------------------------------------------------------------
# Why: Docker ensures the app runs in a consistent environment, regardless of your
# VPS OS version. It isolates dependencies.
# ------------------------------------------------------------------------------
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker not found. Installing Docker...${NC}"
    
    # Download official Docker installation script
    curl -fsSL https://get.docker.com -o get-docker.sh
    # Execute script
    sh get-docker.sh
    rm get-docker.sh
    echo -e "${GREEN}Docker installed successfully.${NC}"
    
    # Add current user to 'docker' group to avoid needing 'sudo' for every command
    if [ "$EUID" -ne 0 ]; then
        echo -e "${YELLOW}Adding current user to docker group...${NC}"
        sudo usermod -aG docker $USER
        echo -e "${RED}Please log out and log back in for group changes to take effect.${NC}"
        echo -e "${RED}Then run this script again.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}Docker is already installed.${NC}"
fi

# ------------------------------------------------------------------------------
# STEP 2: Build Docker Image
# ------------------------------------------------------------------------------
# Why: Creates a self-contained image named 'nanobot' from the source code.
# This compiles Python dependencies defined in pyproject.toml.
# ------------------------------------------------------------------------------
echo -e "${YELLOW}Building nanobot Docker image...${NC}"
docker build -t nanobot .

# ------------------------------------------------------------------------------
# STEP 3: Configuration Setup
# ------------------------------------------------------------------------------
# Why: We need a persistent place to store API keys and conversation history
# that survives container restarts. We use ~/.nanobot on the host.
# ------------------------------------------------------------------------------
CONFIG_DIR="$HOME/.nanobot"
mkdir -p "$CONFIG_DIR"

if [ ! -f "$CONFIG_DIR/config.json" ]; then
    echo -e "${YELLOW}Config not found. Initializing...${NC}"
    
    # Run 'onboard' command inside a temporary container to generate default config
    docker run --rm -v "$CONFIG_DIR:/root/.nanobot" nanobot onboard
    
    # Pause to let the user add their API keys manually
    echo -e "${YELLOW}IMPORTANT: Please edit $CONFIG_DIR/config.json to add your API keys.${NC}"
    echo -e "${YELLOW}Example:${NC}"
    echo -e '  "providers": { "openrouter": { "apiKey": "sk-..." } }'
    read -p "Press Enter when you have configured your API keys (or Ctrl+C to stop)..."
else
    echo -e "${GREEN}Configuration found at $CONFIG_DIR${NC}"
fi

# ------------------------------------------------------------------------------
# STEP 4: Cleanup Old Containers
# ------------------------------------------------------------------------------
# Why: Avoid port conflicts (Address already in use) by removing any previous instance.
# ------------------------------------------------------------------------------
if [ "$(docker ps -aq -f name=nanobot)" ]; then
    echo -e "${YELLOW}Stopping and removing existing nanobot container...${NC}"
    docker stop nanobot >/dev/null 2>&1 || true
    docker rm nanobot >/dev/null 2>&1 || true
fi

# ------------------------------------------------------------------------------
# STEP 5: Run Production Container
# ------------------------------------------------------------------------------
# Flags explanation:
#   -d                  : Detached mode (run in background)
#   --name nanobot      : Name the container for easy management
#   --restart always    : Auto-restart if it crashes or VPS reboots
#   -p 18790:18790      : Expose port for webhooks/API
#   -v ...              : Mount config dir so data persists
# ------------------------------------------------------------------------------
echo -e "${YELLOW}Starting nanobot gateway...${NC}"
docker run -d \
  --name nanobot \
  --restart always \
  -p 18790:18790 \
  -v "$CONFIG_DIR:/root/.nanobot" \
  nanobot gateway

# ------------------------------------------------------------------------------
# STEP 6: Verification
# ------------------------------------------------------------------------------
# Why: Confirm everything worked and show useful info to the user.
# ------------------------------------------------------------------------------
if [ "$(docker ps -q -f name=nanobot)" ]; then
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}   Deployment Successful!                ${NC}"
    echo -e "${GREEN}=========================================${NC}"
    echo -e "Container ID: $(docker ps -q -f name=nanobot)"
    echo -e "Status:       $(docker ps -f name=nanobot --format '{{.Status}}')"
    echo -e "Logs:         docker logs nanobot"
    echo -e "Config:       $CONFIG_DIR/config.json"
else
    echo -e "${RED}Deployment failed. Container is not running.${NC}"
    docker logs nanobot
    exit 1
fi
