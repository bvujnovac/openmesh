import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { devicesApi } from '../lib/api'
import { Search, Filter, Router as RouterIcon, ChevronRight } from 'lucide-react'
import './Devices.css'

export default function Devices() {
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')

  const { data, isLoading, error } = useQuery({
    queryKey: ['devices', searchTerm, statusFilter],
    queryFn: () => devicesApi.list({ limit: 1000 }).then(res => res.data),
  })

  if (isLoading) {
    return <div className="loading">Loading devices...</div>
  }

  if (error) {
    return <div className="error">Error loading devices: {error.message}</div>
  }

  const devices = data?.devices || []
  const filteredDevices = devices.filter(device => {
    const matchesSearch =
      device.hostname?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      device.mac_address?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      device.ip_address?.includes(searchTerm)

    const matchesStatus = statusFilter === 'all' || device.status === statusFilter

    return matchesSearch && matchesStatus
  })

  const statusCounts = {
    all: devices.length,
    online: devices.filter(d => d.status === 'online').length,
    offline: devices.filter(d => d.status === 'offline').length,
    pending: devices.filter(d => d.status === 'pending').length,
  }

  return (
    <div className="devices-page">
      <div className="page-header">
        <div>
          <h1>Devices</h1>
          <p className="subtitle">{data?.total || 0} devices registered</p>
        </div>
      </div>

      <div className="filters-bar">
        <div className="search-box">
          <Search size={20} />
          <input
            type="text"
            placeholder="Search devices..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="status-filters">
          {Object.entries(statusCounts).map(([status, count]) => (
            <button
              key={status}
              className={`filter-btn ${statusFilter === status ? 'active' : ''}`}
              onClick={() => setStatusFilter(status)}
            >
              {status} ({count})
            </button>
          ))}
        </div>
      </div>

      {filteredDevices.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <RouterIcon size={48} className="empty-icon" />
            <h3>No devices found</h3>
            <p>
              {searchTerm || statusFilter !== 'all'
                ? 'Try adjusting your filters'
                : 'Register your first device to get started'}
            </p>
          </div>
        </div>
      ) : (
        <div className="devices-grid">
          {filteredDevices.map((device) => (
            <Link to={`/devices/${device.id}`} key={device.id} className="device-card">
              <div className="device-card-header">
                <div className="device-icon">
                  <RouterIcon size={24} />
                </div>
                <span className={`badge badge-${getStatusColor(device.status)}`}>
                  {device.status}
                </span>
              </div>

              <h3>{device.hostname || 'Unnamed Device'}</h3>

              <div className="device-details">
                <div className="detail-row">
                  <span className="detail-label">IP Address</span>
                  <code className="detail-value">{device.ip_address}</code>
                </div>
                <div className="detail-row">
                  <span className="detail-label">MAC Address</span>
                  <code className="detail-value">{device.mac_address}</code>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Network</span>
                  <span className="detail-value">{device.network?.name || 'N/A'}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Last Seen</span>
                  <span className="detail-value">{formatDate(device.last_seen)}</span>
                </div>
              </div>

              <div className="device-card-footer">
                <span>View details</span>
                <ChevronRight size={16} />
              </div>
            </Link>
          ))}
        </div>
      )}
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
