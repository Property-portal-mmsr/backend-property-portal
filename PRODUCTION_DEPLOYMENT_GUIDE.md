# MakeMyStay Realty – Production Deployment Guide (Unified Enterprise Architecture)

This guide documents the **unified enterprise architecture** for deploying **`employee.makemystay.ai`** alongside your existing **`makemystay.ai`**, **`admin.makemystay.ai`**, and **`api.makemystay.ai`** on Ubuntu 24.04 LTS.

---

## 1. Architecture Overview

```
makemystay.ai          ─┐
                        │
admin.makemystay.ai    ─┼──► https://api.makemystay.ai (FastAPI on Port 8000)
                        │     (Single database, single PM2 process: makemystay-api)
employee.makemystay.ai ─┘
  (Next.js on Port 3005)
```

- **One Backend (`api.makemystay.ai` on port 8000)**: All three portals use the same API and MySQL database.
- **New Frontend (`employee.makemystay.ai` on port 3005)**: Hosted in `/var/www/employee-portal`.

---

## 2. Pre-Deployment Backup Protocol (Mandatory Rollback Plan)

Before replacing or updating any production services, take these three quick backups on your Ubuntu server:

```bash
# 1. Backup existing backend directory
cd /var/www
cp -r makemystay-backend makemystay-backend-backup-$(date +%F)

# 2. Backup existing Nginx configuration
sudo cp /etc/nginx/sites-available/makemystay_all /etc/nginx/sites-available/makemystay_all.backup-$(date +%F)

# 3. Backup MySQL Database
mysqldump -u root -p makemystay > /var/www/makemystay_backup_$(date +%F).sql
```

---

## 3. Server Deployment Commands

### A. Update Existing Backend (`/var/www/makemystay-backend`)
1. Pull/deploy the latest backend changes (auth, RBAC, audit logs, employee routes) into your existing backend directory.
2. Seed MakeMyStay Realty employees:
   ```bash
   cd /var/www/makemystay-backend
   source venv/bin/activate
   python seed_mmsr_employees.py
   ```
3. Restart existing PM2 API process:
   ```bash
   pm2 restart makemystay-api
   ```

### B. Deploy Employee Portal Frontend (`/var/www/employee-portal`)
1. Clone or sync frontend repository:
   ```bash
   cd /var/www
   git clone <your-frontend-repo> employee-portal
   cd employee-portal
   ```
2. Configure environment variable (`.env.production`):
   ```env
   NEXT_PUBLIC_API_URL=https://api.makemystay.ai
   ```
3. Install dependencies & build Next.js:
   ```bash
   npm install
   npm run build
   ```
4. Start Next.js on port `3005` using PM2:
   ```bash
   PORT=3005 pm2 start npm --name employee-portal -- start
   pm2 save
   ```

---

## 4. Nginx Configuration (`/etc/nginx/sites-available/makemystay_all`)

Add the following block to your `/etc/nginx/sites-available/makemystay_all` configuration file:

```nginx
server {
    listen 80;
    server_name employee.makemystay.ai;

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
    }
}
```

> **Pro-Tip (Nginx Optimization)**: As you add more subdomains, you can move common proxy headers into a reusable include file (`include /etc/nginx/snippets/proxy-common.conf;`) to keep your server blocks concise.

Then test and reload Nginx:
```bash
sudo nginx -t
sudo systemctl reload nginx
```


---

## 4. Enable Let's Encrypt SSL

Run Certbot for the new employee subdomain:
```bash
sudo certbot --nginx -d employee.makemystay.ai
```

---

## 5. Verification Checklist

- [x] Access `https://employee.makemystay.ai` over HTTPS.
- [x] Login as an admin (`madhava@makemystay.ai` / `123456`) or employee.
- [x] Verify API responses from `https://api.makemystay.ai`.
- [x] Verify `pm2 list` shows `makemystay-api` (port 8000) and `employee-portal` (port 3005) both online.
