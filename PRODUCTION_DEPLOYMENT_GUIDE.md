# MakeMyStay Realty – Production Deployment Guide

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                AWS EC2: 13.201.61.117                    │
│                                                          │
│  employee.makemystay.ai  → Nginx → :3005 (Next.js)      │
│                                    PM2: employee-portal  │
│                                    /var/www/employee-portal │
│                                                          │
│  employee-api.makemystay.ai → Nginx → :8005 (FastAPI)   │
│                                    PM2: employee-api     │
│                                    /var/www/property-portal-backend │
│                                                          │
│  makemystay.ai / admin.makemystay.ai → :3000 / static   │
│  api.makemystay.ai → :8000   (existing makemystay-api)  │
└─────────────────────────────────────────────────────────┘
```

## Quick Deploy (One Command)

```bash
cd ~/property-portal-backend
./deploy.sh
```

This script handles everything: backup → rsync → npm build → PM2 restart → Nginx → health checks.

---

## Manual Deployment Steps

### 1. Deploy Backend

```bash
# From your local machine:
rsync -az --delete \
    --exclude 'venv/' --exclude '__pycache__/' --exclude '.git/' \
    --exclude '.env' --exclude '*.db' \
    -e "ssh -i ~/.ssh/mms_deploy.pem" \
    ~/property-portal-backend/ \
    ubuntu@13.201.61.117:/var/www/property-portal-backend/

# On the server:
ssh -i ~/.ssh/mms_deploy.pem ubuntu@13.201.61.117
cd /var/www/property-portal-backend
source venv/bin/activate
pip install -r requirements.txt
pm2 restart employee-api
```

### 2. Deploy Frontend

```bash
# From your local machine:
rsync -az --delete \
    --exclude 'node_modules/' --exclude '.next/' --exclude '.git/' \
    -e "ssh -i ~/.ssh/mms_deploy.pem" \
    ~/frontend-property-portal/ \
    ubuntu@13.201.61.117:/var/www/employee-portal/

# On the server:
ssh -i ~/.ssh/mms_deploy.pem ubuntu@13.201.61.117
cd /var/www/employee-portal
npm install
npm run build
pm2 restart employee-portal  # or: pm2 start ecosystem.config.js --only employee-portal
pm2 save
```

### 3. Production Environment Variables

**Backend** (`/var/www/property-portal-backend/.env`):
```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=property_portal
DB_USER=appuser
DB_PASSWORD=StrongPassword@123
SECRET_KEY=propertyportal@2026
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=7
```

**Frontend** (`/var/www/employee-portal/.env.production`):
```env
NEXT_PUBLIC_API_URL=https://employee-api.makemystay.ai/api/v1
```

### 4. Nginx Configuration

The employee server blocks are in `/etc/nginx/sites-available/makemystay_all`:

```nginx
# employee.makemystay.ai → port 3005 (Next.js)
server {
    listen 80;
    server_name employee.makemystay.ai;
    location / {
        proxy_pass http://127.0.0.1:3005;
        ...
    }
}

# employee-api.makemystay.ai → port 8005 (FastAPI)
server {
    listen 80;
    server_name employee-api.makemystay.ai;
    location / {
        proxy_pass http://127.0.0.1:8005;
        ...
    }
}
```

After any Nginx changes:
```bash
sudo nginx -t && sudo systemctl reload nginx
```

### 5. SSL (If not yet configured)

```bash
sudo certbot --nginx -d employee.makemystay.ai -d employee-api.makemystay.ai
```

---

## PM2 Process Reference

| PM2 Name         | Port | Description                        |
|------------------|------|------------------------------------|
| employee-api     | 8005 | FastAPI backend (property portal)  |
| employee-portal  | 3005 | Next.js frontend (employee portal) |
| makemystay-api   | 8000 | Existing MakeMyStay FastAPI        |
| makemystay-celery| -    | Existing Celery worker             |

```bash
pm2 list                    # View all processes
pm2 logs employee-api       # View API logs
pm2 logs employee-portal    # View frontend logs
pm2 restart employee-api    # Restart API
pm2 restart employee-portal # Restart frontend
pm2 save                    # Save process list (survives reboots)
```

---

## Verification Checklist

- [ ] `pm2 list` shows `employee-api` (online) and `employee-portal` (online)
- [ ] `curl http://localhost:8005/health` → `{"status":"healthy"}`
- [ ] `curl -o /dev/null -w '%{http_code}' http://localhost:3005/` → `200`
- [ ] `https://employee.makemystay.ai` loads the login page
- [ ] `https://employee-api.makemystay.ai/docs` shows FastAPI Swagger UI

---

## Rollback

```bash
# On the server:
pm2 stop employee-portal employee-api

# Restore Nginx from backup:
sudo cp /etc/nginx/sites-available/makemystay_all.bak /etc/nginx/sites-available/makemystay_all
sudo nginx -t && sudo systemctl reload nginx
```
