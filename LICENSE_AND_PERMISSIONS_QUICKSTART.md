# License Enforcement & Admin Permissions - Quick Reference

## 🎯 What Was Done

### 1. Admin Users Now Have Full Access ✅
- **Where:** User Management page
- **What:** Admin/superuser users are clearly marked and have access to all permissions and modules
- **Visual Indicators:**
  - Badge: "All Groups (Admin)" in user list
  - Security icon next to each user - click to see detailed permissions
  - Admin detail view shows "👑 Administrator / Superuser"
  - "ALL PERMISSIONS GRANTED" and "ALL MODULES ACCESSIBLE" alerts

### 2. License Enforcement Active ✅
- **Where:** All pages except /license
- **What:** System blocks access when license is expired or invalid
- **Behavior:**
  - Valid license → Normal access to authorized modules
  - No license → Redirect to /license page
  - Expired license → Redirect to /license page with warning banner
  - Invalid license → Redirect to /license page with error message

---

## 🚀 Quick Test Guide

### Test Admin Permissions
1. Log in as admin user (role='admin' or is_superuser=true)
2. Check that ALL menu items are visible (including User Management, Admin Panel)
3. Go to User Management
4. Click Security icon 🔒 next to your admin user
5. Verify it says "ALL PERMISSIONS GRANTED" and "ALL MODULES ACCESSIBLE"

### Test License Enforcement
1. **With Valid License:**
   - Log in and access any module → Should work normally
   
2. **Without License:**
   - Remove/deactivate license
   - Try to access /devices or /audits
   - Should automatically redirect to /license page
   - Should see warning: "No License Activated"
   
3. **With Expired License:**
   - Use expired license
   - Try to access any module
   - Should redirect to /license page
   - Should see warning: "License Expired" with days count

### Test Regular User (Non-Admin)
1. Log in as regular user (not admin)
2. Verify you only see modules you have access to
3. Go to User Management (if you have access)
4. Click Security icon on your user
5. Should see actual list of permissions (not "ALL PERMISSIONS")

---

## 📋 Key Files Modified

### Frontend
```
/frontend/src/
├── contexts/
│   ├── AuthContext.js          (Added isAdmin flag, improved error handling)
│   └── LicenseContext.jsx      (Fixed isLicenseValid field)
├── components/
│   ├── LicenseGuard.jsx        (NEW - Route protection component)
│   ├── LicenseManagement.jsx  (Added warning banner)
│   └── UserManagement.jsx     (Enhanced with permission details dialog)
└── App.js                      (Added LicenseGuard to all routes, admin menu logic)
```

### Backend
- No changes needed! Already working correctly ✅

---

## 🔧 How It Works

### Admin Detection
```javascript
// In AuthContext.js
const isAdmin = user?.role === 'admin' || user?.is_superuser === true;

// In App.js menu filtering
if (isAdmin) return true;  // Admin sees everything
```

### License Guard
```javascript
// Wraps protected routes
<Route path="/devices" element={
  <LicenseGuard>
    <DeviceManagement />
  </LicenseGuard>
} />

// License page is NOT protected
<Route path="/license" element={<LicenseManagement />} />
```

### Flow Diagram
```
User logs in
     ↓
AuthContext checks: isAdmin?
     ↓
   YES → Show all menus, full access
   NO  → Show only authorized modules
     ↓
User clicks menu item
     ↓
LicenseGuard checks: License valid?
     ↓
   YES → Load component
   NO  → Redirect to /license page
```

---

## 🎨 User Experience

### Admin User
```
Login → See all menus → Full access to everything
                    ↓
         User Management shows:
         "👑 Administrator / Superuser"
         "ALL PERMISSIONS GRANTED"
         "ALL MODULES ACCESSIBLE"
```

### Regular User with Valid License
```
Login → See authorized menus → Access allowed modules
                            ↓
              User Management shows:
              List of specific permissions
              List of specific modules
              Group memberships
```

### Any User WITHOUT Valid License
```
Login → Click any module → [BLOCKED] → Redirect to /license
                                    ↓
                        Big warning banner:
                        "⚠️ License Expired/Invalid"
                        "Activate valid license to continue"
```

---

## 🛠️ Common Scenarios

### Scenario 1: New Admin User
**Problem:** Created admin user but they don't see all menus
**Solution:**
- Ensure user has `is_superuser: true` in database
- OR ensure user has `role: 'admin'`
- Logout and login again to refresh token

### Scenario 2: License Expired
**Problem:** Users locked out, can't access anything
**Solution:**
1. Users can still login
2. They get redirected to /license page
3. Admin activates new license key
4. Users refresh page → access restored

### Scenario 3: Check User Permissions
**Problem:** User says they can't access a module
**Solution:**
1. Go to User Management (as admin)
2. Find the user in the list
3. Click Security icon 🔒 next to their name
4. See exactly what permissions and modules they have
5. Add them to appropriate group or mark as superuser

---

## ⚙️ API Endpoints Reference

### License APIs
```bash
# Check license status
GET /license/status

# Activate new license
POST /license/activate
Body: { "license_key": "..." }

# Deactivate license
POST /license/deactivate
```

### User Permission APIs
```bash
# Get all users
GET /user-management/users

# Get user's permissions
GET /user-management/users/{user_id}/permissions

# Get user's module access
GET /user-management/users/{user_id}/modules

# Get all available permissions
GET /user-management/permissions
```

---

## 📊 Verification Checklist

After deployment, verify:

- [ ] Admin user sees ALL menus (including admin-only)
- [ ] Regular user sees ONLY their authorized modules
- [ ] Clicking Security icon on admin shows "ALL PERMISSIONS GRANTED"
- [ ] Clicking Security icon on regular user shows actual permissions
- [ ] With valid license: All modules accessible
- [ ] Without license: Redirects to /license page
- [ ] With expired license: Redirects to /license page
- [ ] License page shows appropriate warning banner
- [ ] License page always accessible (even without license)
- [ ] User can activate new license from license page

---

## 🆘 Troubleshooting

### "Admin user can't see all menus"
1. Check browser console for `isAdmin` value
2. Check localStorage for user object: `localStorage.getItem('auth_user')`
3. Verify user has `is_superuser: true` or `role: 'admin'`
4. Clear cache and login again

### "License page keeps warning even with valid license"
1. Check API response: `GET /license/status`
2. Verify response has `valid: true` or `is_valid: true`
3. Check `days_until_expiry` is positive number
4. Refresh license context: Click refresh button on license page

### "Users stuck in redirect loop"
1. Check if license API is accessible
2. Verify LicenseContext is loading properly
3. Check browser console for errors
4. Ensure `/license` route is NOT wrapped in LicenseGuard

---

## 📝 Summary

**COMPLETED FEATURES:**

✅ Admin users always have full permissions (shown in UI)
✅ Admin users see all menu items
✅ License enforcement blocks access when expired/invalid
✅ License page always accessible
✅ Warning banners on license page
✅ User detail view showing permissions and modules
✅ Visual badges for admin users
✅ Automatic redirect to license page when needed

**FILES MODIFIED:** 6 files
**FILES CREATED:** 1 file (LicenseGuard.jsx)
**BACKEND CHANGES:** None required

**TESTING:** Manual testing recommended for all scenarios above

---

For detailed technical documentation, see: `USER_PERMISSIONS_AND_LICENSE_ENFORCEMENT.md`
