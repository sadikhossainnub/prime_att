# Punch Fetch Feature - Documentation

## Overview

ZK Punch DocType-এ একটি নতুন "Fetch Punches from Device" button যোগ করা হয়েছে যা device থেকে attendance logs (punches) fetch করতে পারে।

## Features

### 1. List View Button
- ZK Punch list view-এ "Fetch Punches from Device" button
- Device picker dialog দিয়ে device select করা যায়
- শুধুমাত্র Active/Pending status-এর devices show হয়

### 2. Role-Based Access
নিচের roles এই feature use করতে পারবে:
- ZK Admin
- System Manager
- ZK Operator

### 3. Command Template
ZK Settings-এ configurable command template:
- Field: `cmd_fetch_attlog`
- Default: `DATA QUERY ATTLOG`
- Device firmware অনুযায়ী customize করা যাবে

## Usage

### From ZK Punch List View

1. ZK Punch list page-এ যান
2. "Fetch Punches from Device" button-এ click করুন
3. Device select করুন dialog থেকে
4. "Fetch" button-এ click করুন
5. Command queue হবে এবং device next poll-এ punches পাঠাবে

### Command Queue

Device fetch করার জন্য একটি ZK Device Command তৈরি হয়:
- Action Name: "Fetch Attendance Logs"
- Status: "Pending" → "Sent" → "Success"/"Failed"
- Device next heartbeat-এ command receive করবে

## Technical Details

### Files Modified

1. **device_manager.py**
   - Added `fetch_punches_from_device()` function
   - Updated `derive_action_name()` to recognize QUERY ATTLOG

2. **zk_punch.js**
   - Added listview_settings with button
   - Device picker dialog implementation

3. **zk_settings.json**
   - Added `cmd_fetch_attlog` field
   - Default: "DATA QUERY ATTLOG"

### API Endpoint

```python
frappe.call({
    method: 'prime_att.zkteco.device_manager.fetch_punches_from_device',
    args: {
        device_sn: 'DEVICE_SERIAL_NUMBER'
    }
})
```

### Command Format

**Default Command:**
```
DATA QUERY ATTLOG
```

**UNVERIFIED:** এই command format ZKTeco protocol documentation থেকে নেওয়া। Real F18 device দিয়ে test করে যদি ভিন্ন format প্রয়োজন হয়, ZK Settings থেকে update করা যাবে।

## Testing

### Manual Test

```bash
# API call করে test করুন
curl -X POST "http://localhost:8000/api/method/prime_att.zkteco.device_manager.fetch_punches_from_device" \
  -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"device_sn": "TEST001"}'
```

### Expected Workflow

1. Button click → Command queued
2. Device polls → Receives command
3. Device sends ATTLOG data via POST to `/iclock/cdata?SN=xxx&table=ATTLOG`
4. Server processes → Creates ZK Punch records
5. List view refresh → New punches visible

### Check Command Status

1. Go to ZK Device Command list
2. Filter by Action Name: "Fetch Attendance Logs"
3. Check status: Pending → Sent → Success

## Configuration

### ZK Settings

Navigate to: **ZK Settings** → **Command Templates**

Field: **Fetch Attendance Logs Command**
- Default: `DATA QUERY ATTLOG`
- Customize if your device firmware requires different format

Examples:
```
DATA QUERY ATTLOG
DATA PULL ATTLOG
QUERY ATTLOG
```

## Troubleshooting

### Button Not Showing
- Clear browser cache
- Reload page with Ctrl+Shift+R
- Check user has required role (ZK Admin/System Manager/ZK Operator)

### Command Not Executing
- Check device is online (is_online=1)
- Verify device status is Active or Pending
- Check command timeout settings (default 120s)
- Review ZK Device Command list for errors

### No Punches Received
- Device may not have any new punches
- Check device's internal memory
- Verify command format in ZK Settings
- Check Error Log for parsing errors

## Security

### Role Requirements
- ZK Operator: Can fetch punches (read operation)
- ZK Admin: Can fetch punches + manage devices
- System Manager: Full access

### Audit Trail
সব fetch commands ZK Device Command-এ logged থাকে:
- Created by (user who initiated)
- Timestamp
- Status
- Result

## Best Practices

1. **Regular Fetching:** Device memory পূর্ণ হওয়ার আগে regular fetch করুন
2. **Batch Processing:** একসাথে multiple devices থেকে fetch করার জন্য script লিখুন
3. **Monitoring:** Failed commands-এর জন্য monitor করুন
4. **Testing:** Production-এ deploy করার আগে test device দিয়ে test করুন

## Future Enhancements

Possible improvements:
- Bulk fetch from all devices button
- Scheduled auto-fetch (hourly/daily)
- Fetch date range support
- Progress indicator for large fetches
- Auto-clear device memory after successful fetch

## Related Documentation

- TESTING_GUIDE.md - Testing procedures
- IMPLEMENTATION_UPDATE.md - Technical implementation
- API.md - API reference

---

**Version:** 2.0.0  
**Added:** November 2, 2026  
**Status:** Ready for testing
