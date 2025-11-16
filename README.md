# OpenMesh Platform

A modern, Python-based platform for managing OpenWrt mesh networks. Inspired by nodewatcher but rebuilt with contemporary technologies for scalability, maintainability, and ease of deployment.

## Features

✅ **Zero-Configuration Deployment** - Routers auto-configure via MAC-based IP assignment
✅ **Universal Hardware Support** - Works with 1000+ OpenWrt-supported devices
✅ **Package Sets** - Predefined configurations (mesh-minimal, mesh-full, gateway, etc.)
✅ **Profile Discovery** - Automatically discovers all available device profiles
✅ **Scalable** - Supports 508+ routers, 64K+ clients
✅ **Real-time Monitoring** - Live topology visualization and metrics
✅ **Custom Firmware Building** - Per-device or fleet-wide image generation
✅ **Babel Routing Protocol** - Efficient mesh routing with automatic failover
✅ **Modern Stack** - FastAPI, React, SQLite, InfluxDB
✅ **Containerized** - Easy deployment with Docker Compose

## Architecture

### Technology Stack

**Backend:**
- **FastAPI** - Modern async Python web framework
- **SQLAlchemy 2.0** - Database ORM with async support
- **Pydantic** - Data validation and settings management
- **Celery** - Distributed task queue for image building
- **Redis** - Caching and message broker

**Database:**
- **SQLite** - Primary database (lightweight, no separate DB server needed)
- **InfluxDB** - Time-series database for metrics (optimized for monitoring data)
- **Optional PostgreSQL** - Can be used instead of SQLite for larger deployments

**Frontend:**
- **React 18** - Modern UI framework with hooks
- **Vite** - Fast build tool and dev server
- **TanStack Query** - Server state management
- **React Router** - Client-side routing
- **Chart.js** - Metrics visualization
- **D3.js** - Network topology (prepared)

**Infrastructure:**
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration

### Core Components

```
openmesh/
├── backend/              # FastAPI backend application
│   ├── api/             # API endpoints (REST)
│   ├── core/            # Core configuration & database
│   ├── models/          # SQLAlchemy database models
│   ├── schemas/         # Pydantic validation schemas
│   ├── services/        # Business logic layer
│   │   ├── config_gen/  # Configuration generators
│   │   ├── image_builder/  # OpenWrt image builder
│   │   └── monitoring/  # Metrics collection (InfluxDB)
│   └── workers/         # Celery async workers
├── frontend/            # React web dashboard
│   ├── src/
│   │   ├── components/  # Reusable UI components
│   │   ├── pages/       # Page components (Dashboard, Devices, etc.)
│   │   └── lib/         # API client and utilities
│   └── vite.config.js   # Vite build configuration
├── node-scripts/        # Router-side scripts
│   ├── openmesh-register.sh        # Device registration
│   └── collect-babel-metrics.sh    # Metrics collection
├── imagebuilder/        # OpenWrt ImageBuilder storage
├── firmware/            # Built firmware images
├── docker/              # Docker configurations
└── docs/                # Documentation
```

## Network Architecture

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
└── Assignment: 2 pools per subnet
```

### Key Design Decisions

1. **MAC-Based IP Assignment** - Deterministic IP allocation using SHA256 hash
2. **Babel Protocol** - Only redistributes infrastructure routes (10.0.0.0/23)
3. **Client Pool Isolation** - 126 clients per router, no route redistribution
4. **Auto-Configuration** - Single UCI defaults script configures entire router

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Git
- 8GB RAM minimum
- Linux, macOS, or WSL2

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/openmesh.git
   cd openmesh
   ```

2. **Copy environment file:**
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` file:**
   - Change `SECRET_KEY` to a random string
   - Adjust network settings if needed

4. **Start the platform:**
   ```bash
   make dev
   ```

5. **Access the platform:**
   - **Web Dashboard:** http://localhost:3000
   - **API:** http://localhost:8000
   - **API Docs:** http://localhost:8000/docs
   - **InfluxDB UI:** http://localhost:8086 (admin/adminadmin)
   - **Health Check:** http://localhost:8000/health

### Development Commands

```bash
make dev         # Start development environment
make stop        # Stop all containers
make build       # Build Docker images
make clean       # Remove containers and volumes
make logs        # Show container logs
make shell       # Open shell in backend container
make db-migrate  # Create new database migration
make db-upgrade  # Apply database migrations
make test        # Run tests
make lint        # Run linters
make format      # Format code
```

## API Usage

### Register a Device

```bash
curl -X POST http://localhost:8000/api/v1/devices/register \
  -H "Content-Type: application/json" \
  -d '{
    "mac_address": "AA:BB:CC:DD:EE:FF",
    "hostname": "mesh-router-01",
    "hardware_model": "TP-Link Archer C7",
    "firmware_version": "OpenWrt 23.05.2"
  }'
```

### Get Device Configuration

```bash
curl http://localhost:8000/api/v1/devices/1/config
```

This returns a UCI defaults script that can be placed in `/etc/uci-defaults/99-openmesh-config` on the router.

### List Devices

```bash
curl http://localhost:8000/api/v1/devices?limit=10&status=online
```

### Create a Network

```bash
curl -X POST http://localhost:8000/api/v1/networks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Community Mesh",
    "slug": "community",
    "network_cidr": "10.0.0.0/16",
    "mesh_ssid": "CommunityMesh",
    "mesh_password": "secure-password-here"
  }'
```

### List Package Sets

```bash
curl http://localhost:8000/api/v1/firmware/package-sets
```

Returns available package sets with descriptions and requirements.

### List Available Device Profiles

```bash
# List all devices for ath79/generic
curl http://localhost:8000/api/v1/firmware/profiles/ath79/generic

# Search for Ubiquiti devices
curl "http://localhost:8000/api/v1/firmware/profiles/ath79/generic?search=ubiquiti"
```

### Build Firmware for Any Device

```bash
curl -X POST http://localhost:8000/api/v1/firmware \
  -H "Content-Type: application/json" \
  -d '{
    "name": "NanoStation M5 XW Mesh Firmware",
    "target": "ath79",
    "subtarget": "generic",
    "profile": "ubnt_nanostation-m-xw",
    "package_set": "mesh-full",
    "openwrt_version": "23.05.2",
    "include_uci_defaults": true
  }'
```

The `package_set` parameter automatically applies:
- mesh-minimal: babeld, kmod-ath9k
- mesh-full: babeld, kmod-ath9k, kmod-ath10k, ath10k-firmware, collectd
- mesh-gateway: Full mesh + firewall4, sqm-scripts, luci
- mesh-monitoring: Full mesh + iperf3, tcpdump
- mesh-client-ap: Full mesh + wpad-mbedtls, sqm-scripts

## Database Schema

### SQLite Tables

- **devices** - Mesh router registry
- **networks** - Network configurations
- **firmware_builds** - Built firmware images
- **alerts** - Network monitoring alerts

### InfluxDB Measurements (Time-Series Metrics)

- **device_health** - System health metrics (CPU, memory, load, uptime)
- **babel_routing** - Babel protocol metrics (neighbors, routes, RTT)
- **link_quality** - Mesh link quality metrics (signal, throughput, packet loss)

### Example Queries

**Get all online devices (SQLite):**
```sql
SELECT hostname, ip_address, last_seen
FROM devices
WHERE status = 'online'
ORDER BY last_seen DESC;
```

**Get Babel metrics for a device (InfluxDB/Flux):**
```flux
from(bucket: "metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "babel_routing")
  |> filter(fn: (r) => r["device_id"] == "1")
```

## Configuration Generator

The platform includes a sophisticated configuration generator that creates OpenWrt UCI scripts:

### IP Allocation Algorithm

```python
from backend.services.config_gen.ip_allocator import IPAllocator

allocator = IPAllocator(
    network_cidr="10.0.0.0/16",
    infrastructure_cidr="10.0.0.0/23",
    max_routers=508,
    clients_per_router=126
)

allocation = allocator.allocate_for_mac("AA:BB:CC:DD:EE:FF")
# Returns: {
#   "router_ip": "10.0.0.42",
#   "dhcp_start": "10.0.2.1",
#   "dhcp_end": "10.0.2.126",
#   "subnet_id": 2
# }
```

### UCI Script Generation

```python
from backend.services.config_gen.uci_generator import UCIGenerator

generator = UCIGenerator(
    router_ip="10.0.0.42",
    dhcp_pool_start="10.0.2.1",
    dhcp_pool_end="10.0.2.126",
    network_cidr="10.0.0.0/16",
    infrastructure_cidr="10.0.0.0/23",
    mesh_ssid="openmesh"
)

script = generator.generate()
# Returns complete UCI defaults script
```

## Deployment Workflow

### Device Registration Flow

1. **Router boots** with OpenMesh firmware
2. **Auto-config script** runs from `/etc/uci-defaults/`
3. **Calls registration API** with MAC address
4. **Platform allocates** IP and DHCP pool
5. **Returns configuration** script
6. **Script configures** network, Babel, WiFi
7. **Router joins** mesh network
8. **Starts reporting** metrics

### Firmware Build Flow

1. **Define build** via API or web UI
2. **Celery task** queues build job
3. **ImageBuilder** downloads OpenWrt, adds packages, includes UCI scripts
4. **Firmware built** asynchronously (5-15 minutes)
5. **Firmware stored** with SHA256 checksum
6. **Available for download** via web UI or API

### Metrics Collection Flow

1. **Router runs** `collect-babel-metrics.sh` via cron (every 60 seconds)
2. **Script collects** system metrics (CPU, memory, load, uptime)
3. **Script queries** Babel daemon on port 33123
4. **Collects Babel metrics**: neighbors, routes, installed routes, xroutes, RTT
5. **Sends JSON** to `/api/v1/devices/{id}/heartbeat`
6. **Platform writes** to InfluxDB (time-series) and SQLite (status)

### Current Metrics

**Implemented:**
- ✅ System metrics: CPU, memory (total/free), load average, uptime
- ✅ Babel metrics: Neighbor count, route count, installed routes, xroutes, avg RTT
- ✅ Device status: Last seen, online/offline tracking

**Planned (Phase 4):**
- ⏳ Per-link metrics: Signal strength, packet loss, throughput
- ⏳ Client metrics: Connected clients, DHCP leases
- ⏳ Alerting: Device offline, high latency, link degradation
- ⏳ Automated notifications: Email, Slack webhooks

## Package Sets

Instead of maintaining device-specific profiles, OpenMesh uses **package sets** that work with any OpenWrt-supported device. This allows the platform to scale to 1000+ devices automatically.

### Available Package Sets

**mesh-minimal** - For low-resource devices
- Minimal mesh routing with Babel
- Requires: 4MB+ flash, 32MB+ RAM
- Packages: babeld, kmod-ath9k
- Ideal for: Legacy hardware, 4-8MB flash devices

**mesh-full** - Recommended for most deployments
- Complete mesh stack with WiFi drivers and monitoring
- Requires: 8MB+ flash, 64MB+ RAM
- Packages: babeld, kmod-ath9k, kmod-ath10k, ath10k-firmware, collectd
- Ideal for: Modern routers, XW series, AC devices

**mesh-gateway** - For internet gateway nodes
- Mesh node with gateway capabilities (NAT, firewall, QoS)
- Requires: 16MB+ flash, 128MB+ RAM
- Packages: babeld, WiFi drivers, firewall4, sqm-scripts, luci
- Ideal for: High-RAM devices, gateway routers

**mesh-monitoring** - Enhanced monitoring and metrics
- Full mesh with enhanced monitoring tools
- Requires: 8MB+ flash, 64MB+ RAM
- Packages: Full mesh + iperf3, tcpdump, enhanced collectd
- Ideal for: Monitoring nodes, testing, development

**mesh-client-ap** - Optimized for client access
- Mesh node with dual SSID and QoS for clients
- Requires: 8MB+ flash, 64MB+ RAM
- Packages: babeld, WiFi drivers, wpad-mbedtls, sqm-scripts
- Ideal for: Client access points, indoor deployments

### Supported Hardware

OpenMesh works with **any device supported by OpenWrt** (1000+ devices). The platform automatically discovers available profiles for each target/subtarget.

**Common targets:**
- **ath79/generic** - Atheros AR71xx/AR913x/AR933x (Ubiquiti, TP-Link, etc.)
- **ramips/mt7621** - MediaTek MT7621 (Xiaomi, GL.iNet, etc.)
- **ipq40xx/generic** - Qualcomm IPQ40xx
- **x86/64** - x86 64-bit PCs and virtual machines
- **bcm27xx/bcm2711** - Raspberry Pi 4
- ...and many more

See the [OpenWrt Table of Hardware](https://openwrt.org/toh/start) to find your device's specifications.

## Web Dashboard

The platform includes a modern React-based web dashboard for managing the mesh network.

### Dashboard Features

**Dashboard Page** (`/`)
- System overview with statistics
- Online devices / total devices
- Active networks count
- Successful firmware builds
- Network health percentage
- Recent devices and builds

**Devices Page** (`/devices`)
- Grid view of all registered devices
- Search by hostname, MAC address, or IP
- Filter by status (online, offline, pending, failed)
- Click through to device details

**Device Detail Page** (`/devices/:id`)
- Complete device information
- Network configuration (IP, MAC, DHCP pool)
- Status indicators and last contact time
- Device notes

**Networks Page** (`/networks`)
- List of mesh networks
- Network CIDR and infrastructure CIDR
- Mesh SSID and settings
- Active/inactive status

**Firmware Page** (`/firmware`)
- List of all firmware builds
- Search and filter by status
- Create new firmware builds with:
  - Target/subtarget selector (10+ common targets)
  - Profile discovery (1000+ devices)
  - Package set selector (5 predefined sets)
  - Search/filter available profiles
- Download built firmware images
- Delete old builds
- View build logs and errors

**Topology Page** (`/topology`)
- Prepared for D3.js network visualization
- Will show real-time mesh connections (Phase 4)

**Metrics Page** (`/metrics`)
- Prepared for Chart.js integration
- Will show device health charts (Phase 4)

### Router Integration Scripts

**`node-scripts/openmesh-register.sh`**
- Auto-registers router with platform
- Receives IP allocation and configuration
- Applies UCI settings automatically

**`node-scripts/collect-babel-metrics.sh`**
- Collects system and Babel metrics
- Runs via cron every 60 seconds
- Sends heartbeat with metrics to platform

See `node-scripts/README.md` for detailed usage instructions.

## Development

### Project Structure

```
backend/
├── api/v1/              # API version 1 endpoints
│   ├── devices.py       # Device management & heartbeat
│   ├── networks.py      # Network management
│   ├── firmware.py      # Firmware build management
│   ├── topology.py      # Network topology data
│   ├── metrics.py       # Time-series metrics queries
│   └── __init__.py      # Router configuration
├── core/                # Core components
│   ├── config.py        # Settings management
│   └── database.py      # Async database configuration
├── models/              # SQLAlchemy database models
│   ├── device.py        # Device model
│   ├── network.py       # Network model
│   ├── firmware.py      # Firmware build model
│   ├── metric.py        # Metrics models (deprecated)
│   └── alert.py         # Alert model
├── schemas/             # Pydantic validation schemas
│   ├── device.py        # Device schemas
│   ├── network.py       # Network schemas
│   └── firmware.py      # Firmware build schemas
├── services/            # Business logic layer
│   ├── device_service.py           # Device operations
│   ├── network_service.py          # Network operations
│   ├── config_gen/                 # Configuration generators
│   │   ├── ip_allocator.py         # SHA256-based IP allocation
│   │   └── uci_generator.py        # UCI script generation
│   ├── image_builder/              # Firmware building
│   │   └── builder.py              # OpenWrt ImageBuilder wrapper
│   └── monitoring/                 # Metrics collection
│       └── influxdb_client.py      # InfluxDB client
├── workers/             # Celery async workers
│   ├── celery_app.py    # Celery configuration
│   └── tasks/
│       └── firmware.py  # Firmware build tasks
└── main.py              # FastAPI application entry point
```

### Adding a New Endpoint

1. **Create schema** in `backend/schemas/`
2. **Create service** in `backend/services/`
3. **Create endpoint** in `backend/api/v1/`
4. **Add tests** in `tests/`

### Database Migrations

```bash
# Create migration
make db-migrate

# Apply migrations
make db-upgrade

# Or manually:
docker-compose exec backend alembic revision --autogenerate -m "Add new field"
docker-compose exec backend alembic upgrade head
```

## Testing

```bash
# Run all tests
make test

# Run specific test file
docker-compose exec backend pytest tests/test_device_service.py

# Run with coverage
docker-compose exec backend pytest --cov=backend --cov-report=html
```

## Implementation Roadmap

### ✅ Phase 1: Foundation - COMPLETED
- [x] Project structure setup
- [x] Database schema design (SQLite + InfluxDB)
- [x] FastAPI application with async support
- [x] Docker development environment
- [x] Device & network models
- [x] IP allocation algorithm (SHA256-based MAC hashing)
- [x] UCI configuration generator
- [x] RESTful API endpoints (devices, networks)

### ✅ Phase 2: Firmware Building - COMPLETED
- [x] OpenWrt ImageBuilder integration
- [x] Celery task queue setup (Redis broker)
- [x] Async firmware building workflow
- [x] Firmware storage and serving
- [x] Build status tracking (pending → building → success/failed)
- [x] Firmware API endpoints (create, list, download, delete)
- [x] Build timeout handling (30 min default)
- [x] SHA256 checksum generation

### ✅ Phase 3: Web Dashboard & Monitoring - COMPLETED
- [x] React 18 frontend with Vite
- [x] 9 dashboard pages (Dashboard, Devices, Networks, Firmware, Topology, Metrics, etc.)
- [x] Device management UI with search & filters
- [x] Firmware build management UI
- [x] Network topology API (placeholder for D3.js visualization)
- [x] Metrics API (InfluxDB queries)
- [x] Node-side scripts (registration, Babel metrics collection)
- [x] Real-time metrics storage (InfluxDB)
- [x] Router auto-registration workflow

### 🔄 Phase 4: Advanced Features - NEXT
- [ ] D3.js network topology visualization
- [ ] Chart.js metrics dashboards
- [ ] WebSocket for real-time updates
- [ ] Alerting system (email, Slack notifications)
- [ ] Alert rule engine
- [ ] Multi-network isolation
- [ ] Automated firmware updates
- [ ] Advanced analytics

### ⏳ Phase 5: Production Hardening
- [ ] Authentication & authorization (JWT)
- [ ] API rate limiting
- [ ] HTTPS/TLS support
- [ ] Firmware image signing
- [ ] Backup and restore
- [ ] High-availability configuration
- [ ] Performance optimization
- [ ] Comprehensive documentation

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run linters: `make lint`
6. Format code: `make format`
7. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

- Documentation: `/docs` directory
- Issues: GitHub Issues
- Discussions: GitHub Discussions

## Related Projects

- [nodewatcher](https://github.com/wlanslovenija/nodewatcher) - Original inspiration
- [OpenWrt](https://openwrt.org/) - Linux distribution for embedded devices
- [Babel](https://www.irif.fr/~jch/software/babel/) - Mesh routing protocol

---

**Status:** Phase 3 Complete - Full-Stack Platform Ready for Production Testing

Built with ❤️ for the mesh networking community
