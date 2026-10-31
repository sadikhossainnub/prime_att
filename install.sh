#!/bin/bash
# Installation script for Prime Att
# Usage: ./install.sh [site_name]

set -e

SITE_NAME=${1:-}

if [ -z "$SITE_NAME" ]; then
    echo "Usage: ./install.sh <site_name>"
    echo "Example: ./install.sh mysite.local"
    exit 1
fi

echo "================================"
echo "Prime Att Installation Script"
echo "================================"
echo ""
echo "Site: $SITE_NAME"
echo ""

# Check if we're in bench directory
if [ ! -f "sites/apps.txt" ]; then
    echo "Error: Must run from bench directory"
    exit 1
fi

# Check if site exists
if [ ! -d "sites/$SITE_NAME" ]; then
    echo "Error: Site $SITE_NAME does not exist"
    exit 1
fi

# Step 1: Install app (this will run after_install hook)
echo "[1/5] Installing app..."
bench --site $SITE_NAME install-app prime_att || {
    echo "Warning: Installation hook failed. Continuing with manual setup..."
}

# Step 2: Run migrations
echo "[2/5] Running migrations..."
bench --site $SITE_NAME migrate

# Step 3: Create DocTypes
echo "[3/5] Creating DocTypes..."
bench --site $SITE_NAME execute prime_att.setup_doctypes.create_all_doctypes

# Step 4: Setup defaults (now that DocTypes exist)
echo "[4/5] Creating default settings..."
bench --site $SITE_NAME execute prime_att.install_script.setup_defaults

# Step 5: Build assets
echo "[5/5] Building assets..."
bench build --app prime_att

echo ""
echo "================================"
echo "Installation Complete!"
echo "================================"
echo ""
echo "Next Steps:"
echo ""
echo "1. Configure Nginx:"
echo "   - Copy nginx/iclock.conf contents to your site's nginx config"
echo "   - Reload nginx: sudo systemctl reload nginx"
echo ""
echo "2. Configure ZK Settings:"
echo "   - Go to: $SITE_NAME/app/zk-settings"
echo "   - Set timezone and status mappings"
echo ""
echo "3. Configure Device:"
echo "   - Set device to push to: http://yourserver/iclock/cdata"
echo ""
echo "4. Test with simulator:"
echo "   cd apps/prime_att/tests"
echo "   python test_device_simulator.py http://yourserver TESTDEV001 test"
echo ""
echo "5. Check logs:"
echo "   bench --site $SITE_NAME console"
echo "   >>> frappe.get_all('ZK Raw Log', limit=5)"
echo ""

exit 0
