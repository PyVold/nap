# Security Setup Guide - Network Audit Platform

🔒 **CRITICAL:** Follow this guide completely before deploying to production.

---

## ⚠️ Pre-Deployment Security Checklist

### 1. Generate Secure Keys

Generate cryptographically secure keys for JWT and encryption:

```bash
# Generate JWT secret key
python -c 'import secrets; print("JWT_SECRET=" + secrets.token_urlsafe(32))'

# Generate encryption key
python -c 'import secrets; print("ENCRYPTION_KEY=" + secrets.token_urlsafe(32))'
```

**Output example:**
```
JWT_SECRET=dGhpc19pc19hX3NlY3VyZV9rZXlfZXhhbXBsZV8xMjM0NTY3ODkw
ENCRYPTION_KEY=YW5vdGhlcl9zZWN1cmVfa2V5X2V4YW1wbGVfMDk4NzY1NDMyMQ
```

### 2. Create .env File

Copy the example and add your generated keys:

```bash
cp .env.example .env
```

Edit `.env` and replace the placeholder values with your generated keys:

```bash
# BEFORE (insecure)
JWT_SECRET=GENERATE_SECURE_KEY_BEFORE_PRODUCTION
ENCRYPTION_KEY=GENERATE_SECURE_KEY_BEFORE_PRODUCTION

# AFTER (with your actual generated keys)
JWT_SECRET=dGhpc19pc19hX3NlY3VyZV9rZXlfZXhhbXBsZV8xMjM0NTY3ODkw
ENCRYPTION_KEY=YW5vdGhlcl9zZWN1cmVfa2V5X2V4YW1wbGVfMDk4NzY1NDMyMQ
```

**⚠️ IMPORTANT:** Never commit `.env` to version control! It's already in `.gitignore`.

### 3. Update Docker Compose

The application will automatically read from environment variables.

**Option A - Use .env file (recommended for Docker):**
```bash
# Docker Compose automatically reads .env file
docker-compose up -d
```

**Option B - Export environment variables:**
```bash
export JWT_SECRET="your-generated-jwt-secret"
export ENCRYPTION_KEY="your-generated-encryption-key"
docker-compose up -d
```

### 4. Verify Keys are Set

Check that services start successfully:

```bash
docker-compose logs device-service | grep -i "jwt\|encryption\|error"
```

✅ **Success:** No error messages about missing JWT_SECRET or ENCRYPTION_KEY

❌ **Failure:** You'll see:
```
RuntimeError: JWT_SECRET environment variable is not set
RuntimeError: ENCRYPTION_KEY environment variable is not set
```

---

## 🔐 Database Credentials

### Change Default Database Password

Edit `docker-compose.yml`:

```yaml
database:
  environment:
    POSTGRES_DB: nap_db
    POSTGRES_USER: nap_user
    POSTGRES_PASSWORD: YOUR_SECURE_PASSWORD_HERE  # Change this!
```

Update all service DATABASE_URL:
```yaml
environment:
  - DATABASE_URL=postgresql://nap_user:YOUR_SECURE_PASSWORD_HERE@database:5432/nap_db
```

### Generate Secure Password

```bash
python -c 'import secrets; print(secrets.token_urlsafe(16))'
```

---

## 👤 User Management Security

### Default Users

The system creates default test users on first startup:
- Username: `admin`, Password: `admin`
- Username: `operator`, Password: `operator`
- Username: `viewer`, Password: `viewer`

### 🚨 CRITICAL: Change Default Credentials

**Immediately after first deployment:**

1. **Login as admin:**
   ```bash
   curl -X POST http://localhost:3000/admin/login \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"admin"}'
   ```

2. **Get your token** from the response

3. **Change admin password:**
   ```bash
   curl -X PUT http://localhost:3000/user-management/users/1 \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"password":"your-new-secure-password"}'
   ```

4. **Delete or disable test accounts:**
   ```bash
   # Delete operator test account
   curl -X DELETE http://localhost:3000/user-management/users/2 \
     -H "Authorization: Bearer YOUR_TOKEN"

   # Delete viewer test account
   curl -X DELETE http://localhost:3000/user-management/users/3 \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

---

## 🌐 Network Security

### 1. Enable HTTPS

**Production MUST use HTTPS.** Options:

**Option A - Reverse Proxy (Recommended):**
```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name network-audit.example.com;

    ssl_certificate /etc/ssl/certs/your-cert.pem;
    ssl_certificate_key /etc/ssl/private/your-key.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Option B - Let's Encrypt:**
```bash
# Install certbot
apt-get install certbot python3-certbot-nginx

# Generate certificate
certbot --nginx -d network-audit.example.com
```

### 2. Configure CORS

Edit `services/api-gateway/app/main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],  # Specify allowed origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### 3. Implement Rate Limiting

Install slowapi:
```bash
pip install slowapi
```

Add to API Gateway:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/devices")
@limiter.limit("10/minute")
async def list_devices():
    ...
```

---

## 🔑 Secrets Management

### For Production - Use Secrets Manager

**AWS Secrets Manager:**
```python
import boto3
import json

def get_secret():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='nap/prod/secrets')
    return json.loads(response['SecretString'])

secrets = get_secret()
JWT_SECRET = secrets['jwt_secret']
ENCRYPTION_KEY = secrets['encryption_key']
```

**HashiCorp Vault:**
```python
import hvac

client = hvac.Client(url='http://vault:8200')
secret = client.secrets.kv.v2.read_secret_version(path='nap/prod')
JWT_SECRET = secret['data']['data']['jwt_secret']
```

**Kubernetes Secrets:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: nap-secrets
type: Opaque
data:
  jwt-secret: <base64-encoded-secret>
  encryption-key: <base64-encoded-key>
```

---

## 📋 Security Verification Checklist

Before going live, verify:

- [ ] JWT_SECRET is set to a secure random value (min 32 bytes)
- [ ] ENCRYPTION_KEY is set to a secure random value (min 32 bytes)
- [ ] Default database password has been changed
- [ ] Default admin password has been changed
- [ ] Default test accounts (operator, viewer) have been deleted
- [ ] HTTPS is enabled with valid SSL certificate
- [ ] CORS is configured to only allow trusted origins
- [ ] Rate limiting is implemented on API endpoints
- [ ] Database credentials are not in version control
- [ ] Secrets are stored in secrets manager (not .env files)
- [ ] All services start without errors
- [ ] Can login and authenticate successfully
- [ ] API endpoints require authentication
- [ ] Role-based permissions work correctly

---

## 🔍 Monitoring & Auditing

### Enable Audit Logging

Check user actions in `audit_logs` table:
```sql
SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 100;
```

### Monitor Failed Login Attempts

```bash
docker-compose logs admin-service | grep "authentication failed"
```

### Set Up Alerts

Configure alerts for:
- Multiple failed login attempts
- Unusual API activity
- Service errors
- Database connection issues

---

## 🚨 Incident Response

### If Keys Are Compromised:

1. **Generate new keys immediately:**
   ```bash
   python -c 'import secrets; print(secrets.token_urlsafe(32))'
   ```

2. **Update all services:**
   ```bash
   # Update .env file
   # Restart services
   docker-compose restart
   ```

3. **Invalidate all sessions:**
   - All users will need to re-login
   - Old JWT tokens will be invalid

4. **Rotate device credentials:**
   - All stored device passwords need to be re-encrypted

### If Database Is Compromised:

1. **Disconnect database from network**
2. **Assess scope of breach**
3. **Restore from backup if necessary**
4. **Rotate all device credentials**
5. **Force password reset for all users**
6. **Review and update security measures**

---

## 📚 Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [PostgreSQL Security](https://www.postgresql.org/docs/current/security.html)

---

## 🆘 Support

If you encounter security issues:

1. **DO NOT** report security issues in public GitHub issues
2. Email security concerns to: [your-security-email]
3. Include: description, impact, and steps to reproduce
4. Allow 48 hours for response

---

**Last Updated:** 2025-11-27  
**Version:** 1.0
