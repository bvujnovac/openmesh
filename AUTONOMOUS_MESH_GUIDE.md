# OpenMesh Autonomous Mesh Deployment Guide

## Overview

This guide documents the corrected autonomous mesh architecture that enables **zero-configuration deployment** without server dependency.

## Architecture Summary

### ✅ Corrected Design

```
1. Flash firmware with embedded autonomous config
2. Router boots → Calculates IP from MAC (local)
3. Router configures network, Babel, WiFi (autonomous)
4. Router joins mesh network (no server needed!)
5. Router reports to platform for monitoring (optional)
```

**Key Principle:** Routers are **autonomous**. The platform is for **monitoring**, not initial configuration.

---

## Components

### 1. Standalone UCI Generator

**Location:** `backend/services/config_gen/standalone_uci_generator.py`

**Purpose:** Generates self-contained configuration scripts that calculate IP addresses locally without server connectivity.

**Features:**
- MAC-based IP calculation using SHA256 hash
- DHCP pool calculation using MD5 hash
- Babel routing configuration (infrastructure-only redistribution)
- WiFi mesh ad-hoc interface
- Optional client AP
- Firewall rules
- Optional platform registration

**Usage:**
```python
from backend.services.config_gen.standalone_uci_generator import StandaloneUCIGenerator

generator = StandaloneUCIGenerator(
    network_cidr="10.0.0.0/16",
    infrastructure_cidr="10.0.0.0/23",
    mesh_ssid="openmesh-backbone",
    mesh_bssid="02:CA:FE:CA:CA:40",
    platform_url="http://10.0.0.1:8000"
)

script = generator.generate()
# script is ready to embed in firmware at /etc/uci-defaults/99-openmesh-config
```

### 2. Image Builder with Autonomous Config

**Location:** `backend/services/image_builder/builder.py`

**New Method:** `embed_autonomous_config()`

**Purpose:** Embeds standalone configuration in firmware images.

**Usage:**
```python
from backend.services.image_builder.builder import ImageBuilder

builder = ImageBuilder(
    version="23.05.2",
    target="ath79",
    subtarget="generic",
    profile="ubnt_nanostation-m-xw"
)

# Add packages
builder.add_package("babeld")
builder.add_package("curl")

# Embed autonomous configuration
builder.embed_autonomous_config(
    network_cidr="10.0.0.0/16",
    infrastructure_cidr="10.0.0.0/23",
    mesh_ssid="openmesh-backbone",
    client_ssid="OpenMesh-WiFi",  # Optional
    client_password="your-password",
    platform_url="http://10.0.0.1:8000"
)

# Build firmware
result = builder.build()
```

**What Gets Embedded:**
1. `/etc/uci-defaults/99-openmesh-config` - Auto-configuration script
2. `/usr/bin/openmesh-heartbeat.sh` - Metrics collection script
3. `/etc/crontabs/root` - Cron job for heartbeat (runs every minute)

### 3. Autonomous Heartbeat Endpoint

**Location:** `backend/api/v1/devices.py`

**Endpoint:** `POST /api/v1/devices/heartbeat`

**Purpose:** Accepts heartbeats from routers with auto-registration.

**Schema:**
```json
{
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "ip_address": "10.0.0.123",
  "hostname": "mesh-AABBCC",
  "cpu_usage_percent": 25.5,
  "memory_total_mb": 128,
  "memory_free_mb": 64,
  "load_average": "0.5,0.4,0.3",
  "uptime_seconds": 3600,
  "firmware_version": "OpenWrt 23.05.2",
  "neighbor_count": 3,
  "route_count": 15
}
```

**Behavior:**
- If device doesn't exist → Auto-register with learned IP
- If device exists → Update status and metrics
- Writes metrics to InfluxDB
- Broadcasts updates via WebSocket

---

## Deployment Workflow

### Step 1: Build Autonomous Firmware

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/firmware \
  -H "Content-Type: application/json" \
  -d '{
    "name": "OpenMesh Autonomous Firmware",
    "target": "ath79",
    "subtarget": "generic",
    "profile": "ubnt_nanostation-m-xw",
    "package_set": "mesh-full",
    "openwrt_version": "23.05.2",
    "include_autonomous_config": true,
    "network_config": {
      "mesh_ssid": "openmesh-backbone",
      "client_ssid": "OpenMesh-WiFi",
      "client_password": "your-password"
    }
  }'
```

### Step 2: Flash Firmware to Routers

```bash
# Download firmware from platform
wget http://localhost:8000/api/v1/firmware/{id}/download -O firmware.bin

# Flash to router (via sysupgrade or web UI)
sysupgrade -n firmware.bin
```

### Step 3: Router Auto-Configuration

**On first boot:**
1. UCI defaults script runs automatically
2. Script reads MAC address from hardware
3. Script calculates router IP: `10.0.0.X` (SHA256 hash of MAC)
4. Script calculates DHCP pool: `10.0.Y.Z` (MD5 hash of MAC)
5. Script configures network, Babel, WiFi
6. Router restarts services
7. Router joins mesh network
8. Router attempts platform registration (non-blocking)

**Timeline:**
- T+0: Router boots
- T+30s: Auto-config script runs
- T+60s: Network configured, services restarted
- T+90s: Router joined mesh, Babel routing active
- T+120s: First heartbeat sent to platform

### Step 4: Platform Monitoring

**Platform auto-registers devices on first heartbeat:**
- Learns IP address from device
- Creates device record in database
- Begins collecting metrics
- Displays in web dashboard

---

## Network Architecture

### Address Space

```
Total Network: 10.0.0.0/16 (65,536 addresses)

Infrastructure Zone (Mesh Routers):
├── Range: 10.0.0.1 → 10.0.1.254 (512 addresses)
├── Capacity: 508 mesh routers
├── Assignment: SHA256(MAC) % 508
└── Babel: Redistributes ONLY this range

Client Zone (DHCP Pools):
├── Range: 10.0.2.1 → 10.0.255.254 (65,024 addresses)
├── Capacity: 508 routers × 126 clients = 64,008 clients
├── Assignment: MD5(MAC) % 508 → subnet ID
└── Pools: 2 per subnet (.1-.126 and .127-.252)
```

### IP Allocation Algorithm

**Router IP (Infrastructure):**
```bash
# SHA256 hash of MAC address
hash=$(echo -n "$MAC" | sha256sum | cut -c1-8)
decimal=$((0x$hash))
router_index=$(($decimal % 508 + 1))

# Calculate IP
third_octet=$(($router_index / 256))
fourth_octet=$(($router_index % 256))
router_ip="10.0.$third_octet.$fourth_octet"
```

**DHCP Pool (Client Zone):**
```bash
# MD5 hash for different distribution
hash=$(echo -n "$MAC" | md5sum | cut -c1-6)
decimal=$((0x$hash))
sequence=$(($decimal % 508 + 1))

# Calculate subnet and pool
subnet_offset=$((($sequence - 1) / 2))
pool_in_subnet=$((($sequence - 1) % 2))
third_octet=$((2 + $subnet_offset))

if [ $pool_in_subnet -eq 0 ]; then
    dhcp_start="10.0.$third_octet.1"      # Pool 1: .1-.126
else
    dhcp_start="10.0.$third_octet.127"    # Pool 2: .127-.252
fi
```

---

## Babel Routing Configuration

### Critical: Infrastructure-Only Redistribution

```uci
# CORRECT - Only redistribute router IPs
uci set babeld.infra_routes=filter
uci set babeld.infra_routes.type='redistribute'
uci set babeld.infra_routes.ip='10.0.0.0/23'
uci set babeld.infra_routes.action='allow'

# Block everything else
uci set babeld.deny_rest=filter
uci set babeld.deny_rest.type='redistribute'
uci set babeld.deny_rest.action='deny'
```

**Why this matters:**
- Redistributing all 64K client IPs would cause memory exhaustion
- Only 508 router IPs need to be in routing table
- Clients communicate via Layer 2 bridging
- Reduces Babel memory footprint from 6MB+ to ~50KB

---

## Metrics Collection

### Heartbeat Script

**Location (on router):** `/usr/bin/openmesh-heartbeat.sh`

**Runs:** Every minute via cron

**Collects:**
- System metrics: CPU, memory, load average, uptime
- Babel metrics: Neighbor count, route count, installed routes, xroutes, RTT
- Device info: MAC, IP, hostname, firmware version

**Sends to:** `POST /api/v1/devices/heartbeat`

**Behavior:**
- Non-blocking, fire-and-forget
- Router continues to function if platform is unreachable
- Retries on next cron execution

---

## Platform Role

### What Platform DOES

✅ **Firmware Building** - Creates images with embedded autonomous config
✅ **Metrics Collection** - Receives and stores device metrics
✅ **Topology Visualization** - Displays mesh network map
✅ **Alerting** - Detects offline devices, high latency
✅ **Web Dashboard** - Provides management UI
✅ **Historical Data** - Time-series metrics in InfluxDB

### What Platform DOES NOT Do

❌ **Initial IP Assignment** - Routers calculate locally
❌ **Initial Configuration** - Embedded in firmware
❌ **Blocking Registration** - Devices self-configure first
❌ **Required for Operation** - Mesh works without platform

**Platform Purpose:** Monitoring and management, not deployment dependency.

---

## Comparison: Old vs. New Architecture

### ❌ Old (Broken) Architecture

```
1. Router boots → No IP
2. Needs to call http://10.0.0.1:8000/api/v1/devices/register
3. ❌ CANNOT REACH SERVER (chicken-and-egg problem)
4. Deployment fails
```

**Problem:** Server-side IP allocation requires connectivity, but connectivity requires IP allocation.

### ✅ New (Corrected) Architecture

```
1. Router boots with firmware
2. Auto-config script runs (embedded in firmware)
3. Calculates IP locally from MAC
4. Configures network, Babel, WiFi
5. Joins mesh autonomously
6. Reports to platform (optional, for monitoring)
```

**Solution:** Autonomous configuration eliminates server dependency.

---

## Testing

### Local Testing with VMs

1. **Build test firmware:**
```bash
make build-test-firmware TARGET=x86 SUBTARGET=64
```

2. **Create VM mesh nodes:**
```bash
# Start 3 VMs with test firmware
./scripts/test-mesh-vm.sh --nodes 3
```

3. **Verify autonomous configuration:**
```bash
# SSH into node 1
ssh root@10.0.0.X

# Check IP assignment
uci get network.lan.ipaddr  # Should be calculated from MAC

# Check Babel status
echo "dump" | nc localhost 33123 | grep "add neighbour"  # Should see 2 neighbors

# Check heartbeat
cat /var/log/messages | grep openmesh-heartbeat
```

4. **Verify platform monitoring:**
```bash
# Check platform received heartbeat
curl http://localhost:8000/api/v1/devices | jq
# Should show auto-registered devices
```

---

## Troubleshooting

### Device Not Appearing in Platform

**Check:**
1. Is heartbeat script running?
   ```bash
   ps | grep openmesh-heartbeat
   ```

2. Can device reach platform?
   ```bash
   curl -v http://10.0.0.1:8000/health
   ```

3. Is cron running?
   ```bash
   /etc/init.d/cron status
   ```

4. Check heartbeat logs:
   ```bash
   logread | grep openmesh
   ```

### Mesh Network Not Forming

**Check:**
1. Is Babel running?
   ```bash
   /etc/init.d/babeld status
   ps | grep babeld
   ```

2. Check Babel neighbors:
   ```bash
   echo "dump" | nc localhost 33123 | grep "add neighbour"
   ```

3. Is WiFi mesh configured?
   ```bash
   uci show wireless | grep mesh
   iwconfig | grep adhoc
   ```

4. Check network configuration:
   ```bash
   uci show network.lan
   ip addr show br-lan
   ```

---

## Migration from Old Implementation

If you have existing platform code using server-side IP allocation:

1. **Update firmware builds** to use `embed_autonomous_config()`
2. **Flash new firmware** to all routers
3. **Platform will auto-learn** IPs from heartbeats
4. **Deprecate** the old `/api/v1/devices/register` endpoint (optional, can keep for compatibility)

---

## Summary

**Key Changes:**
1. ✅ IP calculation moved to firmware (from server)
2. ✅ Auto-configuration embedded in firmware
3. ✅ Platform learns IPs from devices (doesn't assign)
4. ✅ Heartbeat endpoint with auto-registration
5. ✅ Mesh formation is autonomous (no server dependency)

**Benefits:**
- True zero-configuration deployment
- Platform downtime doesn't affect mesh
- Routers self-configure in parallel
- Simpler deployment workflow
- Aligns with comprehensive plan architecture

**Status:** ✅ Architecture corrected and implemented
