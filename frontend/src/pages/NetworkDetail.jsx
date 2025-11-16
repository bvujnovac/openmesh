import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { networksApi } from '../lib/api'
import { ArrowLeft, Network as NetworkIcon } from 'lucide-react'

export default function NetworkDetail() {
  const { id } = useParams()

  const { data: network, isLoading, error } = useQuery({
    queryKey: ['network', id],
    queryFn: () => networksApi.get(id).then((res) => res.data),
  })

  if (isLoading) {
    return <div className="loading">Loading network...</div>
  }

  if (error) {
    return <div className="error">Error loading network: {error.message}</div>
  }

  return (
    <div className="device-detail-page">
      <Link to="/networks" className="back-link">
        <ArrowLeft size={20} />
        Back to Networks
      </Link>

      <div className="device-header">
        <div className="device-header-icon" style={{background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'}}>
          <NetworkIcon size={32} />
        </div>
        <div>
          <h1>{network.name}</h1>
          <span className={`badge badge-${network.is_active ? 'success' : 'secondary'}`}>
            {network.is_active ? 'Active' : 'Inactive'}
          </span>
        </div>
      </div>

      <div className="card">
        <h2>Network Configuration</h2>
        <div className="info-grid">
          <div className="info-item">
            <span className="info-label">Slug</span>
            <code className="info-value">{network.slug}</code>
          </div>
          <div className="info-item">
            <span className="info-label">Network CIDR</span>
            <code className="info-value">{network.network_cidr}</code>
          </div>
          <div className="info-item">
            <span className="info-label">Infrastructure CIDR</span>
            <code className="info-value">{network.infrastructure_cidr}</code>
          </div>
          <div className="info-item">
            <span className="info-label">Mesh SSID</span>
            <span className="info-value">{network.mesh_ssid}</span>
          </div>
          <div className="info-item">
            <span className="info-label">Max Routers</span>
            <span className="info-value">{network.max_routers}</span>
          </div>
          <div className="info-item">
            <span className="info-label">Clients Per Router</span>
            <span className="info-value">{network.clients_per_router}</span>
          </div>
        </div>
      </div>

      {network.description && (
        <div className="card">
          <h2>Description</h2>
          <p>{network.description}</p>
        </div>
      )}
    </div>
  )
}
