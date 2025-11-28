# 🚀 License System - 5 Minute Quickstart

## ✅ Everything is Already Set Up!

The license system has been fully integrated. Here's how to use it immediately:

---

## 🎯 Generate Your First License (30 seconds)

```bash
cd /workspace

python3 scripts/generate_license.py \
  --customer "Test Company" \
  --email "admin@test.com" \
  --tier professional \
  --days 365
```

**Output**: A file in `license_output/license_admin_XXXXXX.txt`

Open that file and copy the long encrypted license key (starts with `gAAAA...`).

---

## 🌐 Activate in the Frontend (1 minute)

1. **Start your application**:
   ```bash
   # Monolith
   python3 main.py
   
   # OR Microservices
   docker-compose up
   ```

2. **Open your browser**: `http://localhost:3000` (or your port)

3. **Login** with your credentials

4. **Click "License"** in the sidebar (look for the 🔑 key icon)

5. **Click "Activate License"** button

6. **Paste the license key** from step 1

7. **Click "Activate"**

**Done!** 🎉

---

## 🎨 What You'll See

### License Dashboard Shows:

✅ **Plan**: PROFESSIONAL  
✅ **Status**: ACTIVE  
✅ **Expires In**: 365 days  

### Usage Quotas:
- 📱 **Devices**: 0 / 100 (0%)
- 👥 **Users**: 0 / 10 (0%)
- 💾 **Storage**: 0 / 50 GB

### Activated Modules (with green checkmarks):
- ✅ Device Management
- ✅ Manual Audits
- ✅ Scheduled Audits
- ✅ Basic Audit Rules
- ✅ Rule Templates
- ✅ API Access
- ✅ Config Backups
- ✅ Drift Detection
- ✅ Webhook Notifications
- ✅ Device Groups
- ✅ Device Discovery

### Locked Modules (upgrade needed):
- ❌ Workflow Automation (Enterprise)
- ❌ Network Topology (Enterprise)
- ❌ AI Features (Enterprise)

---

## 💼 Generate Licenses for Customers

### Starter ($49/mo)
```bash
python3 scripts/generate_license.py \
  --customer "Customer Name" \
  --email "customer@example.com" \
  --tier starter \
  --days 365
```

**Includes**: 10 devices, 2 users, 5 GB, basic features

### Professional ($199/mo)
```bash
python3 scripts/generate_license.py \
  --customer "Customer Name" \
  --email "customer@example.com" \
  --tier professional \
  --days 365
```

**Includes**: 100 devices, 10 users, 50 GB, all professional features

### Enterprise ($999/mo)
```bash
python3 scripts/generate_license.py \
  --customer "Customer Name" \
  --email "customer@example.com" \
  --tier enterprise \
  --days 365
```

**Includes**: Unlimited devices, users, storage, ALL features

---

## 🔑 Custom Quotas

Override default quotas:

```bash
python3 scripts/generate_license.py \
  --customer "Special Customer" \
  --email "special@customer.com" \
  --tier professional \
  --days 365 \
  --devices 500 \
  --users 50 \
  --storage 200
```

---

## 📧 Send to Customer

1. Find the generated file: `license_output/license_CUSTOMER_TIMESTAMP.txt`
2. Email it to the customer
3. Customer activates through UI
4. Done! 🎉

---

## 🛠️ Test API Directly

```bash
# 1. Activate license
curl -X POST http://localhost:3000/license/activate \
  -H "Content-Type: application/json" \
  -d '{"license_key": "YOUR_KEY_HERE"}'

# 2. Check status
curl http://localhost:3000/license/status

# 3. Check if module is enabled
curl http://localhost:3000/license/check-module/scheduled_audits

# 4. View all tiers
curl http://localhost:3000/license/tiers
```

---

## 📊 License Tiers at a Glance

| Feature | Starter | Professional | Enterprise |
|---------|---------|--------------|------------|
| Devices | 10 | 100 | ∞ |
| Users | 2 | 10 | ∞ |
| Storage | 5 GB | 50 GB | ∞ |
| Manual Audits | ✅ | ✅ | ✅ |
| Scheduled Audits | ❌ | ✅ | ✅ |
| API Access | ❌ | ✅ | ✅ |
| Config Backups | ❌ | ✅ | ✅ |
| Workflows | ❌ | ❌ | ✅ |
| AI Features | ❌ | ❌ | ✅ |
| Topology Maps | ❌ | ❌ | ✅ |

---

## ✅ What's Already Done

- ✅ Database tables created
- ✅ Backend API integrated (monolith + microservices)
- ✅ Frontend UI fully integrated
- ✅ License context added
- ✅ Routes and menu added
- ✅ Encryption keys generated
- ✅ `.env` file configured
- ✅ Generation script ready

---

## 📚 More Documentation

- **LICENSE_INTEGRATION_COMPLETE.md** - Full integration guide
- **LICENSE_SYSTEM_README.md** - System overview
- **LICENSE_QUICK_COMMANDS.md** - Command reference

---

## 🎉 You're Ready!

The license system is **100% complete and ready to use right now**.

Just generate a license and activate it! 🚀

---

**Created**: November 28, 2025  
**Status**: ✅ Complete
