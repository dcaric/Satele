#!/bin/bash

# Configuration
export REMOTE_BRIDGE_URL="http://localhost:8000"
export BRIDGE_SECRET_KEY="default-secret-key"

echo "🧹 Cleaning up media cache..."
rm -rf media/*
mkdir -p media

echo "🚀 Starting System (Logging to bridge.log)..."
echo "--- NEW SESSION $(date) ---" >> bridge.log

venv/bin/python server/main.py >> bridge.log 2>&1 &
SERVER_PID=$!

# Start the Autonomous Monitor
venv/bin/python monitor.py >> bridge.log 2>&1 &
MONITOR_PID=$!

mkdir -p .mudslide_cache
node whatsapp_bridge.js >> bridge.log 2>&1 &
WA_PID=$!

# Cleanup on exit
trap "kill $SERVER_PID $BRIDGE_PID $WA_PID" EXIT
echo "✅ All processes started. Tail bridge.log to see activity."
wait
