# Extended Testing Guide - New Features

This guide covers testing for Issues #5, #6, #8, and #9 (newly implemented).

## Prerequisites

```bash
# Ensure site is running
cd ~/frappe-bench
bench start

# In another terminal
cd ~/frappe-bench
```

---

## Issue #5: IN/OUT Detection Modes

### Test 1: Device Status Mapping Mode (Default)

1. **Configure Mode:**
   - Open ZK Settings
   - Set "IN/OUT Mode" = "Device Status Mapping"
   - Save

2. **Send Test Punches:**

```bash
# Punch with Status=0 (Check-In)
curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
  -H "Content-Type: text/plain" \
  -d "123	2024-01-15 09:00:00	0	1	"

# Punch with Status=1 (Check-Out)
curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
  -H "Content-Type: text/plain" \
  -d "123	2024-01-15 17:00:00	1	1	"
```

3. **Verify Results:**
   - Open "ZK Check-in Out" list
   - First record: log_type = "IN"
   - Second record: log_type = "OUT"

---

### Test 2: Alternate Per Person Per Day Mode

1. **Configure Mode:**
   - Open ZK Settings
   - Set "IN/OUT Mode" = "Alternate Per Person Per Day"
   - Save

2. **Send Multiple Punches Same Day:**

```bash
# First punch - should be IN
curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
  -H "Content-Type: text/plain" \
  -d "456	2024-01-15 08:00:00	0	1	"

# Second punch - should be OUT
curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
  -H "Content-Type: text/plain" \
  -d "456	2024-01-15 12:00:00	0	1	"

# Third punch - should be IN
curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
  -H "Content-Type: text/plain" \
  -d "456	2024-01-15 13:00:00	0	1	"

# Fourth punch - should be OUT
curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
  -H "Content-Type: text/plain" \
  -d "456	2024-01-15 18:00:00	0	1	"
```

3. **Verify Results:**
   - Open "ZK Check-in Out" list, filter by PIN 456
   - Expected pattern: IN → OUT → IN → OUT
   - Verify times: 08:00, 12:00, 13:00, 18:00

---

### Test 3: First/Last of Day Mode

1. **Configure Mode:**
   - Open ZK Settings
   - Set "IN/OUT Mode" = "First/Last of Day"
   - Save

2. **Send Multiple Punches:**

```bash
# First punch - should be IN
curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
  -H "Content-Type: text/plain" \
  -d "789	2024-01-15 07:00:00	0	1	"

# Second punch - should be OUT
curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
  -H "Content-Type: text/plain" \
  -d "789	2024-01-15 11:00:00	0	1	"

# Third punch - should be OUT
curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
  -H "Content-Type: text/plain" \
  -d "789	2024-01-15 16:00:00	0	1	"
```

3. **Verify Results:**
   - Open "ZK Check-in Out" list, filter by PIN 789
   - Expected: IN, OUT, OUT
   - First punch of day = IN, rest = OUT

---

## Issue #6: Parser Improvements

### Test 1: Invalid Timestamps Rejected

```bash
# Invalid timestamp - should be skipped and logged
curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
  -H "Content-Type: text/plain" \
  -d "999	INVALID_DATE	0	1	"

# Valid timestamp - should be processed
curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
  -H "Content-Type: text/plain" \
  -d "999	2024-01-15 10:00:00	0	1	"
```

**Verify:**
- Check Error Log for "ATTLOG line 1 has invalid timestamp"
- Check ZK Punch list - should only have ONE record (valid one)
- Timestamp should NOT be current time (now())

---

### Test 2: key=value Format

```bash
# Test key=value format (newer firmware)
curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
  -H "Content-Type: text/plain" \
  -d "PIN=111 DateTime=2024-01-15 14:00:00 Status=1 Verify=15"
```

**Verify:**
- Open ZK Punch list
- Record created with PIN=111
- Time = 14:00:00
- Status = 1

---

### Test 3: CRLF and BOM Handling

Create test file with CRLF:
```bash
# Create payload with Windows line endings and BOM
printf '\xEF\xBB\xBF222\t2024-01-15 15:00:00\t0\t1\t\r\n333\t2024-01-15 15:05:00\t1\t1\t\r\n' > /tmp/test_crlf.txt

# Send it
curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
  -H "Content-Type: text/plain" \
  --data-binary @/tmp/test_crlf.txt
```

**Verify:**
- Both records created (PIN 222 and 333)
- No parsing errors in Error Log
- BOM and CRLF handled correctly

---

### Test 4: Line Number Error Logging

```bash
# Send multi-line with one invalid
curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
  -H "Content-Type: text/plain" \
  -d $'444\t2024-01-15 16:00:00\t0\t1\t\n555\tBAD_TIME\t0\t1\t\n666\t2024-01-15 16:10:00\t0\t1\t'
```

**Verify:**
- Check Error Log
- Error message includes: "ATTLOG line 2 has invalid timestamp"
- Two records created (444 and 666)
- Line 2 (555) skipped

---

## Issue #8: Scheduler Tasks

### Test 1: Enrollment Timeout

1. **Create Test Enrollment:**
   ```python
   # Run in frappe console: bench console
   import frappe
   from frappe.utils import add_to_date, now_datetime
   
   # Create old enrollment
   doc = frappe.get_doc({
       "doctype": "ZK Fingerprint Enrollment",
       "device": "TEST001",
       "person_pin": "111",
       "finger_index": "0",
       "status": "Waiting for User"
   })
   doc.insert()
   
   # Backdate it to 5 minutes ago
   old_time = add_to_date(now_datetime(), minutes=-5)
   frappe.db.set_value("ZK Fingerprint Enrollment", doc.name, "creation", old_time)
   frappe.db.commit()
   print(f"Created enrollment: {doc.name}")
   ```

2. **Wait for Scheduler:**
   - Wait 10+ minutes OR manually trigger:
   ```bash
   bench execute prime_att.zkteco.scheduler.mark_timeout_enrollments
   ```

3. **Verify:**
   - Open enrollment record
   - Status should be "Timeout"
   - Comment added with timeout message
   - Check Error Log for "Marked X enrollments as Timeout"

---

### Test 2: Command Timeout

1. **Create Old Command:**
   ```python
   # Run in frappe console
   import frappe
   from frappe.utils import add_to_date, now_datetime
   
   doc = frappe.get_doc({
       "doctype": "ZK Device Command",
       "device": "TEST001",
       "command": "TEST COMMAND",
       "status": "Sent",
       "action_name": "Test Action"
   })
   doc.insert()
   
   # Backdate to 3 minutes ago
   old_time = add_to_date(now_datetime(), minutes=-3)
   frappe.db.set_value("ZK Device Command", doc.name, "modified", old_time)
   frappe.db.commit()
   print(f"Created command: {doc.name}")
   ```

2. **Trigger Scheduler:**
   ```bash
   bench execute prime_att.zkteco.scheduler.mark_timeout_commands
   ```

3. **Verify:**
   - Command status = "Timeout"
   - Comment added
   - Error Log entry

---

### Test 3: Cleanup Old Punches

1. **Create Old Punch:**
   ```python
   # Run in frappe console
   import frappe
   from frappe.utils import add_to_date, now_datetime
   
   doc = frappe.get_doc({
       "doctype": "ZK Punch",
       "device": "TEST001",
       "pin": "999",
       "punch_time": add_to_date(now_datetime(), days=-100),
       "status_code": "0",
       "verify_type": "1"
   })
   doc.insert()
   frappe.db.commit()
   ```

2. **Trigger Scheduler:**
   ```bash
   bench execute prime_att.zkteco.scheduler.cleanup_old_punches
   ```

3. **Verify:**
   - Check Error Log for "Found X old punch records"
   - Punch NOT deleted (just logged notice)

---

## Issue #8: Placeholder Persons

### Test 1: Auto-create Placeholder

```bash
# Punch from unknown PIN
curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
  -H "Content-Type: text/plain" \
  -d "8888	2024-01-15 09:00:00	0	1	"
```

**Verify:**
- ZK Person created with PIN=8888
- full_name = "User 8888"
- **is_placeholder = 1** ✓
- Check-in record created

---

### Test 2: Promote Placeholder

```bash
# Device pushes USERINFO for same PIN
curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=USERINFO" \
  -H "Content-Type: text/plain" \
  -d "8888	John Doe	0		12345"
```

**Verify:**
- Same ZK Person (PIN=8888) updated
- full_name = "John Doe"
- **is_placeholder = 0** ✓ (promoted)

---

### Test 3: Placeholders Not Synced

1. **Create Mix of Persons:**
   - Person A: PIN=1001, is_placeholder=0, is_active=1
   - Person B: PIN=8888, is_placeholder=1, is_active=1

2. **Sync All Users:**
   - Open ZK Device form
   - Click "Sync All Users"

3. **Verify:**
   - Check ZK Device Command list
   - Should see command for Person A (PIN=1001)
   - Should NOT see command for Person B (PIN=8888, placeholder)

---

## Issue #9: DuplicateEntryError Handling

### Test: Concurrent Person Creation

This requires simulating concurrent requests. Use a simple script:

```python
# Save as test_concurrent.py
import requests
import threading

def send_punch(pin):
    url = "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG"
    headers = {"Content-Type": "text/plain"}
    data = f"{pin}\t2024-01-15 10:00:00\t0\t1\t"
    try:
        response = requests.post(url, headers=headers, data=data)
        print(f"PIN {pin}: {response.status_code}")
    except Exception as e:
        print(f"PIN {pin} error: {e}")

# Send 10 concurrent requests with same PIN
pin = "9999"
threads = []
for i in range(10):
    t = threading.Thread(target=send_punch, args=(pin,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print("All requests completed")
```

Run test:
```bash
cd ~/frappe-bench
python3 test_concurrent.py
```

**Verify:**
- All 10 requests succeed (no DuplicateEntryError)
- Only ONE ZK Person created (PIN=9999)
- 10 ZK Punch records created
- Check Error Log - no duplicate entry errors

---

## Integration Test: Full Workflow

### Scenario: Unknown Employee Punches → Identified → Synced

1. **Unknown Punch:**
   ```bash
   curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
     -H "Content-Type: text/plain" \
     -d "5555	2024-01-15 08:30:00	0	1	"
   ```
   - Verify: Person created with is_placeholder=1

2. **Device Identifies User:**
   ```bash
   curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=USERINFO" \
     -H "Content-Type: text/plain" \
     -d "5555	Jane Smith	0		67890"
   ```
   - Verify: Person promoted (is_placeholder=0, name updated)

3. **More Punches (Alternate Mode):**
   ```bash
   curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
     -H "Content-Type: text/plain" \
     -d "5555	2024-01-15 12:00:00	0	1	"
   
   curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
     -H "Content-Type: text/plain" \
     -d "5555	2024-01-15 13:00:00	0	1	"
   
   curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
     -H "Content-Type: text/plain" \
     -d "5555	2024-01-15 17:30:00	0	1	"
   ```
   - Verify: Check-in/out records with correct IN/OUT pattern

4. **Map to Employee:**
   - Open ZK Person (PIN=5555)
   - Set employee_id = "EMP-001"
   - Save

5. **Sync to HRMS:**
   - Check ZK Check-in Out records
   - Verify sync_status = "Synced" or "Pending"

---

## Performance Test

### High-Volume Punch Upload

```bash
# Generate 1000 punches
for i in $(seq 1 1000); do
  pin=$((1000 + i))
  hour=$((8 + (i % 10)))
  minute=$((i % 60))
  echo "${pin}\t2024-01-15 ${hour}:${minute}:00\t0\t1\t"
done > /tmp/bulk_punches.txt

# Upload in one request
curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
  -H "Content-Type: text/plain" \
  --data-binary @/tmp/bulk_punches.txt
```

**Verify:**
- All 1000 punches processed
- No DuplicateEntryError
- Check processing time in logs
- Verify persons created with is_placeholder=1

---

## Troubleshooting

### Scheduler Not Running
```bash
# Check scheduler status
bench doctor

# Enable scheduler if disabled
bench enable-scheduler

# Manually trigger specific job
bench execute prime_att.zkteco.scheduler.mark_timeout_enrollments
```

### Error Logs Not Showing
```bash
# Check Error Log in Frappe UI
# Or query directly
bench console
>>> frappe.get_all("Error Log", filters={"error": ["like", "%ATTLOG%"]}, limit=10)
```

### Parsers Not Working
```bash
# Enable debug logging
bench --site <site_name> set-config developer_mode 1

# Check logs
tail -f ~/frappe-bench/logs/*.log
```

---

## Expected Results Summary

| Feature | Test | Expected Result |
|---------|------|----------------|
| IN/OUT Modes | Device Mapping | Uses status code |
| IN/OUT Modes | Alternate | IN→OUT→IN→OUT pattern |
| IN/OUT Modes | First/Last | First=IN, rest=OUT |
| Parser | Invalid timestamp | Skipped, logged, NOT now() |
| Parser | key=value format | Parsed correctly |
| Parser | CRLF/BOM | Handled gracefully |
| Scheduler | Enrollment timeout | Status→Timeout after 180s |
| Scheduler | Command timeout | Status→Timeout after 120s |
| Placeholder | Auto-create | is_placeholder=1 |
| Placeholder | Promotion | is_placeholder=0 |
| Placeholder | Sync skip | Not in sync commands |
| Concurrent | DuplicateEntry | No errors, one person |

---

## Notes

- All timestamps in examples use format: `YYYY-MM-DD HH:MM:SS`
- Default site URL: `http://localhost:8000` (adjust for your setup)
- Cron intervals: 5 min (commands), 10 min (enrollments), daily (cleanup)
- All tests can be run without real device
- For production testing, use real F18 device with actual firmware
