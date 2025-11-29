# Encryption Key Error Fix

## Problem

Services are failing to start with this error:
```
RuntimeError: ENCRYPTION_KEY is set to an insecure default value: GENERATE_SECURE_KEY_BEFORE_PRODUCTION
```

## Root Cause

Docker Compose is not reading the `.env` file properly, so services are using the insecure default values instead of the secure keys in your `.env` file.

## Quick Fix

### Option 1: Export Environment Variables (Fastest)

```bash
# Load environment variables from .env file
export $(cat .env | grep -v '^#' | xargs)

# Restart services
docker compose up -d
```

### Option 2: Use --env-file Flag

```bash
docker compose --env-file .env up -d
```

### Option 3: Rebuild with Environment

```bash
# Stop services
docker compose down

# Start with explicit env file
docker compose --env-file .env up -d --build
```

## Verification

Check that environment variables are loaded:

```bash
# Check device-service environment
docker compose exec device-service env | grep ENCRYPTION_KEY

# Should show your secure key, NOT: GENERATE_SECURE_KEY_BEFORE_PRODUCTION
```

## Your Secure Keys

Your `.env` file already contains secure keys:
```bash
JWT_SECRET=YHO6sd3_RxoOT-dWkERwHVgmbDsR1qLNge8pCQ3dvq4
ENCRYPTION_KEY=ktlZSCYAvxcAEx_bF6grV50Z8EqJiPzh2khQwqKURrY
LICENSE_ENCRYPTION_KEY=dRw4GhzUpkAVdD_jRIIskGNwULJR3-idsCj3GKfXCQU=
LICENSE_SECRET_SALT=ee847197c3cffb6338162b0ea8b43630abbe77978c3ef36d004572464e95f040
```

These are **already secure** - you don't need to regenerate them. You just need to ensure Docker Compose reads them correctly.

## Long-Term Fix

Update `docker-compose.yml` to explicitly use the .env file:

```yaml
# At the top of docker-compose.yml
version: '3.8'

# Add env_file to each service
services:
  device-service:
    env_file:
      - .env
    environment:
      # ... other settings
```

## Alternative: Remove Defaults

You can also remove the default values from docker-compose.yml:

```yaml
# Instead of:
- ENCRYPTION_KEY=${ENCRYPTION_KEY:-GENERATE_SECURE_KEY_BEFORE_PRODUCTION}

# Use:
- ENCRYPTION_KEY=${ENCRYPTION_KEY}
```

This will make it fail faster if the variable isn't set, which is safer.
