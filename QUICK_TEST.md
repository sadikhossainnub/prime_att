# Quick Test Reference Card

**One-page guide for rapid testing of all 9 implemented features**

---

## Prerequisites
```bash
# Site running
bench start

# In new terminal
cd ~/frappe-bench
```

---

## Issue #1: Plain-text Responses (BLOCKER)

```bash
# Test handshake - MUST return text/plain
curl -v "http://localhost:8000/iclock/cdata?SN=TEST001" 2>&1 | grep "Content-Type"
# Expected: Content-Type: text/plain

# Test 404 - MUST be plain-text
curl -v "http://localhost:8000/iclock/unknown?SN=TEST001"
# Expected: 404, plain-text body
```

**Pass Criteria:** `Content-Type: text/plain` (NOT application/json or text/html)

---

## Issue #2: Command Lifecycle

```bash
# Check command uses autoincrement naming
bench console
>>> import frappe
>>> cmd = frappe.get_doc({"doctype": "ZK Device Command", "device": "TEST001", "command": "TEST", "action_name": "Test"})
>>> cmd.insert()
>>> print(cmd.name)  # Should be numeric: "1", "2", "3"...
>>> exit()

# Test command retrieval
curl "http://localhost:8000/iclock/getrequest?SN=TEST001"
# Expected: C:1:TEST or similar
```

**Pass Criteria:** Command name is numeric, appears in getrequest

---

## Issue #3: Security - Roles

```python
# Test role enforcement (bench console)
import frappe
frappe.set_user("test_user@example.com")  # User WITHOUT ZK Admin role

try:
    frappe.call("prime_att.zkteco.device_manager.restart_device", device_sn="TEST001")
    print("FAIL: Should have raised PermissionError")
except frappe.PermissionError:
    print("PASS: Role check working")
```

**Pass Criteria:** PermissionError raised for non-admin users

---

## Issue #3: Security - Device Validation

```bash
# Test with wrong comm_key (set comm_key on TEST001 device first)
curl "http://localhost:8000/iclock/cdata?SN=TEST001&key=wrongkey"
# Expected: ERROR: Invalid or blocked device

# Test rate limiting (send 61 requests fast)
for i in {1..61}; do curl -s "http://localhost:8000/iclock/cdata?SN=TEST001" & done; wait
# 61st request should fail
```

**Pass Criteria:** Wrong key rejected, rate limit enforced

---

## Issue #4: Standalone Mode

```bash
# Check employee_id is Data field
bench console
>>> import frappe
>>> meta = frappe.get_meta("ZK Person")
>>> field = next(f for f in meta.fields if f.fieldname == "employee_id")
>>> print(field.fieldtype)  # Should be "Data" not "Link"
>>> exit()
```

**Pass Criteria:** employee_id fieldtype is "Data"

---

## Issue #5: IN/OUT Modes

```bash
# Set mode to "Alternate Per Person Per Day" in ZK Settings

# Send 4 punches same person same day
for i in 1 2 3 4; do
  curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
    -d "555	2024-01-15 0${i}:00:00	0	1	"
  sleep 1
done

# Check ZK Check-in Out list, filter by person PIN 555
# Expected: IN, OUT, IN, OUT pattern
```

**Pass Criteria:** Alternating IN/OUT pattern

---

## Issue #6: Parser - Invalid Timestamps

```bash
# Send invalid timestamp
curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
  -d "999	BAD_DATE	0	1	"

# Check ZK Punch list - should NOT create record
# Check Error Log - should have "invalid timestamp" error
```

**Pass Criteria:** Record NOT created, error logged (NOT current time)

---

## Issue #6: Parser - key=value Format

```bash
# Send key=value format
curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
  -d "PIN=777 DateTime=2024-01-15 10:00:00 Status=1"

# Check ZK Punch list - record should be created
```

**Pass Criteria:** Record created with correct values

---

## Issue #6: Parser - CRLF/BOM

```bash
# Create file with BOM and CRLF
printf '\xEF\xBB\xBF888\t2024-01-15 11:00:00\t0\t1\t\r\n' > /tmp/test_bom.txt

curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
  --data-binary @/tmp/test_bom.txt

# Check ZK Punch list - record should be created
```

**Pass Criteria:** Record created despite BOM and CRLF

---

## Issue #7: HRMS Sync

```python
# Test remote sync (bench console)
import frappe
from prime_att.zkteco.sync_manager import sync_remote

# Create test check-in
checkin = frappe.get_doc({
    "doctype": "ZK Check-in Out",
    "person": "ZK-PERSON-001",  # Must exist with employee_id set
    "log_time": "2024-01-15 09:00:00",
    "log_type": "IN",
    "device": "TEST001"
})
checkin.insert()

# Configure remote sync in ZK Sync Connector
# Then test sync
from prime_att.zkteco.sync_manager import sync_checkin
sync_checkin(checkin.name)

# Check sync_status
print(frappe.get_value("ZK Check-in Out", checkin.name, "sync_status"))
# Should be "Synced" or "Failed" with error message
```

**Pass Criteria:** Sync attempts, proper error handling

---

## Issue #8: Scheduler - Timeouts

```bash
# Create old enrollment (5 minutes ago)
bench console
>>> import frappe
>>> from frappe.utils import add_to_date, now_datetime
>>> doc = frappe.get_doc({"doctype": "ZK Fingerprint Enrollment", "device": "TEST001", "person_pin": "111", "finger_index": "0", "status": "Waiting for User"})
>>> doc.insert()
>>> frappe.db.set_value("ZK Fingerprint Enrollment", doc.name, "creation", add_to_date(now_datetime(), minutes=-5))
>>> frappe.db.commit()
>>> exit()

# Trigger scheduler
bench execute prime_att.zkteco.scheduler.mark_timeout_enrollments

# Check enrollment status - should be "Timeout"
```

**Pass Criteria:** Enrollment marked Timeout

---

## Issue #8: Placeholders

```bash
# Send punch from unknown PIN
curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
  -d "9999	2024-01-15 12:00:00	0	1	"

# Check ZK Person - should exist with is_placeholder=1

# Send USERINFO for same PIN
curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=USERINFO" \
  -d "9999	John Doe	0		"

# Check ZK Person - is_placeholder should now be 0
```

**Pass Criteria:** Placeholder created, then promoted

---

## Issue #9: DuplicateEntry Handling

```python
# Test concurrent creation (save as test_concurrent.py)
import requests
import threading

def punch(pin):
    requests.post(
        "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG",
        headers={"Content-Type": "text/plain"},
        data=f"{pin}\t2024-01-15 13:00:00\t0\t1\t"
    )

# Send 10 concurrent requests same PIN
threads = [threading.Thread(target=punch, args=("8888",)) for _ in range(10)]
for t in threads: t.start()
for t in threads: t.join()

# Check ZK Person - should only have ONE record for PIN 8888
# Check ZK Punch - should have 10 records
# Check Error Log - should have NO DuplicateEntryError
```

```bash
python3 test_concurrent.py
```

**Pass Criteria:** No DuplicateEntry errors, one person, multiple punches

---

## Issue #9: update_device_activity Optimization

```python
# Test optimization (bench console)
import frappe
from prime_att.zkteco.device_manager import update_device_activity

# Check it uses set_value (not get_doc)
import time
start = time.time()
update_device_activity("TEST001", pushver="3.0", language="69")
elapsed = time.time() - start

print(f"Time: {elapsed:.3f}s")  # Should be < 0.1s

# Verify modified timestamp NOT updated
doc = frappe.get_doc("ZK Device", "TEST001")
print(f"Modified: {doc.modified}")  # Should not change on next call

update_device_activity("TEST001")
doc.reload()
print(f"Modified: {doc.modified}")  # Should be same
```

**Pass Criteria:** Fast execution (< 0.1s), modified timestamp unchanged

---

## Full Test Suite

```bash
# Run all curl tests from TESTING_GUIDE.md
cat TESTING_GUIDE.md | grep "^curl" | bash

# Run extended tests
cat TESTING_GUIDE_EXTENDED.md | grep "^curl" | bash
```

---

## Quick Health Check

```bash
# All-in-one health check
echo "=== Plain-text Test ==="
curl -v "http://localhost:8000/iclock/cdata?SN=TEST001" 2>&1 | grep -E "(Content-Type|OK)"

echo -e "\n=== Send Test Punch ==="
curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
  -d "123	2024-01-15 09:00:00	0	1	"

echo -e "\n=== Check Commands ==="
curl "http://localhost:8000/iclock/getrequest?SN=TEST001"

echo -e "\n=== Test Invalid Timestamp (should skip) ==="
curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
  -d "999	INVALID	0	1	"

echo -e "\n=== Test key=value Format ==="
curl -X POST "http://localhost:8000/iclock/cdata?SN=TEST001&table=ATTLOG" \
  -d "PIN=456 DateTime=2024-01-15 10:00:00 Status=0"

echo -e "\n=== Done ==="
```

---

## Expected Results Summary

| Test | Expected Result |
|------|----------------|
| Plain-text | Content-Type: text/plain |
| Command naming | Numeric IDs (1, 2, 3...) |
| Role check | PermissionError for non-admin |
| Wrong comm_key | ERROR: Invalid device |
| Rate limit | 61st request fails |
| employee_id | Data field (not Link) |
| IN/OUT alternate | IN→OUT→IN→OUT pattern |
| Invalid timestamp | Skipped, NOT now() |
| key=value | Parsed correctly |
| CRLF/BOM | Handled gracefully |
| HRMS sync | Status = Synced/Failed |
| Scheduler timeout | Status = Timeout |
| Placeholder | is_placeholder=1→0 |
| Concurrent | No DuplicateEntry |
| update_device | < 0.1s, modified unchanged |

---

## Troubleshooting Quick Reference

**Plain-text not working:**
```bash
# Check nginx config
sudo nano /etc/nginx/sites-available/yoursite
# Must have: proxy_set_header X-Frappe-Site-Name yoursite;
sudo nginx -t && sudo systemctl reload nginx
```

**Scheduler not running:**
```bash
bench doctor  # Check status
bench enable-scheduler  # Enable
bench execute prime_att.zkteco.scheduler.mark_timeout_enrollments  # Manual
```

**Check logs:**
```bash
tail -f ~/frappe-bench/logs/*.log
# Or in Frappe UI: Error Log doctype
```

---

**All tests passing? ✅ Ready for F18 device testing!**
