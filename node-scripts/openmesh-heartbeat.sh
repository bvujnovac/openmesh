#!/bin/sh
#
# OpenMesh Heartbeat and Metrics Collection Script
#
# This script collects system and Babel metrics and sends them to the
# OpenMesh platform. It runs periodically via cron and is non-blocking.
#
# The router functions normally even if the platform is unreachable.
#
# Installation:
#   1. Copy to /usr/bin/openmesh-heartbeat.sh
#   2. Make executable: chmod +x /usr/bin/openmesh-heartbeat.sh
#   3. Add to cron: echo '* * * * * /usr/bin/openmesh-heartbeat.sh' >> /etc/crontabs/root
#   4. Restart cron: /etc/init.d/cron restart
#

# Configuration
PLATFORM_URL="${OPENMESH_PLATFORM_URL:-http://10.0.0.1:8000}"
TIMEOUT=10  # Timeout for HTTP requests (seconds)

# Get device information
get_device_info() {
    MAC=$(cat /sys/class/net/br-lan/address 2>/dev/null || cat /sys/class/net/eth0/address 2>/dev/null)
    IP=$(uci get network.lan.ipaddr 2>/dev/null)
    HOSTNAME=$(uci get system.@system[0].hostname 2>/dev/null || hostname)

    if [ -z "$MAC" ] || [ -z "$IP" ]; then
        logger -t openmesh-heartbeat "ERROR: Could not determine MAC or IP address"
        return 1
    fi

    echo "$MAC|$IP|$HOSTNAME"
}

# Collect system metrics
get_system_metrics() {
    # CPU usage (percentage)
    CPU_USAGE=$(top -bn1 | grep '^CPU:' | awk '{gsub("%",""); print $2}')
    if [ -z "$CPU_USAGE" ]; then
        CPU_USAGE=0
    fi

    # Memory (KB to MB conversion)
    MEM_TOTAL=$(free | grep '^Mem:' | awk '{print int($2/1024)}')
    MEM_FREE=$(free | grep '^Mem:' | awk '{print int($4/1024)}')

    # Load average
    LOAD_AVG=$(cat /proc/loadavg | awk '{print $1","$2","$3}')

    # Uptime (seconds)
    UPTIME=$(cat /proc/uptime | awk '{print int($1)}')

    # Firmware version
    FIRMWARE=$(cat /etc/openwrt_release | grep DISTRIB_DESCRIPTION | cut -d"'" -f2)

    echo "$CPU_USAGE|$MEM_TOTAL|$MEM_FREE|$LOAD_AVG|$UPTIME|$FIRMWARE"
}

# Collect Babel metrics
get_babel_metrics() {
    # Check if Babel is running
    if ! pgrep -x babeld > /dev/null; then
        logger -t openmesh-heartbeat "WARNING: babeld is not running"
        echo "0|0|0|0|0"
        return
    fi

    # Query Babel control socket
    BABEL_DUMP=$(echo "dump" | nc -w 2 localhost 33123 2>/dev/null)

    if [ -z "$BABEL_DUMP" ]; then
        logger -t openmesh-heartbeat "WARNING: Could not connect to Babel control socket"
        echo "0|0|0|0|0"
        return
    fi

    # Count neighbors
    NEIGHBOR_COUNT=$(echo "$BABEL_DUMP" | grep -c "^add neighbour ")

    # Count routes
    ROUTE_COUNT=$(echo "$BABEL_DUMP" | grep -c "^add route ")

    # Count installed routes
    INSTALLED_COUNT=$(echo "$BABEL_DUMP" | grep "^add route " | grep -c "installed yes")

    # Count redistributed routes (xroutes)
    XROUTE_COUNT=$(echo "$BABEL_DUMP" | grep -c "^add xroute ")

    # Calculate average RTT (milliseconds)
    RTT_SUM=$(echo "$BABEL_DUMP" | grep "^add neighbour " | awk '{
        for(i=1; i<=NF; i++) {
            if($i == "rtt") {
                sum += $(i+1)
                count++
            }
        }
    } END {print sum}')

    RTT_COUNT=$(echo "$BABEL_DUMP" | grep "^add neighbour " | awk '{
        for(i=1; i<=NF; i++) {
            if($i == "rtt") {
                count++
            }
        }
    } END {print count}')

    if [ -n "$RTT_SUM" ] && [ -n "$RTT_COUNT" ] && [ "$RTT_COUNT" -gt 0 ]; then
        AVG_RTT=$(awk "BEGIN {printf \"%.2f\", $RTT_SUM / $RTT_COUNT}")
    else
        AVG_RTT=0
    fi

    echo "$NEIGHBOR_COUNT|$ROUTE_COUNT|$INSTALLED_COUNT|$XROUTE_COUNT|$AVG_RTT"
}

# Send heartbeat to platform
send_heartbeat() {
    local mac=$1
    local ip=$2
    local hostname=$3
    local cpu=$4
    local mem_total=$5
    local mem_free=$6
    local load_avg=$7
    local uptime=$8
    local firmware=$9
    shift 9
    local neighbors=$1
    local routes=$2
    local installed=$3
    local xroutes=$4
    local avg_rtt=$5

    # Build JSON payload
    JSON_PAYLOAD=$(cat <<EOF
{
    "mac_address": "$mac",
    "ip_address": "$ip",
    "hostname": "$hostname",
    "cpu_usage_percent": $cpu,
    "memory_total_mb": $mem_total,
    "memory_free_mb": $mem_free,
    "load_average": "$load_avg",
    "uptime_seconds": $uptime,
    "firmware_version": "$firmware",
    "neighbor_count": $neighbors,
    "route_count": $routes,
    "installed_route_count": $installed,
    "xroute_count": $xroutes,
    "avg_rtt_ms": $avg_rtt
}
EOF
)

    # Send to platform (non-blocking, fire-and-forget)
    RESPONSE=$(curl -s -m $TIMEOUT -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$JSON_PAYLOAD" \
        "${PLATFORM_URL}/api/v1/devices/heartbeat" 2>/dev/null || echo "000")

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
        # Success - no logging to reduce syslog spam
        return 0
    else
        logger -t openmesh-heartbeat "WARNING: Platform unreachable (HTTP $HTTP_CODE)"
        return 1
    fi
}

# Main execution
main() {
    # Get device info
    DEVICE_INFO=$(get_device_info)
    if [ $? -ne 0 ]; then
        exit 1
    fi

    MAC=$(echo "$DEVICE_INFO" | cut -d'|' -f1)
    IP=$(echo "$DEVICE_INFO" | cut -d'|' -f2)
    HOSTNAME=$(echo "$DEVICE_INFO" | cut -d'|' -f3)

    # Collect system metrics
    SYSTEM_METRICS=$(get_system_metrics)
    CPU_USAGE=$(echo "$SYSTEM_METRICS" | cut -d'|' -f1)
    MEM_TOTAL=$(echo "$SYSTEM_METRICS" | cut -d'|' -f2)
    MEM_FREE=$(echo "$SYSTEM_METRICS" | cut -d'|' -f3)
    LOAD_AVG=$(echo "$SYSTEM_METRICS" | cut -d'|' -f4)
    UPTIME=$(echo "$SYSTEM_METRICS" | cut -d'|' -f5)
    FIRMWARE=$(echo "$SYSTEM_METRICS" | cut -d'|' -f6)

    # Collect Babel metrics
    BABEL_METRICS=$(get_babel_metrics)
    NEIGHBOR_COUNT=$(echo "$BABEL_METRICS" | cut -d'|' -f1)
    ROUTE_COUNT=$(echo "$BABEL_METRICS" | cut -d'|' -f2)
    INSTALLED_COUNT=$(echo "$BABEL_METRICS" | cut -d'|' -f3)
    XROUTE_COUNT=$(echo "$BABEL_METRICS" | cut -d'|' -f4)
    AVG_RTT=$(echo "$BABEL_METRICS" | cut -d'|' -f5)

    # Send heartbeat
    send_heartbeat "$MAC" "$IP" "$HOSTNAME" "$CPU_USAGE" "$MEM_TOTAL" "$MEM_FREE" \
        "$LOAD_AVG" "$UPTIME" "$FIRMWARE" "$NEIGHBOR_COUNT" "$ROUTE_COUNT" \
        "$INSTALLED_COUNT" "$XROUTE_COUNT" "$AVG_RTT"
}

# Run main function
main
