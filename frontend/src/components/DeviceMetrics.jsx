import { useState, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import MetricsChart from './MetricsChart'
import { RefreshCw } from 'lucide-react'
import { useWebSocket } from '../hooks/useWebSocket'
import { metricsApi } from '../lib/api'

const timeRanges = [
  { label: '1 Hour', value: '-1h' },
  { label: '6 Hours', value: '-6h' },
  { label: '24 Hours', value: '-24h' },
  { label: '7 Days', value: '-7d' },
  { label: '30 Days', value: '-30d' },
]

export default function DeviceMetrics({ deviceId }) {
  const [timeRange, setTimeRange] = useState('-1h')
  const queryClient = useQueryClient()

  // WebSocket connection for real-time updates
  const { isConnected, subscribe, unsubscribe } = useWebSocket('/api/v1/ws', {
    onMessage: (message) => {
      // Handle real-time metrics updates
      if (message.type === 'device_metrics' && message.device_id === deviceId) {
        console.log('Received real-time metrics update:', message.data)
        // Invalidate query to refetch with new data
        queryClient.invalidateQueries(['device-metrics', deviceId, timeRange])
      }
    },
  })

  // Subscribe to device metrics on mount
  useEffect(() => {
    if (isConnected && deviceId) {
      subscribe('device', deviceId)
    }

    return () => {
      if (isConnected && deviceId) {
        unsubscribe('device', deviceId)
      }
    }
  }, [isConnected, deviceId, subscribe, unsubscribe])

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['device-metrics', deviceId, timeRange],
    queryFn: () =>
      metricsApi
        .getDeviceMetrics(deviceId, {
          start: timeRange,
          end: 'now()',
          metrics: 'cpu_usage_percent,memory_free_mb,load_1min,uptime_seconds,babel_neighbors,babel_routes,babel_avg_rtt_ms',
        })
        .then((res) => res.data),
    refetchInterval: 60000, // Refresh every minute (fallback if WebSocket fails)
  })

  if (isLoading) {
    return <div className="loading">Loading metrics...</div>
  }

  if (error) {
    return (
      <div className="error" style={{ padding: '20px' }}>
        <h4>Error loading metrics</h4>
        <p>{error.message}</p>
        <button onClick={() => refetch()} className="btn btn-primary">
          Retry
        </button>
      </div>
    )
  }

  // Group data by field
  const metricsData = {}
  if (data && data.data) {
    data.data.forEach((point) => {
      if (!metricsData[point.field]) {
        metricsData[point.field] = []
      }
      metricsData[point.field].push({
        time: point.time,
        value: point.value,
      })
    })
  }

  const hasData = Object.keys(metricsData).length > 0

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {timeRanges.map((range) => (
            <button
              key={range.value}
              onClick={() => setTimeRange(range.value)}
              className={`btn ${timeRange === range.value ? 'btn-primary' : 'btn-secondary'}`}
              style={{ padding: '6px 12px', fontSize: '14px' }}
            >
              {range.label}
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {isConnected && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#10b981' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#10b981' }}></div>
              Live
            </div>
          )}
          <button
            onClick={() => refetch()}
            className="btn btn-secondary"
            disabled={isFetching}
            style={{ padding: '6px 12px' }}
          >
            <RefreshCw size={16} className={isFetching ? 'spinning' : ''} />
          </button>
        </div>
      </div>

      {!hasData ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#999' }}>
          No metrics data available for this device.
          <br />
          Data will appear once the device starts sending heartbeats.
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '24px' }}>
          {/* CPU Usage */}
          {metricsData.cpu_usage_percent && (
            <div className="card">
              <MetricsChart
                data={metricsData.cpu_usage_percent}
                title="CPU Usage"
                yAxisLabel="Usage (%)"
                color="#ef4444"
                unit="%"
              />
            </div>
          )}

          {/* Memory */}
          {metricsData.memory_free_mb && (
            <div className="card">
              <MetricsChart
                data={metricsData.memory_free_mb}
                title="Free Memory"
                yAxisLabel="Memory (MB)"
                color="#22c55e"
                unit="MB"
              />
            </div>
          )}

          {/* Load Average */}
          {metricsData.load_1min && (
            <div className="card">
              <MetricsChart
                data={metricsData.load_1min}
                title="Load Average (1 min)"
                yAxisLabel="Load"
                color="#f59e0b"
              />
            </div>
          )}

          {/* Uptime */}
          {metricsData.uptime_seconds && (
            <div className="card">
              <MetricsChart
                data={metricsData.uptime_seconds.map(d => ({
                  ...d,
                  value: d.value / 3600, // Convert to hours
                }))}
                title="Uptime"
                yAxisLabel="Hours"
                color="#8b5cf6"
                unit="h"
              />
            </div>
          )}

          {/* Babel Neighbors */}
          {metricsData.babel_neighbors && (
            <div className="card">
              <MetricsChart
                data={metricsData.babel_neighbors}
                title="Babel Neighbors"
                yAxisLabel="Count"
                color="#3b82f6"
              />
            </div>
          )}

          {/* Babel Routes */}
          {metricsData.babel_routes && (
            <div className="card">
              <MetricsChart
                data={metricsData.babel_routes}
                title="Babel Routes"
                yAxisLabel="Count"
                color="#06b6d4"
              />
            </div>
          )}

          {/* Babel RTT */}
          {metricsData.babel_avg_rtt_ms && (
            <div className="card">
              <MetricsChart
                data={metricsData.babel_avg_rtt_ms}
                title="Average RTT"
                yAxisLabel="Latency (ms)"
                color="#ec4899"
                unit="ms"
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
