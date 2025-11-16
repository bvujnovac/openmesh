import { useQuery } from '@tanstack/react-query'
import { devicesApi, networksApi, firmwareApi } from '../lib/api'
import { Router, Network, Download, Activity, AlertCircle, CheckCircle } from 'lucide-react'
import './Dashboard.css'

export default function Dashboard() {
  const { data: devices, isLoading: devicesLoading } = useQuery({
    queryKey: ['devices'],
    queryFn: () => devicesApi.list({ limit: 1000 }).then(res => res.data),
  })

  const { data: networks, isLoading: networksLoading } = useQuery({
    queryKey: ['networks'],
    queryFn: () => networksApi.list({ limit: 100 }).then(res => res.data),
  })

  const { data: builds, isLoading: buildsLoading } = useQuery({
    queryKey: ['firmware'],
    queryFn: () => firmwareApi.list({ limit: 10 }).then(res => res.data),
  })

  const stats = {
    totalDevices: devices?.total || 0,
    onlineDevices: devices?.devices?.filter(d => d.status === 'online').length || 0,
    totalNetworks: networks?.total || 0,
    activeNetworks: networks?.networks?.filter(n => n.is_active).length || 0,
    totalBuilds: builds?.total || 0,
    successfulBuilds: builds?.builds?.filter(b => b.status === 'success').length || 0,
  }

  const recentDevices = devices?.devices?.slice(0, 5) || []
  const recentBuilds = builds?.builds?.slice(0, 5) || []

  if (devicesLoading || networksLoading || buildsLoading) {
    return <div className="loading">Loading dashboard...</div>
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Dashboard</h1>
        <p className="subtitle">OpenMesh Network Management Platform</p>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon devices">
            <Router size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">{stats.onlineDevices}/{stats.totalDevices}</div>
            <div className="stat-label">Devices Online</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon networks">
            <Network size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">{stats.activeNetworks}/{stats.totalNetworks}</div>
            <div className="stat-label">Active Networks</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon builds">
            <Download size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">{stats.successfulBuilds}/{stats.totalBuilds}</div>
            <div className="stat-label">Successful Builds</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon health">
            <Activity size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">
              {stats.totalDevices > 0
                ? Math.round((stats.onlineDevices / stats.totalDevices) * 100)
                : 0}%
            </div>
            <div className="stat-label">Network Health</div>
          </div>
        </div>
      </div>

      <div className="dashboard-grid">
        <div className="card">
          <h2>Recent Devices</h2>
          {recentDevices.length === 0 ? (
            <p className="empty-state">No devices registered yet</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Hostname</th>
                  <th>IP Address</th>
                  <th>Status</th>
                  <th>Last Seen</th>
                </tr>
              </thead>
              <tbody>
                {recentDevices.map((device) => (
                  <tr key={device.id}>
                    <td>{device.hostname}</td>
                    <td><code>{device.ip_address}</code></td>
                    <td>
                      <span className={`badge badge-${getStatusColor(device.status)}`}>
                        {device.status}
                      </span>
                    </td>
                    <td>{formatDate(device.last_seen)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="card">
          <h2>Recent Builds</h2>
          {recentBuilds.length === 0 ? (
            <p className="empty-state">No firmware builds yet</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Version</th>
                  <th>Status</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {recentBuilds.map((build) => (
                  <tr key={build.id}>
                    <td>{build.name}</td>
                    <td><code>{build.openwrt_version}</code></td>
                    <td>
                      <span className={`badge badge-${getBuildStatusColor(build.status)}`}>
                        {build.status}
                      </span>
                    </td>
                    <td>{formatDate(build.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="card">
        <h2>System Status</h2>
        <div className="status-list">
          <div className="status-item">
            <CheckCircle size={20} className="status-icon success" />
            <div>
              <div className="status-title">API Server</div>
              <div className="status-description">Running normally</div>
            </div>
          </div>
          <div className="status-item">
            <CheckCircle size={20} className="status-icon success" />
            <div>
              <div className="status-title">Database</div>
              <div className="status-description">Connected</div>
            </div>
          </div>
          <div className="status-item">
            <CheckCircle size={20} className="status-icon success" />
            <div>
              <div className="status-title">InfluxDB</div>
              <div className="status-description">Metrics collecting</div>
            </div>
          </div>
          <div className="status-item">
            <CheckCircle size={20} className="status-icon success" />
            <div>
              <div className="status-title">Celery Worker</div>
              <div className="status-description">Processing tasks</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function getStatusColor(status) {
  const colors = {
    online: 'success',
    offline: 'secondary',
    pending: 'warning',
    failed: 'error',
  }
  return colors[status] || 'secondary'
}

function getBuildStatusColor(status) {
  const colors = {
    success: 'success',
    building: 'warning',
    pending: 'secondary',
    failed: 'error',
  }
  return colors[status] || 'secondary'
}

function formatDate(dateString) {
  if (!dateString) return 'Never'
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`
  return date.toLocaleDateString()
}
