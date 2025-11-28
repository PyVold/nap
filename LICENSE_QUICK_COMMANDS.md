# License System - Quick Commands Reference

**For**: When you need to quickly generate/manage licenses
**Time**: < 1 minute per command

---

## 🔑 Generate Keys (One-Time Setup)

```bash
# Step 1: Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Step 2: Generate secret salt
python -c "import secrets; print(secrets.token_hex(32))"

# Step 3: Add to .env file
echo "LICENSE_ENCRYPTION_KEY=<key_from_step1>" >> .env
echo "LICENSE_SECRET_SALT=<salt_from_step2>" >> .env
```

---

## 📝 Generate Licenses

### Starter License (10 devices, 2 users)
```bash
python scripts/generate_license.py \
  --customer "Company Name" \
  --email "customer@company.com" \
  --tier starter \
  --days 365
```

### Professional License (100 devices, 10 users)
```bash
python scripts/generate_license.py \
  --customer "Company Name" \
  --email "customer@company.com" \
  --tier professional \
  --days 365 \
  --order "ORD-2025-001"
```

### Enterprise License (Unlimited)
```bash
python scripts/generate_license.py \
  --customer "Company Name" \
  --email "customer@company.com" \
  --tier enterprise \
  --days 365 \
  --order "ORD-2025-001"
```

### Custom Quotas
```bash
python scripts/generate_license.py \
  --customer "Company Name" \
  --email "customer@company.com" \
  --tier professional \
  --days 365 \
  --devices 500 \
  --users 25 \
  --storage 100
```

### Trial License (30 days)
```bash
python scripts/generate_license.py \
  --customer "Trial User" \
  --email "trial@company.com" \
  --tier professional \
  --days 30 \
  --notes "Trial license - expires in 30 days"
```

---

## 📥 Import License to Your Database

```bash
# Import generated license
python scripts/import_license.py license_output/license_abc123.json
```

---

## 🧪 Test License via API

### Activate License
```bash
curl -X POST http://localhost:3000/license/activate \
  -H "Content-Type: application/json" \
  -d '{"license_key": "YOUR_LICENSE_KEY_HERE"}'
```

### Check License Status
```bash
curl http://localhost:3000/license/status | jq
```

### Deactivate License
```bash
curl -X POST http://localhost:3000/license/deactivate
```

---

## 📊 Common License Scenarios

### Scenario 1: New Customer Purchase
```bash
# Generate license
python scripts/generate_license.py \
  --customer "Acme Corp" \
  --email "admin@acme.com" \
  --tier professional \
  --days 365 \
  --order "ORD-2025-042"

# Output: license_output/license_abc123.txt
# Email this file to customer
```

### Scenario 2: License Renewal
```bash
# Generate new license with extended date
python scripts/generate_license.py \
  --customer "Acme Corp" \
  --email "admin@acme.com" \
  --tier professional \
  --days 365 \
  --order "ORD-2025-143" \
  --notes "Renewal for ORD-2025-042"

# Email new license to customer
# Customer replaces old license with new one
```

### Scenario 3: Upgrade Plan
```bash
# Generate higher tier license
python scripts/generate_license.py \
  --customer "Acme Corp" \
  --email "admin@acme.com" \
  --tier enterprise \
  --days 365 \
  --order "ORD-2025-144" \
  --notes "Upgraded from Professional to Enterprise"
```

### Scenario 4: Temporary License Extension
```bash
# Generate 90-day extension
python scripts/generate_license.py \
  --customer "Acme Corp" \
  --email "admin@acme.com" \
  --tier professional \
  --days 90 \
  --notes "90-day extension while renewal is processed"
```

---

## 🔧 Maintenance Commands

### List All Licenses in Database
```bash
# Connect to database
sqlite3 network_audit.db "SELECT id, customer_name, license_tier, expires_at, is_active FROM licenses;"
```

### Deactivate Expired Licenses
```bash
sqlite3 network_audit.db "UPDATE licenses SET is_active=0 WHERE expires_at < datetime('now');"
```

### Check License Validation Logs
```bash
sqlite3 network_audit.db "SELECT * FROM license_validation_logs ORDER BY checked_at DESC LIMIT 10;"
```

---

## 📧 Email Template for Customers

```text
Subject: Your Network Audit Platform License

Dear [Customer Name],

Thank you for your purchase of the Network Audit Platform!

📋 LICENSE DETAILS
Plan: [Professional/Enterprise]
Devices: [100/Unlimited]
Users: [10/Unlimited]
Valid Until: [Date]

🔑 LICENSE KEY
[PASTE LICENSE KEY HERE - LONG STRING]

✅ ACTIVATION STEPS
1. Log into your Network Audit Platform
2. Click on "License" in the sidebar
3. Click "Activate License" button
4. Paste the license key above
5. Click "Activate"

That's it! All features are now available.

📞 SUPPORT
Need help? Contact us:
- Email: support@yourcompany.com
- Phone: [Your Phone]

We're here to help!

Best regards,
[Your Name]
[Your Company]
```

---

## 🚨 Troubleshooting

### Problem: "LICENSE_ENCRYPTION_KEY not set"
```bash
# Solution: Set environment variable
export LICENSE_ENCRYPTION_KEY="your_key_here"

# Or add to .env file
echo "LICENSE_ENCRYPTION_KEY=your_key_here" >> .env
```

### Problem: "License activation failed - invalid"
```bash
# Check if encryption keys match on both sides
# Your machine (generation): Check .env
# Customer deployment: Check their .env

# Keys MUST be identical!
```

### Problem: "License expired"
```bash
# Generate new license with future date
python scripts/generate_license.py \
  --customer "Customer" \
  --email "customer@email.com" \
  --tier professional \
  --days 365
```

### Problem: Customer can't activate license
```bash
# Test license validation locally first
python -c "
from scripts.generate_license import LicenseGenerator
lg = LicenseGenerator()
result = lg.validate_license('LICENSE_KEY_HERE')
print(result)
"
```

---

## 📊 License Analytics

### Count Active Licenses
```bash
sqlite3 network_audit.db "SELECT COUNT(*) FROM licenses WHERE is_active=1;"
```

### Revenue by Tier
```bash
sqlite3 network_audit.db "
SELECT 
  license_tier, 
  COUNT(*) as count,
  CASE 
    WHEN license_tier='starter' THEN COUNT(*) * 49
    WHEN license_tier='professional' THEN COUNT(*) * 199
    WHEN license_tier='enterprise' THEN COUNT(*) * 999
  END as monthly_revenue
FROM licenses 
WHERE is_active=1 
GROUP BY license_tier;
"
```

### Licenses Expiring Soon (30 days)
```bash
sqlite3 network_audit.db "
SELECT customer_name, customer_email, expires_at 
FROM licenses 
WHERE is_active=1 
AND expires_at BETWEEN datetime('now') AND datetime('now', '+30 days')
ORDER BY expires_at;
"
```

---

## 🎯 Quick Checklist

### Before Generating First License:
- [ ] Encryption keys generated
- [ ] Keys added to .env
- [ ] Database migration applied
- [ ] Test license generated successfully
- [ ] Test license validated successfully

### Before Sending to Customer:
- [ ] License generated with correct tier
- [ ] Expiration date verified (1 year = 365 days)
- [ ] Customer name spelled correctly
- [ ] Email address verified
- [ ] Order ID added for tracking
- [ ] License key copied to email

### After Customer Activates:
- [ ] Verify license shows in their UI
- [ ] Check all modules visible
- [ ] Verify quotas displayed correctly
- [ ] Confirm expiration date shown
- [ ] Test a premium feature works

---

## 💡 Pro Tips

### Tip 1: Keep License Records
```bash
# Store all generated licenses in organized folders
mkdir -p licenses/2025/november
mv license_output/* licenses/2025/november/
```

### Tip 2: Automate Renewal Reminders
```bash
# Add to crontab to check daily
0 9 * * * sqlite3 /path/to/network_audit.db "
SELECT customer_name, customer_email, expires_at 
FROM licenses 
WHERE expires_at = date('now', '+30 days')" | mail -s "Licenses Expiring in 30 Days" sales@yourcompany.com
```

### Tip 3: Create License Templates
```bash
# Save common commands to shell scripts
cat > generate_pro_license.sh << 'EOF'
#!/bin/bash
python scripts/generate_license.py \
  --customer "$1" \
  --email "$2" \
  --tier professional \
  --days 365 \
  --order "$3"
EOF

chmod +x generate_pro_license.sh

# Usage: ./generate_pro_license.sh "Company" "email@company.com" "ORD-123"
```

---

## 🔐 Security Best Practices

1. **Never commit keys to git**
   ```bash
   # Add to .gitignore
   echo ".env" >> .gitignore
   echo "license_output/" >> .gitignore
   ```

2. **Keep keys secure**
   - Store in password manager
   - Use environment variables
   - Rotate keys annually

3. **Track license generation**
   - Keep log of all generated licenses
   - Link to orders/invoices
   - Monitor for suspicious activation patterns

---

## 📞 Quick Contact Template

```text
Customer needs: [License renewal/Upgrade/New license]
Customer: [Name]
Email: [Email]
Current tier: [Starter/Pro/Enterprise]
Request: [Details]

Command to run:
python scripts/generate_license.py \
  --customer "[Name]" \
  --email "[Email]" \
  --tier [tier] \
  --days 365 \
  --order "[ORDER-ID]"
```

---

**Keep this file handy!** Bookmark it for quick reference when managing licenses.

**File Location**: `/workspace/LICENSE_QUICK_COMMANDS.md`
