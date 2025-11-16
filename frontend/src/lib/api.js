import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Devices API
export const devicesApi = {
  list: (params) => api.get('/devices', { params }),
  get: (id) => api.get(`/devices/${id}`),
  register: (data) => api.post('/devices/register', data),
  update: (id, data) => api.patch(`/devices/${id}`, data),
  delete: (id) => api.delete(`/devices/${id}`),
  heartbeat: (id, data) => api.post(`/devices/${id}/heartbeat`, data),
  getConfig: (id) => api.get(`/devices/${id}/config`),
}

// Networks API
export const networksApi = {
  list: (params) => api.get('/networks', { params }),
  get: (id) => api.get(`/networks/${id}`),
  create: (data) => api.post('/networks', data),
  update: (id, data) => api.patch(`/networks/${id}`, data),
  delete: (id) => api.delete(`/networks/${id}`),
}

// Firmware API
export const firmwareApi = {
  list: (params) => api.get('/firmware', { params }),
  get: (id) => api.get(`/firmware/${id}`),
  create: (data) => api.post('/firmware', data),
  delete: (id) => api.delete(`/firmware/${id}`),
  download: (id) => {
    return api.get(`/firmware/${id}/download`, {
      responseType: 'blob',
    })
  },
  getSupportedDevices: () => api.get('/firmware/devices/supported'),
}

// Topology API
export const topologyApi = {
  get: () => api.get('/topology'),
  getLinks: () => api.get('/topology/links'),
}

// Metrics API
export const metricsApi = {
  getDeviceMetrics: (deviceId, params) =>
    api.get(`/metrics/devices/${deviceId}`, { params }),
  getNetworkMetrics: (networkId, params) =>
    api.get(`/metrics/networks/${networkId}`, { params }),
  getSystemMetrics: (params) =>
    api.get('/metrics/system', { params }),
}

export default api
