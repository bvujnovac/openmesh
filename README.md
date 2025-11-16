# OpenMesh Platform

A modern, Python-based platform for managing OpenWrt mesh networks. Inspired by nodewatcher but rebuilt with contemporary technologies for scalability, maintainability, and ease of deployment.

## Features

✅ **Zero-Configuration Deployment** - Routers auto-configure via MAC-based IP assignment
✅ **Hardware Agnostic** - Works with any OpenWrt-supported device
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

**Frontend:** (Coming in Phase 4)
- **React** - UI framework
- **D3.js/vis.js** - Network topology visualization
- **WebSockets** - Real-time updates

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
│   │   └── monitoring/  # Metrics collection
│   └── workers/         # Celery async workers
├── frontend/            # Web dashboard (Phase 4)
├── collectors/          # Node-side monitoring scripts
├── imagebuilder/        # OpenWrt ImageBuilder
├── configs/             # Configuration templates
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
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - InfluxDB UI: http://localhost:8086 (admin/adminadmin)
   - Health Check: http://localhost:8000/health

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

### Firmware Build Flow (Phase 2)

1. **Define build** via API or web UI
2. **Celery task** queues build job
3. **ImageBuilder** generates custom firmware
4. **Firmware stored** with metadata
5. **Available for download** or auto-update

## Monitoring (Phase 3)

### Metrics Collection

- **System metrics**: CPU, memory, load, uptime
- **Babel metrics**: Neighbors, routes, RTT
- **Link metrics**: Signal strength, throughput
- **Client metrics**: Connected clients, DHCP leases

### Alerting (Phase 3)

- **Device offline** - Node unreachable
- **High latency** - RTT above threshold
- **Link degraded** - Signal quality issues
- **Route flapping** - Unstable routes

## Development

### Project Structure

```
backend/
├── api/v1/              # API version 1 endpoints
│   ├── devices.py       # Device management
│   ├── networks.py      # Network management
│   └── __init__.py      # Router configuration
├── core/                # Core components
│   ├── config.py        # Settings management
│   └── database.py      # Database configuration
├── models/              # Database models
│   ├── device.py        # Device model
│   ├── network.py       # Network model
│   ├── firmware.py      # Firmware build model
│   ├── metric.py        # Metrics models
│   └── alert.py         # Alert model
├── schemas/             # Pydantic schemas
│   ├── device.py        # Device schemas
│   └── network.py       # Network schemas
├── services/            # Business logic
│   ├── device_service.py      # Device operations
│   ├── network_service.py     # Network operations
│   └── config_gen/            # Configuration generators
│       ├── ip_allocator.py    # IP allocation
│       └── uci_generator.py   # UCI script generation
└── main.py              # FastAPI application
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

### ✅ Phase 1: Foundation (Weeks 1-2) - COMPLETED
- [x] Project structure setup
- [x] Database schema design
- [x] Basic FastAPI application
- [x] Docker development environment
- [x] Device & network models
- [x] IP allocation algorithm
- [x] UCI configuration generator
- [x] Basic API endpoints

### 🔄 Phase 2: Image Builder (Weeks 3-4) - NEXT
- [ ] OpenWrt ImageBuilder integration
- [ ] Celery task queue setup
- [ ] Build configuration templates
- [ ] Firmware storage and serving
- [ ] Build status tracking
- [ ] API endpoints for builds

### ⏳ Phase 3: Monitoring (Weeks 5-6)
- [ ] Babel metrics collector
- [ ] Data ingestion pipeline
- [ ] Time-series storage optimization
- [ ] Alert rule engine
- [ ] Notification system
- [ ] Metrics API endpoints

### ⏳ Phase 4: Dashboard (Weeks 7-8)
- [ ] Frontend application setup
- [ ] Network topology visualization
- [ ] Real-time metrics display
- [ ] Device management UI
- [ ] WebSocket integration

### ⏳ Phase 5: Advanced Features (Weeks 9-10)
- [ ] Multi-network support
- [ ] Automated firmware updates
- [ ] Advanced analytics
- [ ] Performance optimization
- [ ] Documentation & tutorials

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

**Status:** Phase 1 Complete - Ready for Phase 2 Development

Built with ❤️ for the mesh networking community
