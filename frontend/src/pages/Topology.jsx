import { GitBranch } from 'lucide-react'

export default function Topology() {
  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Network Topology</h1>
          <p className="subtitle">Visual representation of your mesh network</p>
        </div>
      </div>

      <div className="card">
        <div className="empty-state">
          <GitBranch size={48} className="empty-icon" />
          <h3>Topology Visualization Coming Soon</h3>
          <p>
            Interactive network topology graph with D3.js will be available here.
            <br />
            This feature will show real-time mesh connections and routing paths.
          </p>
        </div>
      </div>
    </div>
  )
}
