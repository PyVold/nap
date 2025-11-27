# Production Deployment Checklist

**Before deploying to production, verify ALL items in this checklist.**

---

## 🔒 Critical Security Items

### Environment Variables
- [ ] JWT_SECRET is set to a secure random value (min 32 bytes)
  ```bash
  python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
  ```
- [ ] ENCRYPTION_KEY is set to a secure random value (min 32 bytes)
  ```bash
  python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
  ```
- [ ] Both secrets are stored in secrets manager (AWS Secrets Manager, Vault, etc.)
- [ ] `.env` file is NOT committed to version control
- [ ] Database password has been changed from default `nap_password`

### User Accounts
- [ ] Default admin password has been changed from `admin`
- [ ] Default operator account has been deleted or disabled
- [ ] Default viewer account has been deleted or disabled
- [ ] All user accounts have strong passwords (min 12 characters)
- [ ] Created production admin account with different username

---

## 🌐 Network Security

### HTTPS Configuration
- [ ] Valid SSL/TLS certificate is installed
- [ ] HTTP redirects to HTTPS
- [ ] SSL certificate is not self-signed (for production)
- [ ] Certificate expiration is monitored

### CORS Configuration
- [ ] CORS is configured to only allow trusted origins
- [ ] Wildcard `*` is not used in production
- [ ] `allow_credentials` is set appropriately

### Firewall Rules
- [ ] Only necessary ports are exposed (443, 3000-3005 if needed)
- [ ] Database port 5432 is NOT exposed to public internet
- [ ] SSH access is restricted to specific IPs

---

## 🗄️ Database

### Configuration
- [ ] Database credentials are secure and rotated
- [ ] Database is backed up regularly
- [ ] Backup restore procedure has been tested
- [ ] Connection pooling is configured (default: pool_size=10)

### Migrations
- [ ] Database schema is up to date
- [ ] Migrations have been tested on staging
- [ ] Rollback procedure is documented

---

## 🔐 Application Security

### Rate Limiting
- [ ] Rate limiting is implemented on API endpoints
- [ ] DDoS protection is in place

### Authentication
- [ ] All API endpoints require authentication
- [ ] JWT token expiration is configured appropriately (default: 24 hours)
- [ ] Failed login attempts are logged and monitored

### Authorization
- [ ] Role-based permissions are working correctly
- [ ] Admin-only endpoints reject non-admin users
- [ ] Operator permissions are properly restricted

---

## 📊 Monitoring & Logging

### Application Monitoring
- [ ] Health check endpoints are configured
  - [ ] API Gateway: http://localhost:3000/health
  - [ ] All services: http://localhost:300X/health
- [ ] Uptime monitoring is configured
- [ ] Alert notifications are set up

### Logging
- [ ] Logs are centralized (ELK stack, CloudWatch, etc.)
- [ ] Log retention policy is configured
- [ ] Error alerts are configured
- [ ] Security events are logged (failed logins, permission denials)

### Metrics
- [ ] Prometheus/metrics endpoints are configured
- [ ] Grafana dashboards are set up
- [ ] Key metrics are being tracked:
  - [ ] Request rate
  - [ ] Error rate
  - [ ] Response time
  - [ ] Database connection pool usage

---

## 🐳 Docker & Infrastructure

### Docker Configuration
- [ ] Images are built from official base images
- [ ] Images are scanned for vulnerabilities
- [ ] Non-root user is used in containers
- [ ] Secrets are NOT baked into images

### Resource Limits
- [ ] Memory limits are set for each service
- [ ] CPU limits are set for each service
- [ ] Database has sufficient resources allocated

### High Availability
- [ ] Services can run multiple replicas
- [ ] Load balancing is configured
- [ ] Database has replication/failover configured

---

## 🧪 Testing

### Pre-Deployment Tests
- [ ] All critical API endpoints tested
- [ ] Authentication tested with all roles (admin, operator, viewer)
- [ ] Device connectivity tested (Nokia, Cisco)
- [ ] Configuration backup tested
- [ ] Audit execution tested
- [ ] Notification webhooks tested

### Performance Tests
- [ ] Load testing completed
- [ ] Stress testing completed
- [ ] Database query performance is acceptable
- [ ] API response times are within SLA

---

## 📋 Documentation

### Internal Documentation
- [ ] Architecture diagram is up to date
- [ ] API documentation is complete
- [ ] Deployment procedures are documented
- [ ] Troubleshooting guide exists
- [ ] Rollback procedure is documented

### External Documentation
- [ ] User guide is available
- [ ] API documentation is published
- [ ] Change log is maintained

---

## 🔄 Backup & Recovery

### Backup Strategy
- [ ] Database backups are automated
- [ ] Backup retention policy is defined
- [ ] Backups are tested regularly
- [ ] Off-site backups are configured

### Disaster Recovery
- [ ] Disaster recovery plan is documented
- [ ] RTO (Recovery Time Objective) is defined
- [ ] RPO (Recovery Point Objective) is defined
- [ ] DR procedure has been tested

---

## 🚀 Deployment Process

### Pre-Deployment
- [ ] Change window is scheduled and communicated
- [ ] Rollback plan is ready
- [ ] Database backup is taken
- [ ] Staging environment tested

### During Deployment
- [ ] Services are deployed in correct order:
  1. Database migrations
  2. Backend services
  3. API Gateway
  4. Frontend
- [ ] Health checks pass for all services
- [ ] Smoke tests pass

### Post-Deployment
- [ ] All services are running
- [ ] No errors in logs
- [ ] Monitoring shows healthy metrics
- [ ] User acceptance testing completed
- [ ] Rollback plan can be executed if needed

---

## ⚠️ Common Issues to Check

### Configuration Issues
- [ ] Environment variables are set in production environment
- [ ] Service URLs are correct for production
- [ ] Database URL points to production database
- [ ] API Gateway can reach all services

### Security Issues
- [ ] No hardcoded secrets in code
- [ ] No sensitive data in logs
- [ ] No debug endpoints enabled
- [ ] CORS is not set to allow all origins

### Performance Issues
- [ ] Database indexes are created
- [ ] Connection pooling is working
- [ ] No N+1 queries
- [ ] Caching is configured where appropriate

---

## 📞 Emergency Contacts

Document emergency contacts:

- [ ] **DevOps Lead:**
- [ ] **Database Administrator:**
- [ ] **Security Team:**
- [ ] **On-Call Engineer:**

---

## ✅ Sign-Off

Before marking complete, ensure:

| Area | Status | Reviewed By | Date |
|------|--------|-------------|------|
| Security Configuration | ☐ | ___________ | __/__/__ |
| Database Setup | ☐ | ___________ | __/__/__ |
| Network Security | ☐ | ___________ | __/__/__ |
| Monitoring & Alerts | ☐ | ___________ | __/__/__ |
| Backup & Recovery | ☐ | ___________ | __/__/__ |
| Testing Complete | ☐ | ___________ | __/__/__ |
| Documentation Updated | ☐ | ___________ | __/__/__ |

---

## 🔗 Related Documentation

- [SECURITY_SETUP_GUIDE.md](./SECURITY_SETUP_GUIDE.md) - Complete security setup
- [AUDIT_REPORT.md](./AUDIT_REPORT.md) - Security audit findings
- [FIXES_SUMMARY.md](./FIXES_SUMMARY.md) - Applied fixes
- [README_MICROSERVICES.md](./README_MICROSERVICES.md) - Architecture overview

---

**Last Updated:** 2025-11-27  
**Version:** 1.0

