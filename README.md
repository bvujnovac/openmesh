# OpenWrt Mesh Network Project - Context Save

## Project Overview

Building a scalable OpenWrt mesh network with:
- **508 mesh routers maximum** (optimized allocation)
- **64,008 total client capacity** (126 clients per router)
- **Automatic MAC-based IP assignment** (zero configuration)
- **Babel routing protocol** for mesh backbone
- **Single /16 network** (10.0.0.0/16) with separate zones
- **Centralized monitoring dashboard** (next phase)

## Network Architecture Finalized

### Address Space Layout
```
Total Network: 10.0.0.0/16 (65,536 addresses)

Infrastructure Zone (Mesh Routers):
├── Range: 10.0.0.1 → 10.0.1.254 (512 addresses)
├── Capacity: 508 mesh routers
└── Assignment: MAC-based hash distribution

Client Zone (DHCP Pools):
├── Range: 10.0.2.1 → 10.0.255.254 (65,024 addresses)  
├── Capacity: 508 routers × 126 clients = 64,008 clients
└── Assignment: 2 pools per subnet (.1-.126 and .127-.252)
```

### DHCP Pool Allocation
- **2 pools per subnet**: Eliminates boundary spanning issues
- **126 clients per router**: Perfect fit within subnet boundaries
- **254 subnets utilized**: 10.0.2.x through 10.0.255.x
- **No overlaps**: Each router gets unique 126-address pool

## Key Technical Decisions

### 1. Babel Configuration (CRITICAL)
- **Only redistribute infrastructure**: `10.0.0.0/23` (router IPs only)
- **Never redistribute client IPs**: Prevents memory explosion (64K routes)
- **Layer 2 bridging**: Clients communicate via bridge, not routing
- **Protocol 3 filtering**: Only DHCP-installed default routes

### 2. Auto-Configuration Strategy
- **UCI-only approach**: Modifies existing OpenWrt LAN configuration
- **Hardware agnostic**: Uses whatever OpenWrt configured as 'lan'
- **MAC from UCI**: `uci get wireless.@wifi-device[0].macaddr` preferred
- **Single script**: `/etc/uci-defaults/99-mesh-auto-config`

### 3. Interface Design
- **Uses existing LAN**: No custom interface creation
- **Existing bridge**: Works with br-lan (whatever OpenWrt bridged)
- **WAN untouched**: Keeps existing WAN configuration
- **Add mesh WiFi**: Adds ad-hoc interface to existing radio

## Final Configuration Script

Located in artifacts as "OpenWrt Mesh Network Configuration Guide - Final Clean Version"

Key components:
- **Auto-config script**: Pure UCI commands, modifies existing LAN
- **Babel setup**: Infrastructure-only redistribution 
- **WiFi mesh**: Ad-hoc interface for backbone
- **DHCP optimization**: 126 clients, perfect subnet utilization

## Monitoring Requirements (Next Phase)

### Babel Metrics Available
- **Neighbor information**: MAC addresses, signal quality, RTT
- **Route information**: Prefixes, metrics, next hops
- **System information**: Node ID, interfaces, performance
- **Access method**: TCP connection to localhost:33123

### Dashboard Requirements
- **Real-time topology**: Visual mesh network map
- **Performance monitoring**: Latency, convergence, stability  
- **Alerting**: Node disconnections, high latency, route flapping
- **Scale**: Handle 508-router deployment
- **Container deployment**: Docker-based for easy deployment

### Architecture Questions for Dashboard
1. **Deployment**: Docker Compose vs single container
2. **Data persistence**: SQLite vs PostgreSQL, retention period
3. **Authentication**: Internal only vs login system
4. **Reporting frequency**: 30s, 1min, 5min intervals
5. **Alerts**: Thresholds for latency, node down detection

## Current Status

### Completed
✅ Network architecture design (508 routers, 64,008 clients)
✅ Address space optimization (/16 with separate zones)
✅ DHCP pool allocation algorithm (2 per subnet, no overlaps)
✅ Babel configuration (infrastructure-only redistribution)
✅ Auto-configuration script (UCI-only, hardware agnostic)
✅ MAC detection from UCI (WiFi radio preferred)
✅ Complete deployment guide

### Next Steps
🔄 **Centralized monitoring dashboard**:
- Backend: REST API + time-series database
- Frontend: Interactive topology + real-time charts
- Container: Single-command deployment
- Integration: Mesh node monitoring scripts

### Testing Completed
- **DHCP pool generation**: Verified with 510-router test loop
- **Boundary protection**: No .255 starts, no overlaps
- **Address efficiency**: 97.7% of /16 space allocated to clients

## Important Notes

1. **Critical Babel filter**: Must use `10.0.0.0/23` not `10.0.0.0/16`
2. **No VLAN creation**: Script only reads existing UCI, no modifications
3. **Hardware agnostic**: Works with any OpenWrt default configuration
4. **MAC source priority**: WiFi > System > LAN > eth0 > fallback
5. **Perfect scaling**: Exactly 508 routers supported with clean boundaries

## Files Structure
```
/etc/uci-defaults/99-mesh-auto-config  # Main configuration script
/usr/bin/babel-metrics-collector       # Future monitoring script
```

## Contact/Deployment Context
- User working on mesh network for 50+ router deployment
- Hardware agnostic solution needed (various OpenWrt routers)
- Emphasis on zero manual configuration
- Interest in enterprise-scale monitoring and management
