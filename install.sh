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

# Step 1: Install app (this will automatically create DocTypes and setup)
echo "[1/3] Installing app..."
bench --site $SITE_NAME install-app prime_att

# Step 2: Run migrations
echo "[2/3] Running migrations..."
bench --site $SITE_NAME migrate

# Step 3: Build assets
echo "[3/3] Building assets..."
bench build --app prime_att

echo ""
echo "================================"
echo "✓ Installation Complete!"
echo "================================"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1️⃣  Configure Nginx (Required for devices):"
echo "   Edit: /etc/nginx/sites-available/$SITE_NAME"
echo "   Add nginx/iclock.conf content BEFORE 'location /' block"
echo "   Then: sudo nginx -t && sudo systemctl reload nginx"
echo ""
echo "2️⃣  Configure Settings:"
echo "   • ZK Settings: Set timezone and status mappings"
echo "   • ZK Sync Connector: Enable HRMS sync if needed"
echo ""
echo "3️⃣  Register Device:"
echo "   • Create new ZK Device with serial number"
echo "   • Set device to: http://$SITE_NAME/iclock/cdata"
echo ""
echo "4️⃣  Test Connection:"
echo "   cd apps/prime_att/tests"
echo "   python test_device_simulator.py http://$SITE_NAME TESTDEV001 test"
echo ""
echo "📚 Documentation: apps/prime_att/README.md"
echo ""

exit 0
