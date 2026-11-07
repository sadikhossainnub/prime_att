# Prime Att - Testing Guide

## Quick Start Testing

### Prerequisites
```bash
# Ensure app is installed
cd /path/to/bench
bench --site yoursite migrate

# Start bench
bench start

# In another terminal, run tests
```

---

## 1. Plain-Text Response Tests (CRITICAL)

### Test 1.1: Handshake (GET /iclock/cdata)
```bash
curl -v "http://localhost:8000/iclock/cdata?SN=TEST001&options=all&pushver=3.0.0&language=en"
```

**Expected Response:**
```
< HTTP/1.1 200 OK
< Content-Type: text/plain; charset=utf-8

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

**MUST VERIFY:**
- ✅ Status: 200 OK
- ✅ Content-Type: `text/plain` (NOT `application/json` or `text/html`)
- ✅ Body: Plain text with key=value lines

**FAILURE INDICATORS:**
- ❌ `{"message": ...}` - JSON response (FAILED)
- ❌ `<html>` - HTML response (FAILED)
- ❌ 404 Not Found (FAILED)

---

### Test 1.2: Unknown Endpoint
```bash
curl -v "http://localhost:8000/iclock/unknown?SN=TEST001"
```

**Expected:**
```
< HTTP/1.1 404 NOT FOUND
< Content-Type: text/plain

ERROR: Unknown endpoint
```

---

### Test 1.3: Missing SN Parameter
```bash
curl -v "http://localhost:8000/iclock/cdata"
```

**Expected:**
```
< HTTP/1.1 400 BAD REQUEST
< Content-Type: text/plain

ERROR: Missing SN
```

---

### Test 1.4: POST Attendance Data
```bash
curl -v -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
  -H "Content-Type: text/plain" \
  -d $'101\t2024-11-02 10:00:00\t0\t1\t\t\n102\t2024-11-02 10:05:00\t1\t1\t\t'
```

**Expected:**
```
< HTTP/1.1 200 OK
< Content-Type: text/plain

OK
```

**Verify in Database:**
```python
bench --site yoursite console

>>> frappe.get_all("ZK Raw Log", filters={"device": "TEST001"}, limit=1)
[{'name': '...'}]  # Should have entry

>>> frappe.get_all("ZK Punch", filters={"device": "TEST001"}, limit=1)
[{'name': '...'}]  # Should have punch after background processing
```

---

### Test 1.5: Poll Commands (GET /iclock/getrequest)
```bash
curl -v "http://localhost:8000/iclock/getrequest?SN=TEST001"
```

**Expected (no commands):**
```
< HTTP/1.1 200 OK
< Content-Type: text/plain

OK
```

**Expected (with command):**
```
< HTTP/1.1 200 OK
< Content-Type: text/plain

C:1:REBOOT
```

---

### Test 1.6: Command Result (POST /iclock/devicecmd)
```bash
# First create a command via UI or:
bench --site yoursite console
>>> cmd = frappe.get_doc({"doctype": "ZK Device Command", "device": "TEST001", "command": "TEST", "status": "Sent"})
>>> cmd.insert()
>>> frappe.db.commit()
>>> print(cmd.name)  # Note the ID (e.g., "1")

# Then send result:
curl -v -X POST "http://localhost:8000/iclock/devicecmd?SN=TEST001&ID=1" \
  -d "Return=0&CMD=TEST"
```

**Expected:**
```
< HTTP/1.1 200 OK
< Content-Type: text/plain

OK
```

**Verify:**
```python
>>> cmd.reload()
>>> print(cmd.status)  # Should be "Done"
>>> print(cmd.response)  # Should be "Return=0&CMD=TEST"
```

---

## 2. Security Tests

### Test 2.1: Blocked Device
```bash
# Set device status to "Blocked" in UI

curl -v "http://localhost:8000/iclock/cdata?SN=BLOCKED_DEV"
```

**Expected:**
```
< HTTP/1.1 403 FORBIDDEN
< Content-Type: text/plain

ERROR: Invalid or blocked device
```

---

### Test 2.2: Wrong Communication Key
```bash
# Set comm_key on device (e.g., "secret123")

curl -v "http://localhost:8000/iclock/cdata?SN=TEST001&key=wrongkey"
```

**Expected:**
```
< HTTP/1.1 403 FORBIDDEN
< Content-Type: text/plain

ERROR: Invalid or blocked device
```

---

### Test 2.3: Correct Communication Key
```bash
curl -v "http://localhost:8000/iclock/cdata?SN=TEST001&key=secret123"
```

**Expected:**
```
< HTTP/1.1 200 OK
...
Stamp=9999
...
```

---

### Test 2.4: Rate Limiting
```bash
# Send 61 requests rapidly (limit is 60/min by default)
for i in {1..61}; do
  echo "Request $i"
  curl -s "http://localhost:8000/iclock/cdata?SN=TEST001" &
done
wait
```

**Expected:** Some requests should return `ERROR: Rate limit exceeded`

---

### Test 2.5: Role Enforcement
```bash
# Test as user WITHOUT ZK Admin role
bench --site yoursite execute "frappe.auth.login(user='testuser@example.com')"

# Try restricted function (should fail)
bench --site yoursite execute "from prime_att.zkteco.device_manager import restart_device; restart_device('TEST001')"
```

**Expected:** `PermissionError` or "You are not permitted"

---

## 3. Device Lifecycle Tests

### Test 3.1: Auto-Registration (New Device)
```bash
# Ensure allow_auto_register is enabled in ZK Settings

curl -v "http://localhost:8000/iclock/cdata?SN=NEWDEV999"
```

**Expected:**
```
< HTTP/1.1 200 OK
...
```

**Verify:**
```python
>>> frappe.get_doc("ZK Device", "NEWDEV999")
# Should exist with status="Pending"
```

---

### Test 3.2: Pending Device (Data Not Processed)
```bash
# Set device status to "Pending"

curl -X POST "http://localhost:8000/iclock/cdata?SN=PENDING_DEV&table=ATTLOG" \
  -d $'101\t2024-11-02 10:00:00\t0\t1\t\t'
```

**Expected:** Returns `OK`

**Verify:**
```python
>>> frappe.get_all("ZK Raw Log", filters={"device": "PENDING_DEV"})
# Should have entry

>>> frappe.get_all("ZK Punch", filters={"device": "PENDING_DEV"})
# Should be EMPTY (not processed)
```

---

### Test 3.3: Device Activity Tracking
```bash
curl "http://localhost:8000/iclock/cdata?SN=TEST001"
```

**Verify:**
```python
>>> device = frappe.get_doc("ZK Device", "TEST001")
>>> print(device.last_activity)  # Should be recent timestamp
>>> print(device.is_online)  # Should be 1
```

---

## 4. Command Lifecycle Tests

### Test 4.1: Command Autoincrement Naming
```python
bench --site yoursite console

>>> cmd1 = frappe.get_doc({"doctype": "ZK Device Command", "device": "TEST001", "command": "TEST1"})
>>> cmd1.insert()
>>> print(cmd1.name)  # Should be numeric: "1"

>>> cmd2 = frappe.get_doc({"doctype": "ZK Device Command", "device": "TEST001", "command": "TEST2"})
>>> cmd2.insert()
>>> print(cmd2.name)  # Should be "2"
```

---

### Test 4.2: Command Sent and Attempts Incremented
```bash
# Create pending command
bench --site yoursite console
>>> cmd = frappe.get_doc({"doctype": "ZK Device Command", "device": "TEST001", "command": "REBOOT", "status": "Pending", "attempts": 0})
>>> cmd.insert()
>>> frappe.db.commit()

# Poll for commands
curl "http://localhost:8000/iclock/getrequest?SN=TEST001"
```

**Expected:** `C:1:REBOOT` (or similar)

**Verify:**
```python
>>> cmd.reload()
>>> print(cmd.status)  # Should be "Sent"
>>> print(cmd.attempts)  # Should be 1
>>> print(cmd.sent_time)  # Should be set
```

---

### Test 4.3: Command Resend (Normal Command)
```python
# Create command with old sent_time
>>> from frappe.utils import now, add_to_date
>>> cmd = frappe.get_doc({"doctype": "ZK Device Command", "device": "TEST001", "command": "TEST", "status": "Sent", "attempts": 1})
>>> cmd.insert()
>>> frappe.db.set_value("ZK Device Command", cmd.name, "sent_time", add_to_date(now(), seconds=-150))
>>> frappe.db.commit()
```

```bash
# Poll again (timeout is 120s by default)
curl "http://localhost:8000/iclock/getrequest?SN=TEST001"
```

**Expected:** Command resent, attempts incremented to 2

---

### Test 4.4: Destructive Command NOT Resent
```python
# Create REBOOT command with old sent_time
>>> cmd = frappe.get_doc({"doctype": "ZK Device Command", "device": "TEST001", "command": "REBOOT", "status": "Sent", "attempts": 1})
>>> cmd.insert()
>>> frappe.db.set_value("ZK Device Command", cmd.name, "sent_time", add_to_date(now(), seconds=-150))
>>> frappe.db.commit()
```

```bash
curl "http://localhost:8000/iclock/getrequest?SN=TEST001"
```

**Expected:** Returns `OK` (command NOT resent)

**Verify:**
```python
>>> cmd.reload()
>>> print(cmd.status)  # Should be "Failed"
>>> print(cmd.response)  # Should be "No response (timeout)"
```

---

### Test 4.5: Command Success (Return=0)
```python
>>> cmd = frappe.get_doc({"doctype": "ZK Device Command", "device": "TEST001", "command": "TEST", "status": "Sent"})
>>> cmd.insert()
>>> cmd_id = cmd.name
>>> frappe.db.commit()
```

```bash
curl -X POST "http://localhost:8000/iclock/devicecmd?SN=TEST001&ID=$cmd_id" \
  -d "Return=0&CMD=TEST"
```

**Verify:**
```python
>>> cmd.reload()
>>> print(cmd.status)  # Should be "Done"
```

---

### Test 4.6: Command Failure (Return=1)
```python
>>> cmd = frappe.get_doc({"doctype": "ZK Device Command", "device": "TEST001", "command": "TEST", "status": "Sent"})
>>> cmd.insert()
>>> cmd_id = cmd.name
>>> frappe.db.commit()
```

```bash
curl -X POST "http://localhost:8000/iclock/devicecmd?SN=TEST001&ID=$cmd_id" \
  -d "Return=1&CMD=TEST&Error=Something failed"
```

**Verify:**
```python
>>> cmd.reload()
>>> print(cmd.status)  # Should be "Failed"
>>> print(cmd.response)  # Should contain error
```

---

## 5. HRMS Sync Tests

### Test 5.1: Local Sync (No Employee Mapping)
```python
# Create person without employee_id
>>> person = frappe.get_doc({"doctype": "ZK Person", "pin": "999", "full_name": "Test User", "is_active": 1})
>>> person.insert()

# Create check-in
>>> checkin = frappe.get_doc({"doctype": "ZK Check-in Out", "person": person.name, "log_time": now(), "log_type": "IN"})
>>> checkin.insert()

# Try sync
>>> from prime_att.zkteco.sync_manager import sync_checkin
>>> sync_checkin(checkin.name)
```

**Verify:**
```python
>>> checkin.reload()
>>> print(checkin.sync_status)  # Should be "No Mapping"
>>> print(checkin.sync_error)  # Should explain no employee mapping
```

---

### Test 5.2: Auto-Retry After Mapping
```python
# Add employee_id to person
>>> person.employee_id = "EMP-001"
>>> person.save()

# Trigger retry
>>> from prime_att.zkteco.enrollment_manager import retry_no_mapping_for_person
>>> retry_no_mapping_for_person(person.name)

# Wait for background job, then check
>>> checkin.reload()
>>> print(checkin.sync_status)  # Should be "Synced" or "Pending"
```

---

### Test 5.3: Remote Sync (Duplicate Check)
```python
# Configure ZK Sync Connector with remote_url, api_key, api_secret

# Check network request (enable logging or use test server)
# Should see GET request with filters=[["employee","=","EMP-001"],["time","=","2024-11-02 10:00:00"]]
```

---

## 6. Nginx Configuration Test

### Test 6.1: Without X-Frappe-Site-Name (Multi-Tenant)
```bash
# Remove or comment out X-Frappe-Site-Name header

curl -v -H "Host: yoursite.local" "http://server-ip/iclock/cdata?SN=TEST001"
```

**Expected:** May fail in multi-tenant setup

---

### Test 6.2: With X-Frappe-Site-Name
```bash
# Add to nginx config:
# proxy_set_header X-Frappe-Site-Name yoursite.local;

curl -v "http://server-ip/iclock/cdata?SN=TEST001"
```

**Expected:** Works correctly

---

## 7. Integration Testing with Simulator

```bash
cd /path/to/bench/apps/prime_att/tests

# Run device simulator
python test_device_simulator.py http://localhost:8000 TEST001 test
```

**Expected Output:**
```
Testing device simulator...
[OK] Handshake
[OK] Send ATTLOG
[OK] Poll commands
[OK] Send command result
All tests passed!
```

---

## Common Issues & Solutions

### Issue 1: Getting JSON Response
**Problem:** `{"message": "..."}`
**Solution:** 
- Check `handle_iclock_before_request()` is properly raising HTTPException
- Verify nginx passes requests to correct port
- Ensure `before_request` hook is registered in hooks.py

### Issue 2: 404 HTML Response
**Problem:** `<html>404 Not Found</html>`
**Solution:**
- Verify nginx location block is BEFORE `location /`
- Check nginx config syntax with `sudo nginx -t`
- Reload nginx after changes

### Issue 3: Commands Not Sent
**Problem:** `getrequest` always returns OK
**Solution:**
- Check device status is "Active" (not "Pending" or "Blocked")
- Verify command status is "Pending"
- Check command was committed to database

### Issue 4: Multi-Tenant Site Not Found
**Problem:** "Site not found" error
**Solution:**
- Add `proxy_set_header X-Frappe-Site-Name yoursite.local;` to nginx
- Verify site name matches exactly
- Reload nginx

---

## Performance Testing

### Load Test: Multiple Devices
```bash
# Simulate 10 devices polling simultaneously
for i in {1..10}; do
  curl -s "http://localhost:8000/iclock/getrequest?SN=DEV$i" &
done
wait
```

### Load Test: Bulk Attendance Upload
```bash
# Generate large ATTLOG
python -c "
for i in range(1, 1000):
    print(f'{i}\t2024-11-02 10:{i%60:02d}:00\t{i%2}\t1\t\t')
" > /tmp/bulk_attlog.txt

curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
  --data-binary @/tmp/bulk_attlog.txt
```

---

## Cleanup After Testing

```python
bench --site yoursite console

# Delete test devices
>>> frappe.db.delete("ZK Device", {"name": ["like", "TEST%"]})

# Delete test commands
>>> frappe.db.delete("ZK Device Command", {"device": ["like", "TEST%"]})

# Delete test logs
>>> frappe.db.delete("ZK Raw Log", {"device": ["like", "TEST%"]})
>>> frappe.db.delete("ZK Punch", {"device": ["like", "TEST%"]})

# Commit
>>> frappe.db.commit()
```

---

**End of Testing Guide**
