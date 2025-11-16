#!/bin/sh
#
# OpenMesh Device Registration Script
#
# This script registers the device with the OpenMesh platform and configures
# the router based on the platform's response.
#
# Installation:
#   1. Copy to /usr/bin/openmesh-register.sh
#   2. Make executable: chmod +x /usr/bin/openmesh-register.sh
#   3. Run once: /usr/bin/openmesh-register.sh
#

# Configuration
PLATFORM_URL="${OPENMESH_PLATFORM_URL:-http://10.0.0.1:8000}"
CONFIG_DIR="/etc/openmesh"
DEVICE_ID_FILE="${CONFIG_DIR}/device-id"
HOSTNAME=$(uci get system.@system[0].hostname 2>/dev/null || echo "openmesh-router")

# Get MAC address (use eth0 or first available interface)
DEVICE_MAC=$(cat /sys/class/net/eth0/address 2>/dev/null)
if [ -z "$DEVICE_MAC" ]; then
    # Try to find first non-loopback interface
    for iface in /sys/class/net/*; do
        iface_name=$(basename "$iface")
        if [ "$iface_name" != "lo" ]; then
            DEVICE_MAC=$(cat "$iface/address" 2>/dev/null)
            if [ -n "$DEVICE_MAC" ]; then
                break
            fi
        fi
    done
fi

if [ -z "$DEVICE_MAC" ]; then
    echo "Error: Could not determine MAC address"
    exit 1
fi

echo "==================================="
echo "OpenMesh Device Registration"
echo "==================================="
echo "MAC Address: $DEVICE_MAC"
echo "Hostname: $HOSTNAME"
echo "Platform URL: $PLATFORM_URL"
echo ""

# Check if already registered
if [ -f "$DEVICE_ID_FILE" ]; then
    DEVICE_ID=$(cat "$DEVICE_ID_FILE")
    echo "Device already registered with ID: $DEVICE_ID"
    echo "To re-register, delete: $DEVICE_ID_FILE"
    exit 0
fi

# Create config directory
mkdir -p "$CONFIG_DIR"

# Prepare registration payload
JSON_PAYLOAD=$(cat <<EOF
{
    "mac_address": "$DEVICE_MAC",
    "hostname": "$HOSTNAME"
}
EOF
)

# Send registration request
echo "Registering device with platform..."
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -d "$JSON_PAYLOAD" \
    --connect-timeout 10 \
    --max-time 30 \
    "${PLATFORM_URL}/api/v1/devices/register")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
    echo "Error: Registration failed with HTTP $HTTP_CODE"
    echo "$BODY"
    exit 1
fi

echo "Registration successful!"
echo ""

# Parse response (simple JSON parsing with grep/sed)
DEVICE_ID=$(echo "$BODY" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
DEVICE_IP=$(echo "$BODY" | grep -o '"ip_address":"[^"]*"' | head -1 | cut -d'"' -f4)
DHCP_START=$(echo "$BODY" | grep -o '"dhcp_pool_start":"[^"]*"' | head -1 | cut -d'"' -f4)
DHCP_END=$(echo "$BODY" | grep -o '"dhcp_pool_end":"[^"]*"' | head -1 | cut -d'"' -f4)
SUBNET_ID=$(echo "$BODY" | grep -o '"subnet_id":[0-9]*' | head -1 | cut -d':' -f2)

echo "Device Configuration:"
echo "  ID: $DEVICE_ID"
echo "  IP Address: $DEVICE_IP"
echo "  DHCP Pool: $DHCP_START - $DHCP_END"
echo "  Subnet ID: $SUBNET_ID"
echo ""

# Save device ID
echo "$DEVICE_ID" > "$DEVICE_ID_FILE"

# Get full configuration from platform
echo "Fetching device configuration..."
CONFIG_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X GET \
    "${PLATFORM_URL}/api/v1/devices/${DEVICE_ID}/config")

CONFIG_HTTP_CODE=$(echo "$CONFIG_RESPONSE" | tail -n1)
CONFIG_BODY=$(echo "$CONFIG_RESPONSE" | sed '$d')

if [ "$CONFIG_HTTP_CODE" != "200" ]; then
    echo "Warning: Could not fetch configuration (HTTP $CONFIG_HTTP_CODE)"
else
    # Extract UCI script from response
    UCI_SCRIPT=$(echo "$CONFIG_BODY" | grep -o '"uci_script":"[^"]*"' | head -1 | cut -d'"' -f4 | sed 's/\\n/\n/g')

    if [ -n "$UCI_SCRIPT" ]; then
        echo "Applying UCI configuration..."
        echo "$UCI_SCRIPT" > /tmp/openmesh-uci-config.sh
        chmod +x /tmp/openmesh-uci-config.sh
        /tmp/openmesh-uci-config.sh
        rm /tmp/openmesh-uci-config.sh

        # Commit all UCI changes
        uci commit

        # Reload network and restart Babel
        /etc/init.d/network reload
        /etc/init.d/babeld restart

        echo "Configuration applied successfully!"
    fi
fi

echo ""
echo "==================================="
echo "Registration Complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "  1. Set up metrics collection:"
echo "     opkg install curl netcat"
echo "     wget -O /usr/bin/collect-babel-metrics.sh http://${PLATFORM_URL}/node-scripts/collect-babel-metrics.sh"
echo "     chmod +x /usr/bin/collect-babel-metrics.sh"
echo ""
echo "  2. Add to crontab:"
echo "     echo '* * * * * /usr/bin/collect-babel-metrics.sh' >> /etc/crontabs/root"
echo "     /etc/init.d/cron restart"
echo ""
echo "Device is now part of the OpenMesh network!"
