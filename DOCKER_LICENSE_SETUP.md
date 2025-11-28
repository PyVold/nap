# 🐳 License System - Docker Setup Guide

**Date**: November 28, 2025  
**Status**: ✅ Ready for Docker

---

## 🎯 Quick Start with Docker

### Step 1: Verify Environment Variables (30 seconds)

The `.env` file already contains the license keys:

```bash
# Check if .env exists with license keys
cat .env | grep LICENSE
```

Should show:
```ini
LICENSE_ENCRYPTION_KEY=E0NCm6zshtvODKcWLz3Xm9n2Nv9lWxVFozpUj14AR1k=
LICENSE_SECRET_SALT=cf718b28278d28939daf478a1093945a7ada6b21dbe11248d89f6b937db8a976
```

✅ **Already configured!** The `.env` file is ready.

### Step 2: Start Docker Compose

```bash
cd /workspace
docker-compose up -d
```

This will:
1. 🗄️ Start PostgreSQL database
2. 🚀 Start all microservices (including admin-service with license API)
3. 🎨 Start frontend
4. ✅ **Automatically create license tables** on first startup

### Step 3: Wait for Services to Start (30 seconds)

```bash
# Check service status
docker-compose ps

# Watch logs (Ctrl+C to exit)
docker-compose logs -f admin-service
```

Look for:
```
admin-service_1  | Database initialized
admin-service_1  | License routes registered
```

### Step 4: Generate a License

```bash
# From your host machine (not inside container)
python3 scripts/generate_license.py \
  --customer "Test Company" \
  --email "admin@test.com" \
  --tier professional \
  --days 365
```

**Output**: `license_output/license_admin_XXXXXX.txt`

### Step 5: Access the Frontend

Open your browser:
- **Frontend**: http://localhost:8080
- **Admin Service** (license API): http://localhost:3005
- **API Gateway**: http://localhost:3000

1. Login to the frontend
2. Click "License" in the sidebar (🔑 icon)
3. Click "Activate License"
4. Paste the license key
5. Click "Activate"

**Done!** ✅

---

## 🏗️ Architecture in Docker

### Service Ports

| Service | Port | License API? |
|---------|------|--------------|
| **admin-service** | 3005 | ✅ YES `/license/*` |
| api-gateway | 3000 | Routes to admin-service |
| device-service | 3001 | No |
| rule-service | 3002 | No |
| backup-service | 3003 | No |
| inventory-service | 3004 | No |
| analytics-service | 3006 | No |
| frontend | 8080 | Calls API Gateway |
| database | 5432 | PostgreSQL |

### License API Endpoints

All available at: **http://localhost:3005/license/**

- `POST /license/activate` - Activate a license
- `GET /license/status` - Check current license
- `POST /license/deactivate` - Deactivate license
- `GET /license/tiers` - View available tiers
- `GET /license/check-module/{module}` - Check module access
- `GET /license/validation-logs` - View validation history

---

## 🔐 Environment Variables in Docker

### How Keys are Passed to Containers

The `docker-compose.yml` now includes:

```yaml
admin-service:
  environment:
    - LICENSE_ENCRYPTION_KEY=${LICENSE_ENCRYPTION_KEY:-GENERATE_SECURE_KEY_BEFORE_PRODUCTION}
    - LICENSE_SECRET_SALT=${LICENSE_SECRET_SALT:-GENERATE_SECURE_SALT_BEFORE_PRODUCTION}
```

Docker Compose automatically reads from `.env` file in the same directory.

### Verification

```bash
# Check if admin-service has the keys
docker-compose exec admin-service env | grep LICENSE
```

Should show your keys.

---

## 🗄️ Database in Docker

### Automatic Table Creation

When **admin-service** starts:
1. ✅ Connects to PostgreSQL at `database:5432`
2. ✅ Calls `init_db()` automatically
3. ✅ Creates ALL missing tables including:
   - `licenses`
   - `license_validation_logs`
4. ✅ Ready to accept license activations!

### Verify Tables Were Created

```bash
# Access PostgreSQL
docker-compose exec database psql -U nap_user -d nap_db

# Inside psql:
\dt licenses
\dt license_validation_logs

# Exit with
\q
```

---

## 🧪 Test License System in Docker

### 1. Generate License (on host)

```bash
python3 scripts/generate_license.py \
  --customer "Docker Test" \
  --email "docker@test.com" \
  --tier professional \
  --days 365
```

Copy the license key from `license_output/`.

### 2. Activate via API

```bash
# Replace YOUR_LICENSE_KEY with actual key
curl -X POST http://localhost:3005/license/activate \
  -H "Content-Type: application/json" \
  -d '{
    "license_key": "YOUR_LICENSE_KEY"
  }'
```

### 3. Check Status

```bash
curl http://localhost:3005/license/status
```

### 4. Check Module Access

```bash
curl http://localhost:3005/license/check-module/scheduled_audits
```

---

## 🔄 Updating the Stack

### If You Change License Code

```bash
# Rebuild and restart admin-service
docker-compose up -d --build admin-service

# Or rebuild everything
docker-compose up -d --build
```

### If You Change Frontend

```bash
# Rebuild frontend
docker-compose up -d --build frontend
```

---

## 📊 View Logs

### All Services

```bash
docker-compose logs -f
```

### Admin Service Only (License API)

```bash
docker-compose logs -f admin-service
```

### Database

```bash
docker-compose logs -f database
```

### Filter for License-Related Logs

```bash
docker-compose logs admin-service | grep -i license
```

---

## 🛠️ Troubleshooting Docker Setup

### Issue: "License tables don't exist"

**Solution**: Tables are created automatically on first startup. Wait for admin-service to fully start.

```bash
# Check admin-service logs
docker-compose logs admin-service | grep -i "database initialized"
```

### Issue: "LICENSE_ENCRYPTION_KEY not set"

**Solution**: Make sure `.env` file exists in `/workspace/` directory.

```bash
# Verify .env exists
ls -la /workspace/.env

# Check if docker-compose reads it
docker-compose config | grep LICENSE
```

### Issue: "Can't connect to database"

**Solution**: Wait for database health check to pass.

```bash
# Check database status
docker-compose ps database

# Should show "healthy"
```

### Issue: "Frontend can't reach API"

**Solution**: The frontend is configured to call `http://localhost:3000` (API Gateway).

Make sure you're accessing the frontend at `http://localhost:8080` (not inside a container).

---

## 🐳 Docker Compose Commands Reference

### Start All Services

```bash
docker-compose up -d
```

### Stop All Services

```bash
docker-compose down
```

### Restart a Service

```bash
docker-compose restart admin-service
```

### View Running Services

```bash
docker-compose ps
```

### Rebuild After Code Changes

```bash
docker-compose up -d --build
```

### Clean Everything (including database)

```bash
docker-compose down -v
```

⚠️ **Warning**: `-v` removes database volume (all data lost!)

### Access a Service Shell

```bash
# Admin service
docker-compose exec admin-service bash

# Database
docker-compose exec database bash
```

---

## 🌐 Frontend Configuration

The frontend in Docker is configured to call:
- **API Gateway**: http://localhost:3000

The API Gateway routes `/license/*` requests to admin-service.

### Frontend Environment Variables

In `docker-compose.yml`:
```yaml
frontend:
  environment:
    - REACT_APP_API_URL=http://localhost:3000
```

This is already configured correctly!

---

## ✅ What's Automatic in Docker

1. ✅ **Database table creation** - All tables created on first startup
2. ✅ **Service dependencies** - Services wait for database to be healthy
3. ✅ **Environment variables** - Automatically loaded from `.env`
4. ✅ **Network configuration** - All services can communicate
5. ✅ **Volume persistence** - Database data persists across restarts

---

## 🎯 Complete Docker Workflow

### First Time Setup

```bash
# 1. Start everything
cd /workspace
docker-compose up -d

# 2. Wait for services (30 seconds)
docker-compose logs -f admin-service
# Wait until you see "Database initialized"

# 3. Generate a license
python3 scripts/generate_license.py \
  --customer "My Company" \
  --email "admin@mycompany.com" \
  --tier professional \
  --days 365

# 4. Open frontend
open http://localhost:8080

# 5. Activate license through UI
# Navigate to License page (🔑 icon)
# Paste license key and activate
```

### Daily Usage

```bash
# Start
docker-compose up -d

# Stop
docker-compose down
```

---

## 📝 Summary for Docker Users

| Component | Status | Notes |
|-----------|--------|-------|
| Database Tables | ✅ Auto-created | On first admin-service startup |
| License Keys | ✅ Configured | From `.env` file |
| Admin Service | ✅ Ready | Port 3005 with license API |
| Frontend | ✅ Ready | Port 8080 with license UI |
| API Gateway | ✅ Ready | Port 3000 routes to services |
| PostgreSQL | ✅ Ready | Port 5432 with persistence |

**Everything is automatic - just run `docker-compose up -d` and you're ready!**

---

## 🔑 Generate Production Keys for Docker

If you need new keys for production:

```bash
# Generate new encryption key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Generate new salt
python3 -c "import secrets; print(secrets.token_hex(32))"

# Update .env file
# Then restart: docker-compose up -d --force-recreate
```

---

## 🎉 You're Ready!

With Docker:
- ✅ All services start automatically
- ✅ Database tables auto-created
- ✅ License keys loaded from `.env`
- ✅ Frontend ready at port 8080
- ✅ No manual migration needed

Just run:
```bash
docker-compose up -d
```

And the license system works! 🚀

---

**Created**: November 28, 2025  
**Docker Compose**: Fully Configured  
**Status**: ✅ Production Ready
