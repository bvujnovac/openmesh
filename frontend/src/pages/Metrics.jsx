import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BarChart3, Router as RouterIcon } from 'lucide-react'
import { devicesApi } from '../lib/api'
import DeviceMetrics from '../components/DeviceMetrics'

export default function Metrics() {
  const [selectedDeviceId, setSelectedDeviceId] = useState(null)

  const { data: devicesData, isLoading } = useQuery({
    queryKey: ['devices'],
    queryFn: () => devicesApi.list({ limit: 1000 }).then(res => res.data),
  })

  const devices = devicesData?.devices || []
  const onlineDevices = devices.filter(d => d.status === 'online')

  // Auto-select first online device if none selected
  if (!selectedDeviceId && onlineDevices.length > 0) {
    setSelectedDeviceId(onlineDevices[0].id)
  }

  if (isLoading) {
    return <div className="loading">Loading devices...</div>
  }

  if (devices.length === 0) {
    return (
      <div>
        <div className="page-header">
          <div>
            <h1>Metrics & Analytics</h1>
            <p className="subtitle">Real-time performance metrics and historical data</p>
          </div>
        </div>

        <div className="card">
          <div className="empty-state">
            <RouterIcon size={48} className="empty-icon" />
            <h3>No Devices Found</h3>
            <p>
              Register devices to start collecting and viewing metrics.
              <br />
              Metrics are automatically collected from device heartbeats and stored in InfluxDB.
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (onlineDevices.length === 0) {
    return (
      <div>
        <div className="page-header">
          <div>
            <h1>Metrics & Analytics</h1>
            <p className="subtitle">Real-time performance metrics and historical data</p>
          </div>
        </div>

        <div className="card">
          <div className="empty-state">
            <BarChart3 size={48} className="empty-icon" />
            <h3>No Online Devices</h3>
            <p>
              Metrics are only available for online devices.
              <br />
              Devices must send heartbeats to appear as online and collect metrics.
            </p>
          </div>
        </div>
      </div>
    )
  }

  const selectedDevice = devices.find(d => d.id === selectedDeviceId)

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Metrics & Analytics</h1>
          <p className="subtitle">Real-time performance metrics and historical data</p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          <label htmlFor="device-select" style={{ fontWeight: '500', fontSize: '14px' }}>
            Select Device:
          </label>
          <select
            id="device-select"
            value={selectedDeviceId || ''}
            onChange={(e) => setSelectedDeviceId(Number(e.target.value))}
            style={{
              flex: '1',
              minWidth: '200px',
              maxWidth: '400px',
              padding: '8px 12px',
              borderRadius: '6px',
              border: '1px solid var(--color-border)',
              fontSize: '14px',
              backgroundColor: 'var(--color-surface)',
            }}
          >
            {onlineDevices.map((device) => (
              <option key={device.id} value={device.id}>
                {device.hostname || `Device ${device.id}`} ({device.ip_address}) - {device.network?.name || 'No Network'}
              </option>
            ))}
          </select>

          {selectedDevice && (
            <div style={{ marginLeft: 'auto', display: 'flex', gap: '16px', fontSize: '14px' }}>
              <div>
                <span style={{ color: 'var(--color-text-secondary)' }}>Status:</span>{' '}
                <span className={`badge badge-${selectedDevice.status === 'online' ? 'success' : 'secondary'}`}>
                  {selectedDevice.status}
                </span>
              </div>
              <div>
                <span style={{ color: 'var(--color-text-secondary)' }}>MAC:</span>{' '}
                <code style={{ fontSize: '12px' }}>{selectedDevice.mac_address}</code>
              </div>
            </div>
          )}
        </div>
      </div>

      {selectedDeviceId && (
        <div className="card">
          <DeviceMetrics deviceId={selectedDeviceId} />
        </div>
      )}
    </div>
  )
}
