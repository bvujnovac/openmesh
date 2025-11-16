# OpenMesh Architecture Correction

## Critical Issue Identified

### Current Implementation (BROKEN)

```
1. Router boots → No network config
2. Router needs to call http://10.0.0.1:8000/api/v1/devices/register
3. ❌ CANNOT REACH SERVER - No IP address, no routing!
4. Chicken-and-egg problem
```

**Problem:** Server-side IP allocation requires network connectivity, but network connectivity requires IP allocation.

---

## Correct Architecture (from Comprehensive Plan)

### Device Boot Flow (Self-Configuring)

```
1. Router boots with firmware
2. UCI defaults script runs from /etc/uci-defaults/99-openmesh-config
3. Script reads local MAC address
4. Script calculates IP locally using SHA256(MAC) % 508
5. Script configures network, Babel, WiFi
6. Router joins mesh automatically (no server needed!)
7. Router sends metrics to platform (optional, for monitoring)
```

---

## Platform Role Separation

### ❌ What Platform Should NOT Do
- **Initial IP allocation** (can't work without network!)
- **Initial device configuration** (router can't reach server)
- **Blocking device registration** (prevents autonomous mesh formation)

### ✅ What Platform SHOULD Do
1. **Firmware Building** - Build images with embedded auto-config
2. **Metrics Collection** - Receive heartbeats from configured routers
3. **Topology Visualization** - Display mesh network map
4. **Alerting** - Notify when devices go offline
5. **Network Management UI** - View and manage mesh
6. **Optional Registration** - Track devices for monitoring (post-configuration)

---

## Required Changes

### 1. Embed IP Calculation in Firmware

The firmware image must include the complete auto-config script from the comprehensive plan:

**File:** `/etc/uci-defaults/99-openmesh-config` (embedded in firmware)

```bash
#!/bin/sh
# OpenMesh Auto-Configuration Script
# Embedded in firmware - runs on first boot

# Get MAC address
get_mac() {
    # Try WiFi radio first
    MAC=$(uci get wireless.@wifi-device[0].macaddr 2>/dev/null)
    [ -z "$MAC" ] && MAC=$(cat /sys/class/net/br-lan/address 2>/dev/null)
    [ -z "$MAC" ] && MAC=$(cat /sys/class/net/eth0/address 2>/dev/null)
    echo "$MAC"
}

# Calculate router IP from MAC using SHA256 hash
calculate_router_ip() {
    local mac=$1
    local hash=$(echo -n "$mac" | sha256sum | cut -c1-8)
    local decimal=$((0x$hash))
    local host_offset=$(($decimal % 508 + 1))

    local third_octet=$(($host_offset / 256))
    local fourth_octet=$(($host_offset % 256))

    # Boundary protection
    [ $third_octet -gt 1 ] && third_octet=1 && fourth_octet=254
    [ $fourth_octet -eq 0 ] && fourth_octet=1
    [ $fourth_octet -eq 255 ] && fourth_octet=254

    echo "10.0.$third_octet.$fourth_octet"
}

# Calculate DHCP pool
calculate_dhcp_pool() {
    local mac=$1
    local hash=$(echo -n "$mac" | md5sum | cut -c1-6)
    local decimal=$((0x$hash))
    local sequence=$(($decimal % 508 + 1))

    local subnet_offset=$((($sequence - 1) / 2))
    local pool_in_subnet=$((($sequence - 1) % 2))

    local third_octet=$((2 + $subnet_offset))
    [ $third_octet -gt 255 ] && third_octet=$((2 + ($subnet_offset % 254)))

    if [ $pool_in_subnet -eq 0 ]; then
        fourth_octet=1      # First pool: .1-.126
    else
        fourth_octet=127    # Second pool: .127-.252
    fi

    echo "10.0.$third_octet.$fourth_octet"
}

# Main configuration
MAC=$(get_mac)
ROUTER_IP=$(calculate_router_ip "$MAC")
DHCP_START_IP=$(calculate_dhcp_pool "$MAC")
DHCP_START_4TH=$(echo $DHCP_START_IP | cut -d. -f4)

# Configure network
uci set network.lan.ipaddr="$ROUTER_IP"
uci set network.lan.netmask="255.255.0.0"

# Configure DHCP
uci set dhcp.lan.start="$DHCP_START_4TH"
uci set dhcp.lan.limit="126"

# Configure Babel (infrastructure-only redistribution)
# ... (rest of comprehensive plan script)

uci commit
/etc/init.d/network restart
```

**Key Point:** This script is **embedded in the firmware image** and requires NO server connectivity.

---

### 2. Update Firmware Build Process

The platform's firmware builder should:

```python
# backend/services/image_builder/builder.py

def build_firmware(self, device_profile, package_set):
    """Build firmware with embedded auto-config script."""

    # 1. Download OpenWrt ImageBuilder
    self.download_imagebuilder()

    # 2. Add packages from package set
    packages = PACKAGE_SETS[package_set]

    # 3. Generate UCI defaults script (SELF-CONTAINED)
    uci_script = self._generate_standalone_uci_script(
        network_cidr="10.0.0.0/16",
        infrastructure_cidr="10.0.0.0/23",
        mesh_ssid=self.mesh_ssid,
        mesh_password=self.mesh_password
    )

    # 4. Embed script in firmware
    self.add_file(
        "/etc/uci-defaults/99-openmesh-config",
        uci_script,
        mode="0755"  # Executable
    )

    # 5. Build image
    self.build()
```

---

### 3. Metrics Collection (Post-Configuration)

Routers contact platform **AFTER** they've configured themselves:

**File:** `/usr/bin/openmesh-heartbeat.sh` (embedded in firmware)

```bash
#!/bin/sh
# Sends metrics to platform (optional - continues if platform unreachable)

PLATFORM_URL="${OPENMESH_PLATFORM_URL:-http://10.0.0.1:8000}"
DEVICE_MAC=$(cat /sys/class/net/br-lan/address)
ROUTER_IP=$(uci get network.lan.ipaddr)

# Collect metrics
CPU_USAGE=$(top -bn1 | grep 'CPU:' | awk '{print $2}')
MEMORY_FREE=$(free | grep Mem | awk '{print $4}')
BABEL_NEIGHBORS=$(echo "dump" | nc localhost 33123 | grep -c "add neighbour")

# Send to platform (non-blocking, fire-and-forget)
curl -s -m 5 -X POST "$PLATFORM_URL/api/v1/metrics/heartbeat" \
    -H "Content-Type: application/json" \
    -d "{
        \"mac_address\": \"$DEVICE_MAC\",
        \"ip_address\": \"$ROUTER_IP\",
        \"cpu_usage\": $CPU_USAGE,
        \"memory_free\": $MEMORY_FREE,
        \"babel_neighbors\": $BABEL_NEIGHBORS
    }" || true  # Continue if platform unreachable

# Router functions normally even if platform is down!
```

**Cron Job:** `* * * * * /usr/bin/openmesh-heartbeat.sh`

---

## Updated Platform API

### Heartbeat Endpoint (Auto-Registration)

```python
@router.post("/api/v1/metrics/heartbeat")
async def receive_heartbeat(heartbeat: HeartbeatData):
    """
    Receive metrics from mesh router.
    Auto-registers device if not seen before.
    """
    # Check if device exists
    device = await db.get_device_by_mac(heartbeat.mac_address)

    if not device:
        # Auto-register new device
        device = Device(
            mac_address=heartbeat.mac_address,
            ip_address=heartbeat.ip_address,  # Router tells us its IP
            status=DeviceStatus.ONLINE,
            first_seen=datetime.utcnow()
        )
        db.add(device)

    # Update last seen and metrics
    device.last_seen = datetime.utcnow()
    device.status = DeviceStatus.ONLINE

    # Store metrics in InfluxDB
    influx.write_metrics(device.id, heartbeat.metrics)

    await db.commit()
    return {"status": "ok"}
```

**Key Change:** Platform **learns** IP addresses from routers, doesn't assign them!

---

## Architecture Comparison

### Before (BROKEN)
```
Router → [No Network] → Can't reach server → STUCK
```

### After (CORRECT)
```
Router → Calculates IP locally → Configures network → Joins mesh → Reports to platform (optional)
```

---

## Migration Path

### Phase 1: Fix Firmware Builder
1. Create standalone UCI script generator (no server dependency)
2. Embed IP calculation algorithm in script
3. Update firmware build process to include script

### Phase 2: Update Platform API
1. Change heartbeat endpoint to auto-register devices
2. Remove blocking device registration requirement
3. Platform becomes monitoring tool, not configuration tool

### Phase 3: Update Documentation
1. Clarify platform role (monitoring, not initial config)
2. Document standalone mesh formation
3. Update deployment guides

---

## Benefits of Corrected Architecture

1. **Zero Server Dependency** - Mesh forms without platform
2. **Resilient** - Platform downtime doesn't affect mesh
3. **Scalable** - Routers self-configure in parallel
4. **Simple** - Flash firmware → Router auto-configures
5. **Decentralized** - True mesh network, not client-server

---

## Comprehensive Plan Alignment

This corrected architecture **exactly matches** the comprehensive plan you provided:

- ✅ MAC-based local IP calculation
- ✅ Embedded UCI defaults script
- ✅ Zero configuration deployment
- ✅ Automatic mesh formation
- ✅ Platform for monitoring only (not required for operation)

**Your comprehensive plan was correct from the start!** The current platform implementation deviated from it incorrectly.

---

## Next Steps

1. Extract IP allocation algorithm to standalone shell script
2. Update `backend/services/config_gen/uci_generator.py` to generate standalone script
3. Update firmware builder to embed standalone script
4. Test with VM-based mesh nodes
5. Validate autonomous mesh formation without platform

---

**Priority:** HIGH - Current implementation cannot deploy functional mesh network
**Effort:** Medium - Requires refactoring UCI generator and firmware builder
**Impact:** Critical - Fixes fundamental architectural flaw
