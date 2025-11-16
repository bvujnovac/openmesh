#!/bin/sh
#
# Babel Metrics Collection Script for OpenWrt
#
# This script collects Babel routing metrics and sends them to the OpenMesh platform.
# It should be run periodically via cron (e.g., every 30 seconds).
#
# Installation:
#   1. Copy this script to /usr/bin/collect-babel-metrics.sh
#   2. Make it executable: chmod +x /usr/bin/collect-babel-metrics.sh
#   3. Add to crontab: * * * * * /usr/bin/collect-babel-metrics.sh
#

# Configuration (should match device registration)
PLATFORM_URL="${OPENMESH_PLATFORM_URL:-http://10.0.0.1:8000}"
DEVICE_ID_FILE="/etc/openmesh/device-id"
DEVICE_MAC=$(cat /sys/class/net/eth0/address 2>/dev/null || echo "00:00:00:00:00:00")

# Check if Babel is running
if ! pgrep -x babeld > /dev/null; then
    echo "Error: babeld is not running"
    exit 1
fi

# Get device ID (stored after registration)
if [ -f "$DEVICE_ID_FILE" ]; then
    DEVICE_ID=$(cat "$DEVICE_ID_FILE")
else
    echo "Warning: Device not registered. Attempting registration..."
    # This should trigger device registration
    exit 1
fi

# Collect system metrics
UPTIME=$(cat /proc/uptime | cut -d' ' -f1 | cut -d'.' -f1)
LOAD_AVG=$(cat /proc/loadavg | awk '{print $1","$2","$3}')
MEM_TOTAL=$(free | grep Mem | awk '{print int($2/1024)}')
MEM_FREE=$(free | grep Mem | awk '{print int($4/1024)}')
CPU_USAGE=$(top -bn1 | grep "CPU:" | awk '{print $2}' | sed 's/%//')

# Collect Babel metrics via babeld control socket
# babeld listens on port 33123 by default
BABEL_PORT=33123

# Get neighbor count
NEIGHBOR_COUNT=$(echo "dump" | nc localhost $BABEL_PORT 2>/dev/null | grep -c "^neighbour")

# Get route count
ROUTE_COUNT=$(echo "dump" | nc localhost $BABEL_PORT 2>/dev/null | grep -c "^route")

# Get installed route count
INSTALLED_COUNT=$(echo "dump" | nc localhost $BABEL_PORT 2>/dev/null | grep "^route" | grep -c "installed yes")

# Get xroute count (redistributed routes)
XROUTE_COUNT=$(echo "dump" | nc localhost $BABEL_PORT 2>/dev/null | grep -c "^xroute")

# Calculate average RTT from neighbors (if available)
# This requires babeld to be compiled with RTT support
AVG_RTT=$(echo "dump" | nc localhost $BABEL_PORT 2>/dev/null | \
    grep "^neighbour" | \
    grep -o "rtt [0-9.]*" | \
    awk '{sum+=$2; count++} END {if(count>0) print int(sum/count); else print 0}')

# Parse Babel interface metrics
# Get list of interfaces running Babel
BABEL_INTERFACES=$(echo "dump" | nc localhost $BABEL_PORT 2>/dev/null | \
    grep "^interface" | \
    awk '{print $2}')

# Collect per-interface metrics
INTERFACE_METRICS=""
for iface in $BABEL_INTERFACES; do
    # Get interface up/down status
    IF_STATUS=$(echo "dump" | nc localhost $BABEL_PORT 2>/dev/null | \
        grep "^interface $iface" | \
        grep -o "up [a-z]*" | \
        awk '{print $2}')

    # Count neighbors on this interface
    IF_NEIGHBORS=$(echo "dump" | nc localhost $BABEL_PORT 2>/dev/null | \
        grep "^neighbour" | \
        grep -c "if $iface")

    # Build interface metrics JSON fragment
    if [ -n "$INTERFACE_METRICS" ]; then
        INTERFACE_METRICS="$INTERFACE_METRICS,"
    fi
    INTERFACE_METRICS="${INTERFACE_METRICS}\"${iface}\":{\"status\":\"${IF_STATUS}\",\"neighbors\":${IF_NEIGHBORS}}"
done

# Build JSON payload
JSON_PAYLOAD=$(cat <<EOF
{
    "uptime_seconds": ${UPTIME},
    "load_average": "${LOAD_AVG}",
    "memory_total_mb": ${MEM_TOTAL},
    "memory_free_mb": ${MEM_FREE},
    "cpu_usage_percent": ${CPU_USAGE:-0},
    "neighbor_count": ${NEIGHBOR_COUNT:-0},
    "route_count": ${ROUTE_COUNT:-0},
    "installed_route_count": ${INSTALLED_COUNT:-0},
    "xroute_count": ${XROUTE_COUNT:-0},
    "avg_rtt_ms": ${AVG_RTT:-0},
    "babel_interfaces": {${INTERFACE_METRICS}}
}
EOF
)

# Send heartbeat with metrics to platform
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -d "$JSON_PAYLOAD" \
    --connect-timeout 5 \
    --max-time 10 \
    "${PLATFORM_URL}/api/v1/devices/${DEVICE_ID}/heartbeat" 2>/dev/null)

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "204" ] || [ "$HTTP_CODE" = "200" ]; then
    # Success - log to syslog
    logger -t openmesh-metrics "Metrics sent successfully (neighbors: $NEIGHBOR_COUNT, routes: $ROUTE_COUNT)"
    exit 0
else
    # Error - log and exit with error code
    logger -t openmesh-metrics "Failed to send metrics: HTTP $HTTP_CODE"
    echo "Error: Failed to send metrics (HTTP $HTTP_CODE)"
    echo "$BODY"
    exit 1
fi
