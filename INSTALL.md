# Prime Att - Installation Guide

## সঠিক Installation Order

Installation এর সময় error এড়ানোর জন্য এই order follow করুন:

### Method 1: Automated Installation (Recommended)

```bash
# Bench directory তে যান
cd /path/to/frappe-bench

# App install করুন (DocTypes তৈরি হবে না)
bench --site yoursite.local install-app prime_att

# DocTypes তৈরি করুন
bench --site yoursite.local execute prime_att.setup_doctypes.create_all_doctypes

# Default settings তৈরি করুন
bench --site yoursite.local execute prime_att.install_script.setup_defaults

# Roles setup করুন
bench --site yoursite.local execute prime_att.install_script.setup_roles

# Migration run করুন
bench --site yoursite.local migrate

# Assets build করুন
bench build --app prime_att

# Restart
bench restart
```

### Method 2: Using Install Script

```bash
cd /path/to/frappe-bench
chmod +x apps/prime_att/install.sh
apps/prime_att/install.sh yoursite.local
```

## যদি Installation Error হয়

### Error: Module import failed for ZK Command Template

**কারণ:** DocTypes create হওয়ার আগে after_install hook run হয়ে গেছে

**Fix:**

```bash
# 1. DocTypes manually create করুন
bench --site yoursite.local execute prime_att.setup_doctypes.create_all_doctypes

# 2. Default settings create করুন
bench --site yoursite.local execute prime_att.install_script.setup_defaults

# 3. Roles setup করুন
bench --site yoursite.local execute prime_att.install_script.setup_roles

# 4. Migrate
bench --site yoursite.local migrate

# 5. Build
bench build --app prime_att

# 6. Restart
bench restart
```

## Verify Installation

```bash
# Check app installed
bench --site yoursite.local list-apps
# Should show: prime_att

# Check DocTypes created
bench --site yoursite.local console
```

Console এ:

```python
# DocTypes check
frappe.get_all("DocType", filters={"module": "Prime Attendance System"})

# Settings check
frappe.get_single("ZK Settings")
frappe.get_single("ZK Sync Connector")

# Roles check
frappe.get_all("Role", filters={"name": ["in", ["ZK Admin", "ZK Operator"]]})
```

## Next Steps After Installation

### 1. Configure Nginx

`/etc/nginx/sites-available/yoursite.conf` এ add করুন:

```nginx
location ~* ^/iclock/(cdata|getrequest|devicecmd) {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_pass_header Content-Type;
    proxy_buffering off;
}
```

Reload:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 2. Configure ZK Settings

```bash
bench --site yoursite.local browse
# Go to: /app/zk-settings
```

Set:
- Timezone: Asia/Dhaka
- Duplicate Tolerance: 5 seconds
- Status Mappings থাকবে (auto-created)

### 3. Setup User Roles

```bash
bench --site yoursite.local add-user-role your@email.com "ZK Admin"
```

### 4. Test Installation

```bash
cd apps/prime_att/tests
python test_device_simulator.py http://yoursite.local TESTDEV001 test
```

Check:
```bash
bench --site yoursite.local console
```

```python
# Should have data
frappe.get_all("ZK Device")
frappe.get_all("ZK Raw Log", limit=5)
frappe.get_all("ZK Person", limit=5)
```

## Common Issues

### Issue 1: Permission Denied

```bash
# Give proper permissions
chmod +x apps/prime_att/install.sh
chmod +x apps/prime_att/tests/test_device_simulator.py
```

### Issue 2: DocTypes not showing in UI

```bash
# Clear cache
bench --site yoursite.local clear-cache
bench restart
```

### Issue 3: Import errors

```bash
# Reinstall app
bench --site yoursite.local uninstall-app prime_att
bench --site yoursite.local install-app prime_att

# Then follow Method 1 steps above
```

## Uninstall (if needed)

```bash
# Backup first!
bench --site yoursite.local backup

# Uninstall
bench --site yoursite.local uninstall-app prime_att

# Remove app
bench remove-app prime_att
```

## Update App

```bash
# Get latest code
cd apps/prime_att
git pull

# Migrate
bench --site yoursite.local migrate

# Build
bench build --app prime_att

# Restart
bench restart
```

## Support

যদি কোনো সমস্যা হয়:

1. Check error logs:
   ```bash
   tail -f ~/frappe-bench/sites/yoursite.local/logs/worker.error.log
   ```

2. Check console for errors:
   ```bash
   bench --site yoursite.local console
   ```

3. Check DocType creation:
   ```bash
   bench --site yoursite.local execute prime_att.setup_doctypes.create_all_doctypes
   ```

Installation সম্পন্ন হলে QUICKSTART.md দেখুন device configuration এর জন্য!
