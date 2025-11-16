import { useState, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { GitBranch, RefreshCw } from 'lucide-react'
import axios from 'axios'
import NetworkTopology from '../components/NetworkTopology'
import { useWebSocket } from '../hooks/useWebSocket'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
})

export default function Topology() {
  const [networkFilter, setNetworkFilter] = useState(null)
  const queryClient = useQueryClient()

  // WebSocket connection for real-time topology updates
  const { isConnected, subscribe, unsubscribe } = useWebSocket('/api/v1/ws', {
    onMessage: (message) => {
      // Handle real-time topology and device updates
      if (message.type === 'topology_update') {
        console.log('Received topology update:', message.data)
        queryClient.invalidateQueries(['topology', networkFilter])
      } else if (message.type === 'device_update') {
        console.log('Received device update:', message.data)
        // Topology changes when devices come online/offline
        queryClient.invalidateQueries(['topology', networkFilter])
      }
    },
  })

  // Subscribe to topology updates on mount
  useEffect(() => {
    if (isConnected) {
      subscribe('topology')
    }

    // CRITICAL: Cleanup subscription on unmount to prevent server memory leak
    return () => {
      if (unsubscribe) {
        unsubscribe('topology')
      }
    }
  }, [isConnected, subscribe, unsubscribe])

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['topology', networkFilter],
    queryFn: () => {
      const params = networkFilter ? { network_id: networkFilter } : {}
      return api.get('/topology', { params }).then((res) => res.data)
    },
    refetchInterval: 30000, // Refresh every 30 seconds (fallback if WebSocket fails)
  })

  if (isLoading) {
    return (
      <div className="loading" style={{ textAlign: 'center', padding: '40px' }}>
        Loading topology...
      </div>
    )
  }

  if (error) {
    return (
      <div className="error" style={{ padding: '40px' }}>
        <h3>Error loading topology</h3>
        <p>{error.message}</p>
        <button onClick={() => refetch()} className="btn btn-primary">
          Retry
        </button>
      </div>
    )
  }

  const hasData = data && data.nodes && data.nodes.length > 0

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Network Topology</h1>
          <p className="subtitle">
            {data?.summary ? (
              <>
                {data.summary.total_nodes} devices, {data.summary.total_links} connections
                {' · '}
                <span style={{ color: '#22c55e' }}>
                  {data.summary.online_nodes} online
                </span>
                {isConnected && (
                  <>
                    {' · '}
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: '#10b981' }}>
                      <div style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#10b981' }}></div>
                      Live updates
                    </span>
                  </>
                )}
              </>
            ) : (
              'Visual representation of your mesh network'
            )}
          </p>
        </div>
        <button
          className="btn btn-secondary"
          onClick={() => refetch()}
          disabled={isFetching}
        >
          <RefreshCw size={20} className={isFetching ? 'spinning' : ''} />
          Refresh
        </button>
      </div>

      {!hasData ? (
        <div className="card">
          <div className="empty-state">
            <GitBranch size={48} className="empty-icon" />
            <h3>No Devices Found</h3>
            <p>
              Register devices to see your mesh network topology.
              <br />
              Devices will appear here once they connect to the platform.
            </p>
          </div>
        </div>
      ) : (
        <div className="card">
          <NetworkTopology data={data} height={600} />
        </div>
      )}
    </div>
  )
}

