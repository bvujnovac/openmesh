import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { devicesApi } from '../lib/api'
import { ArrowLeft, Router as RouterIcon, Activity, Clock, Network } from 'lucide-react'
import './DeviceDetail.css'

export default function DeviceDetail() {
  const { id } = useParams()

  const { data: device, isLoading, error } = useQuery({
    queryKey: ['device', id],
    queryFn: () => devicesApi.get(id).then(res => res.data),
  })

  if (isLoading) {
    return <div className="loading">Loading device...</div>
  }

  if (error) {
    return <div className="error">Error loading device: {error.message}</div>
  }

  return (
    <div className="device-detail-page">
      <Link to="/devices" className="back-link">
        <ArrowLeft size={20} />
        Back to Devices
      </Link>

      <div className="device-header">
        <div className="device-header-icon">
          <RouterIcon size={32} />
        </div>
        <div>
          <h1>{device.hostname || 'Unnamed Device'}</h1>
          <span className={`badge badge-${getStatusColor(device.status)}`}>
            {device.status}
          </span>
        </div>
      </div>

      <div className="details-grid">
        <div className="card">
          <h2>Device Information</h2>
          <div className="info-grid">
            <div className="info-item">
              <span className="info-label">IP Address</span>
              <code className="info-value">{device.ip_address}</code>
            </div>
            <div className="info-item">
              <span className="info-label">MAC Address</span>
              <code className="info-value">{device.mac_address}</code>
            </div>
            <div className="info-item">
              <span className="info-label">Subnet ID</span>
              <span className="info-value">{device.subnet_id}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Network</span>
              <span className="info-value">{device.network?.name || 'N/A'}</span>
            </div>
            <div className="info-item">
              <span className="info-label">DHCP Pool Start</span>
              <code className="info-value">{device.dhcp_pool_start}</code>
            </div>
            <div className="info-item">
              <span className="info-label">DHCP Pool End</span>
              <code className="info-value">{device.dhcp_pool_end}</code>
            </div>
            <div className="info-item">
              <span className="info-label">Created</span>
              <span className="info-value">{formatDateTime(device.created_at)}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Last Seen</span>
              <span className="info-value">{formatDateTime(device.last_seen)}</span>
            </div>
          </div>
        </div>

        <div className="card">
          <h2>Status</h2>
          <div className="status-indicators">
            <div className="status-indicator">
              <Activity size={20} className="indicator-icon" />
              <div>
                <div className="indicator-label">Current Status</div>
                <div className="indicator-value">{device.status}</div>
              </div>
            </div>
            <div className="status-indicator">
              <Clock size={20} className="indicator-icon" />
              <div>
                <div className="indicator-label">Last Contact</div>
                <div className="indicator-value">{formatRelativeTime(device.last_seen)}</div>
              </div>
            </div>
            <div className="status-indicator">
              <Network size={20} className="indicator-icon" />
              <div>
                <div className="indicator-label">Network Status</div>
                <div className="indicator-value">
                  {device.status === 'online' ? 'Connected' : 'Disconnected'}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {device.notes && (
        <div className="card">
          <h2>Notes</h2>
          <p>{device.notes}</p>
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

function formatDateTime(dateString) {
  if (!dateString) return 'Never'
  return new Date(dateString).toLocaleString()
}

function formatRelativeTime(dateString) {
  if (!dateString) return 'Never'
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins} minutes ago`
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)} hours ago`
  if (diffMins < 10080) return `${Math.floor(diffMins / 1440)} days ago`
  return 'More than a week ago'
}
