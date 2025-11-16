import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { networksApi } from '../lib/api'
import { Network as NetworkIcon, ChevronRight, Plus } from 'lucide-react'

export default function Networks() {
  const [showCreateModal, setShowCreateModal] = useState(false)
  const queryClient = useQueryClient()

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
          <p className="subtitle">{networks.length} mesh network{networks.length !== 1 ? 's' : ''}</p>
        </div>
        <button className="btn btn-primary" onClick={() => {
          console.log('Create Network button clicked')
          setShowCreateModal(true)
        }}>
          <Plus size={20} />
          Create Network
        </button>
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

      {showCreateModal && (
        <CreateNetworkModal onClose={() => setShowCreateModal(false)} />
      )}
    </div>
  )
}

function CreateNetworkModal({ onClose }) {
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState({
    name: '',
    slug: '',
    network_cidr: '10.0.0.0/16',
    mesh_ssid: '',
    mesh_password: '',
    client_ssid: '',
    client_password: '',
    description: '',
  })

  const createMutation = useMutation({
    mutationFn: (data) => {
      console.log('Creating network with data:', data)
      return networksApi.create(data)
    },
    onSuccess: (response) => {
      console.log('Network created successfully:', response)
      queryClient.invalidateQueries({ queryKey: ['networks'] })
      onClose()
    },
    onError: (error) => {
      console.error('Failed to create network:', error)
      console.error('Error response:', error.response?.data)
    },
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    console.log('Form submitted with data:', formData)
    createMutation.mutate(formData)
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))

    // Auto-generate slug from name
    if (name === 'name' && !formData.slug) {
      const slug = value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
      setFormData((prev) => ({ ...prev, slug }))
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Create Network</h2>
          <button className="modal-close" onClick={onClose}>
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {createMutation.isError && (
              <div className="alert alert-error">
                {createMutation.error.response?.data?.detail || 'Failed to create network'}
              </div>
            )}

            <div className="form-group">
              <label htmlFor="name">Network Name *</label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleChange}
                required
                placeholder="e.g., Community Mesh Network"
              />
            </div>

            <div className="form-group">
              <label htmlFor="slug">Slug *</label>
              <input
                type="text"
                id="slug"
                name="slug"
                value={formData.slug}
                onChange={handleChange}
                required
                pattern="[a-z0-9-]+"
                placeholder="e.g., community-mesh"
              />
              <small>URL-safe identifier (lowercase letters, numbers, and hyphens)</small>
            </div>

            <div className="form-group">
              <label htmlFor="network_cidr">Network CIDR *</label>
              <input
                type="text"
                id="network_cidr"
                name="network_cidr"
                value={formData.network_cidr}
                onChange={handleChange}
                required
                pattern="\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}"
                placeholder="e.g., 10.0.0.0/16"
              />
              <small>IP address range for the entire mesh network</small>
            </div>

            <div className="form-group">
              <label htmlFor="mesh_ssid">Mesh SSID *</label>
              <input
                type="text"
                id="mesh_ssid"
                name="mesh_ssid"
                value={formData.mesh_ssid}
                onChange={handleChange}
                required
                maxLength="32"
                placeholder="e.g., CommunityMesh"
              />
              <small>WiFi network name for mesh backbone (not visible to clients)</small>
            </div>

            <div className="form-group">
              <label htmlFor="mesh_password">Mesh Password</label>
              <input
                type="password"
                id="mesh_password"
                name="mesh_password"
                value={formData.mesh_password}
                onChange={handleChange}
                minLength="8"
                placeholder="Minimum 8 characters"
              />
              <small>Leave empty for open mesh (not recommended)</small>
            </div>

            <div className="form-group">
              <label htmlFor="client_ssid">Client SSID</label>
              <input
                type="text"
                id="client_ssid"
                name="client_ssid"
                value={formData.client_ssid}
                onChange={handleChange}
                maxLength="32"
                placeholder="e.g., CommunityWiFi"
              />
              <small>WiFi network name for client devices (optional)</small>
            </div>

            <div className="form-group">
              <label htmlFor="client_password">Client Password</label>
              <input
                type="password"
                id="client_password"
                name="client_password"
                value={formData.client_password}
                onChange={handleChange}
                minLength="8"
                placeholder="Minimum 8 characters"
              />
            </div>

            <div className="form-group">
              <label htmlFor="description">Description</label>
              <textarea
                id="description"
                name="description"
                value={formData.description}
                onChange={handleChange}
                rows="3"
                placeholder="Optional description of this network"
              />
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={createMutation.isPending}
            >
              {createMutation.isPending ? 'Creating...' : 'Create Network'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
