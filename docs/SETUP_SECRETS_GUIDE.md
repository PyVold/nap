# NAP - Secrets, Passwords & License Setup Guide

This guide walks you through generating all secrets, passwords, and license keys
required to deploy the Network Audit Platform in production.

---

## Table of Contents

1. [Quick Start (All-in-One Script)](#quick-start)
2. [Generating Individual Secrets](#generating-individual-secrets)
3. [Filling in .env.prod](#filling-in-envprod)
4. [Generating License Keys](#generating-license-keys)
5. [Activating a License](#activating-a-license)
6. [Local LLM Setup (Ollama)](#local-llm-setup)
7. [Verifying Your Setup](#verifying-your-setup)
8. [Rotating Secrets](#rotating-secrets)

---

## Quick Start

Run this script to generate all required secrets at once:

```bash
# Copy the example env file
cp .env.prod.example .env.prod

# Generate all secrets and print them
echo "=== NAP Production Secrets ==="
echo ""
echo "JWT_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
echo "ENCRYPTION_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
echo "LICENSE_ENCRYPTION_KEY=$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
echo "LICENSE_SECRET_SALT=$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
echo "POSTGRES_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
echo "REDIS_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
echo "GRAFANA_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_urlsafe(16))')"
```

Copy each generated value into the corresponding field in `.env.prod`.

> **IMPORTANT**: Save these values somewhere secure (password manager, vault).
> If you lose them, encrypted data (device credentials, licenses) cannot be recovered.

---

## Generating Individual Secrets

### JWT_SECRET

Used for signing authentication tokens (JWT). All users must re-login if this changes.

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Example output: `Kx7mN2qP4rS8vW1yA3bD6eF9gH0jL5nO`

### ENCRYPTION_KEY

Used for encrypting device credentials (SSH/NETCONF passwords) stored in the database.

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

> **WARNING**: If you change this key, all stored device credentials become unreadable.
> You will need to re-enter credentials for all devices.

### LICENSE_ENCRYPTION_KEY

Used for encrypting and decrypting license keys. Must be a valid **Fernet key** (base64-encoded 32-byte key).

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Example output: `ZmDfcTF7_60GrrY3LbXKh5EuLXK9v4Bz7vWG80f7KJI=`

> **NOTE**: This is NOT the same format as the other keys. It must be a Fernet key
> (always ends with `=`). Using a regular `secrets.token_urlsafe()` value will cause errors.

### LICENSE_SECRET_SALT

Used for HMAC signing of license payloads to prevent tampering.

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Example output: `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2`

### POSTGRES_PASSWORD

Password for the PostgreSQL database user.

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```

> After generating, also update the `DATABASE_URL` to include the same password:
> ```
> DATABASE_URL=postgresql://nap_user:<YOUR_PASSWORD>@database:5432/nap_db
> ```

### REDIS_PASSWORD

Password for the Redis cache/session store.

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```

> Also update `REDIS_URL` to include the same password:
> ```
> REDIS_URL=redis://:<YOUR_PASSWORD>@redis:6379
> ```

### GRAFANA_PASSWORD

Admin password for the Grafana monitoring dashboard.

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(16))"
```

---

## Filling in .env.prod

After generating all secrets, your `.env.prod` should look like this (with your actual values):

```bash
# Security
JWT_SECRET=Kx7mN2qP4rS8vW1yA3bD6eF9gH0jL5nO
ENCRYPTION_KEY=Rm4tY7uI0pA2sD5fG8hJ1kL3zX6cV9bN
LICENSE_ENCRYPTION_KEY=ZmDfcTF7_60GrrY3LbXKh5EuLXK9v4Bz7vWG80f7KJI=
LICENSE_SECRET_SALT=a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2

# Database
POSTGRES_DB=nap_db
POSTGRES_USER=nap_user
POSTGRES_PASSWORD=YourSecureDbPassword123
DATABASE_URL=postgresql://nap_user:YourSecureDbPassword123@database:5432/nap_db

# Redis
REDIS_PASSWORD=YourSecureRedisPassword
REDIS_URL=redis://:YourSecureRedisPassword@redis:6379

# Grafana
GRAFANA_PASSWORD=YourGrafanaPassword
```

> **Never commit `.env.prod` to git.** It is already in `.gitignore`.

---

## Generating License Keys

NAP uses encrypted license keys to control feature tiers (Starter, Professional, Enterprise).

### Prerequisites

You need the same `LICENSE_ENCRYPTION_KEY` and `LICENSE_SECRET_SALT` values that are
configured in your `.env.prod`. The license generator signs and encrypts the key using
these values, and the running NAP instance decrypts using the same values.

### Using the generate_license.py Script

```bash
# Set the keys (use the same values as in .env.prod)
export LICENSE_ENCRYPTION_KEY="ZmDfcTF7_60GrrY3LbXKh5EuLXK9v4Bz7vWG80f7KJI="
export LICENSE_SECRET_SALT="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2"

# Generate an Enterprise license valid for 1 year
python3 scripts/generate_license.py \
    --customer "Your Name" \
    --email "admin@yourcompany.com" \
    --company "Your Company" \
    --tier enterprise \
    --days 365
```

### License Tiers

| Tier | Devices | Users | Storage | Features |
|------|---------|-------|---------|----------|
| **Starter** | 10 | 2 | 5 GB | Basic device management, manual audits, health checks |
| **Professional** | 100 | 10 | 50 GB | + Scheduled audits, rule templates, backups, drift detection, discovery, API access |
| **Enterprise** | Unlimited | Unlimited | Unlimited | All features including AI, workflows, integrations, SSO |

### Custom Quotas

Override tier defaults with custom limits:

```bash
python3 scripts/generate_license.py \
    --customer "Big Client" \
    --email "admin@bigclient.com" \
    --tier professional \
    --days 365 \
    --max-devices 500 \
    --max-users 50
```

### Save License to File

```bash
python3 scripts/generate_license.py \
    --customer "Client" \
    --email "admin@client.com" \
    --tier enterprise \
    --days 365 \
    --output license_key.txt
```

---

## Activating a License

### Option 1: Web UI

1. Log in to NAP as an admin user
2. Navigate to **Admin > License Management**
3. Paste the license key string
4. Click **Activate**

### Option 2: API

```bash
# First, get a JWT token by logging in
TOKEN=$(curl -s -X POST http://localhost:3000/login \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "admin"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Activate the license
curl -X POST http://localhost:3000/license/activate \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"license_key": "<paste_your_license_key_here>"}'
```

### Verify License Status

```bash
curl -s http://localhost:3000/license/status \
    -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

## Local LLM Setup

NAP defaults to using a local LLM (Ollama) for air-gapped/offline deployments.

### Starting Ollama

```bash
# Start all services including Ollama
docker compose -f docker-compose.prod.yml --env-file .env.prod --profile local-llm up -d

# Pull a model (first time only - choose based on your hardware)
# Small (3B params, ~2GB RAM) - fast but less capable:
docker exec nap-ollama-1 ollama pull llama3.2:3b

# Medium (8B params, ~5GB RAM) - good balance:
docker exec nap-ollama-1 ollama pull llama3

# Large (70B params, ~40GB RAM) - most capable:
docker exec nap-ollama-1 ollama pull llama3:70b
```

### Configuration in .env.prod

```bash
AI_PROVIDER=local
LOCAL_LLM_URL=http://ollama:11434
LOCAL_MODEL=llama3
LOCAL_LLM_API_FORMAT=ollama
OLLAMA_MEMORY_LIMIT=8G
```

### Using Other Local LLM Servers

NAP also supports any OpenAI-compatible API server:

| Server | API Format | Example URL |
|--------|-----------|-------------|
| **Ollama** (default) | `ollama` | `http://ollama:11434` |
| **vLLM** | `openai` | `http://vllm-server:8000` |
| **LocalAI** | `openai` | `http://localai:8080` |
| **LM Studio** | `openai` | `http://host.docker.internal:1234` |
| **text-generation-webui** | `openai` | `http://tgw:5000` |

To use an OpenAI-compatible server, set:

```bash
LOCAL_LLM_API_FORMAT=openai
LOCAL_LLM_URL=http://your-server:port
LOCAL_MODEL=your-model-name
```

### Verify AI Service

```bash
# Check AI service health and local LLM connection
curl -s http://localhost:3000/ai/status | python3 -m json.tool
```

---

## Verifying Your Setup

After filling in `.env.prod` and starting the platform:

```bash
# 1. Start the platform
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# 2. Check all services are healthy
curl -s http://localhost:3000/health | python3 -m json.tool

# 3. Test login
curl -s -X POST http://localhost:3000/login \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "admin"}'

# 4. Check license status (after activation)
curl -s http://localhost:3000/license/status \
    -H "Authorization: Bearer <token>" | python3 -m json.tool

# 5. Check AI service
curl -s http://localhost:3000/ai/status | python3 -m json.tool
```

---

## Rotating Secrets

### JWT_SECRET

1. Update `JWT_SECRET` in `.env.prod`
2. Restart all services: `docker compose -f docker-compose.prod.yml --env-file .env.prod restart`
3. All users will need to log in again (existing JWT tokens become invalid)

### ENCRYPTION_KEY

> **Caution**: Changing this key makes existing encrypted device credentials unreadable.

1. Export existing device credentials first (backup)
2. Update `ENCRYPTION_KEY` in `.env.prod`
3. Restart services
4. Re-enter device credentials for all managed devices

### LICENSE_ENCRYPTION_KEY / LICENSE_SECRET_SALT

> **Caution**: Changing these keys invalidates all existing license keys.

1. Update the keys in `.env.prod`
2. Re-generate license keys using the new keys
3. Restart services
4. Re-activate the new license key

### POSTGRES_PASSWORD

1. Update `POSTGRES_PASSWORD` and `DATABASE_URL` in `.env.prod`
2. Connect to PostgreSQL and change the password:
   ```bash
   docker exec -it nap-database-1 psql -U nap_user -d nap_db -c "ALTER USER nap_user PASSWORD 'new_password';"
   ```
3. Restart all services

---

## Security Checklist

- [ ] All `GENERATE_*` placeholders replaced with real values in `.env.prod`
- [ ] `.env.prod` is NOT committed to git (check with `git status`)
- [ ] `LICENSE_ENCRYPTION_KEY` is a valid Fernet key (ends with `=`)
- [ ] `DATABASE_URL` password matches `POSTGRES_PASSWORD`
- [ ] `REDIS_URL` password matches `REDIS_PASSWORD`
- [ ] `CORS_ALLOWED_ORIGINS` is set to your actual domain (not `*`)
- [ ] Default admin password changed after first login
- [ ] License key generated and activated
- [ ] Secrets stored in a password manager or vault
- [ ] `DEBUG_MODE=false` in production
