# OpenMesh Node Scripts

Scripts for OpenWrt routers to integrate with the OpenMesh platform.

## Overview

These scripts enable OpenWrt routers to:
- Register with the OpenMesh platform
- Receive network configuration automatically
- Collect and report Babel routing metrics
- Send heartbeat messages

## Scripts

### 1. openmesh-register.sh

Initial device registration script.

**Purpose:** Register the router with the OpenMesh platform and apply initial configuration.

**Features:**
- Detects device MAC address automatically
- Registers with platform
- Receives assigned IP address and DHCP pool
- Downloads and applies UCI configuration
- Configures network interfaces, Babel routing, and WiFi

**Installation on Router:**

```bash
# Download script
wget -O /usr/bin/openmesh-register.sh http://PLATFORM_IP:8000/node-scripts/openmesh-register.sh

# Make executable
chmod +x /usr/bin/openmesh-register.sh

# Set platform URL (optional, defaults to 10.0.0.1:8000)
export OPENMESH_PLATFORM_URL="http://10.0.0.1:8000"

# Run registration
/usr/bin/openmesh-register.sh
```

**Environment Variables:**
- `OPENMESH_PLATFORM_URL` - Platform URL (default: `http://10.0.0.1:8000`)

### 2. collect-babel-metrics.sh

Continuous metrics collection script.

**Purpose:** Collect Babel routing metrics and system health data, send to platform.

**Metrics Collected:**

**System Metrics:**
- Uptime (seconds)
- Load average (1min, 5min, 15min)
- Memory total/free (MB)
- CPU usage (%)

**Babel Metrics:**
- Neighbor count
- Route count
- Installed route count
- Redistributed route count (xroutes)
- Average RTT to neighbors (ms)
- Per-interface status and neighbor counts

**Installation on Router:**

```bash
# Install dependencies
opkg update
opkg install curl netcat

# Download script
wget -O /usr/bin/collect-babel-metrics.sh http://PLATFORM_IP:8000/node-scripts/collect-babel-metrics.sh

# Make executable
chmod +x /usr/bin/collect-babel-metrics.sh

# Test run
/usr/bin/collect-babel-metrics.sh

# Add to crontab (runs every minute)
echo '* * * * * /usr/bin/collect-babel-metrics.sh' >> /etc/crontabs/root
/etc/init.d/cron restart
```

**Cron Scheduling Options:**

```bash
# Every 30 seconds (runs twice per minute)
* * * * * /usr/bin/collect-babel-metrics.sh
* * * * * sleep 30; /usr/bin/collect-babel-metrics.sh

# Every minute
* * * * * /usr/bin/collect-babel-metrics.sh

# Every 5 minutes
*/5 * * * * /usr/bin/collect-babel-metrics.sh
```

**Requirements:**
- `curl` - For HTTP requests to platform
- `netcat` (`nc`) - For querying Babel control socket
- `babeld` - Babel routing daemon (port 33123)

## Integration with Firmware Builds

These scripts can be automatically included in OpenWrt firmware builds:

1. **Via UCI Defaults:**
   - Platform generates UCI defaults script during firmware build
   - Script includes device configuration
   - Applied on first boot via `/etc/uci-defaults/`

2. **Via Custom Files:**
   - Add scripts to firmware build using ImageBuilder
   - Scripts placed in `/usr/bin/` in the built image
   - Cron jobs configured in `/etc/crontabs/root`

Example firmware build with scripts:

```python
from backend.services.image_builder.builder import ImageBuilder

builder = ImageBuilder(
    version="23.05.2",
    target="ath79",
    subtarget="generic"
)

# Add required packages
builder.add_package("curl")
builder.add_package("netcat")
builder.add_package("babeld")

# Add scripts
builder.add_file(
    "/usr/bin/openmesh-register.sh",
    open("node-scripts/openmesh-register.sh").read()
)
builder.add_file(
    "/usr/bin/collect-babel-metrics.sh",
    open("node-scripts/collect-babel-metrics.sh").read()
)

# Add cron job
cron_entry = "* * * * * /usr/bin/collect-babel-metrics.sh\n"
builder.add_file("/etc/crontabs/root", cron_entry)

# Build
result = builder.build()
```

## Deployment Workflow

### Option 1: Post-Installation (Manual)

1. Flash stock OpenWrt or basic OpenMesh firmware
2. Connect router to network
3. SSH into router
4. Run registration script
5. Install metrics collection script
6. Router is now managed

### Option 2: Pre-Configured Firmware (Automated)

1. Build firmware with scripts included
2. Flash firmware to router
3. Router auto-registers on first boot
4. Metrics automatically collected
5. Zero manual configuration required

### Option 3: Hybrid (Recommended for Testing)

1. Build basic firmware with Babel and packages
2. Flash to router
3. Manually run registration
4. Test configuration
5. Once validated, create pre-configured firmware for production

## Troubleshooting

### Registration Issues

```bash
# Check network connectivity
ping 10.0.0.1

# Test platform reachability
curl http://10.0.0.1:8000/health

# Check MAC address detection
cat /sys/class/net/eth0/address

# Manual registration with debug
sh -x /usr/bin/openmesh-register.sh
```

### Metrics Collection Issues

```bash
# Check if Babel is running
ps | grep babeld

# Test Babel control socket
echo "dump" | nc localhost 33123

# Check device ID file
cat /etc/openmesh/device-id

# Test metrics collection manually
/usr/bin/collect-babel-metrics.sh

# Check logs
logread | grep openmesh-metrics
```

### Common Errors

**"babeld is not running"**
- Solution: Install and start babeld
```bash
opkg install babeld
/etc/init.d/babeld enable
/etc/init.d/babeld start
```

**"Device not registered"**
- Solution: Run registration script first
```bash
/usr/bin/openmesh-register.sh
```

**"Could not determine MAC address"**
- Solution: Manually specify interface
```bash
cat /sys/class/net/br-lan/address  # Use br-lan instead of eth0
```

**HTTP timeout errors**
- Solution: Check platform URL and firewall
```bash
# Test platform connectivity
curl -v http://10.0.0.1:8000/health

# Check routing
ip route get 10.0.0.1
```

## Security Considerations

**Current Implementation (Development):**
- No authentication on API endpoints
- Scripts run as root
- No encryption (HTTP)
- Platform URL configurable via environment

**Production Recommendations:**
1. Use HTTPS with valid certificates
2. Implement API key authentication
3. Restrict platform access via firewall
4. Use least-privilege execution (non-root user)
5. Validate all input data
6. Rate limit API endpoints

## Platform Integration

The platform expects these endpoints to be used:

- `POST /api/v1/devices/register` - Device registration
- `GET /api/v1/devices/{id}/config` - Get device configuration
- `POST /api/v1/devices/{id}/heartbeat` - Send metrics and heartbeat

Metrics are stored in InfluxDB and can be queried via:
- `GET /api/v1/metrics/devices/{id}` - Device-specific metrics
- `GET /api/v1/metrics/networks/{id}` - Network-wide metrics

## License

Part of the OpenMesh platform. See main project LICENSE file.
