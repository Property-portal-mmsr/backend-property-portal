#!/bin/bash
set -e

# ===== CONFIG & OVERRIDES =====
DOMAIN="employee-api.makemystay.ai"
EC2_USER="ubuntu"
PEM_KEY="${DEPLOY_PEM:-/Users/maheswaranm/.ssh/mms_deploy.pem}"
WEB_BASE_DIR="/var/www/property-portal-backend"
PM2_APP_NAME="employee-api"

# Common SSH options for reliability and automated environments
SSH_OPTS="-i $PEM_KEY -o StrictHostKeyChecking=no -o ConnectTimeout=15 -o ServerAliveInterval=60"

# Target Servers - Deploying to BOTH instances just in case ALB routes to either
ALL_SERVERS=("13.126.149.224" "13.201.61.117")
FAILED_SERVERS=()

echo "🚀 Starting Deployment for Backend ($DOMAIN)..."

for SERVER in "${ALL_SERVERS[@]}"; do
    echo "--------------------------------------------------------"
    echo "🚀 Deploying to $SERVER..."
    
    # ===== PREFLIGHT CHECK =====
    echo "🔍 Checking server reachability..."
    if ! ssh $SSH_OPTS -o BatchMode=yes $EC2_USER@$SERVER "exit" 2>/dev/null; then
      echo "❌ Error: Cannot reach server @ $SERVER via SSH."
      FAILED_SERVERS+=("$SERVER")
      continue
    fi

    echo "🔐 Ensuring permissions on $WEB_BASE_DIR..."
    ssh $SSH_OPTS $EC2_USER@$SERVER "sudo mkdir -p $WEB_BASE_DIR && sudo chown -R $EC2_USER:$EC2_USER $WEB_BASE_DIR"

    echo "📦 Syncing source files to $WEB_BASE_DIR..."
    # Rsync everything except venv, pycache, and git to keep upload fast
    if ! rsync -avz --delete \
      --exclude 'venv' \
      --exclude '__pycache__' \
      --exclude '.git' \
      --exclude '*.pyc' \
      -e "ssh $SSH_OPTS" ./ "$EC2_USER@$SERVER:$WEB_BASE_DIR/"; then
      echo "❌ Error: rsync failed for $SERVER."
      FAILED_SERVERS+=("$SERVER")
      continue
    fi

    echo "⚙️ Setting up virtual environment, installing dependencies, and restarting PM2 on $SERVER..."
    if ! ssh $SSH_OPTS $EC2_USER@$SERVER "
        cd $WEB_BASE_DIR
        
        # Create virtual environment if it doesn't exist
        if [ ! -d \"venv\" ]; then
            echo \"🐍 Creating Python virtual environment...\"
            python3 -m venv venv
        fi
        
        echo \"📦 Installing dependencies...\"
        ./venv/bin/pip install -r requirements.txt
        
        echo \"🔄 Restarting PM2 process...\"
        pm2 restart $PM2_APP_NAME || pm2 start ./venv/bin/python --name \"$PM2_APP_NAME\" -- -m uvicorn app.main:app --host 0.0.0.0 --port 8005 --workers 2
        pm2 save
    "; then
      echo "❌ Error: Dependency installation or PM2 restart failed on $SERVER."
      FAILED_SERVERS+=("$SERVER")
      continue
    fi
    echo "✅ Successfully deployed to $SERVER"
done

echo "--------------------------------------------------------"
if [ ${#FAILED_SERVERS[@]} -gt 0 ]; then
  echo "❌ Deployment failed on: ${FAILED_SERVERS[*]}"
  exit 1
fi

echo "✅ All-Server Backend Deployment complete!"
