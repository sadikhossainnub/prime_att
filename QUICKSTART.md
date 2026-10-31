# Quick Start Guide - Prime Att

Get your ZKTeco devices connected and syncing in 15 minutes.

## Prerequisites

- Frappe v15 or v16 installed
- Nginx configured
- ZKTeco device with network connectivity
- (Optional) HRMS app installed for attendance sync

## Installation (5 minutes)

```bash
# 1. Get the app
cd /path/to/frappe-bench
bench get-app /home/prime/frappe-bench/apps/prime_att

# 2. Install on your site
bench --site yoursite.local install-app prime_att

# 3. Run setup
bench --site yoursite.local execute prime_att.setup_doctypes.create_all_doctypes
bench --site yoursite.local execute prime_att.install_script.after_install
```

## Nginx Configuration (2 minutes)

Add to `/etc/nginx/conf.d/yoursite.conf` **BEFORE** the main `location /` block:

```nginx
location ~* ^/iclock/(cdata|getrequest|devicecmd) {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_pass_header Content-Type;
    proxy_buffering off;
}
```

Reload nginx:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Device Configuration (3 minutes)

On your ZKTeco device:

1. Navigate to: **Comm** → **Cloud Server** (or **Push Settings**)
2. Configure:
   - **Server IP**: Your Frappe server IP/hostname
   - **Server Port**: 80 (or 443 for HTTPS)
   - **Push URL**: `/iclock/cdata`
   - **Push Protocol**: HTTP
   - **Push Interval**: 30 seconds
   - **Device SN**: Note this down (e.g., DEVICE001)
3. Save and test connection

## First Connection (2 minutes)

1. Device will automatically register in Frappe
2. Go to: **ZK Device** list
3. Find your device (status: Pending)
4. Click to open, set:
   - **Device Name**: Meaningful name (e.g., "Main Entrance")
   - **Status**: Active
   - **Location**: Office location
5. Save

Device should show **Is Online** ✓ within 30 seconds.

## Register Your First User (3 minutes)

### Method 1: Create New User

1. Go to: **ZK Person** → New
2. Fill in:
   - **PIN**: 101 (unique number)
   - **Full Name**: John Doe
   - **Card Number**: (optional)
3. In **Devices** table, add your device
4. Save
5. Click **Push to Device(s)**
6. Click **Enroll Fingerprint**:
   - Select device
   - Choose finger (0-9)
   - Submit
7. **Go to device and place finger on scanner**
8. Check **ZK Fingerprint Enrollment** - status should become "Enrolled"

### Method 2: Import from Device

If users are already registered on the device:

1. Open **ZK Device** form
2. Click **Pull Users**
3. Wait for device to respond
4. Check **ZK Person** list - users imported automatically

## Test Attendance (1 minute)

1. Have user punch on the device
2. Go to: **ZK Punch** list
3. You should see the punch record within seconds
4. Go to: **ZK Check-in Out** list
5. You should see the processed check-in/out record

## Set Up HRMS Sync (Optional)

### Local HRMS

If HRMS app is installed on same site:

1. Go to: **ZK Sync Connector**
2. Set:
   - **Mode**: Local HRMS
   - **Auto Sync**: ✓
3. Save
4. Map users:
   - Option A: Set **ZK Person.Employee** field
   - Option B: Set **Employee.attendance_device_id** = ZK Person PIN
5. Punches will automatically sync to **Employee Checkin**

### Remote ERPNext

To sync to a different ERPNext instance:

1. Get API credentials from remote site:
   ```bash
   # On remote site
   bench --site remote.local execute frappe.generate_api_key --kwargs "{'user':'your@email.com'}"
   ```
2. Go to: **ZK Sync Connector**
3. Set:
   - **Mode**: Remote ERPNext
   - **Remote URL**: https://remote-erpnext.com
   - **API Key**: (from step 1)
   - **API Secret**: (from step 1)
   - **Auto Sync**: ✓
4. Save

## Verify Everything Works

Run this checklist:

- [ ] Device shows "Is Online" in ZK Device
- [ ] Device last activity updates every ~30 seconds
- [ ] User can be pushed to device successfully
- [ ] Fingerprint enrollment completes
- [ ] Punches appear in ZK Punch list
- [ ] Check-ins appear in ZK Check-in Out list
- [ ] (If HRMS) Check-ins sync to Employee Checkin

## Troubleshooting

### Device Not Connecting

```bash
# Check nginx logs
sudo tail -f /var/log/nginx/error.log

# Check Frappe logs
tail -f ~/frappe-bench/sites/yoursite.local/logs/worker.error.log

# Test with simulator
cd ~/frappe-bench/apps/prime_att/tests
python test_device_simulator.py http://yoursite.local TESTDEV001 test
```

### No Punches Received

1. Check **ZK Raw Log** - are payloads coming in?
2. If yes: Check background worker is running
   ```bash
   bench --site yoursite.local doctor
   ```
3. If no: Check device status is "Active", not "Pending" or "Blocked"

### Sync Not Working

1. Check **ZK Check-in Out** → sync_error field
2. Common issues:
   - **"No Mapping"**: User not mapped to employee
   - **"Connection error"**: Remote URL not reachable
   - **"API Error 403"**: Invalid API credentials

Fix and click **Retry Sync** button.

## Next Steps

- **Add more users**: Bulk import or create individually
- **Configure status mappings**: Customize IN/OUT rules in ZK Settings
- **Set up shifts in HRMS**: For automatic attendance calculation
- **Monitor**: Set up alerts for offline devices
- **Scale**: Add more devices, they all connect to same endpoints

## Getting Help

- **Documentation**: See README.md and TESTING.md
- **Logs**: Check Error Log doctype in Frappe
- **Debug**: Enable debug mode and check ZK Raw Log
- **Community**: Post in Frappe forum with "prime_att" tag

## Common Scenarios

### Scenario 1: 100 Employees, 1 Device

1. Create 100 ZK Person records (or import from CSV)
2. Bulk push to device using custom script
3. Users enroll fingerprints on device directly
4. Templates automatically captured
5. Set up HRMS sync
6. Done!

### Scenario 2: Multiple Offices, Multiple Devices

1. Add all devices (each gets unique SN)
2. Set location for each device
3. Push users to relevant devices (users can be on multiple devices)
4. All punches flow to central system
5. HRMS processes all attendance

### Scenario 3: Remote Branch with VPN

1. Ensure branch device can reach main server via VPN
2. Configure device with main server IP
3. Everything else same as local device
4. Consider local caching if connection unreliable

## Performance Tips

- **Large installations** (>1000 users): Increase worker count
  ```bash
  bench setup supervisor --yes
  # Edit supervisor conf to add more workers
  ```
- **High punch volume**: Enable Redis queue monitoring
- **Slow sync**: Increase batch_size in ZK Sync Connector
- **Background processing**: Ensure worker is running
  ```bash
  bench worker --queue default
  ```

That's it! You should now have a fully functional ZKTeco attendance system.
