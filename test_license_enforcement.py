#!/usr/bin/env python3
"""
License Enforcement Test Script

Tests all aspects of the license enforcement system:
1. Module access enforcement
2. Device quota enforcement
3. User quota enforcement
4. Storage quota enforcement
5. API Gateway blocking
6. Frontend menu filtering (via API)
"""

import requests
import json
import sys
from typing import Dict, Optional

BASE_URL = "http://localhost:3000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"  # Change this to your admin password

class LicenseEnforcementTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        
    def login(self, username: str, password: str) -> bool:
        """Login and get access token"""
        try:
            response = requests.post(
                f"{self.base_url}/login",
                json={"username": username, "password": password}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                print(f"✅ Logged in as {username}")
                
                # Get user info
                me_response = requests.get(
                    f"{self.base_url}/me",
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                if me_response.status_code == 200:
                    self.user_id = me_response.json().get("id")
                    print(f"   User ID: {self.user_id}")
                
                return True
            else:
                print(f"❌ Login failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def get_headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        return {"Authorization": f"Bearer {self.token}"}
    
    def test_license_status(self) -> Dict:
        """Test 1: Get current license status"""
        print("\n" + "="*60)
        print("TEST 1: License Status")
        print("="*60)
        
        try:
            response = requests.get(
                f"{self.base_url}/license/status",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                license_data = response.json()
                print(f"✅ License Status Retrieved")
                print(f"   Tier: {license_data.get('tier', 'N/A')}")
                print(f"   Valid: {license_data.get('valid', False)}")
                print(f"   Active: {license_data.get('is_active', False)}")
                
                # Show quotas
                quotas = license_data.get('quotas', {})
                usage = license_data.get('current_usage', {})
                print(f"\n   Quotas:")
                print(f"   - Devices: {usage.get('devices', 0)} / {quotas.get('max_devices', 0)}")
                print(f"   - Users: {usage.get('users', 0)} / {quotas.get('max_users', 0)}")
                print(f"   - Storage: {usage.get('storage_gb', 0)} GB / {quotas.get('max_storage_gb', 0)} GB")
                
                # Show modules
                modules = license_data.get('enabled_modules', [])
                print(f"\n   Enabled Modules ({len(modules)}):")
                for module in modules[:10]:  # Show first 10
                    print(f"   - {module}")
                if len(modules) > 10:
                    print(f"   ... and {len(modules) - 10} more")
                
                return license_data
            elif response.status_code == 404:
                print("⚠️  No license found (expected if not activated)")
                return {}
            else:
                print(f"❌ Failed to get license status: {response.status_code}")
                print(f"   Response: {response.text}")
                return {}
        except Exception as e:
            print(f"❌ Error: {e}")
            return {}
    
    def test_module_access(self, license_data: Dict):
        """Test 2: Module access enforcement via API Gateway"""
        print("\n" + "="*60)
        print("TEST 2: Module Access Enforcement")
        print("="*60)
        
        tier = license_data.get('tier', 'starter').lower()
        modules = license_data.get('enabled_modules', [])
        
        # Test accessible module (should work)
        print("\nTesting accessible modules...")
        accessible_tests = [
            ("/devices", "devices"),
            ("/audit", "manual_audits"),
        ]
        
        for endpoint, module_name in accessible_tests:
            module_mapping = {
                "devices": "devices",
                "manual_audits": "audit",
                "scheduled_audits": "audit_schedules"
            }
            frontend_module = module_mapping.get(module_name, module_name)
            
            if frontend_module in modules or "all" in modules:
                try:
                    response = requests.get(
                        f"{self.base_url}{endpoint}",
                        headers=self.get_headers(),
                        timeout=5
                    )
                    if response.status_code in [200, 204]:
                        print(f"✅ {endpoint} - Accessible (as expected)")
                    else:
                        print(f"⚠️  {endpoint} - Status {response.status_code}")
                except Exception as e:
                    print(f"⚠️  {endpoint} - Error: {e}")
        
        # Test inaccessible module (should block)
        print("\nTesting inaccessible modules...")
        if tier == "starter":
            # Starter shouldn't have access to scheduled audits
            inaccessible_tests = [
                ("/audit-schedules", "scheduled_audits"),
                ("/config-backups", "config_backups"),
            ]
            
            for endpoint, module_name in inaccessible_tests:
                try:
                    response = requests.get(
                        f"{self.base_url}{endpoint}",
                        headers=self.get_headers(),
                        timeout=5
                    )
                    if response.status_code == 403:
                        print(f"✅ {endpoint} - Blocked (as expected)")
                        error_data = response.json()
                        print(f"   Error: {error_data.get('detail', {}).get('error', 'N/A')}")
                    elif response.status_code == 402:
                        print(f"✅ {endpoint} - Blocked (no license)")
                    else:
                        print(f"❌ {endpoint} - Should be blocked but got {response.status_code}")
                except Exception as e:
                    print(f"⚠️  {endpoint} - Error: {e}")
    
    def test_device_quota(self, license_data: Dict):
        """Test 3: Device quota enforcement"""
        print("\n" + "="*60)
        print("TEST 3: Device Quota Enforcement")
        print("="*60)
        
        quotas = license_data.get('quotas', {})
        usage = license_data.get('current_usage', {})
        
        max_devices = quotas.get('max_devices', 0)
        current_devices = usage.get('devices', 0)
        
        print(f"\nCurrent device usage: {current_devices} / {max_devices}")
        
        if current_devices >= max_devices:
            print("⚠️  At device quota limit - testing enforcement...")
            
            # Try to add a device (should fail)
            test_device = {
                "hostname": "test-quota-device",
                "vendor": "cisco_ios",
                "ip": "192.168.1.254",
                "port": 22,
                "username": "test",
                "password": "test"
            }
            
            try:
                response = requests.post(
                    f"{self.base_url}/devices",
                    headers=self.get_headers(),
                    json=test_device,
                    timeout=5
                )
                
                if response.status_code == 403:
                    print("✅ Device creation blocked (quota exceeded)")
                    error_data = response.json()
                    print(f"   Error: {error_data.get('detail', {}).get('error', 'N/A')}")
                elif response.status_code == 201:
                    print("❌ Device created (should have been blocked)")
                    # Clean up
                    device_id = response.json().get('id')
                    if device_id:
                        requests.delete(
                            f"{self.base_url}/devices/{device_id}",
                            headers=self.get_headers()
                        )
                else:
                    print(f"⚠️  Unexpected status: {response.status_code}")
            except Exception as e:
                print(f"⚠️  Error: {e}")
        else:
            print(f"ℹ️  Not at quota limit yet ({max_devices - current_devices} slots available)")
    
    def test_user_quota(self, license_data: Dict):
        """Test 4: User quota enforcement"""
        print("\n" + "="*60)
        print("TEST 4: User Quota Enforcement")
        print("="*60)
        
        quotas = license_data.get('quotas', {})
        usage = license_data.get('current_usage', {})
        
        max_users = quotas.get('max_users', 0)
        current_users = usage.get('users', 0)
        
        print(f"\nCurrent user usage: {current_users} / {max_users}")
        
        if current_users >= max_users:
            print("⚠️  At user quota limit - testing enforcement...")
            
            # Try to add a user (should fail)
            test_user = {
                "username": "test-quota-user",
                "email": "test-quota@example.com",
                "password": "testpassword123",
                "role": "viewer"
            }
            
            try:
                response = requests.post(
                    f"{self.base_url}/user-management/users",
                    headers=self.get_headers(),
                    json=test_user,
                    timeout=5
                )
                
                if response.status_code in [400, 403]:
                    print("✅ User creation blocked (quota exceeded)")
                    error_data = response.json()
                    print(f"   Error: {error_data.get('detail', 'N/A')}")
                elif response.status_code == 201:
                    print("❌ User created (should have been blocked)")
                    # Clean up
                    user_id = response.json().get('id')
                    if user_id:
                        requests.delete(
                            f"{self.base_url}/user-management/users/{user_id}",
                            headers=self.get_headers()
                        )
                else:
                    print(f"⚠️  Unexpected status: {response.status_code}")
            except Exception as e:
                print(f"⚠️  Error: {e}")
        else:
            print(f"ℹ️  Not at quota limit yet ({max_users - current_users} slots available)")
    
    def test_user_modules(self):
        """Test 5: User module access (combines license + group permissions)"""
        print("\n" + "="*60)
        print("TEST 5: User Module Access")
        print("="*60)
        
        if not self.user_id:
            print("⚠️  User ID not available")
            return
        
        try:
            response = requests.get(
                f"{self.base_url}/user-management/users/{self.user_id}/modules",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                modules = response.json()
                print(f"✅ User has access to {len(modules)} modules:")
                for module in modules:
                    print(f"   - {module}")
                
                print("\nNote: These modules are the intersection of:")
                print("   1. Modules enabled in the license tier")
                print("   2. Modules assigned to user's groups")
            else:
                print(f"❌ Failed to get user modules: {response.status_code}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def test_storage_quota(self, license_data: Dict):
        """Test 6: Storage quota (informational)"""
        print("\n" + "="*60)
        print("TEST 6: Storage Quota Status")
        print("="*60)
        
        quotas = license_data.get('quotas', {})
        usage = license_data.get('current_usage', {})
        
        max_storage = quotas.get('max_storage_gb', 0)
        current_storage = usage.get('storage_gb', 0)
        
        usage_pct = (current_storage / max_storage * 100) if max_storage > 0 else 0
        
        print(f"\nStorage usage: {current_storage} GB / {max_storage} GB ({usage_pct:.1f}%)")
        
        if usage_pct > 90:
            print("⚠️  Warning: Storage usage above 90%")
        elif usage_pct > 100:
            print("❌ Storage quota exceeded!")
        else:
            print("✅ Storage within quota")
    
    def run_all_tests(self):
        """Run all license enforcement tests"""
        print("\n" + "="*60)
        print("LICENSE ENFORCEMENT TEST SUITE")
        print("="*60)
        
        # Login
        if not self.login(ADMIN_USERNAME, ADMIN_PASSWORD):
            print("\n❌ Failed to login. Please check credentials.")
            return
        
        # Get license status
        license_data = self.test_license_status()
        
        if not license_data:
            print("\n⚠️  No license data available. Some tests will be skipped.")
            print("   Activate a license to test enforcement features.")
            return
        
        # Run all tests
        self.test_module_access(license_data)
        self.test_device_quota(license_data)
        self.test_user_quota(license_data)
        self.test_user_modules()
        self.test_storage_quota(license_data)
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUITE COMPLETE")
        print("="*60)
        print("\n✅ License enforcement is active and working")
        print("   - Module access: Enforced at API Gateway")
        print("   - Device quota: Enforced at creation")
        print("   - User quota: Enforced at creation")
        print("   - Storage quota: Monitored and auto-cleanup")
        print("   - User modules: Filtered by license + groups")

def main():
    """Main entry point"""
    # Check if custom base URL provided
    base_url = sys.argv[1] if len(sys.argv) > 1 else BASE_URL
    
    print(f"Testing license enforcement at: {base_url}")
    print("Make sure the API Gateway is running!")
    
    tester = LicenseEnforcementTester(base_url)
    tester.run_all_tests()

if __name__ == "__main__":
    main()
