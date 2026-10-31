## Prime Att

**ZKTeco ADMS (iClock Protocol) Server for Frappe**

Prime Att is a custom Frappe app that implements a complete ZKTeco ADMS (PUSH SDK / iClock) server with device management, fingerprint enrollment, and HRMS synchronization capabilities.

## Features

### 1. Protocol Layer (iClock / PUSH SDK)

Implements the complete ZKTeco iClock protocol over plain HTTP:

- **Device Handshake** - Auto-registration of unknown devices with configurable parameters
- **Attendance Logs (ATTLOG)** - Receives and processes punch records from devices
- **User Info (USERINFO)** - Syncs user data bidirectionally
- **Fingerprint Templates (FINGERTMP)** - Securely stores encrypted biometric templates
- **Operation Logs (OPERLOG)** - Audit trail of device operations
- **Command Polling** - Bidirectional command queue for device control
- **Heartbeat Monitoring** - Real-time online/offline status

All responses are `text/plain` (not Frappe JSON) to comply with device requirements.

### 2. User Management & Fingerprint Enrollment

- **ZK Person** - Central user registry with device mapping
- **Push to Device** - Send user info (PIN, Name, Card, Privilege) to devices
- **Fingerprint Enrollment**:
  - Interactive enrollment workflow (Queued → Sent → Waiting → Enrolled)
  - Multi-finger support (0-9 finger indexes)
  - Configurable command templates per device/firmware
  - Status tracking with retry mechanisms
  - Walk-up enrollment support (devices can send templates independently)
- **Pull Users** - Import users from device
- **Delete User** - Remove users from device
- **Template Storage** - Encrypted storage (ZK Admin access only)

### 3. Punch Processing & HRMS Sync

**Punch Records:**
- Timezone conversion (default: Asia/Dhaka)
- Duplicate detection with configurable tolerance
- Status code → IN/OUT mapping
- Unknown PIN handling (creates unmapped ZK Person)

**HRMS Synchronization:**
- **Local Mode**: Direct integration with HRMS app (if installed)
- **Remote Mode**: API-based sync to remote ERPNext instance
- Idempotent: never creates duplicate Employee Checkin records
- Automatic background sync with exponential backoff retry
- Manual retry for failed records
- Comprehensive sync logging

**Employee Mapping:**
- Map by `ZK Person.employee` field
- Auto-map by `Employee.attendance_device_id`
- Bulk mapping tool
- List of unmapped PINs

## Installation

### 1. Install the App

```bash
# Get the app
cd frappe-bench
bench get-app https://github.com/yourusername/prime_att.git

# Install in site
bench --site yoursite.local install-app prime_att

# Create roles and doctypes
bench --site yoursite.local migrate
bench --site yoursite.local execute prime_att.setup_doctypes.create_all_doctypes
```

### 2. Nginx Configuration

**Option A: Direct Pass-through (Recommended)**

Add to your site's nginx config (before other location blocks):

```nginx
# ZKTeco iClock endpoints - bypass Frappe's JSON wrapper
location ~* ^/iclock/(cdata|getrequest|devicecmd) {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Important: Don't modify response
    proxy_pass_header Content-Type;
}
```

**Option B: Rewrite to Guest Method**

If direct pass-through doesn't work:

```nginx
location ~* ^/iclock/(.*) {
    rewrite ^/iclock/(.*)$ /api/method/prime_att.zkteco.iclock_protocol.iclock_handler last;
}
```

Reload nginx:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 3. Configure Device

**On ZKTeco Device:**

1. Go to **Communication** → **Cloud Server** or **Push Settings**
2. Set **Server IP**: Your Frappe server IP/domain
3. Set **Server Port**: 80 (or 443 for HTTPS)
4. Set **Push URL**: `/iclock/cdata`
5. Set **Push Protocol**: HTTP
6. Set **Push Interval**: 30 seconds
7. Optional: Set **Comm Key** (must match in Frappe device doc)
8. Save and test connection

### 4. Configure Prime Att

**Set up Settings:**

```bash
bench --site yoursite.local execute --args "['Administrator']" --console
```

```python
# Create default settings
settings = frappe.get_single("ZK Settings")
settings.timezone = "Asia/Dhaka"
settings.duplicate_tolerance = 5

# Add status mappings
settings.append("status_mappings", {
    "status_code": "0",
    "log_type": "IN",
    "description": "Check In"
})
settings.append("status_mappings", {
    "status_code": "1",
    "log_type": "OUT",
    "description": "Check Out"
})

settings.save()
```

**Approve Device:**

After device connects, it will appear in **ZK Device** list with status "Pending". Change to "Active" to enable processing.

### 5. Set Up HRMS Sync

**For Local HRMS:**

```python
connector = frappe.get_single("ZK Sync Connector")
connector.mode = "Local HRMS"
connector.auto_sync = 1
connector.sync_from_date = "2024-01-01"
connector.save()
```

**For Remote ERPNext:**

```python
connector = frappe.get_single("ZK Sync Connector")
connector.mode = "Remote ERPNext"
connector.remote_url = "https://your-erpnext.com"
connector.api_key = "your_api_key"
connector.api_secret = "your_api_secret"
connector.auto_sync = 1
connector.batch_size = 100
connector.save()
```

## HRMS Setup (ERPNext Side)

Prime Att creates `Employee Checkin` records. HRMS must be configured to process them:

1. **Map Employees**: Set `Employee.attendance_device_id` = ZK Person PIN
2. **Create Shift Types**: Enable "Auto Attendance" in Shift Type
3. **Assign Shifts**: Create Shift Assignments for employees
4. **Configure Attendance**: HRMS will automatically create Attendance from check-ins

## Usage

### Register User and Enroll Fingerprint

1. Create **ZK Person**: Set PIN, Name, Card Number
2. Click **Push to Device(s)**: Select devices to push user info
3. Click **Enroll Fingerprint**:
   - Select device
   - Choose finger index (0-9)
   - Submit
4. **Device enters enrollment mode** - user places finger
5. Check **ZK Fingerprint Enrollment** for status
6. Template automatically stored when device sends FINGERTMP

### View Punches and Check-ins

- **ZK Punch**: Raw device punches
- **ZK Check-in Out**: Processed check-ins with sync status
- **ZK Sync Log**: Detailed sync history

### Command Management

- **ZK Device Command**: View all sent commands
- Commands auto-executed when device polls

### Debugging

- **ZK Raw Log**: Every payload received from device
- Check device last activity and online status

## Testing

### Device Simulator

```bash
cd /home/prime/frappe-bench/apps/prime_att/tests

# Run test scenario
python test_device_simulator.py http://yoursite.local TESTDEV001 test

# Run continuous heartbeat
python test_device_simulator.py http://yoursite.local TESTDEV001 heartbeat
```

### Unit Tests

```bash
bench --site yoursite.local run-tests --app prime_att
```

## Tested On

- **Frappe**: v15.x, v16.x
- **Devices**: ZKTeco F18, K40, K50 (should work with all iClock-compatible devices)
- **Firmware**: Various (command templates configurable per device)

## Roles & Permissions

- **ZK Admin**: Full access including biometric templates
- **ZK Operator**: Device management, user management, view punches

## API Reference

All device endpoints are guest-accessible (authenticated by SN and optional comm_key):

- `GET /iclock/cdata?SN=xxx&options=all` - Handshake
- `POST /iclock/cdata?SN=xxx&table=ATTLOG` - Upload data
- `GET /iclock/getrequest?SN=xxx` - Poll commands
- `POST /iclock/devicecmd?SN=xxx&ID=xxx` - Command result

Whitelisted methods for UI:

```python
# Enrollment
frappe.call("prime_att.zkteco.enrollment_manager.enroll_fingerprint", {
    person_name: "ZK Person name",
    device_sn: "DEVICE001",
    finger_index: "0"
})

# Push user to devices
frappe.call("prime_att.zkteco.enrollment_manager.push_to_devices", {
    person_name: "ZK Person name",
    device_list: ["DEVICE001", "DEVICE002"]
})

# Pull users from device
frappe.call("prime_att.zkteco.enrollment_manager.pull_users_from_device", {
    device_sn: "DEVICE001"
})

# Retry failed sync
frappe.call("prime_att.zkteco.sync_manager.retry_failed_checkin", {
    checkin_name: "ZK Check-in Out name"
})

# Bulk mapping
frappe.call("prime_att.zkteco.enrollment_manager.bulk_map_employees")
```

## Troubleshooting

**Device not connecting:**
- Check nginx config and reload
- Verify device can reach server (ping, telnet port 80)
- Check device Push URL setting
- Look for errors in **ZK Raw Log**

**No punches received:**
- Verify device status is "Active" (not Pending/Blocked)
- Check device last activity timestamp
- Test with device simulator
- Check **ZK Raw Log** for incoming payloads

**Sync failing:**
- Check **ZK Check-in Out** sync_error field
- Verify person is mapped to employee
- For Remote mode: test API credentials
- Check **ZK Sync Log** for details

**Enrollment not working:**
- Check **ZK Device Command** status
- Verify user was pushed to device first
- Check device firmware - may need custom command template
- Look at **ZK Fingerprint Enrollment** status field

## Architecture

```
Device → nginx → Frappe Site
           ↓
    /iclock/* endpoints (text/plain)
           ↓
    ZK Raw Log (store immediately)
           ↓
    Background Processor (frappe.enqueue)
           ↓
    ├─ ZK Punch → ZK Check-in Out → HRMS Sync
    ├─ ZK Person (update from USERINFO/FINGERTMP)
    └─ ZK Fingerprint Enrollment (mark enrolled)
```

## License

MIT

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch version-16
bench install-app prime_att
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/prime_att
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade
### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


### License

mit
