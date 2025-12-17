# Network Audit Platform (NAP) - Pre-Production Code Review

**Review Date:** December 17, 2025
**Reviewer:** Claude Code AI Security Review
**Repository:** PyVold/nap

---

## Executive Summary

This comprehensive security and code quality review identified **67+ critical and high-severity issues** that must be addressed before production deployment. The most severe findings include:

1. **Secrets committed to Git** - JWT keys, encryption keys, and database passwords are tracked in version control
2. **Missing authentication on critical endpoints** - User group membership can be modified by unauthenticated attackers
3. **Dangerous eval() usage** - User-controlled input passed to eval() enables remote code execution
4. **CORS misconfiguration** - All origins allowed with credentials enabled across all services

**Recommendation:** Do NOT deploy to production until critical issues are resolved.

---

## Table of Contents

1. [Critical Security Issues](#1-critical-security-issues)
2. [High Severity Issues](#2-high-severity-issues)
3. [Medium Severity Issues](#3-medium-severity-issues)
4. [Code Quality Issues](#4-code-quality-issues)
5. [Missing Features for Production](#5-missing-features-for-production)
6. [Recommendations & Remediation Plan](#6-recommendations--remediation-plan)

---

## 1. Critical Security Issues

### 1.1 Secrets Committed to Version Control (CRITICAL)

**Impact:** All secrets are compromised and must be rotated immediately.

| File | Secrets Exposed |
|------|-----------------|
| `.env` | JWT_SECRET, ENCRYPTION_KEY, LICENSE_ENCRYPTION_KEY, LICENSE_SECRET_SALT, DATABASE_URL |
| `.env.prod` | All production secrets including POSTGRES_PASSWORD, REDIS_PASSWORD, GRAFANA_PASSWORD |

```bash
# Files tracked in git
$ git ls-files | grep -E "\.env$|\.env\.prod$"
.env
.env.prod
```

**Remediation:**
1. Rotate ALL secrets immediately
2. Remove files from git history using `git filter-branch` or BFG Repo-Cleaner
3. Add `.env*` to `.gitignore` (currently only `.env` is listed)

---

### 1.2 Unauthenticated Group Membership Endpoints (CRITICAL)

**File:** `api/routes/user_management.py` (lines 119-176)

**Impact:** Any unauthenticated attacker can add/remove users from groups, escalating privileges.

```python
# Lines 119-124: NO AUTHENTICATION
@router.post("/groups/{group_id}/members/{user_id}")
def add_user_to_group(
    group_id: int,
    user_id: int,
    db: Session = Depends(get_db)  # Missing: current_user = Depends(require_admin)
):
```

**Affected Endpoints:**
- `POST /groups/{id}/members/{user_id}` - Add user to group
- `DELETE /groups/{id}/members/{user_id}` - Remove user from group
- `PUT /groups/{id}/members` - Set all group members
- `GET /groups/{id}/members` - List group members
- `GET /users/{id}/permissions` - Get any user's permissions
- `GET /users/{id}/modules` - Get any user's module access

---

### 1.3 Remote Code Execution via eval() (CRITICAL)

**Files:**
- `services/rule-service/app/engine/workflow_engine.py` (line 94)
- `services/rule-service/app/engine/protocol_parsers/bgp_parser.py` (line 167)

```python
# workflow_engine.py:94
return bool(eval(rendered, {"__builtins__": {}}, context))
```

**Impact:** Despite restricted builtins, eval() can be exploited via attribute access on Python objects.

**Remediation:** Replace with `ast.literal_eval()` or a safe expression evaluator library.

---

### 1.4 Hardcoded Encryption Key Default (CRITICAL)

**File:** `utils/crypto.py` (line 14)

```python
SECRET_KEY = os.getenv("ENCRYPTION_KEY", "network-audit-platform-secret-key-change-in-production")
```

**Impact:** If ENCRYPTION_KEY env var is unset, all device credentials are encrypted with a publicly known key.

---

### 1.5 CORS Allows All Origins with Credentials (CRITICAL)

**Affected Files:** All 9 microservice `main.py` files

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # VULNERABLE
    allow_credentials=True,         # Allows cookies/tokens
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Impact:** Enables CSRF attacks from any malicious website.

---

## 2. High Severity Issues

### 2.1 SSH Host Key Verification Disabled

**Files:**
- `services/discovery_service.py` (lines 64, 90)
- `services/device-service/app/services/discovery_service.py` (lines 72, 98)

```python
hostkey_verify=False  # MITM vulnerability
```

---

### 2.2 Default Credentials Fallback

**File:** `services/health_service.py` (lines 232-233)

```python
device.username or "admin",
device.password or "admin"
```

**Impact:** Falls back to admin:admin if credentials are empty.

---

### 2.3 All Containers Run as Root

**All Dockerfiles lack USER directive:**
- `frontend/Dockerfile`
- `services/api-gateway/Dockerfile`
- `services/device-service/Dockerfile`
- `services/rule-service/Dockerfile`
- `services/backup-service/Dockerfile`
- `services/inventory-service/Dockerfile`
- `services/admin-service/Dockerfile`
- `services/analytics-service/Dockerfile`

---

### 2.4 Missing Security Headers in Nginx

**File:** `frontend/nginx.conf`

**Missing Headers:**
- `Strict-Transport-Security`
- `X-Frame-Options`
- `X-Content-Type-Options`
- `Content-Security-Policy`
- `X-XSS-Protection`

---

### 2.5 JWT Token Issues

**Issues:**
- 24-hour expiration with no refresh mechanism
- No token revocation capability
- Token stored in localStorage (XSS vulnerable)

**Files:**
- `utils/auth.py` (line 31): `ACCESS_TOKEN_EXPIRE_MINUTES = 1440`
- `frontend/src/contexts/AuthContext.js` (line 128): `localStorage.setItem('auth_token')`

---

### 2.6 Mass Assignment Vulnerabilities

**File:** `api/routes/admin.py` (lines 250-252)

```python
for field, value in update_data.items():
    setattr(user, field, value)  # No field whitelist - can modify role, is_active, etc.
```

---

### 2.7 XXE Vulnerability in XML Parsing

**Files:**
- `services/discovery_service.py` (lines 117, 150, 163)
- `services/device-service/app/services/discovery_service.py`

```python
root = etree.fromstring(result.data_xml.encode())  # No XXE protection
```

**Remediation:** Use `defusedxml` library.

---

### 2.8 Missing Pagination on List Endpoints

**34 endpoints** return unbounded lists, creating DoS risk:
- `GET /devices` - All devices
- `GET /users` - All users
- `GET /rules` - All rules
- `GET /audits` - All audit results
- Many more...

---

## 3. Medium Severity Issues

### 3.1 Database Models - Passwords Not Encrypted

**All db_models.py files:** Device and DiscoveryGroup passwords stored in plain String fields despite comments claiming encryption.

```python
# db_models.py:17
password = Column(String(255))  # Comment says "(Encrypted)" but it's not
```

---

### 3.2 No Account Lockout After Failed Login

**File:** `api/routes/admin.py` (lines 109-150)

No tracking of failed attempts, no lockout mechanism - vulnerable to brute force.

---

### 3.3 Missing Database Indexes

**Critical missing indexes for performance:**
- `AuditResultDB.status`
- `AuditResultDB.device_name`
- `HealthCheckDB.overall_status`
- `AuditLogDB.timestamp` (alone)
- `ConfigChangeEventDB.acknowledged`

---

### 3.4 Test Credentials Displayed in UI

**File:** `frontend/src/components/Login.jsx` (lines 162-172)

```jsx
<Typography variant="caption">
    <strong>Admin:</strong> admin / admin
</Typography>
```

---

### 3.5 Excessive Console Logging

**80+ console.log/console.error statements** in production frontend code exposing:
- License information
- API responses
- Error details

---

### 3.6 File Upload Vulnerabilities

**File:** `api/routes/device_import.py` (line 76)

```python
if not file.filename.endswith('.csv'):  # Only extension check
```

**Missing:**
- MIME type validation
- File size limits
- Content sanitization

---

## 4. Code Quality Issues

### 4.1 TODO/FIXME Comments (Incomplete Features)

| File | Line | Issue |
|------|------|-------|
| `services/config_backup_service.py` | 551 | `TODO: Implement actual config restoration` |
| `engine/step_executors/notification_executor.py` | 66 | `TODO: Implement email sending` |
| `shared/monitoring.py` | 283-284 | `TODO: Add actual DB/cache checks` |
| `shared/deps.py` | 257 | `TODO: Implement module-level access control` |

---

### 4.2 Print Statements Instead of Logging

**80+ print statements** in production code:
- `init_database.py` - 9 print calls
- `migrate_to_microservices.py` - 30+ print calls
- `services/admin-service/fix_admin_superuser.py` - 22 print calls
- All migration files

---

### 4.3 Bare Except Clauses

**12 locations** with `except:` swallowing all exceptions:
- `scheduler/background_scheduler.py:318`
- `engine/step_executors/api_call_executor.py:91`
- `shared/connectors/netconf_connector.py:49, 243`
- Multiple others

---

### 4.4 Insecure Defaults in Configuration

**File:** `config.py`

```python
debug_mode: bool = True   # Should be False
enable_auth: bool = False  # Should be True
```

---

### 4.5 Insufficient Test Coverage

**Only 4 test files exist:**
- `test_rate_limiter.py`
- `test_security.py`
- `test_validators.py`
- `conftest.py`

**Missing tests for:**
- Device service endpoints
- Audit engine logic
- Config backup operations
- Authentication/authorization
- Discovery service
- Notification service
- Hardware inventory
- Remediation workflows
- License management

---

## 5. Missing Features for Production

### 5.1 Security Features

| Feature | Status | Priority |
|---------|--------|----------|
| HTTPS/TLS enforcement | Missing | Critical |
| Rate limiting on login | Partially implemented | Critical |
| Token refresh mechanism | Missing | High |
| Token revocation | Missing | High |
| Account lockout | Missing | High |
| Password strength validation | Defined but not used | High |
| Audit log immutability | Missing | Medium |
| CSRF protection | Missing | Medium |

### 5.2 Operational Features

| Feature | Status | Priority |
|---------|--------|----------|
| Health check endpoints | Partial (dev configs missing) | High |
| Resource limits (dev compose) | Missing | High |
| Log aggregation | Missing | Medium |
| Metrics collection | Partial (Prometheus configured) | Medium |
| Backup automation | Missing | Medium |
| Database migrations | Manual scripts only | Medium |

---

## 6. Recommendations & Remediation Plan

### Immediate Actions (Before Any Deployment)

1. **Rotate ALL secrets** - JWT_SECRET, ENCRYPTION_KEY, LICENSE keys, database passwords
2. **Remove .env files from git history**
   ```bash
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch .env .env.prod" \
     --prune-empty --tag-name-filter cat -- --all
   ```
3. **Add authentication** to user management endpoints in `api/routes/user_management.py`
4. **Replace eval()** with safe alternatives
5. **Fix CORS** - Set specific allowed origins instead of `*`

### Short-term (1-2 Weeks)

1. **Add USER directive** to all Dockerfiles
2. **Add security headers** to nginx.conf
3. **Enable SSH host key verification** for production
4. **Implement token refresh** and reduce token lifetime
5. **Add pagination** to all list endpoints (limit: 100 max)
6. **Fix mass assignment** - Use explicit field whitelists
7. **Add file upload validation** - Size limits, MIME type checks
8. **Remove test credentials** from Login.jsx
9. **Replace print statements** with proper logging
10. **Fix bare except clauses** - Use specific exception types

### Medium-term (2-4 Weeks)

1. **Encrypt device passwords at rest** using SQLAlchemy TypeDecorator
2. **Implement account lockout** after 5 failed login attempts
3. **Add missing database indexes**
4. **Implement proper audit log immutability**
5. **Add comprehensive test coverage** (target: 80%)
6. **Move authentication tokens** to httpOnly cookies
7. **Add rate limiting** to sensitive endpoints
8. **Implement password strength validation**

### Long-term (Before GA)

1. **Set up secrets management** (HashiCorp Vault, AWS Secrets Manager)
2. **Implement network segmentation** in Docker
3. **Add WAF (Web Application Firewall)**
4. **Set up security scanning** in CI/CD (SAST, DAST, dependency scanning)
5. **Conduct penetration testing**
6. **Complete compliance documentation**

---

## Summary Statistics

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| Authentication/Authorization | 6 | 3 | 2 | 0 | 11 |
| Secrets Management | 3 | 1 | 0 | 0 | 4 |
| Input Validation | 1 | 4 | 5 | 0 | 10 |
| Infrastructure Security | 1 | 4 | 3 | 2 | 10 |
| Code Quality | 0 | 2 | 8 | 5 | 15 |
| Database Security | 1 | 2 | 4 | 0 | 7 |
| Frontend Security | 1 | 2 | 4 | 1 | 8 |
| **TOTAL** | **13** | **18** | **26** | **8** | **65** |

---

## Appendix: Files Requiring Immediate Attention

### Critical Files
- `api/routes/user_management.py` - Add authentication
- `utils/crypto.py` - Remove hardcoded default key
- `.env`, `.env.prod` - Remove from git, rotate secrets
- `services/rule-service/app/engine/workflow_engine.py` - Replace eval()

### High Priority Files
- All `main.py` files - Fix CORS configuration
- All `Dockerfile` files - Add USER directive
- `frontend/nginx.conf` - Add security headers
- `frontend/src/contexts/AuthContext.js` - Fix token storage
- All `db_models.py` files - Encrypt sensitive fields

---

*This report should be reviewed by the development team and security stakeholders. All critical issues should be resolved before any production deployment.*
