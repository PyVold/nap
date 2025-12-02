#!/bin/bash
# Comprehensive License Diagnostic Script
# This script checks all aspects of the license system to identify issues

echo "================================================================================"
echo "COMPREHENSIVE LICENSE DIAGNOSTIC"
echo "================================================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we can use docker compose or docker-compose
if command -v docker-compose &> /dev/null; then
    DC="docker-compose"
elif docker compose version &> /dev/null 2>&1; then
    DC="docker compose"
else
    echo -e "${RED}ERROR: docker-compose not found${NC}"
    echo "Please install Docker Compose first"
    exit 1
fi

echo "1. CHECKING CONTAINERS"
echo "--------------------------------------------------------------------------------"
echo "Container Status:"
$DC ps
echo ""

echo "2. CHECKING DATABASE - ACTIVE LICENSES"
echo "--------------------------------------------------------------------------------"
echo "Active Licenses in Database:"
$DC exec -T database psql -U nap_user -d nap_db -c "
SELECT
    id,
    license_tier,
    is_active,
    activated_at,
    customer_name,
    max_devices,
    max_users,
    max_storage_gb
FROM licenses
ORDER BY activated_at DESC;" 2>/dev/null

active_count=$($DC exec -T database psql -U nap_user -d nap_db -t -c "SELECT COUNT(*) FROM licenses WHERE is_active = true;" 2>/dev/null | tr -d ' ')
echo ""
if [ "$active_count" -eq 0 ]; then
    echo -e "${RED}❌ ERROR: No active license!${NC}"
    echo "Please activate a license through the UI first."
    exit 1
elif [ "$active_count" -gt 1 ]; then
    echo -e "${RED}❌ ERROR: Multiple active licenses detected! ($active_count licenses)${NC}"
    echo "This will cause license switching to fail!"
    echo ""
    echo "To fix, run this SQL command:"
    echo "$DC exec -T database psql -U nap_user -d nap_db -c \\"
    echo "  UPDATE licenses SET is_active = false;"
    echo "  UPDATE licenses SET is_active = true"
    echo "  WHERE activated_at = (SELECT MAX(activated_at) FROM licenses);\\"
    echo ""
    echo -e "${YELLOW}Would you like to fix this now? (y/n)${NC}"
    read -r fix_licenses
    if [ "$fix_licenses" = "y" ]; then
        echo "Fixing licenses..."
        $DC exec -T database psql -U nap_user -d nap_db -c "
            UPDATE licenses SET is_active = false;
            UPDATE licenses SET is_active = true
            WHERE activated_at = (SELECT MAX(activated_at) FROM licenses);
        " 2>/dev/null
        echo -e "${GREEN}✅ Fixed! Only the most recent license is now active.${NC}"
    fi
else
    echo -e "${GREEN}✅ Single active license (correct)${NC}"
fi
echo ""

echo "3. TESTING MODULE-MAPPINGS ENDPOINT"
echo "--------------------------------------------------------------------------------"
mappings_response=$(curl -s http://localhost:3000/license/module-mappings)
if echo "$mappings_response" | grep -q "mappings"; then
    echo -e "${GREEN}✅ Module mappings endpoint is working${NC}"
    echo "Sample mappings:"
    echo "$mappings_response" | python3 -m json.tool 2>/dev/null | head -30
else
    echo -e "${RED}❌ Module mappings endpoint failed!${NC}"
    echo "Response: $mappings_response"
    echo ""
    echo "This means admin-service is not running the updated code."
    echo "You need to rebuild: $DC build admin-service && $DC up -d admin-service"
fi
echo ""

echo "4. TESTING USER MODULES ENDPOINT"
echo "--------------------------------------------------------------------------------"
# First, get the first user ID
user_id=$($DC exec -T database psql -U nap_user -d nap_db -t -c "SELECT id FROM users ORDER BY id LIMIT 1;" 2>/dev/null | tr -d ' ')

if [ -z "$user_id" ]; then
    echo -e "${YELLOW}⚠️  No users found in database${NC}"
else
    echo "Testing for user ID: $user_id"

    # Try to get user modules (this might need authentication)
    user_modules_response=$(curl -s http://localhost:3000/user-management/users/$user_id/modules 2>&1)

    if echo "$user_modules_response" | grep -q "modules"; then
        echo -e "${GREEN}✅ User modules endpoint is working${NC}"
        echo "User modules:"
        echo "$user_modules_response" | python3 -m json.tool 2>/dev/null

        # Check if modules are backend names or frontend names
        if echo "$user_modules_response" | grep -q "manual_audits"; then
            echo -e "${GREEN}✅ Returning backend module names (correct)${NC}"
        elif echo "$user_modules_response" | grep -q "audit"; then
            echo -e "${RED}❌ Returning frontend module names (wrong!)${NC}"
            echo "admin-service needs to be rebuilt with updated code"
        fi
    else
        echo -e "${YELLOW}⚠️  Could not test user modules (might need authentication)${NC}"
        echo "Response: $user_modules_response"
        echo ""
        echo "To test manually from inside container:"
        echo "$DC exec admin-service python3 /app/diagnose_license.py"
    fi
fi
echo ""

echo "5. CHECKING USER GROUP CONFIGURATION"
echo "--------------------------------------------------------------------------------"
echo "First user's group membership:"
$DC exec -T database psql -U nap_user -d nap_db -c "
SELECT
    u.id as user_id,
    u.username,
    u.is_superuser,
    COUNT(ugm.group_id) as group_count
FROM users u
LEFT JOIN user_group_memberships ugm ON u.id = ugm.user_id
GROUP BY u.id, u.username, u.is_superuser
LIMIT 3;" 2>/dev/null
echo ""

echo "Group module access:"
$DC exec -T database psql -U nap_user -d nap_db -c "
SELECT
    g.id as group_id,
    g.name as group_name,
    gma.module_name,
    gma.can_access
FROM user_groups g
LEFT JOIN group_module_access gma ON g.id = gma.group_id
WHERE gma.can_access = true
ORDER BY g.id, gma.module_name
LIMIT 20;" 2>/dev/null
echo ""

echo "6. CHECKING QUOTA USAGE"
echo "--------------------------------------------------------------------------------"
$DC exec -T database psql -U nap_user -d nap_db -c "
SELECT
    'Devices' as resource,
    (SELECT COUNT(*) FROM devices) as current_count,
    (SELECT max_devices FROM licenses WHERE is_active = true LIMIT 1) as max_allowed
UNION ALL
SELECT
    'Users' as resource,
    (SELECT COUNT(*) FROM users) as current_count,
    (SELECT max_users FROM licenses WHERE is_active = true LIMIT 1) as max_allowed
UNION ALL
SELECT
    'Storage (GB)' as resource,
    COALESCE((SELECT SUM(size_bytes) / (1024*1024*1024.0)::numeric(10,2) FROM config_backups), 0) as current_count,
    (SELECT max_storage_gb FROM licenses WHERE is_active = true LIMIT 1) as max_allowed;" 2>/dev/null
echo ""

echo "7. RUNNING INTERNAL DIAGNOSTIC"
echo "--------------------------------------------------------------------------------"
echo "Running diagnose_license.py in admin-service container:"
$DC exec admin-service python3 /app/diagnose_license.py 2>&1 | head -100
echo ""

echo "8. RECOMMENDATIONS"
echo "--------------------------------------------------------------------------------"

# Check if admin-service was built recently
echo "Checking when containers were built..."
admin_image_id=$($DC images -q admin-service 2>/dev/null | head -1)
if [ -n "$admin_image_id" ]; then
    image_created=$(docker inspect "$admin_image_id" --format='{{.Created}}' 2>/dev/null)
    echo "Admin-service image created: $image_created"
    echo ""
fi

echo "Common fixes:"
echo ""
echo "1️⃣  If module-mappings endpoint failed:"
echo "   $DC build admin-service"
echo "   $DC up -d admin-service"
echo "   $DC logs -f admin-service --tail=50"
echo ""

echo "2️⃣  If multiple active licenses:"
echo "   Already shown above in section 2"
echo ""

echo "3️⃣  If user has no groups:"
echo "   Create a user group and assign the user to it"
echo "   Groups control which modules users can access"
echo ""

echo "4️⃣  If frontend still shows wrong menu:"
echo "   - Hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)"
echo "   - Or try incognito/private mode"
echo "   - Check browser console for errors"
echo ""

echo "5️⃣  If quota enforcement doesn't work:"
echo "   - Ensure device-service is also rebuilt"
echo "   - Check API logs when trying to exceed quota"
echo ""

echo "================================================================================"
echo "DIAGNOSTIC COMPLETE"
echo "================================================================================"
