# License System - Quick Implementation Guide

**Target**: Implement working license system in 1-2 weeks
**Priority**: CRITICAL for monetization

---

## Table of Contents
1. [Quick Start (Day 1)](#day-1-database-schema)
2. [Core License Logic (Day 2-3)](#day-2-3-license-manager)
3. [API Integration (Day 4-5)](#day-4-5-api-integration)
4. [Frontend UI (Day 6-7)](#day-6-7-frontend)
5. [Testing & Launch (Day 8-10)](#day-8-10-testing)

---

## Day 1: Database Schema

### Step 1: Add License Tables to db_models.py

```python
# shared/db_models.py or services/admin-service/app/db_models.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Text, ForeignKey, Numeric, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from shared.database import Base

class TenantDB(Base):
    """Multi-tenant support"""
    __tablename__ = "tenants"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(100), unique=True, index=True)
    domain = Column(String(200), unique=True, nullable=True)
    
    # Status
    status = Column(String(50), default="active")  # active, suspended, cancelled
    trial_ends_at = Column(DateTime, nullable=True)
    
    # Contact
    admin_email = Column(String(200))
    billing_email = Column(String(200))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    license = relationship("LicenseKeyDB", back_populates="tenant", uselist=False)
    devices = relationship("DeviceDB", back_populates="tenant")
    users = relationship("UserDB", back_populates="tenant")


class LicenseKeyDB(Base):
    """Product licenses"""
    __tablename__ = "license_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), unique=True, index=True)
    
    # License details
    license_key = Column(Text, unique=True, nullable=False)
    license_tier = Column(String(50), nullable=False, index=True)
    license_type = Column(String(50), default="subscription")
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    issued_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, index=True, nullable=True)
    
    # Quotas
    max_devices = Column(Integer)
    max_users = Column(Integer)
    max_storage_gb = Column(Integer, default=10)
    api_rate_limit = Column(Integer, default=100)
    
    # Features (JSON)
    enabled_modules = Column(JSON, default=list)
    enabled_features = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_validated = Column(DateTime, nullable=True)
    
    # Relationships
    tenant = relationship("TenantDB", back_populates="license")


class LicenseValidationLogDB(Base):
    """License validation audit trail"""
    __tablename__ = "license_validation_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True)
    validation_result = Column(String(50), index=True)
    validation_message = Column(Text)
    checked_at = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ip_address = Column(String(45))
```

### Step 2: Add tenant_id to Existing Tables

```python
# Update DeviceDB, AuditResultDB, etc.

class DeviceDB(Base):
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    # ... rest of fields
    
    tenant = relationship("TenantDB", back_populates="devices")
```

### Step 3: Create Migration

```bash
cd /workspace

# Generate migration
alembic revision --autogenerate -m "Add license system tables"

# Review migration file in migrations/versions/

# Apply migration
alembic upgrade head
```

---

## Day 2-3: License Manager

### Step 1: Create License Manager Service

```python
# shared/license_manager.py

import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from cryptography.fernet import Fernet

class LicenseManager:
    """License generation and validation"""
    
    def __init__(self):
        # Get or generate encryption key
        key = os.getenv("LICENSE_ENCRYPTION_KEY")
        if not key:
            # Generate one-time (save this!)
            key = Fernet.generate_key().decode()
            print(f"Generated LICENSE_ENCRYPTION_KEY: {key}")
            print("Add this to your .env file!")
        
        self.cipher = Fernet(key.encode() if isinstance(key, str) else key)
        self.secret_salt = os.getenv("LICENSE_SECRET_SALT", "change-me-in-production")
    
    def generate_license(
        self,
        tenant_id: int,
        tier: str,
        expires_at: datetime = None,
        **quotas
    ) -> str:
        """Generate encrypted license key"""
        
        if expires_at is None:
            expires_at = datetime.utcnow() + timedelta(days=365)
        
        # Build license payload
        license_data = {
            "tenant_id": tenant_id,
            "tier": tier,
            "issued_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at.isoformat(),
            "max_devices": quotas.get("max_devices", 10),
            "max_users": quotas.get("max_users", 5),
            "max_storage_gb": quotas.get("max_storage_gb", 10),
            "enabled_modules": quotas.get("enabled_modules", []),
        }
        
        # Create signature
        data_str = json.dumps(license_data, sort_keys=True)
        signature = hashlib.sha256(f"{data_str}{self.secret_salt}".encode()).hexdigest()
        license_data["signature"] = signature
        
        # Encrypt
        encrypted = self.cipher.encrypt(json.dumps(license_data).encode())
        return encrypted.decode()
    
    def validate_license(self, license_key: str) -> Dict:
        """Validate and decode license"""
        try:
            # Decrypt
            decrypted = self.cipher.decrypt(license_key.encode())
            data = json.loads(decrypted.decode())
            
            # Verify signature
            signature = data.pop("signature")
            data_str = json.dumps(data, sort_keys=True)
            expected_sig = hashlib.sha256(f"{data_str}{self.secret_salt}".encode()).hexdigest()
            
            if signature != expected_sig:
                return {"valid": False, "reason": "tampered", "message": "License signature invalid"}
            
            # Check expiration
            expires_at = datetime.fromisoformat(data["expires_at"])
            if datetime.utcnow() > expires_at:
                return {
                    "valid": False,
                    "reason": "expired",
                    "message": f"License expired on {expires_at.date()}",
                    "data": data
                }
            
            return {"valid": True, "reason": "valid", "message": "License is valid", "data": data}
        
        except Exception as e:
            return {"valid": False, "reason": "invalid", "message": f"Invalid license: {str(e)}"}
    
    def check_quota(self, license_data: Dict, quota_type: str, current_value: int) -> bool:
        """Check if within quota"""
        quota_key = f"max_{quota_type}"
        max_allowed = license_data.get(quota_key, 0)
        return current_value < max_allowed
    
    def has_feature(self, license_data: Dict, feature: str) -> bool:
        """Check if feature is enabled"""
        tier = license_data.get("tier", "starter")
        
        # Define tier hierarchy
        tier_features = {
            "starter": ["devices", "manual_audits", "basic_rules"],
            "professional": ["devices", "manual_audits", "basic_rules", "scheduled_audits", "api_access", "backups"],
            "enterprise": ["all"],  # All features
            "enterprise_plus": ["all", "multi_tenant", "white_label"]
        }
        
        if tier in ["enterprise", "enterprise_plus"]:
            return True
        
        allowed_features = tier_features.get(tier, [])
        return feature in allowed_features

# Singleton
license_manager = LicenseManager()
```

### Step 2: Test License Generation

```python
# test_license.py

from shared.license_manager import license_manager
from datetime import datetime, timedelta

# Generate a license
license_key = license_manager.generate_license(
    tenant_id=1,
    tier="professional",
    expires_at=datetime.utcnow() + timedelta(days=365),
    max_devices=100,
    max_users=10,
    max_storage_gb=50
)

print(f"License Key:\n{license_key}\n")

# Validate it
result = license_manager.validate_license(license_key)
print(f"Validation Result: {result}")

# Check feature access
if result["valid"]:
    print(f"Has API access: {license_manager.has_feature(result['data'], 'api_access')}")
    print(f"Has SSO: {license_manager.has_feature(result['data'], 'sso')}")
```

```bash
python test_license.py
```

---

## Day 4-5: API Integration

### Step 1: License Middleware

```python
# shared/middleware/license_middleware.py

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from shared.license_manager import license_manager
from shared.database import get_db
import db_models

class LicenseMiddleware(BaseHTTPMiddleware):
    """Enforce license on API requests"""
    
    async def dispatch(self, request, call_next):
        # Skip public endpoints
        public_paths = ["/docs", "/redoc", "/openapi.json", "/health", "/login", "/signup"]
        if any(request.url.path.startswith(p) for p in public_paths):
            return await call_next(request)
        
        # Get tenant (assume set by TenantMiddleware)
        tenant = getattr(request.state, "tenant", None)
        if not tenant:
            # For now, use tenant_id=1 (single-tenant mode)
            tenant_id = 1
        else:
            tenant_id = tenant.id
        
        # Get license from DB
        db = next(get_db())
        license_obj = db.query(db_models.LicenseKeyDB).filter(
            db_models.LicenseKeyDB.tenant_id == tenant_id,
            db_models.LicenseKeyDB.is_active == True
        ).first()
        
        if not license_obj:
            return JSONResponse(
                {"error": "No active license", "action": "contact_sales"},
                status_code=402
            )
        
        # Validate license
        validation = license_manager.validate_license(license_obj.license_key)
        if not validation["valid"]:
            return JSONResponse(
                {
                    "error": "License invalid or expired",
                    "reason": validation["reason"],
                    "message": validation["message"],
                    "action": "renew_license"
                },
                status_code=402
            )
        
        # Add license data to request
        request.state.license = validation["data"]
        request.state.license_id = license_obj.id
        
        # Continue
        return await call_next(request)
```

### Step 2: Add Middleware to Main App

```python
# main.py or services/api-gateway/app/main.py

from shared.middleware.license_middleware import LicenseMiddleware

app = FastAPI(...)

# Add license middleware (AFTER CORS, BEFORE routes)
app.add_middleware(LicenseMiddleware)
```

### Step 3: License Admin API

```python
# services/admin-service/app/routes/licensing_admin.py

from fastapi import APIRouter, Depends, HTTPException
from shared.license_manager import license_manager
from shared.database import get_db
from sqlalchemy.orm import Session
import db_models
from datetime import datetime, timedelta
from pydantic import BaseModel

router = APIRouter(prefix="/admin/licensing", tags=["Licensing"])

class LicenseCreateRequest(BaseModel):
    tenant_id: int
    tier: str
    duration_days: int = 365
    max_devices: int = 10
    max_users: int = 5
    max_storage_gb: int = 10

@router.post("/generate")
async def generate_license(
    request: LicenseCreateRequest,
    db: Session = Depends(get_db)
):
    """Generate new license (admin only)"""
    
    # Check if tenant exists
    tenant = db.query(db_models.TenantDB).filter(
        db_models.TenantDB.id == request.tenant_id
    ).first()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Generate license key
    license_key = license_manager.generate_license(
        tenant_id=request.tenant_id,
        tier=request.tier,
        expires_at=datetime.utcnow() + timedelta(days=request.duration_days),
        max_devices=request.max_devices,
        max_users=request.max_users,
        max_storage_gb=request.max_storage_gb
    )
    
    # Deactivate old licenses
    db.query(db_models.LicenseKeyDB).filter(
        db_models.LicenseKeyDB.tenant_id == request.tenant_id
    ).update({"is_active": False})
    
    # Save new license
    new_license = db_models.LicenseKeyDB(
        tenant_id=request.tenant_id,
        license_key=license_key,
        license_tier=request.tier,
        is_active=True,
        expires_at=datetime.utcnow() + timedelta(days=request.duration_days),
        max_devices=request.max_devices,
        max_users=request.max_users,
        max_storage_gb=request.max_storage_gb
    )
    
    db.add(new_license)
    db.commit()
    db.refresh(new_license)
    
    return {
        "id": new_license.id,
        "license_key": license_key,
        "tier": request.tier,
        "expires_at": new_license.expires_at,
        "message": "License generated successfully"
    }

@router.get("/validate")
async def validate_license(db: Session = Depends(get_db)):
    """Validate current license"""
    
    # For now, use tenant_id=1
    tenant_id = 1
    
    license_obj = db.query(db_models.LicenseKeyDB).filter(
        db_models.LicenseKeyDB.tenant_id == tenant_id,
        db_models.LicenseKeyDB.is_active == True
    ).first()
    
    if not license_obj:
        raise HTTPException(status_code=404, detail="No active license")
    
    validation = license_manager.validate_license(license_obj.license_key)
    
    # Count current usage
    device_count = db.query(db_models.DeviceDB).filter(
        db_models.DeviceDB.tenant_id == tenant_id
    ).count()
    
    user_count = db.query(db_models.UserDB).filter(
        db_models.UserDB.tenant_id == tenant_id
    ).count()
    
    return {
        "valid": validation["valid"],
        "reason": validation["reason"],
        "message": validation["message"],
        "tier": license_obj.license_tier,
        "expires_at": license_obj.expires_at,
        "quotas": {
            "devices": {
                "current": device_count,
                "max": license_obj.max_devices,
                "percentage": (device_count / license_obj.max_devices * 100) if license_obj.max_devices else 0
            },
            "users": {
                "current": user_count,
                "max": license_obj.max_users,
                "percentage": (user_count / license_obj.max_users * 100) if license_obj.max_users else 0
            }
        }
    }

@router.post("/{license_id}/renew")
async def renew_license(
    license_id: int,
    duration_days: int = 365,
    db: Session = Depends(get_db)
):
    """Extend license expiration"""
    
    license_obj = db.query(db_models.LicenseKeyDB).filter(
        db_models.LicenseKeyDB.id == license_id
    ).first()
    
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")
    
    # Extend from current expiry or now (whichever is later)
    base_date = max(license_obj.expires_at, datetime.utcnow())
    new_expiry = base_date + timedelta(days=duration_days)
    
    license_obj.expires_at = new_expiry
    license_obj.is_active = True
    license_obj.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": "License renewed",
        "new_expiry": new_expiry
    }
```

### Step 4: Include Router

```python
# services/admin-service/app/main.py

from routes import licensing_admin

app.include_router(licensing_admin.router)
```

---

## Day 6-7: Frontend

### Step 1: Create License Context

```jsx
// frontend/src/contexts/LicenseContext.jsx

import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../api/api';

const LicenseContext = createContext();

export const useLicense = () => useContext(LicenseContext);

export const LicenseProvider = ({ children }) => {
  const [license, setLicense] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLicense();
  }, []);

  const fetchLicense = async () => {
    try {
      const response = await api.get('/admin/licensing/validate');
      setLicense(response.data);
    } catch (error) {
      console.error('License check failed:', error);
      setLicense({ valid: false, tier: 'none' });
    } finally {
      setLoading(false);
    }
  };

  const hasFeature = (feature) => {
    if (!license || !license.valid) return false;
    
    const tierFeatures = {
      starter: ['devices', 'manual_audits', 'basic_rules'],
      professional: ['devices', 'manual_audits', 'basic_rules', 'scheduled_audits', 'api_access', 'backups', 'webhooks'],
      enterprise: ['all'],
    };
    
    const allowed = tierFeatures[license.tier] || [];
    return allowed.includes('all') || allowed.includes(feature);
  };

  return (
    <LicenseContext.Provider value={{ license, loading, hasFeature, refetch: fetchLicense }}>
      {children}
    </LicenseContext.Provider>
  );
};
```

### Step 2: Wrap App with License Provider

```jsx
// frontend/src/App.js

import { LicenseProvider } from './contexts/LicenseContext';

function App() {
  return (
    <LicenseProvider>
      {/* Rest of app */}
    </LicenseProvider>
  );
}
```

### Step 3: Create Upgrade Prompt Component

```jsx
// frontend/src/components/UpgradePrompt.jsx

import React from 'react';
import { Box, Card, CardContent, Typography, Button, Chip } from '@mui/material';
import LockIcon from '@mui/icons-material/Lock';

export default function UpgradePrompt({ feature, requiredPlan, description }) {
  return (
    <Box p={3}>
      <Card sx={{ maxWidth: 600, mx: 'auto', textAlign: 'center', py: 4 }}>
        <CardContent>
          <LockIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          
          <Typography variant="h4" gutterBottom>
            Upgrade Required
          </Typography>
          
          <Typography variant="body1" color="text.secondary" paragraph>
            <strong>{feature}</strong> is available on the{' '}
            <Chip label={requiredPlan} color="primary" size="small" /> plan and above.
          </Typography>
          
          {description && (
            <Typography variant="body2" color="text.secondary" paragraph>
              {description}
            </Typography>
          )}
          
          <Button
            variant="contained"
            color="primary"
            size="large"
            sx={{ mt: 2 }}
            onClick={() => window.open('/pricing', '_blank')}
          >
            View Plans & Pricing
          </Button>
          
          <Button
            variant="text"
            size="small"
            sx={{ mt: 1, display: 'block', mx: 'auto' }}
            onClick={() => window.open('mailto:sales@yourcompany.com', '_blank')}
          >
            Contact Sales
          </Button>
        </CardContent>
      </Card>
    </Box>
  );
}
```

### Step 4: Use in Components

```jsx
// frontend/src/components/AuditSchedules.jsx

import { useLicense } from '../contexts/LicenseContext';
import UpgradePrompt from './UpgradePrompt';

export default function AuditSchedules() {
  const { hasFeature, license } = useLicense();

  if (!hasFeature('scheduled_audits')) {
    return (
      <UpgradePrompt
        feature="Scheduled Audits"
        requiredPlan="Professional"
        description="Automate your compliance checks with cron-based scheduling"
      />
    );
  }

  return (
    <div>
      {/* Normal audit schedules UI */}
    </div>
  );
}
```

### Step 5: License Dashboard

```jsx
// frontend/src/components/LicenseDashboard.jsx

import React from 'react';
import { Box, Card, CardContent, Typography, LinearProgress, Grid, Chip, Alert } from '@mui/material';
import { useLicense } from '../contexts/LicenseContext';

export default function LicenseDashboard() {
  const { license } = useLicense();

  if (!license) return <div>Loading...</div>;

  const daysUntilExpiry = Math.ceil(
    (new Date(license.expires_at) - new Date()) / (1000 * 60 * 60 * 24)
  );

  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>
        License & Usage
      </Typography>

      {/* License Info */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6">Current Plan</Typography>
              <Chip 
                label={license.tier?.toUpperCase()} 
                color="primary" 
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6">Status</Typography>
              <Chip 
                label={license.valid ? 'ACTIVE' : 'EXPIRED'} 
                color={license.valid ? 'success' : 'error'}
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6">Expires In</Typography>
              <Typography variant="h4" color={daysUntilExpiry < 30 ? 'error' : 'text.primary'}>
                {daysUntilExpiry} days
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Device Quota */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Devices
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'baseline', mb: 1 }}>
                <Typography variant="h3">
                  {license.quotas?.devices?.current || 0}
                </Typography>
                <Typography variant="h6" color="text.secondary" sx={{ ml: 1 }}>
                  / {license.quotas?.devices?.max || 0}
                </Typography>
              </Box>
              <LinearProgress 
                variant="determinate" 
                value={license.quotas?.devices?.percentage || 0}
                color={license.quotas?.devices?.percentage > 80 ? 'warning' : 'primary'}
              />
            </CardContent>
          </Card>
        </Grid>

        {/* User Quota */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Users
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'baseline', mb: 1 }}>
                <Typography variant="h3">
                  {license.quotas?.users?.current || 0}
                </Typography>
                <Typography variant="h6" color="text.secondary" sx={{ ml: 1 }}>
                  / {license.quotas?.users?.max || 0}
                </Typography>
              </Box>
              <LinearProgress 
                variant="determinate" 
                value={license.quotas?.users?.percentage || 0}
                color={license.quotas?.users?.percentage > 80 ? 'warning' : 'primary'}
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Alerts */}
      {daysUntilExpiry < 30 && (
        <Alert severity="warning" sx={{ mt: 3 }}>
          Your license expires in {daysUntilExpiry} days. Contact sales to renew.
        </Alert>
      )}
    </Box>
  );
}
```

---

## Day 8-10: Testing & Launch

### Test Plan

#### 1. License Generation Test

```bash
curl -X POST http://localhost:3005/admin/licensing/generate \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": 1,
    "tier": "professional",
    "duration_days": 365,
    "max_devices": 100,
    "max_users": 10
  }'
```

#### 2. License Validation Test

```bash
curl http://localhost:3005/admin/licensing/validate
```

#### 3. Quota Enforcement Test

```python
# Try adding 101st device when limit is 100
# Should return 403 error
```

#### 4. Feature Gating Test

```bash
# Try accessing scheduled audits with Starter license
# Should show upgrade prompt
```

#### 5. Expiration Test

```python
# Generate license with expires_at = yesterday
# All API calls should return 402 Payment Required
```

---

### Production Checklist

- [ ] Environment variables set:
  - `LICENSE_ENCRYPTION_KEY`
  - `LICENSE_SECRET_SALT`
- [ ] Database migrations applied
- [ ] Default tenant created
- [ ] Test license generated
- [ ] Middleware enabled
- [ ] Frontend context integrated
- [ ] All API endpoints protected
- [ ] Quota checks on device/user creation
- [ ] Feature gates on premium features
- [ ] Error messages user-friendly
- [ ] Admin API restricted to admins
- [ ] Documentation updated

---

## Pricing Configuration

### Create Tier Definitions

```python
# shared/license_tiers.py

LICENSE_TIERS = {
    "starter": {
        "name": "Starter",
        "price_monthly": 49,
        "price_annual": 490,
        "max_devices": 10,
        "max_users": 2,
        "max_storage_gb": 5,
        "features": [
            "devices",
            "manual_audits",
            "basic_rules",
            "email_notifications"
        ]
    },
    "professional": {
        "name": "Professional",
        "price_monthly": 199,
        "price_annual": 1990,
        "max_devices": 100,
        "max_users": 10,
        "max_storage_gb": 50,
        "features": [
            "devices",
            "manual_audits",
            "scheduled_audits",
            "api_access",
            "backups",
            "drift_detection",
            "webhooks",
            "rule_templates"
        ]
    },
    "enterprise": {
        "name": "Enterprise",
        "price_monthly": 999,
        "price_annual": 9990,
        "max_devices": 999999,  # Unlimited
        "max_users": 999999,
        "max_storage_gb": 999999,
        "features": ["all"]
    }
}
```

---

## Quick Commands Reference

```bash
# Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Add to .env
echo "LICENSE_ENCRYPTION_KEY=<your-key>" >> .env
echo "LICENSE_SECRET_SALT=$(openssl rand -hex 32)" >> .env

# Apply migrations
alembic upgrade head

# Test license generation
python test_license.py

# Start services
docker-compose up -d

# Check logs
docker logs admin-service --tail 100 -f
```

---

## Troubleshooting

### "License not found"
- Check tenant_id is correct
- Verify license was created in database
- Check `is_active = True`

### "License expired"
- Check `expires_at` date
- Renew license via API

### "Feature not available"
- Check tier has access to feature
- Verify `hasFeature()` logic

### "Quota exceeded"
- Check current usage vs. limit
- Upgrade plan or purchase add-on

---

## Next Steps After Basic Implementation

1. **Add Billing Integration** (Stripe/Chargebee)
2. **Self-Service Signup** (trial accounts)
3. **Usage Metering** (track actual usage)
4. **License Analytics Dashboard** (for internal team)
5. **Automated Renewal Reminders** (email alerts)
6. **Upgrade/Downgrade Flows** (plan changes)

---

**Estimated Time**: 8-10 days for basic working system
**Result**: License-based access control with tiered pricing
**Status**: Ready to monetize!
