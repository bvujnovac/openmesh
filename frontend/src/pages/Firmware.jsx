import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { firmwareApi } from '../lib/api'
import {
  Download,
  Plus,
  Search,
  Filter,
  ChevronRight,
  Trash2,
  FileDown,
} from 'lucide-react'
import './Firmware.css'

export default function Firmware() {
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const queryClient = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ['firmware', searchTerm, statusFilter],
    queryFn: () => firmwareApi.list({ limit: 100 }).then((res) => res.data),
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => firmwareApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['firmware'])
    },
  })

  if (isLoading) {
    return <div className="loading">Loading firmware builds...</div>
  }

  if (error) {
    return <div className="error">Error loading builds: {error.message}</div>
  }

  const builds = data?.builds || []
  const filteredBuilds = builds.filter((build) => {
    const matchesSearch =
      build.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      build.build_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      build.openwrt_version?.includes(searchTerm)

    const matchesStatus =
      statusFilter === 'all' || build.status === statusFilter

    return matchesSearch && matchesStatus
  })

  const statusCounts = {
    all: builds.length,
    success: builds.filter((b) => b.status === 'success').length,
    building: builds.filter((b) => b.status === 'building').length,
    failed: builds.filter((b) => b.status === 'failed').length,
    pending: builds.filter((b) => b.status === 'pending').length,
  }

  const handleDownload = async (buildId, filename) => {
    try {
      const response = await firmwareApi.download(buildId)
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', filename)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Download failed:', error)
      alert('Failed to download firmware')
    }
  }

  const handleDelete = async (buildId) => {
    if (window.confirm('Are you sure you want to delete this build?')) {
      try {
        await deleteMutation.mutateAsync(buildId)
      } catch (error) {
        console.error('Delete failed:', error)
        alert('Failed to delete build')
      }
    }
  }

  return (
    <div className="firmware-page">
      <div className="page-header">
        <div>
          <h1>Firmware Builds</h1>
          <p className="subtitle">{data?.total || 0} builds total</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
          <Plus size={20} />
          New Build
        </button>
      </div>

      <div className="filters-bar">
        <div className="search-box">
          <Search size={20} />
          <input
            type="text"
            placeholder="Search builds..."
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

      {filteredBuilds.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <Download size={48} className="empty-icon" />
            <h3>No builds found</h3>
            <p>
              {searchTerm || statusFilter !== 'all'
                ? 'Try adjusting your filters'
                : 'Create your first firmware build to get started'}
            </p>
          </div>
        </div>
      ) : (
        <div className="builds-list">
          {filteredBuilds.map((build) => (
            <div key={build.id} className="build-card">
              <div className="build-card-header">
                <div>
                  <h3>
                    <Link to={`/firmware/${build.id}`}>{build.name}</Link>
                  </h3>
                  <p className="build-number">{build.build_number}</p>
                </div>
                <span className={`badge badge-${getBuildStatusColor(build.status)}`}>
                  {build.status}
                </span>
              </div>

              <div className="build-details">
                <div className="detail-row">
                  <span className="detail-label">OpenWrt Version</span>
                  <code className="detail-value">{build.openwrt_version}</code>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Target</span>
                  <code className="detail-value">
                    {build.target}/{build.subtarget}
                  </code>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Profile</span>
                  <code className="detail-value">{build.profile || 'Generic'}</code>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Created</span>
                  <span className="detail-value">{formatDate(build.created_at)}</span>
                </div>
                {build.status === 'success' && (
                  <>
                    <div className="detail-row">
                      <span className="detail-label">Image Size</span>
                      <span className="detail-value">
                        {formatBytes(build.image_size_bytes)}
                      </span>
                    </div>
                    <div className="detail-row">
                      <span className="detail-label">Downloads</span>
                      <span className="detail-value">{build.download_count || 0}</span>
                    </div>
                  </>
                )}
              </div>

              <div className="build-actions">
                <Link to={`/firmware/${build.id}`} className="btn btn-secondary">
                  <ChevronRight size={16} />
                  Details
                </Link>
                {build.status === 'success' && (
                  <button
                    className="btn btn-primary"
                    onClick={() => handleDownload(build.id, build.image_filename)}
                  >
                    <FileDown size={16} />
                    Download
                  </button>
                )}
                {!build.is_default && (
                  <button
                    className="btn btn-error"
                    onClick={() => handleDelete(build.id)}
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreateModal && (
        <CreateBuildModal onClose={() => setShowCreateModal(false)} />
      )}
    </div>
  )
}

function CreateBuildModal({ onClose }) {
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState({
    name: '',
    openwrt_version: '23.05.2',
    device_key: '',
    target: 'ath79',
    subtarget: 'generic',
    profile: '',
    include_uci_defaults: true,
  })

  // Fetch supported devices
  const { data: devicesData } = useQuery({
    queryKey: ['supported-devices'],
    queryFn: () => firmwareApi.getSupportedDevices().then((res) => res.data),
  })

  const supportedDevices = devicesData?.devices || []

  const createMutation = useMutation({
    mutationFn: (data) => firmwareApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries(['firmware'])
      onClose()
    },
  })

  const handleDeviceSelect = (deviceKey) => {
    const device = supportedDevices.find((d) => d.key === deviceKey)
    if (device) {
      setFormData({
        ...formData,
        device_key: deviceKey,
        target: device.target,
        subtarget: device.subtarget,
        profile: device.profile,
        name: formData.name || `${device.name} Firmware`,
      })
    } else {
      setFormData({
        ...formData,
        device_key: '',
      })
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    createMutation.mutate(formData)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Create Firmware Build</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Build Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
            />
          </div>

          <div className="form-group">
            <label>Device Type</label>
            <select
              value={formData.device_key}
              onChange={(e) => handleDeviceSelect(e.target.value)}
            >
              <option value="">Custom (manual configuration)</option>
              <optgroup label="Ubiquiti NanoStation">
                {supportedDevices
                  .filter((d) => d.key.startsWith('nanostation-') && !d.key.includes('loco'))
                  .map((device) => (
                    <option key={device.key} value={device.key}>
                      {device.name} ({device.flash_size_mb}MB / {device.ram_size_mb}MB RAM)
                    </option>
                  ))}
              </optgroup>
              <optgroup label="Ubiquiti NanoStation Loco">
                {supportedDevices
                  .filter((d) => d.key.includes('loco'))
                  .map((device) => (
                    <option key={device.key} value={device.key}>
                      {device.name} ({device.flash_size_mb}MB / {device.ram_size_mb}MB RAM)
                    </option>
                  ))}
              </optgroup>
              <optgroup label="Other Ubiquiti">
                {supportedDevices
                  .filter(
                    (d) =>
                      !d.key.startsWith('nanostation-') &&
                      !d.key.includes('loco')
                  )
                  .map((device) => (
                    <option key={device.key} value={device.key}>
                      {device.name} ({device.flash_size_mb}MB / {device.ram_size_mb}MB RAM)
                    </option>
                  ))}
              </optgroup>
            </select>
            {formData.device_key && (
              <small className="form-hint">
                {supportedDevices.find((d) => d.key === formData.device_key)?.notes}
              </small>
            )}
          </div>

          <div className="form-group">
            <label>OpenWrt Version</label>
            <input
              type="text"
              value={formData.openwrt_version}
              onChange={(e) =>
                setFormData({ ...formData, openwrt_version: e.target.value })
              }
              required
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Target</label>
              <input
                type="text"
                value={formData.target}
                onChange={(e) => setFormData({ ...formData, target: e.target.value })}
                required
              />
            </div>

            <div className="form-group">
              <label>Subtarget</label>
              <input
                type="text"
                value={formData.subtarget}
                onChange={(e) =>
                  setFormData({ ...formData, subtarget: e.target.value })
                }
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label>Profile (optional)</label>
            <input
              type="text"
              value={formData.profile}
              onChange={(e) => setFormData({ ...formData, profile: e.target.value })}
              placeholder="e.g. tplink_archer-c7-v5"
            />
          </div>

          <div className="form-group checkbox">
            <label>
              <input
                type="checkbox"
                checked={formData.include_uci_defaults}
                onChange={(e) =>
                  setFormData({ ...formData, include_uci_defaults: e.target.checked })
                }
              />
              Include UCI defaults script
            </label>
          </div>

          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={createMutation.isLoading}
            >
              {createMutation.isLoading ? 'Creating...' : 'Create Build'}
            </button>
          </div>

          {createMutation.isError && (
            <div className="error">
              Failed to create build: {createMutation.error.message}
            </div>
          )}
        </form>
      </div>
    </div>
  )
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
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleDateString()
}

function formatBytes(bytes) {
  if (!bytes) return 'N/A'
  const mb = bytes / (1024 * 1024)
  return `${mb.toFixed(2)} MB`
}
