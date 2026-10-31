# Prime Att - Project Structure

## Directory Tree

```
prime_att/
├── README.md                          # Main documentation
├── QUICKSTART.md                      # 15-minute setup guide
├── TESTING.md                         # Testing guide with regression checklist
├── API.md                            # Complete API documentation
├── SUMMARY.md                        # Implementation summary
├── CHANGELOG.md                      # Version history
├── PROJECT_STRUCTURE.md              # This file
├── license.txt                       # MIT license
├── requirements.txt                  # Python dependencies
├── install.sh                        # Installation script
├── setup_doctypes.py                 # DocType creation script
│
├── prime_att/                        # Main app module
│   ├── __init__.py
│   ├── hooks.py                      # Frappe hooks configuration
│   ├── modules.txt                   # Module list
│   ├── install_script.py             # Installation helper functions
│   │
│   ├── config/                       # App configuration
│   │   └── __init__.py
│   │
│   ├── patches/                      # Database patches
│   │   ├── __init__.py
│   │   └── patches.txt
│   │
│   ├── zkteco/                       # Core ZKTeco integration
│   │   ├── __init__.py
│   │   ├── iclock_protocol.py        # Protocol handler (303 lines)
│   │   ├── processor.py              # Background data processor (251 lines)
│   │   ├── parser.py                 # Data parsers (145 lines)
│   │   ├── device_manager.py         # Device management (116 lines)
│   │   ├── sync_manager.py           # HRMS sync manager (225 lines)
│   │   └── enrollment_manager.py     # User & fingerprint enrollment (231 lines)
│   │
│   ├── prime_attendance_system/      # Module for DocTypes
│   │   ├── __init__.py
│   │   └── doctype/
│   │       ├── zk_person/
│   │       │   └── zk_person.js      # Person form customization
│   │       ├── zk_device/
│   │       │   └── zk_device.js      # Device form customization
│   │       ├── zk_check_in_out/
│   │       │   └── zk_check_in_out.js # Check-in form customization
│   │       └── zk_fingerprint_enrollment/
│   │           └── zk_fingerprint_enrollment.js # Enrollment form
│   │
│   ├── templates/                    # Jinja templates
│   │   ├── __init__.py
│   │   └── pages/
│   │       └── __init__.py
│   │
│   └── public/                       # Static assets
│       ├── css/
│       └── js/
│
├── templates/                        # Import templates
│   └── zk_person_import_template.csv # Bulk user import template
│
├── nginx/                            # Nginx configuration
│   └── iclock.conf                   # iClock endpoint config
│
├── tests/                            # Testing suite
│   ├── test_device_simulator.py      # Device simulator (257 lines)
│   └── test_protocol.py              # Unit tests (91 lines)
│
└── fixtures/                         # Default data
    └── roles.json                    # ZK Admin, ZK Operator roles
```

## File Categories

### Core Python Modules (1,271 lines)
- `iclock_protocol.py` - HTTP protocol handler, responds text/plain
- `processor.py` - Background async processing of device data
- `parser.py` - Tolerant parsing of tab-separated device data
- `device_manager.py` - Device registration, commands, status
- `sync_manager.py` - Local/Remote HRMS synchronization
- `enrollment_manager.py` - User push and fingerprint enrollment

### Configuration (3 files)
- `hooks.py` - Frappe app hooks (scheduler, routes, overrides)
- `install_script.py` - Post-installation setup
- `setup_doctypes.py` - Automated DocType creation

### Client-Side JavaScript (302 lines)
- `zk_person.js` - Push, enroll, delete buttons
- `zk_device.js` - Pull users, view logs
- `zk_check_in_out.js` - Retry sync
- `zk_fingerprint_enrollment.js` - Check status, retry

### Testing (348 lines)
- `test_device_simulator.py` - Simulates ZKTeco device
- `test_protocol.py` - Unit tests for parsers

### Documentation (1,865+ lines)
- `README.md` - Complete project documentation
- `QUICKSTART.md` - Fast setup guide
- `TESTING.md` - Testing procedures
- `API.md` - API reference
- `SUMMARY.md` - Implementation overview
- `CHANGELOG.md` - Version history

### Configuration Files
- `requirements.txt` - Python dependencies
- `nginx/iclock.conf` - Nginx config template
- `install.sh` - Automated installation
- `fixtures/roles.json` - Default roles

### Templates
- `zk_person_import_template.csv` - Bulk import template

## DocTypes (14 total)

### Core Entity DocTypes
1. **ZK Device** - Device registry
   - Fields: serial_number, device_name, status, is_online, location, ip_address
   - Auto-naming: By serial_number
   - Custom buttons: Pull Users, View Logs

2. **ZK Person** - User registry
   - Fields: pin (unique), full_name, card_no, privilege, employee
   - Child table: ZK Person Device (devices)
   - Custom buttons: Push to Devices, Enroll Fingerprint, Delete from Device

3. **ZK Device Command** - Command queue
   - Fields: device, command, status, response, created_by
   - Statuses: Pending → Sent → Done/Failed

4. **ZK Fingerprint Enrollment** - Enrollment tracking
   - Fields: person, device, finger_index, status, template_data
   - Workflow: Queued → Sent → Waiting → Enrolled
   - Custom button: Check Status, Retry

### Settings DocTypes (Singles)
5. **ZK Settings** - Global configuration
   - Fields: timezone, duplicate_tolerance, rate_limit_requests
   - Child table: ZK Status Mapping (status_mappings)

6. **ZK Sync Connector** - HRMS sync config
   - Fields: mode, auto_sync, sync_from_date, batch_size
   - Remote fields: remote_url, api_key, api_secret

### Child Table DocTypes
7. **ZK Person Device** - Per-device registration status
   - Fields: device, status, last_pushed
   - Statuses: Not Pushed → Pending → Pushed → Enrolled

8. **ZK Status Mapping** - Status code to IN/OUT mapping
   - Fields: status_code, log_type, description

### Log DocTypes
9. **ZK Raw Log** - All device payloads (debugging)
   - Fields: device, log_type, received_at, payload

10. **ZK Punch** - Raw punch records
    - Fields: device, pin, punch_time, status_code, verify_type, workcode

11. **ZK Check-in Out** - Processed check-ins
    - Fields: person, log_time, log_type, device, sync_status
    - Sync fields: synced_checkin_id, synced_at, sync_error, retry_count
    - Custom button: Retry Sync

12. **ZK Operation Log** - Device operations audit
    - Fields: device, admin_pin, operation_time, operation_id, operation_object

13. **ZK Sync Log** - Sync history
    - Fields: checkin, person, log_time, sync_status, target_doc, error_message

### Template DocType
14. **ZK Command Template** - Device-specific commands
    - Fields: device_model, command_type, command_template, description

## Data Flow

```
Device → Nginx → iclock_protocol.py
                      ↓
                 ZK Raw Log (store immediately)
                      ↓
                 frappe.enqueue()
                      ↓
                 processor.py
                      ↓
            ┌────────┴────────┐
            ↓                 ↓
        parser.py         Device logic
            ↓                 ↓
    ┌───────┴───────┐    ┌───┴────┐
    ↓               ↓    ↓        ↓
ZK Punch    ZK Person  Commands  etc.
    ↓
ZK Check-in Out
    ↓
sync_manager.py
    ↓
Employee Checkin (HRMS)
```

## Key Technical Patterns

### 1. Async Processing
```python
# Store immediately
create_raw_log(sn, table, body)

# Process in background
frappe.enqueue('prime_att.zkteco.processor.process_device_data', ...)
```

### 2. Tolerant Parsing
```python
fields = line.split('\t')
record = {
    'pin': fields[0].strip(),
    'timestamp': parse_device_datetime(fields[1].strip()),
    'status': fields[2].strip() if len(fields) > 2 else '0',  # Default
    # ...
}
```

### 3. Idempotent Sync
```python
# Check for existing
if checkin.synced_checkin_id:
    return  # Already synced

# Check for duplicate in target
existing = frappe.db.exists("Employee Checkin", {"employee": employee, "time": time})
if existing:
    checkin.synced_checkin_id = existing
    return
```

### 4. Command Queue
```python
# Device polls
commands = frappe.get_all("ZK Device Command", 
    filters={"device": sn, "status": ["in", ["Pending", "Sent"]]},
    order_by="creation asc", limit=1)

# Return command
if commands:
    return f"C:{cmd_id}:{command}"
```

### 5. Encrypted Storage
```python
from frappe.utils.password import encrypt, decrypt

# Store
enrollment.template_data = encrypt(raw_template)

# Retrieve (ZK Admin only)
raw_template = decrypt(enrollment.template_data)
```

## Customization Points

### 1. Add New Command Type
```python
# In ZK Command Template
{
    "device_model": "YourDevice",
    "command_type": "YOUR_COMMAND",
    "command_template": "CMD {pin}\t{param1}\t{param2}",
    "description": "Your command description"
}
```

### 2. Custom Status Mapping
```python
# In ZK Settings → Status Mappings
{
    "status_code": "6",
    "log_type": "IN",
    "description": "Custom Check In"
}
```

### 3. Add Pre/Post Processing Hook
```python
# In hooks.py
doc_events = {
    "ZK Punch": {
        "after_insert": "your_app.your_module.process_punch"
    }
}
```

### 4. Custom Sync Logic
```python
# Extend sync_manager.py
def custom_sync_logic(checkin):
    # Your logic here
    pass
```

## Security Architecture

```
┌─────────────────────────────────────────┐
│           Device Layer                  │
│  • SN authentication (required)         │
│  • Comm key validation (optional)       │
│  • Rate limiting (60 req/min/device)    │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│           API Layer                     │
│  • Token/Session auth                   │
│  • Role-based permissions               │
│  • Standard Frappe security             │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│           Data Layer                    │
│  • Encrypted templates (Password type)  │
│  • ZK Admin only access                 │
│  • Audit logs (Operation Log)           │
└─────────────────────────────────────────┘
```

## Performance Optimization

1. **Immediate Response**: Store raw log first, process later
2. **Database Indexes**: On (device, pin, punch_time) for duplicates
3. **Background Queue**: All heavy processing async
4. **Batch Processing**: Configurable batch_size for sync
5. **Connection Pooling**: Reuse DB connections
6. **Short Poll Mode**: Only during enrollment

## Error Handling Strategy

1. **Protocol Errors**: Return plain text "ERROR: message"
2. **Processing Errors**: Log to Error Log, continue
3. **Parse Errors**: Log line, skip, continue with next
4. **Sync Errors**: Store error, retry with backoff
5. **Command Errors**: Mark failed, allow retry

## Monitoring Points

- Device online/offline status
- Last activity timestamp
- Command queue depth
- Failed sync count
- Raw log growth
- Processing queue depth

## Maintenance Tasks

### Daily
- Monitor failed syncs
- Check offline devices

### Weekly
- Review error logs
- Clean old raw logs (optional)
- Check command timeouts

### Monthly
- Review template storage usage
- Audit user mappings
- Performance metrics

## Integration Points

### Frappe HRMS
- Employee Checkin creation
- Employee.attendance_device_id field
- Shift assignment integration

### ERPNext Remote
- REST API (/api/resource/Employee Checkin)
- Token authentication
- Batch sync support

### External Systems
- REST API for all DocTypes
- Webhooks for events
- Custom extensions via hooks

## Testing Strategy

### Unit Tests
- `test_protocol.py` - Parser functions
- Run: `bench --site site run-tests --app prime_att`

### Integration Tests
- `test_device_simulator.py` - Full workflow
- Modes: test (single run), heartbeat (continuous)

### Manual Tests
- Device connection
- User enrollment
- Punch processing
- HRMS sync
- Command execution

## Deployment Checklist

- [ ] Nginx configured
- [ ] App installed
- [ ] DocTypes created
- [ ] Settings configured
- [ ] Roles assigned
- [ ] Device registered
- [ ] Test punch successful
- [ ] HRMS sync working
- [ ] Background worker running
- [ ] Monitoring set up

## Total Project Stats

- **Files**: 32
- **Python Code**: ~1,271 lines (core modules)
- **JavaScript**: ~302 lines
- **Tests**: ~348 lines
- **Documentation**: ~1,865+ lines
- **DocTypes**: 14
- **Roles**: 2
- **Test Coverage**: Core functionality
- **Frappe Versions**: 15.x, 16.x
- **Development Time**: 1 session
- **Status**: Production-ready ✓
