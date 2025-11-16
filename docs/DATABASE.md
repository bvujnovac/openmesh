# Database Architecture

## Overview

OpenMesh uses a dual-database architecture optimized for different data types:

- **SQLite** - Primary database for application data (devices, networks, firmware, alerts)
- **InfluxDB** - Time-series database for metrics (device health, Babel routing, link quality)

## SQLite Configuration

### Why SQLite?

SQLite is the default database for OpenMesh because:

1. **Zero Configuration** - No separate database server required
2. **Single File** - Easy backup, migration, and deployment
3. **ACID Compliant** - Full transactional support
4. **Fast** - Excellent performance for read-heavy workloads
5. **Portable** - Works on any platform without dependencies

### Database Location

The SQLite database file is stored in a Docker volume:

```
Docker: /app/data/openmesh.db
Host (via volume): docker volume inspect openmesh_sqlite_data
```

For local development without Docker:
```
./openmesh.db (in project root)
```

### Connection Settings

The database URL is configured in `.env`:

```bash
DATABASE_URL=sqlite+aiosqlite:///./openmesh.db
```

For Docker (absolute path):
```bash
DATABASE_URL=sqlite+aiosqlite:////app/data/openmesh.db
```

### SQLite-Specific Configuration

The platform automatically configures SQLite for optimal performance:

```python
# backend/core/database.py
if settings.is_sqlite:
    engine = create_async_engine(
        str(settings.DATABASE_URL),
        echo=settings.DEBUG,
        connect_args={"check_same_thread": False},  # Multi-threading support
    )
```

### Performance Tuning

SQLite is tuned with these pragmas (can be added to connection):

```sql
PRAGMA journal_mode = WAL;          -- Write-Ahead Logging for concurrency
PRAGMA synchronous = NORMAL;        -- Balance safety and performance
PRAGMA cache_size = -64000;         -- 64MB cache
PRAGMA temp_store = MEMORY;         -- Use memory for temp tables
PRAGMA mmap_size = 268435456;       -- 256MB memory-mapped I/O
```

## InfluxDB Configuration

### Why InfluxDB?

InfluxDB is used for time-series metrics because:

1. **Optimized for Time-Series** - Purpose-built for timestamp data
2. **High Write Throughput** - Handles thousands of metrics/second
3. **Efficient Storage** - Compression optimized for time-series
4. **Powerful Queries** - Flux query language for analytics
5. **Data Retention** - Automatic downsampling and expiration

### Measurements

InfluxDB stores three types of measurements:

#### 1. device_health
System health metrics from routers:
- CPU usage, load average
- Memory usage (total, free, cached)
- Uptime
- Connected clients

#### 2. babel_routing
Babel routing protocol metrics:
- Neighbor count and details
- Route count (total and installed)
- Average RTT to neighbors
- Route metrics and costs

#### 3. link_quality
Mesh link quality between routers:
- Signal strength (dBm)
- Noise level (dBm)
- SNR (Signal-to-Noise Ratio)
- Babel link metric
- RTT (Round-Trip Time)
- Packet statistics

### InfluxDB Configuration

Settings in `.env`:

```bash
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=openmesh-dev-token-change-in-production
INFLUXDB_ORG=openmesh
INFLUXDB_BUCKET=metrics
```

### Retention Policies

Default retention: 30 days (can be configured in InfluxDB UI)

Recommended retention policies:
- Raw data: 7 days
- 5-minute aggregates: 30 days
- 1-hour aggregates: 1 year
- Daily aggregates: 5 years

## Database Schema

### SQLite Tables

#### devices
Mesh router registry with network assignment:
```sql
CREATE TABLE devices (
    id INTEGER PRIMARY KEY,
    mac_address VARCHAR(17) UNIQUE NOT NULL,
    hostname VARCHAR(255) NOT NULL,
    ip_address VARCHAR(15) UNIQUE NOT NULL,
    dhcp_pool_start VARCHAR(15) NOT NULL,
    dhcp_pool_end VARCHAR(15) NOT NULL,
    subnet_id INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,
    -- ... additional fields
);
```

#### networks
Mesh network configurations:
```sql
CREATE TABLE networks (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    network_cidr VARCHAR(18) NOT NULL,
    infrastructure_cidr VARCHAR(18) NOT NULL,
    mesh_ssid VARCHAR(32) NOT NULL,
    -- ... additional fields
);
```

#### firmware_builds
Firmware build tracking:
```sql
CREATE TABLE firmware_builds (
    id INTEGER PRIMARY KEY,
    build_number VARCHAR(50) UNIQUE NOT NULL,
    openwrt_version VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    image_filename VARCHAR(255),
    image_size_bytes INTEGER,
    -- ... additional fields
);
```

#### alerts
Network monitoring alerts:
```sql
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    device_id INTEGER,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    -- ... additional fields
);
```

## Migrations

### Creating Migrations

```bash
# Auto-generate migration from model changes
make db-migrate

# Or manually:
docker-compose exec backend alembic revision --autogenerate -m "Add new field"
```

### Applying Migrations

```bash
# Apply all pending migrations
make db-upgrade

# Or manually:
docker-compose exec backend alembic upgrade head
```

### Migration Files

Migrations are stored in `alembic/versions/` with timestamps:
```
alembic/versions/20250116_1030-abc123_add_device_location.py
```

## Backup and Restore

### SQLite Backup

**Using Docker volume:**
```bash
# Backup
docker run --rm -v openmesh_sqlite_data:/data -v $(pwd):/backup alpine \
    tar czf /backup/openmesh-db-backup.tar.gz -C /data .

# Restore
docker run --rm -v openmesh_sqlite_data:/data -v $(pwd):/backup alpine \
    tar xzf /backup/openmesh-db-backup.tar.gz -C /data
```

**Direct file copy:**
```bash
# Backup
docker cp openmesh-backend:/app/data/openmesh.db ./backup-$(date +%Y%m%d).db

# Restore
docker cp ./backup-20250116.db openmesh-backend:/app/data/openmesh.db
```

### InfluxDB Backup

**Using InfluxDB CLI:**
```bash
# Backup
docker exec openmesh-influxdb influx backup /backup
docker cp openmesh-influxdb:/backup ./influxdb-backup-$(date +%Y%m%d)

# Restore
docker cp ./influxdb-backup-20250116 openmesh-influxdb:/restore
docker exec openmesh-influxdb influx restore /restore
```

## Switching to PostgreSQL (Optional)

For deployments with >1000 routers, PostgreSQL may be preferred:

### 1. Install PostgreSQL Dependencies

```bash
pip install -e ".[postgres]"
```

### 2. Update Environment

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/openmesh
```

### 3. Update Docker Compose

Add PostgreSQL service:
```yaml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: openmesh
      POSTGRES_PASSWORD: openmesh
      POSTGRES_DB: openmesh
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
```

### 4. Run Migrations

```bash
make db-upgrade
```

The platform automatically detects the database type and configures accordingly.

## Troubleshooting

### SQLite Database Locked

**Problem:** `database is locked` error

**Solution:**
```bash
# Check for long-running queries
docker exec openmesh-backend sqlite3 /app/data/openmesh.db ".timeout 10000"

# Enable WAL mode (Write-Ahead Logging)
docker exec openmesh-backend sqlite3 /app/data/openmesh.db "PRAGMA journal_mode=WAL;"
```

### InfluxDB Connection Failed

**Problem:** Cannot connect to InfluxDB

**Solution:**
```bash
# Check InfluxDB status
docker logs openmesh-influxdb

# Verify credentials
curl http://localhost:8086/health

# Reset InfluxDB (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d influxdb
```

### Migration Conflicts

**Problem:** Alembic migration conflicts

**Solution:**
```bash
# View current revision
docker-compose exec backend alembic current

# View migration history
docker-compose exec backend alembic history

# Downgrade if needed
docker-compose exec backend alembic downgrade -1

# Resolve conflicts and re-migrate
docker-compose exec backend alembic upgrade head
```

## Best Practices

### 1. Regular Backups
- Automate daily SQLite backups
- Retain at least 7 days of backups
- Test restore procedures monthly

### 2. Monitoring
- Monitor SQLite file size
- Track InfluxDB disk usage
- Set up alerts for database errors

### 3. Maintenance
- Vacuum SQLite periodically (monthly)
- Review InfluxDB retention policies
- Clean up old metrics data

### 4. Security
- Never expose database ports publicly
- Use strong passwords for InfluxDB
- Encrypt backup files
- Rotate InfluxDB tokens regularly

## Performance Benchmarks

Typical performance on modest hardware (4 CPU, 8GB RAM):

**SQLite:**
- Device queries: <10ms
- Complex joins: <50ms
- Bulk inserts: 1000+ rows/sec
- Database size: ~100MB per 1000 devices

**InfluxDB:**
- Metric writes: 10,000+ points/sec
- Query response: <100ms for 1 hour of data
- Storage: ~50MB per device per month (30s intervals)
- Compression ratio: ~10:1

## References

- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [SQLite Performance Tuning](https://www.sqlite.org/optoverview.html)
- [InfluxDB Documentation](https://docs.influxdata.com/)
- [SQLAlchemy Async Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
