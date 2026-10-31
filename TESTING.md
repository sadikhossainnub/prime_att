# Testing Guide for Prime Att

## Test Environment Setup

### Tested Configurations

**Frappe Versions:**
- v15.x (Compatibility verified)
- v16.x (Primary development version)

**Tested Devices:**
- ZKTeco F18 (Primary test device)
- Should work with: K40, K50, and all iClock-compatible devices

### Setup Test Environment

```bash
# 1. Install app
bench --site test.local install-app prime_att

# 2. Run migrations
bench --site test.local migrate

# 3. Create DocTypes
bench --site test.local execute prime_att.setup_doctypes.create_all_doctypes

# 4. Assign roles to test user
bench --site test.local add-user-role test@example.com "ZK Admin"
```

## Unit Tests

### Run All Tests

```bash
bench --site test.local run-tests --app prime_att
```

### Run Specific Test

```bash
bench --site test.local run-tests --app prime_att --module tests.test_protocol
```

### Test Coverage

```bash
bench --site test.local run-tests --app prime_att --coverage
```

## Device Simulator Testing

The device simulator mimics a real ZKTeco device for testing without hardware.

### Basic Test Scenario

```bash
cd /home/prime/frappe-bench/apps/prime_att/tests

# Run complete test scenario
python test_device_simulator.py http://test.local:8000 TESTDEV001 test
```

This will:
1. Perform handshake
2. Send 2 user records (USERINFO)
3. Send 2 attendance logs (ATTLOG)
4. Send 1 fingerprint template (FINGERTMP)
5. Poll for commands once

### Continuous Heartbeat Mode

```bash
# Run continuous polling (simulates real device)
python test_device_simulator.py http://test.local:8000 TESTDEV001 heartbeat
```

Leave running and test:
- Send commands from Frappe (device will execute)
- Real-time monitoring

### Custom Test Data

Edit `test_device_simulator.py` and modify the `run_test_scenario()` function to test specific scenarios.

## Integration Tests

### Test 1: Device Registration & Handshake

1. Start device simulator in heartbeat mode
2. Check **ZK Device** list - device should appear with status "Pending"
3. Change status to "Active"
4. Verify `last_activity` updates every 30 seconds
5. Check `is_online` checkbox is checked

**Expected Results:**
- Device auto-registered
- Online status accurate
- Raw logs captured in **ZK Raw Log**

### Test 2: Attendance Log Processing

1. Run simulator test scenario
2. Check **ZK Raw Log** - should see ATTLOG entry
3. Check **ZK Punch** - should see 2 punch records with correct timestamps
4. Check **ZK Check-in Out** - should see 2 check-in/out records
5. Verify timezone conversion (timestamps should be in site timezone)

**Expected Results:**
- All punches captured
- No duplicates (run twice, count should stay same)
- Status codes mapped correctly to IN/OUT

### Test 3: User Info Processing

1. Run simulator test scenario
2. Check **ZK Person** list - should see 2 new persons (PIN 101, 102)
3. Verify names: "John Doe", "Jane Smith"
4. Check device registration in person's Devices table

**Expected Results:**
- Persons auto-created
- Device added to person's device list with status "Pushed"

### Test 4: Fingerprint Template Storage

1. Run simulator test scenario
2. Check **ZK Person** for PIN 101
3. Verify device status changed to "Enrolled"
4. Check **ZK Fingerprint Enrollment** - if enrollment was pending, status should be "Enrolled"

**Expected Results:**
- Template stored (encrypted, only visible to ZK Admin)
- Enrollment record updated if exists

### Test 5: Push User to Device

1. Create **ZK Person**: PIN=201, Name="Test User"
2. Add device to Devices table
3. Click "Push to Device(s)"
4. Start simulator in heartbeat mode
5. Check **ZK Device Command** - should see "DATA UPDATE USERINFO" command with status "Sent"
6. Simulator should receive and execute command

**Expected Results:**
- Command created
- Command status: Pending → Sent → Done
- Device receives command in polling

### Test 6: Fingerprint Enrollment

**Prerequisites:**
- Person exists and is pushed to device
- Device is online (simulator running in heartbeat mode)

**Steps:**
1. Open **ZK Person** form
2. Click "Enroll Fingerprint"
3. Select device and finger index
4. Submit
5. Check **ZK Fingerprint Enrollment** - status should progress:
   - Queued → Sent → Waiting for User
6. Run simulator with FINGERTMP data for this person/finger
7. Status should change to "Enrolled"

**Expected Results:**
- Enrollment workflow completes
- Template stored securely
- Person device status = "Enrolled"

### Test 7: HRMS Sync (Local Mode)

**Prerequisites:**
- HRMS app installed
- Employee exists with `attendance_device_id` = "101"

**Steps:**
1. Configure **ZK Sync Connector**: Mode = "Local HRMS"
2. Run simulator test scenario (creates punches for PIN 101)
3. Check **ZK Check-in Out** - sync_status should be "Synced"
4. Check ERPNext **Employee Checkin** - should see new record
5. Verify no duplicates on second run

**Expected Results:**
- Employee Checkin created
- Idempotent (no duplicates)
- Mapping by attendance_device_id works

### Test 8: HRMS Sync (Remote Mode)

**Prerequisites:**
- Remote ERPNext instance accessible
- API key configured

**Steps:**
1. Configure **ZK Sync Connector**: 
   - Mode = "Remote ERPNext"
   - Set remote_url, api_key, api_secret
2. Run simulator test scenario
3. Check **ZK Check-in Out** - sync_status should be "Synced"
4. Check remote ERPNext **Employee Checkin** - should see new record
5. Check **ZK Sync Log** for success entry

**Expected Results:**
- Remote checkin created via API
- Error handling for network issues
- Retry mechanism works

### Test 9: Failed Sync Retry

1. Configure invalid remote URL (to force failure)
2. Run simulator test scenario
3. Check **ZK Check-in Out** - sync_status = "Failed"
4. Fix configuration
5. Click "Retry Sync" button on check-in form
6. Verify sync succeeds

**Expected Results:**
- Failure captured with error message
- Manual retry works
- Exponential backoff on auto-retry

### Test 10: Command Polling & Execution

1. Device simulator running in heartbeat mode
2. Send various commands from Frappe
3. Verify device receives and executes
4. Check command status updates

**Commands to test:**
- DATA QUERY USERINFO
- DATA UPDATE USERINFO PIN=X
- DATA DELETE USERINFO PIN=X
- ENROLL_FP (if supported)

### Test 11: Duplicate Detection

1. Run simulator test scenario twice with same data
2. Check **ZK Punch** count - should not double
3. Adjust duplicate_tolerance in **ZK Settings**
4. Test edge cases (within tolerance vs outside)

**Expected Results:**
- Duplicates correctly detected
- Tolerance setting respected

### Test 12: Unknown PIN Handling

1. Send ATTLOG for PIN that doesn't exist
2. Check **ZK Person** - should auto-create unmapped person
3. Check **ZK Check-in Out** - sync_status = "No Mapping"
4. Map person to employee
5. Retry sync
6. Verify sync succeeds

**Expected Results:**
- Unmapped person created
- Sync waits for mapping
- Works after mapping

## Load Testing

### Bulk Punch Test

```python
# In bench console
import requests
from datetime import datetime, timedelta

sn = "LOADTEST001"
base_url = "http://test.local:8000"

# Send 1000 punches
records = []
start_time = datetime.now()
for i in range(1000):
    pin = str(100 + (i % 100))  # 100 users
    ts = (start_time + timedelta(minutes=i)).strftime('%Y-%m-%d %H:%M:%S')
    records.append(f"{pin}\t{ts}\t0\t1\t")

payload = '\n'.join(records)

response = requests.post(
    f"{base_url}/iclock/cdata?SN={sn}&table=ATTLOG",
    data=payload.encode('utf-8')
)

print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
```

**Expected Results:**
- All punches processed
- Background queue handles load
- No data loss

## Regression Testing Checklist

Before each release, verify:

- [ ] Device registration (auto and manual)
- [ ] Handshake and configuration
- [ ] ATTLOG processing
- [ ] USERINFO processing
- [ ] FINGERTMP processing
- [ ] OPERLOG processing
- [ ] Command queue (all command types)
- [ ] User push to device
- [ ] Fingerprint enrollment flow
- [ ] Delete user from device
- [ ] Pull users from device
- [ ] Local HRMS sync
- [ ] Remote ERPNext sync
- [ ] Duplicate detection
- [ ] Timezone conversion
- [ ] Status code mapping
- [ ] Employee mapping (both methods)
- [ ] Bulk mapping tool
- [ ] Failed sync retry
- [ ] Online/offline detection
- [ ] Rate limiting
- [ ] Security (comm key validation)
- [ ] Encrypted template storage

## Performance Benchmarks

Target performance on modern server (4 CPU, 8GB RAM):

- Handshake response: < 100ms
- ATTLOG processing: < 50ms per record
- Duplicate check: < 10ms
- Sync to HRMS: < 200ms per record
- Command poll: < 50ms

Monitor with:
```bash
bench --site test.local watch
```

## Known Issues & Workarounds

### Issue: nginx returns JSON instead of text/plain

**Symptom:** Device shows error, logs show JSON response

**Fix:** Ensure nginx config has direct pass-through for /iclock/* BEFORE other location blocks

### Issue: Device not polling commands

**Symptom:** Commands stuck in "Pending" status

**Fix:** 
- Check device poll interval setting
- Verify device is sending heartbeat (check last_activity)
- Test with simulator in heartbeat mode

### Issue: Fingerprint enrollment timeout

**Symptom:** Status stays "Waiting for User", never becomes "Enrolled"

**Fix:**
- Check device firmware compatibility
- Try custom command template in ZK Command Template
- For F18: Verify command format in device manual

### Issue: Sync fails with "No Mapping"

**Symptom:** Check-ins not syncing to HRMS

**Fix:**
- Set ZK Person.employee field, OR
- Set Employee.attendance_device_id field
- Run bulk mapping tool

## Version Compatibility Testing

### Frappe v15 Specifics

```bash
# Test on v15 site
bench --site v15.local install-app prime_att
bench --site v15.local migrate

# Run compatibility tests
bench --site v15.local run-tests --app prime_att
```

**Known Differences:**
- Minor API changes handled internally
- No feature differences

### Frappe v16 Specifics

Full support, all features work.

## Reporting Issues

When reporting issues, include:

1. Frappe version
2. Device model and firmware
3. Steps to reproduce
4. Error log from **Error Log** doctype
5. Sample from **ZK Raw Log** (if protocol issue)
6. Command status from **ZK Device Command** (if command issue)
7. Sync error from **ZK Check-in Out** (if sync issue)
