#!/bin/bash
# =============================================================================
# MakeMyStay Realty – Employee Portal Full Deployment Script
# Target Server: ubuntu@13.201.61.117
# =============================================================================
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh
#
# What this script does:
#   1. Pushes the latest backend (property-portal-backend) to the server
#   2. Pushes the latest frontend (frontend-property-portal) to the server
#   3. Installs dependencies, builds Next.js, restarts PM2
#   4. Updates Nginx config (adds employee.makemystay.ai + employee-api.makemystay.ai blocks)
#   5. Verifies everything is running
# =============================================================================

set -e  # Exit on any error

# ------------- Configuration -------------------------------------------------
SERVER="ubuntu@13.201.61.117"
SSH_KEY="$HOME/.ssh/mms_deploy.pem"
SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no"

BACKEND_LOCAL="$HOME/property-portal-backend"
BACKEND_REMOTE="/var/www/property-portal-backend"

FRONTEND_LOCAL="$HOME/frontend-property-portal"
FRONTEND_REMOTE="/var/www/employee-portal"

NGINX_CONF="/etc/nginx/sites-available/makemystay_all"

# Colors for output
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

log()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()   { echo -e "${GREEN}[OK]${NC}   $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERR]${NC}  $1"; exit 1; }

# ------------- Helper: ssh command -------------------------------------------
run_remote() {
    ssh $SSH_OPTS "$SERVER" "$1"
}

# =============================================================================
# STEP 1 – Pre-deployment backup
# =============================================================================
log "Step 1: Creating server-side backups..."
run_remote "
    set -e
    cd /var/www

    # Backup backend
    [ -d property-portal-backend ] && cp -r property-portal-backend property-portal-backend-backup-\$(date +%F-%H%M) && echo 'Backend backed up'

    # Backup Nginx config
    sudo cp $NGINX_CONF ${NGINX_CONF}.backup-\$(date +%F-%H%M) 2>/dev/null || true && echo 'Nginx config backed up'
"
ok "Backups created."

# =============================================================================
# STEP 2 – Deploy Backend
# =============================================================================
log "Step 2: Deploying backend to $BACKEND_REMOTE..."

# Sync backend files (exclude venv, pycache, .git, local .env)
rsync -az --delete \
    --exclude 'venv/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '.git/' \
    --exclude '.env' \
    --exclude '.env.local' \
    --exclude '*.db' \
    -e "ssh $SSH_OPTS" \
    "$BACKEND_LOCAL/" "$SERVER:$BACKEND_REMOTE/"

ok "Backend files synced."

# Write production .env on the server
log "Writing production .env for backend..."
run_remote "cat > $BACKEND_REMOTE/.env << 'ENVEOF'
DB_HOST=172.31.46.162
DB_PORT=3306
DB_NAME=property_portal
DB_USER=appuser
DB_PASSWORD=StrongPassword@123
SECRET_KEY=propertyportal@2026
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=7
ENVEOF
echo '.env written'"

# Install Python dependencies
log "Installing Python dependencies..."
run_remote "
    set -e
    cd $BACKEND_REMOTE
    if [ ! -d venv ]; then
        python3 -m venv venv
        echo 'Created new venv'
    fi
    source venv/bin/activate
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    echo 'Dependencies installed'
"
ok "Backend dependencies ready."

# =============================================================================
# STEP 3 – Deploy Frontend
# =============================================================================
log "Step 3: Deploying frontend to $FRONTEND_REMOTE..."

# Sync frontend source files (exclude node_modules, .next build artifacts, .git)
rsync -az --delete \
    --exclude 'node_modules/' \
    --exclude '.next/' \
    --exclude '.git/' \
    --exclude '.env.local' \
    -e "ssh $SSH_OPTS" \
    "$FRONTEND_LOCAL/" "$SERVER:$FRONTEND_REMOTE/"

ok "Frontend files synced."

# Install npm dependencies and build
log "Installing npm dependencies and building Next.js..."
run_remote "
    set -e
    cd $FRONTEND_REMOTE

    # Set production env
    cat > .env.production << 'ENVEOF'
NEXT_PUBLIC_API_URL=https://employee-api.makemystay.ai/api/v1
ENVEOF

    # Install and build
    npm install --prefer-offline 2>&1 | tail -5
    npm run build 2>&1 | tail -10
    echo 'Next.js build complete'
"
ok "Frontend built successfully."

# =============================================================================
# STEP 4 – Update Nginx Configuration
# =============================================================================
log "Step 4: Updating Nginx config..."

run_remote "sudo bash -s" << 'NGINX_SCRIPT'
set -e
NGINX_CONF="/etc/nginx/sites-available/makemystay_all"

# Check if employee blocks already exist
if grep -q "employee.makemystay.ai" "$NGINX_CONF" 2>/dev/null; then
    echo "Employee Nginx blocks already exist, skipping..."
else
    echo "Adding employee Nginx server blocks..."
    cat >> "$NGINX_CONF" << 'NGINX_BLOCK'

# -------------------------------------------------------------------
# Employee Portal Frontend: employee.makemystay.ai → port 3005
# -------------------------------------------------------------------
server {
    listen 80;
    listen [::]:80;
    server_name employee.makemystay.ai;

    location = /health {
        access_log off;
        return 200 'healthy\n';
        add_header Content-Type text/plain;
    }

    location / {
        proxy_pass http://127.0.0.1:3005;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }
}

# -------------------------------------------------------------------
# Employee API Backend: employee-api.makemystay.ai → port 8005
# -------------------------------------------------------------------
server {
    listen 80;
    listen [::]:80;
    server_name employee-api.makemystay.ai;

    location = /health {
        access_log off;
        return 200 'healthy\n';
        add_header Content-Type text/plain;
    }

    location / {
        proxy_pass http://127.0.0.1:8005;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }
}
NGINX_BLOCK
    echo "Nginx blocks added."
fi

# Test and reload nginx
nginx -t && systemctl reload nginx
echo "Nginx reloaded OK"
NGINX_SCRIPT

ok "Nginx config updated and reloaded."

# =============================================================================
# STEP 5 – Restart PM2 Processes
# =============================================================================
log "Step 5: Restarting PM2 processes..."

run_remote "
    set -e
    cd $BACKEND_REMOTE

    # Start/restart employee-api using ecosystem.config.js
    if pm2 list | grep -q 'employee-api'; then
        pm2 restart employee-api
        echo 'employee-api restarted'
    else
        pm2 start ecosystem.config.js --only employee-api
        echo 'employee-api started'
    fi

    # Start/restart employee-portal
    if pm2 list | grep -q 'employee-portal'; then
        pm2 restart employee-portal
        echo 'employee-portal restarted'
    else
        # employee-portal cwd is /var/www/employee-portal, use ecosystem.config.js
        pm2 start ecosystem.config.js --only employee-portal
        echo 'employee-portal started'
    fi

    # Save PM2 process list so it survives reboots
    pm2 save
    echo 'PM2 process list saved'
"

ok "PM2 processes restarted."

# =============================================================================
# STEP 6 – Verification
# =============================================================================
log "Step 6: Verifying deployment..."
sleep 5  # Give processes time to start

run_remote "
    echo '=== PM2 Status ==='
    pm2 list

    echo ''
    echo '=== Port Check ==='
    netstat -tlnp 2>/dev/null | grep -E '3005|8005|80|443' || ss -tlnp | grep -E '3005|8005|80|443'

    echo ''
    echo '=== Health Checks ==='
    echo -n 'employee-api health: '
    curl -sf http://localhost:8005/health && echo ' ✅' || echo ' ❌'
    echo -n 'employee-portal health: '
    curl -sf http://localhost:3005/ > /dev/null && echo ' ✅ (200)' || echo ' ❌'
"

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  Deployment Complete!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo "  🌐 Frontend:  https://employee.makemystay.ai"
echo "  🔗 API:       https://employee-api.makemystay.ai"
echo "  📋 API Docs:  https://employee-api.makemystay.ai/docs"
echo ""
echo "  If SSL is not yet configured, run on the server:"
echo "  sudo certbot --nginx -d employee.makemystay.ai -d employee-api.makemystay.ai"
echo ""
