import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { networksApi } from '../lib/api'
import { Network as NetworkIcon, ChevronRight } from 'lucide-react'

export default function Networks() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['networks'],
    queryFn: () => networksApi.list({ limit: 100 }).then((res) => res.data),
  })

  if (isLoading) {
    return <div className="loading">Loading networks...</div>
  }

  if (error) {
    return <div className="error">Error loading networks: {error.message}</div>
  }

  const networks = data?.networks || []

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Networks</h1>
          <p className="subtitle">{data?.total || 0} mesh networks</p>
        </div>
      </div>

      {networks.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <NetworkIcon size={48} className="empty-icon" />
            <h3>No networks found</h3>
            <p>Create your first mesh network to get started</p>
          </div>
        </div>
      ) : (
        <div className="devices-grid">
          {networks.map((network) => (
            <Link to={`/networks/${network.id}`} key={network.id} className="device-card">
              <div className="device-card-header">
                <div className="device-icon" style={{background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'}}>
                  <NetworkIcon size={24} />
                </div>
                <span className={`badge badge-${network.is_active ? 'success' : 'secondary'}`}>
                  {network.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>

              <h3>{network.name}</h3>

              <div className="device-details">
                <div className="detail-row">
                  <span className="detail-label">Network CIDR</span>
                  <code className="detail-value">{network.network_cidr}</code>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Infrastructure CIDR</span>
                  <code className="detail-value">{network.infrastructure_cidr}</code>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Mesh SSID</span>
                  <span className="detail-value">{network.mesh_ssid}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Max Routers</span>
                  <span className="detail-value">{network.max_routers}</span>
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
