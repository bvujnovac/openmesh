import { BarChart3 } from 'lucide-react'

export default function Metrics() {
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
          <h3>Metrics Dashboard Coming Soon</h3>
          <p>
            Interactive charts showing device health, network performance, and Babel routing metrics.
            <br />
            Data from InfluxDB will be visualized using Chart.js.
          </p>
        </div>
      </div>
    </div>
  )
}
