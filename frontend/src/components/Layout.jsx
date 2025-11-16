import { Outlet, Link, useLocation } from 'react-router-dom'
import {
  Activity,
  Router,
  Network,
  Cpu,
  Download,
  BarChart3,
  GitBranch
} from 'lucide-react'
import './Layout.css'

const navItems = [
  { path: '/', label: 'Dashboard', icon: Activity },
  { path: '/devices', label: 'Devices', icon: Router },
  { path: '/networks', label: 'Networks', icon: Network },
  { path: '/topology', label: 'Topology', icon: GitBranch },
  { path: '/firmware', label: 'Firmware', icon: Download },
  { path: '/metrics', label: 'Metrics', icon: BarChart3 },
]

export default function Layout() {
  const location = useLocation()

  return (
    <div className="layout">
      <nav className="sidebar">
        <div className="sidebar-header">
          <Cpu size={32} className="logo-icon" />
          <h1>OpenMesh</h1>
        </div>

        <ul className="nav-list">
          {navItems.map(({ path, label, icon: Icon }) => (
            <li key={path}>
              <Link
                to={path}
                className={`nav-link ${location.pathname === path ? 'active' : ''}`}
              >
                <Icon size={20} />
                <span>{label}</span>
              </Link>
            </li>
          ))}
        </ul>

        <div className="sidebar-footer">
          <div className="status-indicator">
            <div className="status-dot online"></div>
            <span>System Online</span>
          </div>
        </div>
      </nav>

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}
