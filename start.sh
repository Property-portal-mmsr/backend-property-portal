#!/bin/bash
# ============================================================
#  MakeMyStay Backend – One-command startup script
#  Opens SSH tunnel → waits for MySQL → starts uvicorn
# ============================================================

set -e

# ---- Config ------------------------------------------------
PEM_KEY="${HOME}/.ssh/mms_deploy.pem"
EC2_USER="ubuntu"
EC2_HOST="13.126.149.224"          # primary server
LOCAL_PORT=3336
REMOTE_HOST="127.0.0.1"
REMOTE_PORT=3306
TUNNEL_LOG="/tmp/mms_tunnel.log"
# ------------------------------------------------------------

echo "🔑  Checking SSH tunnel on 127.0.0.1:${LOCAL_PORT}..."

if nc -z 127.0.0.1 ${LOCAL_PORT} 2>/dev/null; then
    echo "✅  Tunnel is already open on port ${LOCAL_PORT}, reusing it!"
    TUNNEL_PID=""
else
    # Open a fresh tunnel in the background
    echo "   ↳ Opening tunnel  ${LOCAL_PORT} → ${EC2_HOST}:${REMOTE_PORT}  ..."
    ssh -i "$PEM_KEY" \
        -o StrictHostKeyChecking=no \
        -o ExitOnForwardFailure=yes \
        -o ServerAliveInterval=30 \
        -o ServerAliveCountMax=3 \
        -N -L "${LOCAL_PORT}:${REMOTE_HOST}:${REMOTE_PORT}" \
        "${EC2_USER}@${EC2_HOST}" > "$TUNNEL_LOG" 2>&1 &

    TUNNEL_PID=$!
    echo "   ↳ Tunnel PID: ${TUNNEL_PID}"
fi

# Wait up to 15 s for MySQL to become reachable
echo "⏳  Waiting for MySQL on 127.0.0.1:${LOCAL_PORT} ..."
for i in $(seq 1 15); do
    if nc -z 127.0.0.1 ${LOCAL_PORT} 2>/dev/null; then
        echo "✅  MySQL is reachable!"
        break
    fi
    if [ "$i" -eq 15 ]; then
        echo "❌  Tunnel did not open within 15 s. See ${TUNNEL_LOG}"
        cat "$TUNNEL_LOG"
        kill "$TUNNEL_PID" 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

# Kill tunnel when the script exits / is Ctrl+C'd if we started it
trap 'if [ -n "$TUNNEL_PID" ]; then echo "🛑  Shutting down tunnel..."; kill $TUNNEL_PID 2>/dev/null || true; fi' EXIT INT TERM

# Start uvicorn
echo "🚀  Starting uvicorn..."
PYTHONPATH=. venv/bin/uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
