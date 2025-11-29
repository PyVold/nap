# User Permissions and License Enforcement Implementation

## Overview
This document describes the implementation of two critical features:
1. **Admin/Superuser Always Has Full Permissions** - Administrators have unrestricted access to all modules and permissions
2. **License Enforcement** - System blocks access to all modules (except license page) when license is expired or invalid

## Implementation Date
November 29, 2025

---

## 1. Admin/Superuser Full Permissions

### Frontend Changes

#### `/frontend/src/contexts/AuthContext.js`
**Changes Made:**
- Added `isAdmin` flag that checks if user is admin or superuser
- Added `accessInfoLoaded` state to track when user access info has been fetched
- Improved error handling for module/permission fetching
- Added validation to ensure arrays are returned even on errors

**Key Features:**
```javascript
const isAdmin = user?.role === 'admin' || user?.is_superuser === true;
```

#### `/frontend/src/App.js`
**Changes Made:**
- Updated menu filtering logic to always show all menu items for admin users
- Non-admin users only see modules they have explicit access to
- Admin users see all menu items including admin-only sections

**Menu Filtering Logic:**
```javascript
// Admin/superuser always sees all menu items (including admin-only)
if (isAdmin) return true;

// Hide admin panel for non-admins
if (item.adminOnly) return false;
```

#### `/frontend/src/components/UserManagement.jsx`
**Changes Made:**
- Added visual indicator showing admin users have "All Groups (Admin)"
- Added Security icon to superuser badge
- Created new **User Detail Dialog** that shows:
  - Full list of user's permissions
  - Module access rights
  - Group memberships
  - Special messaging for superusers: "ALL PERMISSIONS GRANTED" and "ALL MODULES ACCESSIBLE"

**New Features:**
- Click on Security icon next to any user to see their detailed permissions
- Superusers clearly labeled with 👑 icon and special messaging
- Color-coded chips showing permissions (primary) and modules (secondary)

### Backend

The backend already properly handles admin permissions through `/services/user_group_service.py`:

**`get_user_permissions()` method:**
- Returns all available permissions if user is superuser
- Aggregates permissions from all user groups otherwise

**`get_user_modules()` method:**
- Returns all available modules if user is superuser
- Aggregates module access from all user groups otherwise

---

## 2. License Enforcement System

### Frontend Changes

#### `/frontend/src/components/LicenseGuard.jsx` (NEW FILE)
**Purpose:** Protects routes by checking if license is valid

**Key Features:**
1. **LicenseGuard Component:**
   - Wraps protected routes
   - Shows loading spinner while checking license
   - Redirects to `/license` page if:
     - No license is installed
     - License is expired
     - License is invalid
   - Allows access if license is valid

2. **LicenseWarningBanner Component:**
   - Displays on license page when license is invalid/expired
   - Shows detailed error messages:
     - "No License Activated" - when no license exists
     - "License Expired" - when license has expired (with days since expiry)
     - "License Invalid" - when license is corrupted or invalid
   - Provides guidance to contact sales or activate new license

**Usage:**
```jsx
<Route path="/devices" element={<LicenseGuard><DeviceManagement /></LicenseGuard>} />
```

#### `/frontend/src/App.js`
**Changes Made:**
- Imported `LicenseGuard` component
- Wrapped ALL routes with `<LicenseGuard>` except:
  - `/login` - Login page (not authenticated)
  - `/license` - License management page (must always be accessible)
- License page is always accessible so users can activate/fix license issues

**Route Protection Example:**
```jsx
{/* License page is NOT protected - always accessible */}
<Route path="/license" element={<LicenseManagement />} />

{/* All other routes are protected by LicenseGuard */}
<Route path="/" element={<LicenseGuard><Dashboard /></LicenseGuard>} />
<Route path="/devices" element={<LicenseGuard><DeviceManagement /></LicenseGuard>} />
// ... etc
```

#### `/frontend/src/components/LicenseManagement.jsx`
**Changes Made:**
- Imported `LicenseWarningBanner` component
- Added banner at top of license page to show warning when license is invalid
- Banner appears automatically when license issues are detected

#### `/frontend/src/contexts/LicenseContext.jsx`
**Changes Made:**
- Updated `isLicenseValid` to check both `license.valid` and `license.is_valid` fields
- Ensures compatibility with different API response formats

---

## User Experience Flow

### When License is Valid
1. User logs in successfully
2. LicenseGuard checks license status
3. User can access all authorized modules based on permissions
4. Admin users see all modules
5. Regular users see only modules they have access to

### When License is Expired/Invalid
1. User logs in successfully (authentication still works)
2. User tries to access any module (e.g., `/devices`, `/audits`)
3. LicenseGuard intercepts the request
4. User is redirected to `/license` page
5. Large warning banner appears explaining the issue
6. User must activate valid license to continue
7. All navigation menu items still visible but clicking them redirects to license page

### Admin User Experience
1. Admin users always see ALL menu items
2. Admin users have access to:
   - All regular modules (devices, audits, rules, etc.)
   - Admin-only sections (User Management, Admin Panel)
3. In User Management:
   - Admin users marked with "All Groups (Admin)" badge
   - Clicking Security icon shows "ALL PERMISSIONS GRANTED" message
   - Clearly labeled as 👑 Administrator/Superuser

---

## Testing Checklist

### License Enforcement
- [ ] Access module without license - should redirect to /license
- [ ] Access module with expired license - should redirect to /license
- [ ] Access module with valid license - should load normally
- [ ] License page accessible without license - should always work
- [ ] Warning banner shows on license page when invalid
- [ ] Warning banner does NOT show when license is valid

### Admin Permissions
- [ ] Admin user sees all menu items
- [ ] Regular user only sees authorized modules
- [ ] Admin badge shows "All Groups (Admin)" in user list
- [ ] Clicking Security icon on admin user shows "ALL PERMISSIONS GRANTED"
- [ ] Clicking Security icon on admin user shows "ALL MODULES ACCESSIBLE"
- [ ] Regular user shows actual permissions and modules

### User Management
- [ ] View user details shows permissions correctly
- [ ] Superuser users show special badges and messaging
- [ ] Regular users show group-based permissions
- [ ] Can create/edit/delete users
- [ ] Can create/edit/delete groups
- [ ] Can manage group memberships

---

## API Endpoints Used

### Authentication & User Info
- `POST /login` - User authentication
- `GET /me` - Get current user info

### User Management
- `GET /user-management/users` - Get all users
- `GET /user-management/users/{id}/permissions` - Get user permissions
- `GET /user-management/users/{id}/modules` - Get user module access
- `GET /user-management/groups` - Get all groups

### License Management
- `GET /license/status` - Get current license status
- `POST /license/activate` - Activate new license
- `POST /license/deactivate` - Deactivate license

---

## Configuration

### No Configuration Required
The system automatically:
- Detects admin/superuser status from user object
- Checks license validity on every protected route access
- Caches license status to avoid repeated API calls
- Handles license errors gracefully

### Customization Options

**To add new protected routes:**
```jsx
<Route path="/new-module" element={<LicenseGuard><NewModule /></LicenseGuard>} />
```

**To add module to admin access list:**
Edit `/frontend/src/App.js` - add to `allMenuItems`:
```javascript
{ text: 'New Module', icon: <Icon />, path: '/new-module', module: 'new_module' }
```

**To add new permission:**
Edit `/models/user_group.py` - add to `Permission` class:
```python
NEW_PERMISSION = "new_permission"
```

---

## Security Considerations

### Admin Access
- Admin/superuser status is verified server-side via JWT token
- Frontend only uses this for UI display
- Backend enforces actual permissions via dependency injection
- All API endpoints check permissions before allowing operations

### License Enforcement
- License validation happens on backend
- Frontend guards are for UX only - they improve user experience
- Backend APIs should also validate license before processing requests
- License status cached in context to reduce API calls

### Authentication Flow
1. User logs in → receives JWT token
2. Token includes user role and superuser flag
3. Frontend displays UI based on role
4. Backend validates token and permissions on every request
5. License checked separately from authentication

---

## Troubleshooting

### Issue: Admin user can't see all menus
**Solution:** Verify:
- User has `is_superuser: true` or `role: 'admin'` in token
- `isAdmin` flag is true in AuthContext
- Menu filtering logic checks `isAdmin` first

### Issue: License page shows warning but license is valid
**Solution:** Check:
- License API returns `valid: true` or `is_valid: true`
- License object is not null
- `days_until_expiry` is positive number

### Issue: User redirected to license page constantly
**Solution:** Verify:
- License API endpoint is accessible
- License database record exists
- License `valid` field is true
- License hasn't expired

### Issue: User permissions not loading
**Solution:** Check:
- User has `user_id` in stored user object
- `/user-management/users/{id}/permissions` endpoint works
- Backend returns array (not error)
- AuthContext `accessInfoLoaded` becomes true

---

## Future Enhancements

### Recommended Additions
1. **Backend License Middleware** - Add middleware to all API routes that checks license validity
2. **License Expiry Notifications** - Email alerts 30/15/7/1 days before expiry
3. **Usage Tracking** - Track which modules are being used to help with license decisions
4. **Audit Log** - Log all admin actions for security compliance
5. **Role-Based Dashboard** - Show different dashboard for admin vs regular users
6. **Permission Templates** - Quick permission sets (Read-Only, Power User, etc.)

### Nice-to-Have Features
- Export user permissions to CSV
- Bulk user import from CSV/LDAP
- Two-factor authentication for admin users
- Session timeout settings per user role
- IP whitelist for admin access

---

## Summary

### What Was Implemented ✅

1. **Admin Full Access:**
   - Admins always see all menus
   - Admins marked with special badges
   - User detail view shows "ALL PERMISSIONS GRANTED" for admins
   - Frontend menu filtering respects admin status

2. **License Enforcement:**
   - Created LicenseGuard component
   - All routes except /license wrapped with guard
   - Automatic redirect when license invalid/expired
   - Warning banner on license page
   - User-friendly error messages

3. **Enhanced User Management:**
   - New user detail dialog showing all permissions
   - Visual indicators for admin users
   - Better group membership display
   - Clear permission and module listings

### Files Modified
- `/frontend/src/contexts/AuthContext.js`
- `/frontend/src/contexts/LicenseContext.jsx`
- `/frontend/src/App.js`
- `/frontend/src/components/UserManagement.jsx`
- `/frontend/src/components/LicenseManagement.jsx`

### Files Created
- `/frontend/src/components/LicenseGuard.jsx`

### Backend (No Changes Required)
The backend already properly handles admin permissions through the existing `UserGroupService`. No backend changes were needed.

---

## Support

For questions or issues:
1. Check this documentation first
2. Review the console for error messages
3. Verify API endpoints are returning expected data
4. Check user object structure in localStorage
5. Verify license status via API: `GET /license/status`
