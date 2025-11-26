# Rule Templates Guide

## Overview

Rule templates provide pre-built compliance checks for different vendors and frameworks (CIS, PCI-DSS, NIST, Best Practices).

## Available Vendors

- **Cisco IOS XR** (`CISCO_XR`)
- **Nokia SROS** (`NOKIA_SROS`)

## Compliance Frameworks

- **CIS Benchmarks**: Industry best practices for secure configuration
- **PCI-DSS**: Payment Card Industry Data Security Standard
- **NIST 800-53**: National Institute of Standards and Technology security controls
- **Best Practices**: General security and operational best practices

## How to Use Templates

### 1. Initialize Built-in Templates

Templates are automatically initialized when the application starts. You can also manually initialize them:

```bash
POST /rule-templates/initialize
```

### 2. Browse Available Templates

```bash
# List all templates
GET /rule-templates/

# Filter by vendor
GET /rule-templates/?vendor=NOKIA_SROS

# Filter by framework
GET /rule-templates/?framework=CIS

# Filter by category
GET /rule-templates/?category=CIS%20Benchmark
```

### 3. Apply Templates to Create Audit Rules

```bash
POST /rule-templates/apply
Content-Type: application/json

{
  "template_id": 1,
  "custom_name": "My Custom SSH Check"  # Optional
}
```

This creates an active audit rule from the template.

### 4. Run Audits

```bash
POST /audit/
Content-Type: application/json

{
  "device_ids": [1, 2, 3],
  "rule_ids": []  # Empty = use all enabled rules
}
```

## Vendor-Specific Examples

### Cisco IOS XR

#### Example 1: SSH Protocol 2 Only (CIS)

**Template:**
```json
{
  "name": "CIS: SSH Protocol 2 Only",
  "description": "Ensure SSH is configured to use protocol version 2 only",
  "vendor": "CISCO_XR",
  "framework": "CIS",
  "xpath": "/ssh/server",
  "expected_value": "v2",
  "check_type": "contains"
}
```

**What it checks:**
- Connects to Cisco XR device via NETCONF
- Queries `/ssh/server` configuration path
- Verifies SSH version 2 is configured
- Marks as PASS if "v2" is found in configuration

**Expected configuration on device:**
```
ssh server v2
ssh server vrf default
```

**How to audit:**
1. Add Cisco XR devices to platform
2. Initialize templates or apply CIS: SSH Protocol 2 template
3. Run audit on devices
4. Review findings

#### Example 2: AAA Authentication (CIS)

**Template:**
```json
{
  "name": "CIS: Enable AAA Authentication",
  "description": "Ensure AAA authentication is enabled",
  "vendor": "CISCO_XR",
  "framework": "CIS",
  "xpath": "/aaa/authentication",
  "expected_value": "true",
  "check_type": "exists"
}
```

**What it checks:**
- Verifies AAA authentication configuration exists
- Critical security control for access management

**Expected configuration:**
```
aaa authentication login default group tacacs+ local
aaa authentication login console local
```

#### Example 3: Login Banner (CIS)

**Template:**
```json
{
  "name": "CIS: Configure Login Banner",
  "description": "Ensure login banner is configured",
  "vendor": "CISCO_XR",
  "framework": "CIS",
  "xpath": "/banner/login",
  "check_type": "exists"
}
```

**Expected configuration:**
```
banner login "Authorized access only. All activities monitored."
```

### Nokia SROS

#### Example 1: SSH Configuration (CIS)

**Template:**
```json
{
  "name": "CIS: Nokia SSH Configuration",
  "description": "Ensure SSH is properly configured on Nokia SROS",
  "vendor": "NOKIA_SROS",
  "framework": "CIS",
  "xpath": "/configure/system/security/ssh",
  "check_type": "exists"
}
```

**What it checks:**
- Uses pysros to connect to Nokia SR OS device
- Queries `/configure/system/security/ssh` path
- Verifies SSH is configured
- Returns structured data in JSON format (not containerized)

**Expected configuration on device:**
```
/configure system security
    ssh
        server admin-state enable
        client
            admin-state enable
        preserve-key
    exit
```

**How to audit Nokia devices:**
1. Add Nokia SROS devices with pysros credentials
2. Apply Nokia SSH template
3. System uses `nokia_sros_connector.py` which:
   - Connects via pysros `connect()` method
   - Executes `connection.running.get(xpath)`
   - Converts pysros Container objects to JSON dictionaries
   - Handles `_Empty` objects (returns `{}`)
4. Audit engine compares results against template criteria

#### Example 2: User Authentication (CIS)

**Template:**
```json
{
  "name": "CIS: Nokia User Authentication",
  "description": "Ensure proper user authentication on Nokia SROS",
  "vendor": "NOKIA_SROS",
  "framework": "CIS",
  "xpath": "/configure/system/security/user-params",
  "check_type": "exists"
}
```

**Expected configuration:**
```
/configure system security
    user-params
        local-user
            user "admin"
                password "$2y$10$..."
                access console
                console member "administrative"
            exit
    exit
```

#### Example 3: Login Banner (CIS)

**Template:**
```json
{
  "name": "CIS: Nokia Login Banner",
  "description": "Ensure login banner is configured",
  "vendor": "NOKIA_SROS",
  "framework": "CIS",
  "xpath": "/configure/system/login-control",
  "check_type": "exists"
}
```

**Expected configuration:**
```
/configure system
    login-control
        motd "Authorized access only"
        pre-login-message "Warning: Unauthorized access prohibited"
    exit
```

#### Example 4: NTP Configuration (Best Practice)

**Template:**
```json
{
  "name": "Best Practice: Nokia NTP Configuration",
  "description": "Ensure NTP is configured for time synchronization",
  "vendor": "NOKIA_SROS",
  "framework": "Best Practice",
  "xpath": "/configure/system/time/ntp",
  "check_type": "exists"
}
```

**Expected configuration:**
```
/configure system time
    ntp
        admin-state enable
        server "192.168.1.1"
            admin-state enable
        exit
    exit
```

#### Example 5: Encryption (PCI-DSS)

**Template:**
```json
{
  "name": "PCI-DSS: Nokia Encryption",
  "description": "Ensure strong encryption is configured",
  "vendor": "NOKIA_SROS",
  "framework": "PCI-DSS",
  "xpath": "/configure/system/security/tls",
  "check_type": "exists"
}
```

**Expected configuration:**
```
/configure system security
    tls
        cert-profile "default"
            entry 1
                certificate-file "cert.pem"
                key-file "key.pem"
            exit
        exit
    exit
```

## Understanding Check Types

### `exists`
Checks if the configuration path exists (has any value).

**Pass:** Path exists in configuration
**Fail:** Path does not exist

**Example:**
```json
{
  "xpath": "/aaa/authentication",
  "check_type": "exists"
}
```

### `contains`
Checks if the configuration value contains a specific string.

**Pass:** Configuration contains the expected value
**Fail:** Configuration doesn't contain the expected value

**Example:**
```json
{
  "xpath": "/ssh/server",
  "expected_value": "v2",
  "check_type": "contains"
}
```

### `equals`
Checks if the configuration exactly matches the expected value.

**Pass:** Configuration exactly equals expected value
**Fail:** Configuration doesn't match

**Example:**
```json
{
  "xpath": "/admin-state",
  "expected_value": "enable",
  "check_type": "equals"
}
```

## Creating Custom Templates

You can create your own templates via the API:

```bash
POST /rule-templates/
Content-Type: application/json

{
  "name": "Custom: My Security Check",
  "description": "Check for custom security requirement",
  "category": "Custom",
  "vendors": ["CISCO_XR"],
  "severity": "HIGH",
  "checks": [
    {
      "xpath": "/custom/path",
      "expected_value": "secure_value",
      "check_type": "contains"
    }
  ],
  "framework": "Custom",
  "tags": {"custom": "tag"}
}
```

## Audit Workflow

### Step 1: Setup Devices
```bash
POST /devices/
{
  "hostname": "router1",
  "ip": "192.168.1.1",
  "vendor": "CISCO_XR",
  "port": 830,
  "username": "admin",
  "password": "password"
}
```

### Step 2: Initialize or Browse Templates
```bash
GET /rule-templates/?vendor=CISCO_XR&framework=CIS
```

### Step 3: Apply Templates
```bash
# Apply multiple templates
POST /rule-templates/apply
{"template_id": 1}

POST /rule-templates/apply
{"template_id": 2}

POST /rule-templates/apply
{"template_id": 3}
```

### Step 4: Run Audit
```bash
POST /audit/
{
  "device_ids": [1],
  "rule_ids": []  # Uses all enabled rules
}
```

### Step 5: View Results
```bash
# Get latest results
GET /audit/results?latest_only=true

# Get specific device results
GET /audit/results/1

# Get device audit history
GET /audit/results/1/history?limit=10
```

## Template Categories

### CIS Benchmark
- Industry consensus security configuration baselines
- Covers: Access Control, Authentication, Logging, Network Security
- Severity: Typically HIGH to CRITICAL

### PCI-DSS
- Payment card industry security requirements
- Covers: Encryption, Access Control, Logging, Monitoring
- Severity: Typically CRITICAL for encryption, HIGH for logging

### NIST 800-53
- Federal information security standards
- Covers: Access Control, Audit & Accountability, System Integrity
- Severity: Typically HIGH

### Best Practices
- General operational and security best practices
- Covers: NTP, SNMP, Logging, Monitoring
- Severity: Typically MEDIUM to HIGH

## Troubleshooting

### Template Not Found
```bash
# List available templates
GET /rule-templates/

# Initialize if empty
POST /rule-templates/initialize
```

### Audit Fails with "Configuration path not found"
- Check if xpath is correct for your device vendor
- Verify device is accessible via NETCONF
- Check if configuration actually exists on device

### pysros Container Serialization Error
**Fixed**: The system now automatically converts pysros Container objects to JSON dictionaries, including handling of `_Empty` objects.

### Device Connection Failed
- Verify IP address and port
- Check NETCONF is enabled on device
- Verify credentials are correct
- Check network connectivity

## Best Practices

1. **Start with CIS templates** for baseline security
2. **Group devices by vendor** for efficient auditing
3. **Run audits on schedule** using audit schedules
4. **Review results regularly** and fix failures promptly
5. **Create custom templates** for organization-specific requirements
6. **Use drift detection** to catch unauthorized changes
7. **Enable notifications** for critical audit failures

## Framework Mapping

| Framework | Focus Area | Use Case |
|-----------|-----------|----------|
| CIS | General Security Hardening | Baseline security for all devices |
| PCI-DSS | Payment Security | Devices handling payment data |
| NIST | Federal Compliance | Government/Federal requirements |
| Best Practices | Operational Excellence | General operational standards |

## API Reference

- `GET /rule-templates/` - List templates
- `POST /rule-templates/initialize` - Initialize built-in templates
- `POST /rule-templates/apply` - Create audit rule from template
- `GET /rule-templates/frameworks` - List available frameworks
- `GET /rule-templates/categories` - List available categories
- `POST /audit/` - Run audit
- `GET /audit/results` - Get audit results
