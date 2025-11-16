import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { firmwareApi } from '../lib/api'
import { ArrowLeft, Download, FileDown } from 'lucide-react'

export default function FirmwareDetail() {
  const { id } = useParams()

  const { data: build, isLoading, error } = useQuery({
    queryKey: ['firmware', id],
    queryFn: () => firmwareApi.get(id).then((res) => res.data),
  })

  if (isLoading) {
    return <div className="loading">Loading build...</div>
  }

  if (error) {
    return <div className="error">Error loading build: {error.message}</div>
  }

  const handleDownload = async () => {
    try {
      const response = await firmwareApi.download(id)
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', build.image_filename)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Download failed:', error)
      alert('Failed to download firmware')
    }
  }

  return (
    <div className="device-detail-page">
      <Link to="/firmware" className="back-link">
        <ArrowLeft size={20} />
        Back to Firmware
      </Link>

      <div className="device-header">
        <div className="device-header-icon" style={{background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)'}}>
          <Download size={32} />
        </div>
        <div>
          <h1>{build.name}</h1>
          <span className={`badge badge-${getBuildStatusColor(build.status)}`}>
            {build.status}
          </span>
        </div>
        {build.status === 'success' && (
          <button className="btn btn-primary" onClick={handleDownload}>
            <FileDown size={20} />
            Download
          </button>
        )}
      </div>

      <div className="card">
        <h2>Build Information</h2>
        <div className="info-grid">
          <div className="info-item">
            <span className="info-label">Build Number</span>
            <code className="info-value">{build.build_number}</code>
          </div>
          <div className="info-item">
            <span className="info-label">OpenWrt Version</span>
            <code className="info-value">{build.openwrt_version}</code>
          </div>
          <div className="info-item">
            <span className="info-label">Target</span>
            <code className="info-value">{build.target}/{build.subtarget}</code>
          </div>
          <div className="info-item">
            <span className="info-label">Profile</span>
            <code className="info-value">{build.profile || 'Generic'}</code>
          </div>
          <div className="info-item">
            <span className="info-label">Status</span>
            <span className="info-value">{build.status}</span>
          </div>
          <div className="info-item">
            <span className="info-label">Created</span>
            <span className="info-value">{new Date(build.created_at).toLocaleString()}</span>
          </div>
          {build.build_started_at && (
            <div className="info-item">
              <span className="info-label">Build Started</span>
              <span className="info-value">{new Date(build.build_started_at).toLocaleString()}</span>
            </div>
          )}
          {build.build_completed_at && (
            <div className="info-item">
              <span className="info-label">Build Completed</span>
              <span className="info-value">{new Date(build.build_completed_at).toLocaleString()}</span>
            </div>
          )}
          {build.build_duration_seconds && (
            <div className="info-item">
              <span className="info-label">Build Duration</span>
              <span className="info-value">{formatDuration(build.build_duration_seconds)}</span>
            </div>
          )}
          {build.image_size_bytes && (
            <div className="info-item">
              <span className="info-label">Image Size</span>
              <span className="info-value">{formatBytes(build.image_size_bytes)}</span>
            </div>
          )}
          {build.download_count !== undefined && (
            <div className="info-item">
              <span className="info-label">Downloads</span>
              <span className="info-value">{build.download_count}</span>
            </div>
          )}
        </div>
      </div>

      {build.base_packages && build.base_packages.length > 0 && (
        <div className="card">
          <h2>Packages</h2>
          <div style={{display: 'flex', flexWrap: 'wrap', gap: '0.5rem'}}>
            {build.base_packages.map((pkg) => (
              <span key={pkg} className="badge badge-secondary">
                {pkg}
              </span>
            ))}
          </div>
        </div>
      )}

      {build.error_message && (
        <div className="card">
          <h2>Error Message</h2>
          <pre style={{color: 'var(--color-error)', whiteSpace: 'pre-wrap'}}>{build.error_message}</pre>
        </div>
      )}

      {build.build_log && (
        <div className="card">
          <h2>Build Log</h2>
          <pre style={{
            background: '#1e1e1e',
            color: '#d4d4d4',
            padding: '1rem',
            borderRadius: 'var(--radius)',
            overflow: 'auto',
            maxHeight: '500px',
            fontSize: '0.875rem',
            whiteSpace: 'pre-wrap',
            wordWrap: 'break-word'
          }}>{build.build_log}</pre>
        </div>
      )}
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

function formatBytes(bytes) {
  if (!bytes) return 'N/A'
  const mb = bytes / (1024 * 1024)
  return `${mb.toFixed(2)} MB`
}

function formatDuration(seconds) {
  if (!seconds) return 'N/A'
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}m ${secs}s`
}
