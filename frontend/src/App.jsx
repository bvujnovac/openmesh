import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Devices from './pages/Devices'
import DeviceDetail from './pages/DeviceDetail'
import Networks from './pages/Networks'
import NetworkDetail from './pages/NetworkDetail'
import Topology from './pages/Topology'
import Firmware from './pages/Firmware'
import FirmwareDetail from './pages/FirmwareDetail'
import Metrics from './pages/Metrics'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000, // 30 seconds
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="devices" element={<Devices />} />
            <Route path="devices/:id" element={<DeviceDetail />} />
            <Route path="networks" element={<Networks />} />
            <Route path="networks/:id" element={<NetworkDetail />} />
            <Route path="topology" element={<Topology />} />
            <Route path="firmware" element={<Firmware />} />
            <Route path="firmware/:id" element={<FirmwareDetail />} />
            <Route path="metrics" element={<Metrics />} />
          </Route>
        </Routes>
      </Router>
    </QueryClientProvider>
  )
}

export default App
