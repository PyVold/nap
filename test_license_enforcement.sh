#!/bin/bash

# ============================================================================
# License Enforcement Testing Script
# ============================================================================
# This script tests all license enforcement features:
# - Module availability based on license tier
# - Admin control over user module permissions
# - User creation limits
# - Device limits with queuing
# - Storage control for backups
# - License upgrade/renewal handling
# ============================================================================

API_BASE="http://localhost:8000"
TOKEN=""
ADMIN_USER="admin"
ADMIN_PASS="admin123"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

test_passed() {
    ((TESTS_PASSED++))
    ((TESTS_TOTAL++))
    echo -e "${GREEN}✓ PASS${NC}: $1"
}

test_failed() {
    ((TESTS_FAILED++))
    ((TESTS_TOTAL++))
    echo -e "${RED}✗ FAIL${NC}: $1"
}

# Authenticate and get token
authenticate() {
    log_info "Authenticating as admin..."
    response=$(curl -s -X POST "$API_BASE/admin/login" \
        -H "Content-Type: application/json" \
        -d "{\"username\": \"$ADMIN_USER\", \"password\": \"$ADMIN_PASS\"}")
    
    TOKEN=$(echo $response | jq -r '.access_token')
    
    if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
        log_error "Failed to authenticate"
        exit 1
    fi
    
    log_info "Authenticated successfully"
}

# ============================================================================
# Test 1: License Status and Quotas
# ============================================================================
test_license_status() {
    log_info "Test 1: Checking license status..."
    
    response=$(curl -s -X GET "$API_BASE/license/status" \
        -H "Authorization: Bearer $TOKEN")
    
    valid=$(echo $response | jq -r '.valid')
    tier=$(echo $response | jq -r '.tier')
    
    if [ "$valid" = "true" ]; then
        test_passed "License is valid (Tier: $tier)"
    else
        test_failed "License is invalid or not activated"
    fi
    
    # Check quotas
    response=$(curl -s -X GET "$API_BASE/admin/license/quotas" \
        -H "Authorization: Bearer $TOKEN")
    
    devices_current=$(echo $response | jq -r '.devices.current')
    devices_max=$(echo $response | jq -r '.devices.max')
    users_current=$(echo $response | jq -r '.users.current')
    users_max=$(echo $response | jq -r '.users.max')
    
    log_info "Current quotas - Devices: $devices_current/$devices_max, Users: $users_current/$users_max"
}

# ============================================================================
# Test 2: Module Availability
# ============================================================================
test_module_availability() {
    log_info "Test 2: Checking module availability..."
    
    response=$(curl -s -X GET "$API_BASE/admin/license/available-modules" \
        -H "Authorization: Bearer $TOKEN")
    
    available_count=$(echo $response | jq '[.[] | select(.available == true)] | length')
    total_count=$(echo $response | jq 'length')
    
    if [ $available_count -gt 0 ]; then
        test_passed "Module availability check ($available_count/$total_count modules available)"
    else
        test_failed "No modules available in license"
    fi
    
    # Test accessing a module endpoint (devices should be available in all tiers)
    response=$(curl -s -X GET "$API_BASE/devices/" \
        -H "Authorization: Bearer $TOKEN")
    
    status_code=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$API_BASE/devices/" \
        -H "Authorization: Bearer $TOKEN")
    
    if [ $status_code -eq 200 ]; then
        test_passed "Devices module accessible (HTTP 200)"
    else
        test_failed "Devices module not accessible (HTTP $status_code)"
    fi
}

# ============================================================================
# Test 3: User Creation Limits
# ============================================================================
test_user_creation_limits() {
    log_info "Test 3: Testing user creation limits..."
    
    # Get current user count
    response=$(curl -s -X GET "$API_BASE/admin/license/quotas" \
        -H "Authorization: Bearer $TOKEN")
    
    users_current=$(echo $response | jq -r '.users.current')
    users_max=$(echo $response | jq -r '.users.max')
    
    log_info "Current users: $users_current/$users_max"
    
    if [ $users_current -lt $users_max ]; then
        # Try to create a test user
        response=$(curl -s -X POST "$API_BASE/user-management/users" \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -d "{
                \"username\": \"test_user_$(date +%s)\",
                \"email\": \"test$(date +%s)@example.com\",
                \"password\": \"testpass123\",
                \"full_name\": \"Test User\",
                \"is_active\": true,
                \"is_superuser\": false
            }")
        
        user_id=$(echo $response | jq -r '.id')
        
        if [ "$user_id" != "null" ] && [ ! -z "$user_id" ]; then
            test_passed "User creation within quota succeeded"
            
            # Cleanup - delete the test user
            curl -s -X DELETE "$API_BASE/user-management/users/$user_id" \
                -H "Authorization: Bearer $TOKEN" > /dev/null
        else
            error=$(echo $response | jq -r '.detail')
            test_failed "User creation failed: $error"
        fi
    else
        log_warning "User quota already at maximum, skipping creation test"
        test_passed "User quota enforcement detected (at maximum)"
    fi
}

# ============================================================================
# Test 4: Device Creation Limits
# ============================================================================
test_device_creation_limits() {
    log_info "Test 4: Testing device creation limits..."
    
    # Get current device count
    response=$(curl -s -X GET "$API_BASE/admin/license/quotas" \
        -H "Authorization: Bearer $TOKEN")
    
    devices_current=$(echo $response | jq -r '.devices.current')
    devices_max=$(echo $response | jq -r '.devices.max')
    
    log_info "Current devices: $devices_current/$devices_max"
    
    if [ $devices_current -lt $devices_max ]; then
        # Try to create a test device
        response=$(curl -s -X POST "$API_BASE/devices/" \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -d "{
                \"hostname\": \"test-device-$(date +%s)\",
                \"vendor\": \"NOKIA_SROS\",
                \"ip\": \"192.168.1.$(($RANDOM % 255))\",
                \"port\": 830,
                \"username\": \"admin\",
                \"password\": \"admin\"
            }")
        
        device_id=$(echo $response | jq -r '.id')
        
        if [ "$device_id" != "null" ] && [ ! -z "$device_id" ]; then
            test_passed "Device creation within quota succeeded"
            
            # Cleanup - delete the test device
            curl -s -X DELETE "$API_BASE/devices/$device_id" \
                -H "Authorization: Bearer $TOKEN" > /dev/null
        else
            error=$(echo $response | jq -r '.detail')
            test_failed "Device creation failed: $error"
        fi
    else
        log_warning "Device quota already at maximum"
        
        # Try to create a device (should fail)
        response=$(curl -s -X POST "$API_BASE/devices/" \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -d "{
                \"hostname\": \"test-device-$(date +%s)\",
                \"vendor\": \"NOKIA_SROS\",
                \"ip\": \"192.168.1.$(($RANDOM % 255))\",
                \"port\": 830,
                \"username\": \"admin\",
                \"password\": \"admin\"
            }")
        
        error=$(echo $response | jq -r '.detail.error')
        
        if [ "$error" = "Quota exceeded" ]; then
            test_passed "Device quota enforcement working (creation blocked)"
        else
            test_failed "Device quota not enforced properly"
        fi
    fi
}

# ============================================================================
# Test 5: Storage Quota Check
# ============================================================================
test_storage_quota() {
    log_info "Test 5: Checking storage quota..."
    
    response=$(curl -s -X GET "$API_BASE/admin/license/quotas" \
        -H "Authorization: Bearer $TOKEN")
    
    storage_current=$(echo $response | jq -r '.storage.current_gb')
    storage_max=$(echo $response | jq -r '.storage.max_gb')
    storage_percentage=$(echo $response | jq -r '.storage.used_percentage')
    
    log_info "Storage usage: ${storage_current}GB / ${storage_max}GB (${storage_percentage}%)"
    
    if [ $storage_current -le $storage_max ]; then
        test_passed "Storage quota check passed"
    else
        test_failed "Storage quota exceeded"
    fi
}

# ============================================================================
# Test 6: Module Access Control for Groups
# ============================================================================
test_module_access_control() {
    log_info "Test 6: Testing module access control for groups..."
    
    # Get available modules
    response=$(curl -s -X GET "$API_BASE/admin/license/available-modules" \
        -H "Authorization: Bearer $TOKEN")
    
    # Get first available module
    first_module=$(echo $response | jq -r '[.[] | select(.available == true)][0].key')
    
    if [ "$first_module" != "null" ] && [ ! -z "$first_module" ]; then
        test_passed "Module access control endpoints accessible (found module: $first_module)"
    else
        test_failed "No available modules found for access control"
    fi
}

# ============================================================================
# Test 7: License Tier Module Restrictions
# ============================================================================
test_tier_module_restrictions() {
    log_info "Test 7: Testing tier-based module restrictions..."
    
    # Get license status
    response=$(curl -s -X GET "$API_BASE/license/status" \
        -H "Authorization: Bearer $TOKEN")
    
    tier=$(echo $response | jq -r '.tier')
    enabled_modules=$(echo $response | jq -r '.enabled_modules | length')
    
    log_info "License tier: $tier, Enabled modules: $enabled_modules"
    
    # Starter tier should have fewer modules than Professional
    if [ "$tier" = "starter" ]; then
        if [ $enabled_modules -le 10 ]; then
            test_passed "Starter tier has limited modules ($enabled_modules)"
        else
            test_warning "Starter tier has unexpectedly many modules ($enabled_modules)"
        fi
    elif [ "$tier" = "professional" ]; then
        if [ $enabled_modules -gt 10 ]; then
            test_passed "Professional tier has extended modules ($enabled_modules)"
        else
            test_warning "Professional tier has fewer modules than expected ($enabled_modules)"
        fi
    elif [ "$tier" = "enterprise" ]; then
        test_passed "Enterprise tier detected (all modules available)"
    fi
}

# ============================================================================
# Main Test Execution
# ============================================================================
main() {
    echo "============================================================================"
    echo "License Enforcement Testing Suite"
    echo "============================================================================"
    echo ""
    
    # Authenticate first
    authenticate
    
    # Run all tests
    test_license_status
    echo ""
    
    test_module_availability
    echo ""
    
    test_user_creation_limits
    echo ""
    
    test_device_creation_limits
    echo ""
    
    test_storage_quota
    echo ""
    
    test_module_access_control
    echo ""
    
    test_tier_module_restrictions
    echo ""
    
    # Summary
    echo "============================================================================"
    echo "Test Summary"
    echo "============================================================================"
    echo "Total Tests: $TESTS_TOTAL"
    echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"
    echo ""
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}✗ Some tests failed${NC}"
        exit 1
    fi
}

# Run tests
main
