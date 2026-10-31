# Prime Att API Documentation

## Device Protocol API (iClock)

These endpoints are called by ZKTeco devices. All responses are `text/plain`.

### 1. Handshake

**Endpoint:** `GET /iclock/cdata`

**Description:** Initial device connection and configuration retrieval.

**Parameters:**
- `SN` (required): Device serial number
- `options` (optional): Device options (usually "all")
- `pushver` (optional): Push protocol version
- `language` (optional): Device language
- `key` (optional): Communication key for authentication

**Response Format:** Text lines with key=value pairs

```
Stamp=9999
OpStamp=9999
ErrorDelay=120
Delay=30
TransTimes=00:00;23:59
TransInterval=1
TransFlag=TransData AttLog OpLog EnrollUser ChgUser
Realtime=1
Encrypt=0
```

**Example:**
```bash
curl "http://yoursite.local/iclock/cdata?SN=DEVICE001&options=all&pushver=3.0.0&language=en"
```

### 2. Upload Attendance Logs

**Endpoint:** `POST /iclock/cdata`

**Description:** Upload attendance punch records.

**Parameters:**
- `SN` (required): Device serial number
- `table` (required): "ATTLOG"
- `key` (optional): Communication key

**Body Format:** Tab-separated values, one record per line

```
PIN<TAB>DateTime<TAB>Status<TAB>Verify<TAB>WorkCode<TAB>Reserved1<TAB>Reserved2
```

**Example:**
```bash
curl -X POST "http://yoursite.local/iclock/cdata?SN=DEVICE001&table=ATTLOG" \
  -H "Content-Type: text/plain" \
  -d "101	2024-10-31 09:00:00	0	1		
102	2024-10-31 09:05:00	1	1		"
```

**Response:** `OK`

### 3. Upload User Info

**Endpoint:** `POST /iclock/cdata`

**Parameters:**
- `SN` (required): Device serial number
- `table` (required): "USERINFO"

**Body Format:**
```
PIN<TAB>Name<TAB>Privilege<TAB>Password<TAB>CardNo<TAB>Group<TAB>Timezone<TAB>VerifyMode
```

**Response:** `OK`

### 4. Upload Fingerprint Template

**Endpoint:** `POST /iclock/cdata`

**Parameters:**
- `SN` (required): Device serial number
- `table` (required): "FINGERTMP"

**Body Format:**
```
PIN<TAB>FID<TAB>Size<TAB>Valid<TAB>Template
```

**Response:** `OK`

### 5. Upload Operation Log

**Endpoint:** `POST /iclock/cdata`

**Parameters:**
- `SN` (required): Device serial number
- `table` (required): "OPERLOG"

**Body Format:**
```
AdminPIN<TAB>OperTime<TAB>OpID<TAB>OpObject<TAB>Extra
```

**Response:** `OK`

### 6. Poll Commands (Heartbeat)

**Endpoint:** `GET /iclock/getrequest`

**Description:** Device polls for pending commands.

**Parameters:**
- `SN` (required): Device serial number
- `key` (optional): Communication key

**Response:**
- If commands pending: `C:<command_id>:<command>`
- If no commands: `OK`

**Example Response:**
```
C:CMD-12345:DATA UPDATE USERINFO PIN=101	Name=John Doe	Privilege=0	Card=1001
```

**Example:**
```bash
curl "http://yoursite.local/iclock/getrequest?SN=DEVICE001"
```

### 7. Command Result

**Endpoint:** `POST /iclock/devicecmd`

**Description:** Device reports command execution result.

**Parameters:**
- `SN` (required): Device serial number
- `ID` (required): Command ID (from getrequest response)
- `key` (optional): Communication key

**Body:** Command execution result (text)

**Response:** `OK`

**Example:**
```bash
curl -X POST "http://yoursite.local/iclock/devicecmd?SN=DEVICE001&ID=CMD-12345" \
  -d "OK: User updated"
```

## Frappe Whitelisted API

These endpoints are called from the Frappe UI or external integrations.

### 1. Enroll Fingerprint

**Method:** `prime_att.zkteco.enrollment_manager.enroll_fingerprint`

**Parameters:**
- `person_name` (required): ZK Person name
- `device_sn` (required): Device serial number
- `finger_index` (required): Finger index (0-9)
- `overwrite` (optional): Overwrite existing (default: 1)

**Returns:** Enrollment record name

**Example (JavaScript):**
```javascript
frappe.call({
    method: 'prime_att.zkteco.enrollment_manager.enroll_fingerprint',
    args: {
        person_name: 'ZKP-0001',
        device_sn: 'DEVICE001',
        finger_index: '0',
        overwrite: 1
    },
    callback: function(r) {
        console.log('Enrollment ID:', r.message);
    }
});
```

**Example (Python):**
```python
import frappe

enrollment_id = frappe.call(
    'prime_att.zkteco.enrollment_manager.enroll_fingerprint',
    person_name='ZKP-0001',
    device_sn='DEVICE001',
    finger_index='0',
    overwrite=1
)
```

**Example (cURL):**
```bash
curl -X POST "http://yoursite.local/api/method/prime_att.zkteco.enrollment_manager.enroll_fingerprint" \
  -H "Authorization: token api_key:api_secret" \
  -H "Content-Type: application/json" \
  -d '{"person_name":"ZKP-0001","device_sn":"DEVICE001","finger_index":"0","overwrite":1}'
```

### 2. Push to Devices

**Method:** `prime_att.zkteco.enrollment_manager.push_to_devices`

**Parameters:**
- `person_name` (required): ZK Person name
- `device_list` (optional): Array of device serial numbers (if null, pushes to all)

**Returns:** Array of results

**Example:**
```javascript
frappe.call({
    method: 'prime_att.zkteco.enrollment_manager.push_to_devices',
    args: {
        person_name: 'ZKP-0001',
        device_list: ['DEVICE001', 'DEVICE002']
    },
    callback: function(r) {
        console.log('Results:', r.message);
    }
});
```

### 3. Pull Users from Device

**Method:** `prime_att.zkteco.enrollment_manager.pull_users_from_device`

**Parameters:**
- `device_sn` (required): Device serial number

**Returns:** Command ID

**Example:**
```javascript
frappe.call({
    method: 'prime_att.zkteco.enrollment_manager.pull_users_from_device',
    args: {
        device_sn: 'DEVICE001'
    },
    callback: function(r) {
        frappe.msgprint('Pull command sent');
    }
});
```

### 4. Delete User from Device

**Method:** `prime_att.zkteco.enrollment_manager.delete_user_from_device`

**Parameters:**
- `person_name` (required): ZK Person name
- `device_sn` (required): Device serial number

**Example:**
```javascript
frappe.call({
    method: 'prime_att.zkteco.enrollment_manager.delete_user_from_device',
    args: {
        person_name: 'ZKP-0001',
        device_sn: 'DEVICE001'
    }
});
```

### 5. Check Enrollment Status

**Method:** `prime_att.zkteco.enrollment_manager.check_enrollment_status`

**Parameters:**
- `enrollment_name` (required): ZK Fingerprint Enrollment name

**Returns:** Object with status and message

**Example:**
```javascript
frappe.call({
    method: 'prime_att.zkteco.enrollment_manager.check_enrollment_status',
    args: {
        enrollment_name: 'ZKFE-0001'
    },
    callback: function(r) {
        console.log('Status:', r.message.status);
        console.log('Message:', r.message.message);
    }
});
```

### 6. Bulk Map Employees

**Method:** `prime_att.zkteco.enrollment_manager.bulk_map_employees`

**Returns:** Object with auto_mapped count and unmapped list

**Example:**
```javascript
frappe.call({
    method: 'prime_att.zkteco.enrollment_manager.bulk_map_employees',
    callback: function(r) {
        console.log('Auto-mapped:', r.message.auto_mapped);
        console.log('Unmapped:', r.message.unmapped);
    }
});
```

### 7. Retry Failed Checkin

**Method:** `prime_att.zkteco.sync_manager.retry_failed_checkin`

**Parameters:**
- `checkin_name` (required): ZK Check-in Out name

**Example:**
```javascript
frappe.call({
    method: 'prime_att.zkteco.sync_manager.retry_failed_checkin',
    args: {
        checkin_name: 'ZKCO-0001'
    }
});
```

## REST API (GET/POST)

Access DocTypes via standard Frappe REST API.

### Get Device List

**Endpoint:** `GET /api/resource/ZK Device`

**Authentication:** API Key/Secret or Session

**Example:**
```bash
curl "http://yoursite.local/api/resource/ZK Device" \
  -H "Authorization: token api_key:api_secret"
```

**Response:**
```json
{
  "data": [
    {
      "name": "DEVICE001",
      "device_name": "Main Entrance",
      "status": "Active",
      "is_online": 1,
      "last_activity": "2024-10-31 10:30:00"
    }
  ]
}
```

### Get Punches

**Endpoint:** `GET /api/resource/ZK Punch`

**Filters:**
- `device`: Device serial number
- `pin`: User PIN
- `punch_time`: Punch time range

**Example:**
```bash
curl "http://yoursite.local/api/resource/ZK Punch?filters=[[\"device\",\"=\",\"DEVICE001\"],[\"punch_time\",\">\",\"2024-10-31\"]]" \
  -H "Authorization: token api_key:api_secret"
```

### Get Check-ins

**Endpoint:** `GET /api/resource/ZK Check-in Out`

**Filters:**
- `person`: ZK Person name
- `log_time`: Time range
- `sync_status`: Pending, Synced, Failed, No Mapping

**Example:**
```bash
curl "http://yoursite.local/api/resource/ZK Check-in Out?filters=[[\"sync_status\",\"=\",\"Failed\"]]&limit=10" \
  -H "Authorization: token api_key:api_secret"
```

### Create Person

**Endpoint:** `POST /api/resource/ZK Person`

**Example:**
```bash
curl -X POST "http://yoursite.local/api/resource/ZK Person" \
  -H "Authorization: token api_key:api_secret" \
  -H "Content-Type: application/json" \
  -d '{
    "pin": "101",
    "full_name": "John Doe",
    "card_no": "1001",
    "privilege": "0",
    "is_active": 1,
    "employee": "EMP-001"
  }'
```

## Python API (Internal)

Use these functions in custom scripts, hooks, or other apps.

### Get Person by PIN

```python
person = frappe.db.get_value("ZK Person", {"pin": "101"}, ["name", "full_name", "employee"])
```

### Get Recent Punches

```python
punches = frappe.get_all(
    "ZK Punch",
    filters={
        "device": "DEVICE001",
        "punch_time": [">", "2024-10-31"]
    },
    fields=["name", "pin", "punch_time", "status_code"],
    order_by="punch_time desc",
    limit=100
)
```

### Send Custom Command

```python
from prime_att.zkteco.device_manager import send_command

cmd_id = send_command(
    device_sn="DEVICE001",
    command="DATA QUERY ATTLOG",
    created_by="Administrator"
)
```

### Manual Sync

```python
from prime_att.zkteco.sync_manager import sync_checkin

sync_checkin("ZKCO-0001")
```

### Bulk Sync

```python
from prime_att.zkteco.sync_manager import bulk_sync_pending

bulk_sync_pending()  # Syncs all pending check-ins
```

## Webhooks

Set up webhooks to get notified of events.

### Available DocTypes for Webhooks

- **ZK Punch**: Triggered on new punch
- **ZK Check-in Out**: Triggered on check-in/out
- **ZK Person**: Triggered on user creation/update
- **ZK Device**: Triggered on device changes
- **ZK Fingerprint Enrollment**: Triggered on enrollment status changes

**Example Webhook (New Punch):**

1. Go to: Webhook List → New
2. Set:
   - **DocType**: ZK Punch
   - **Request URL**: https://your-webhook-url.com/endpoint
   - **Condition**: (empty for all, or filter)
   - **Enabled**: ✓
3. Select webhook_data fields to send

## Rate Limits

Device endpoints (`/iclock/*`) are rate-limited per device SN:

- Default: 60 requests per minute per device
- Configurable in **ZK Settings** → rate_limit_requests

Exceeding limit returns: `ERROR: Rate limit exceeded`

## Authentication

### Device Authentication

Devices authenticate using:
1. **SN** (Serial Number): Required
2. **key** (Communication Key): Optional, set in ZK Device doc

### API Authentication

REST API uses standard Frappe authentication:
1. **Session**: Cookie-based (for browser)
2. **API Key/Secret**: Token-based (for external apps)
3. **OAuth**: If configured

Generate API credentials:
```bash
bench --site yoursite.local execute frappe.generate_api_key --kwargs "{'user':'your@email.com'}"
```

## Error Responses

### Device Protocol Errors

All errors returned as plain text:

- `ERROR: Missing SN` - No serial number provided
- `ERROR: Invalid or blocked device` - Device not found or blocked
- `ERROR: Unknown endpoint` - Invalid URL path
- `ERROR: Internal error` - Server error (check logs)

### API Errors

Standard Frappe error responses (JSON):

```json
{
  "_server_messages": "[\"Error message\"]",
  "exc_type": "ValidationError"
}
```

## Status Codes

### Device Protocol

- `200 OK`: Success
- `500 Internal Server Error`: Server error

### REST API

- `200 OK`: Success
- `401 Unauthorized`: Authentication failed
- `403 Forbidden`: Permission denied
- `404 Not Found`: Resource not found
- `417 Expectation Failed`: Validation error
- `500 Internal Server Error`: Server error

## Testing

Use the included simulator for testing:

```bash
cd /path/to/prime_att/tests
python test_device_simulator.py http://yoursite.local TESTDEV001 test
```

Or use curl:

```bash
# Handshake
curl "http://yoursite.local/iclock/cdata?SN=TEST001&options=all"

# Send punch
curl -X POST "http://yoursite.local/iclock/cdata?SN=TEST001&table=ATTLOG" \
  -d "101	2024-10-31 09:00:00	0	1		"

# Poll commands
curl "http://yoursite.local/iclock/getrequest?SN=TEST001"
```

## Support

- **Documentation**: See README.md, QUICKSTART.md, TESTING.md
- **Logs**: Check Error Log in Frappe
- **Debug**: Enable developer mode and check console
- **Community**: Frappe forum with "prime_att" tag
