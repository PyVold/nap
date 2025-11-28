# License System - Quick Command Reference

This file contains commonly used commands for the license system.

---

## First Time Setup

### 1. Generate Encryption Keys

```bash
# Generate encryption key
python -c "from cryptography.fernet import Fernet; print('LICENSE_ENCRYPTION_KEY=\"' + Fernet.generate_key().decode() + '\"')"

# Generate salt
python -c "import secrets; print('LICENSE_SECRET_SALT=\"' + secrets.token_hex(32) + '\"')"
```

### 2. Add to Environment

```bash
# Add to .env file
echo 'LICENSE_ENCRYPTION_KEY="<your_key>"' >> .env
echo 'LICENSE_SECRET_SALT="<your_salt>"' >> .env
```

### 3. Run Database Migration

```bash
python migrations/add_license_system.py
```

---

## Generate Licenses

### Starter License (1 year)

```bash
python scripts/generate_license.py \
  --customer "Customer Name" \
  --email "customer@example.com" \
  --tier starter \
  --days 365
```

**Includes:**
- 10 devices
- 2 users
- 5 GB storage
- Basic modules

### Professional License (1 year)

```bash
python scripts/generate_license.py \
  --customer "Professional Customer" \
  --email "admin@company.com" \
  --tier professional \
  --days 365
```

**Includes:**
- 100 devices
- 10 users
- 50 GB storage
- Advanced modules (scheduled audits, API access, backups, etc.)

### Enterprise License (2 years)

```bash
python scripts/generate_license.py \
  --customer "Enterprise Corp" \
  --email "it@enterprise.com" \
  --tier enterprise \
  --days 730
```

**Includes:**
- Unlimited devices
- Unlimited users
- Unlimited storage
- All modules

### Custom Quotas

```bash
python scripts/generate_license.py \
  --customer "Custom Client" \
  --email "admin@custom.com" \
  --tier professional \
  --days 365 \
  --devices 200 \
  --users 25 \
  --storage 100
```

---

## Test License Locally

### 1. Start the Application

```bash
# Monolithic mode
python main.py

# OR Microservices mode
docker-compose up -d
```

### 2. Activate License via API

```bash
# Get the license key from license_output/license_*.txt
LICENSE_KEY="<paste_license_key_here>"

# Activate
curl -X POST http://localhost:3000/license/activate \
  -H "Content-Type: application/json" \
  -d "{\"license_key\": \"$LICENSE_KEY\"}"
```

### 3. Check License Status

```bash
curl http://localhost:3000/license/status | jq
```

### 4. Check Module Access

```bash
# Check if scheduled_audits is available
curl http://localhost:3000/license/check-module/scheduled_audits | jq
```

### 5. View All Tiers

```bash
curl http://localhost:3000/license/tiers | jq
```

---

## Common Scenarios

### Generate Trial License (30 days)

```bash
python scripts/generate_license.py \
  --customer "Trial User" \
  --email "trial@example.com" \
  --tier professional \
  --days 30
```

### Generate License with Order ID

```bash
python scripts/generate_license.py \
  --customer "Paid Customer" \
  --email "customer@company.com" \
  --tier enterprise \
  --days 365 \
  --order-id "INV-2025-001"
```

### Generate License with Company Name

```bash
python scripts/generate_license.py \
  --customer "John Smith" \
  --email "john@acme.com" \
  --company "Acme Corporation" \
  --tier professional \
  --days 365
```

---

## Deactivate License

```bash
curl -X POST http://localhost:3000/license/deactivate
```

---

## Check Validation Logs

```bash
curl http://localhost:3000/license/validation-logs | jq
```

---

## Troubleshooting

### Issue: "License validation failed"

**Solution:**
1. Check that LICENSE_ENCRYPTION_KEY is set correctly
2. Verify the key hasn't changed since license generation
3. Make sure the license hasn't expired

```bash
# Check environment variables
echo $LICENSE_ENCRYPTION_KEY
```

### Issue: "Module not available"

**Solution:**
Check the current license tier and required tier:

```bash
curl http://localhost:3000/license/check-module/scheduled_audits | jq
```

### Issue: "Quota exceeded"

**Solution:**
Check current quotas:

```bash
curl http://localhost:3000/license/status | jq .quotas
```

Upgrade to higher tier or reduce usage.

---

## Python API Usage

### In Backend Code

```python
from shared.license_manager import license_manager

# Validate a license
validation = license_manager.validate_license(license_key)
print(validation)

# Check module access
license_data = validation["data"]
has_access = license_manager.has_module(license_data, "scheduled_audits")

# Check quota
within_quota, max_allowed, message = license_manager.check_quota(
    license_data,
    "devices",
    current_device_count
)
```

### With Decorators

```python
from shared.license_manager import require_module, require_quota
from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/schedules")
@require_module("scheduled_audits")
async def get_schedules(request: Request):
    # Only accessible if license has scheduled_audits module
    return {"schedules": [...]}

@router.post("/devices")
@require_quota("devices", buffer=1)
async def add_device(request: Request):
    # Only allowed if within device quota
    return {"device": {...}}
```

---

## Frontend Integration

### Check License Status

```javascript
const response = await fetch('/license/status');
const license = await response.json();

console.log('Tier:', license.tier);
console.log('Days until expiry:', license.days_until_expiry);
console.log('Enabled modules:', license.enabled_modules);
```

### Activate License

```javascript
const response = await fetch('/license/activate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ license_key: userInputKey })
});

if (response.ok) {
  console.log('License activated!');
}
```

### Check Module Access

```javascript
const response = await fetch('/license/check-module/scheduled_audits');
const result = await response.json();

if (result.has_access) {
  // Show feature
} else {
  // Show upgrade prompt
}
```

---

## Production Checklist

- [ ] Generate production encryption key and salt
- [ ] Store keys securely (not in code)
- [ ] Set LICENSE_ENCRYPTION_KEY in environment
- [ ] Set LICENSE_SECRET_SALT in environment
- [ ] Run database migration
- [ ] Generate test license to verify
- [ ] Activate test license in UI
- [ ] Test feature gating
- [ ] Test quota enforcement
- [ ] Document license generation process for sales team
- [ ] Create process for sending licenses to customers

---

## Support

**Generated license files location:**
- `license_output/license_*.txt` - Send to customer
- `license_output/license_*.json` - Keep for records

**Documentation:**
- `LICENSE_SYSTEM_README.md` - Complete overview
- `OFFLINE_LICENSE_IMPLEMENTATION.md` - Implementation guide
- `FRONTEND_LICENSE_INTEGRATION_GUIDE.md` - Frontend guide

**For help:**
- Check logs for validation errors
- Verify encryption keys match
- Ensure license hasn't expired
- Test with a new trial license
