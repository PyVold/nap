# Offline / Air-Gapped Deployment Guide

This guide explains how to deploy the Network Audit Platform in offline/air-gapped environments where Docker containers cannot access the internet during build or runtime.

## 📋 Overview

The offline deployment uses pre-built base images containing all dependencies:
- **nap-python-base**: Python 3.11 + all Python packages from all services
- **nap-frontend-base**: Node 18 + all npm packages
- **postgres:15**: Database (pulled from Docker Hub)
- **nginx:alpine**: Web server for frontend (pulled from Docker Hub)

## 🔄 Deployment Workflow

```
┌─────────────────────────────────┐
│  System with Internet Access    │
│  (Build & Export)                │
└────────┬────────────────────────┘
         │
         │ 1. Build base images
         │ 2. Export as tar files
         │ 3. Copy to offline system
         │
┌────────▼────────────────────────┐
│  Offline System                  │
│  (Load & Deploy)                 │
└──────────────────────────────────┘
```

---

## 🖥️ Part 1: Preparation (Internet-Connected System)

### Step 1: Build Base Images

Run this on a system with internet access:

```bash
cd /home/user/nap

# Make scripts executable
chmod +x docker/*.sh

# Build base images with all dependencies
./docker/build-base-images.sh
```

**This will:**
- Build `nap-python-base:latest` with all Python dependencies
- Build `nap-frontend-base:latest` with all npm packages
- Pull `postgres:15` and `nginx:alpine`

**Expected output:**
```
✅ Python base image built successfully
✅ Frontend base image built successfully
✅ All base images ready
```

### Step 2: Export Base Images

```bash
# Export images as tar files
./docker/export-base-images.sh
```

**This creates:**
- `docker/base-images-export/nap-python-base.tar` (~1.5GB)
- `docker/base-images-export/nap-frontend-base.tar` (~500MB)
- `docker/base-images-export/nginx-alpine.tar` (~50MB)
- `docker/base-images-export/postgres-15.tar` (~150MB)

### Step 3: Package for Transfer

```bash
# Compress for faster transfer
cd docker/base-images-export
tar czf nap-base-images.tar.gz *.tar

# Or create a single archive of everything
cd ../../
tar czf nap-offline-deploy.tar.gz \
    docker/base-images-export/*.tar \
    services/ \
    frontend/ \
    shared/ \
    docker-compose.offline.yml \
    .env.example
```

### Step 4: Transfer to Offline System

Copy the tar files or archive to your offline system using:
- USB drive
- Secure file transfer
- Physical media
- Any approved transfer method

---

## 🔒 Part 2: Deployment (Offline System)

### Step 1: Extract Files

```bash
# If you created the full archive:
tar xzf nap-offline-deploy.tar.gz
cd nap

# Or if you only transferred base image tars:
mkdir -p docker/base-images-export
cp /path/to/*.tar docker/base-images-export/
```

### Step 2: Load Base Images

```bash
# Load base images into Docker
./docker/load-base-images.sh
```

**Expected output:**
```
✅ Loaded nap-python-base:latest
✅ Loaded nap-frontend-base:latest
✅ Loaded nginx:alpine
✅ Loaded postgres:15
```

**Verify:**
```bash
docker images | grep -E "nap-python-base|nap-frontend-base|nginx|postgres"
```

### Step 3: Generate Offline Dockerfiles

```bash
# Generate Dockerfile.offline for all services
./docker/generate-offline-dockerfiles.sh
```

### Step 4: Configure Environment

```bash
# Copy and edit environment variables
cp .env.example .env
nano .env  # or vim, vi, etc.
```

**Required settings:**
```bash
DATABASE_URL=postgresql://nap_user:nap_password@database:5432/nap_db
JWT_SECRET=<generate-with-python-secrets>
ENCRYPTION_KEY=<generate-with-python-secrets>
```

### Step 5: Build Application Images

```bash
# Build all services (NO internet access needed!)
docker compose -f docker-compose.offline.yml build

# This will be FAST because dependencies are already installed
# It only copies code and creates final images
```

### Step 6: Start Services

```bash
# Start all services
docker compose -f docker-compose.offline.yml up -d

# Check status
docker compose -f docker-compose.offline.yml ps

# View logs
docker compose -f docker-compose.offline.yml logs -f
```

### Step 7: Verify Deployment

```bash
# Check all services are running
docker compose -f docker-compose.offline.yml ps

# Test API Gateway
curl http://localhost:3000/health

# Access frontend
# Open browser: http://<server-ip>:8080

# Default login: admin / admin
```

---

## 🔄 Updates and Maintenance

### Updating Application Code

When you have code updates:

1. **On internet system:**
   ```bash
   # No need to rebuild base images if dependencies haven't changed
   # Just copy the updated code files
   tar czf nap-code-update.tar.gz services/ frontend/ shared/
   ```

2. **On offline system:**
   ```bash
   # Extract updated code
   tar xzf nap-code-update.tar.gz

   # Rebuild application images (fast, only code changes)
   docker compose -f docker-compose.offline.yml build

   # Restart services
   docker compose -f docker-compose.offline.yml up -d
   ```

### Updating Dependencies

If you add new Python packages or npm modules:

1. **On internet system:**
   ```bash
   # Rebuild base images
   ./docker/build-base-images.sh

   # Export new base images
   ./docker/export-base-images.sh

   # Transfer to offline system
   ```

2. **On offline system:**
   ```bash
   # Load updated base images
   ./docker/load-base-images.sh

   # Rebuild application images
   docker compose -f docker-compose.offline.yml build

   # Restart services
   docker compose -f docker-compose.offline.yml up -d
   ```

---

## 📊 Image Sizes

| Image | Approximate Size |
|-------|------------------|
| nap-python-base | ~1.5 GB |
| nap-frontend-base | ~500 MB |
| postgres:15 | ~150 MB |
| nginx:alpine | ~50 MB |
| **Total** | **~2.2 GB** |

Application images (after build): ~100-200 MB each

---

## 🛠️ Troubleshooting

### "Base image not found"

```bash
# Verify base images are loaded
docker images | grep nap

# If missing, run load script again
./docker/load-base-images.sh
```

### "Cannot connect to database"

```bash
# Check database is healthy
docker compose -f docker-compose.offline.yml ps database

# Check logs
docker compose -f docker-compose.offline.yml logs database

# Wait for database to be ready
docker compose -f docker-compose.offline.yml up -d database
sleep 10
```

### Services fail to start

```bash
# Check service logs
docker compose -f docker-compose.offline.yml logs <service-name>

# Check all services
docker compose -f docker-compose.offline.yml logs

# Restart specific service
docker compose -f docker-compose.offline.yml restart <service-name>
```

### Build fails with "No such file or directory"

Ensure you're in the project root directory:
```bash
cd /home/user/nap  # or wherever you extracted the files
docker compose -f docker-compose.offline.yml build
```

---

## 🔐 Security Considerations

1. **Change default credentials** immediately after first deployment
2. **Generate secure secrets** for JWT_SECRET and ENCRYPTION_KEY
3. **Review firewall rules** on the offline system
4. **Regular backups** of database volume
5. **Access control** for Docker host and services

---

## 📝 Quick Reference

### Common Commands

```bash
# Start services
docker compose -f docker-compose.offline.yml up -d

# Stop services
docker compose -f docker-compose.offline.yml down

# View logs
docker compose -f docker-compose.offline.yml logs -f [service-name]

# Restart service
docker compose -f docker-compose.offline.yml restart [service-name]

# Rebuild after code changes
docker compose -f docker-compose.offline.yml build [service-name]
docker compose -f docker-compose.offline.yml up -d [service-name]

# Check status
docker compose -f docker-compose.offline.yml ps

# Clean up (CAUTION: Removes data!)
docker compose -f docker-compose.offline.yml down -v
```

---

## ✅ Checklist

**Before Transfer:**
- [ ] Base images built successfully
- [ ] Base images exported as tar files
- [ ] All code files packaged
- [ ] .env.example included
- [ ] Documentation included

**After Transfer:**
- [ ] Files extracted on offline system
- [ ] Base images loaded into Docker
- [ ] .env configured with secure secrets
- [ ] Application images built
- [ ] Services started successfully
- [ ] Frontend accessible
- [ ] Admin login working
- [ ] Default passwords changed

---

## 🆘 Support

For issues or questions:
1. Check logs: `docker compose -f docker-compose.offline.yml logs`
2. Verify base images: `docker images | grep nap`
3. Check service health: `docker compose -f docker-compose.offline.yml ps`
4. Review this guide's troubleshooting section

---

**Last Updated:** 2025-12-02
