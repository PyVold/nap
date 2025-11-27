import axios from 'axios';

// Use relative URLs in development (proxy will handle it)
// Use full URL in production or when REACT_APP_API_URL is set
const API_BASE_URL = process.env.REACT_APP_API_URL || '';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API Activity tracking
let activeRequests = 0;
const apiActivityListeners = [];

export const subscribeToApiActivity = (callback) => {
  apiActivityListeners.push(callback);
  return () => {
    const index = apiActivityListeners.indexOf(callback);
    if (index > -1) {
      apiActivityListeners.splice(index, 1);
    }
  };
};

const notifyApiActivity = (isActive) => {
  apiActivityListeners.forEach((callback) => callback(isActive, activeRequests));
};

// Request interceptor
api.interceptors.request.use(
  (config) => {
    activeRequests++;
    notifyApiActivity(true);
    
    // Ensure token is attached to every request
    const token = localStorage.getItem('auth_token');
    if (token && !config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => {
    activeRequests--;
    notifyApiActivity(activeRequests > 0);
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    activeRequests--;
    notifyApiActivity(activeRequests > 0);
    return response;
  },
  (error) => {
    activeRequests--;
    notifyApiActivity(activeRequests > 0);
    
    // Handle authentication errors
    if (error.response?.status === 401) {
      console.error('Authentication failed:', error.response?.data?.detail || error.message);
      // Optionally redirect to login page
      // window.location.href = '/login';
    }
    
    return Promise.reject(error);
  }
);

// Devices API
export const devicesAPI = {
  getAll: () => api.get('/devices/'),
  getById: (id) => api.get(`/devices/${id}`),
  create: (device) => api.post('/devices/', device),
  update: (id, device) => api.put(`/devices/${id}`, device),
  delete: (id) => api.delete(`/devices/${id}`),
  discover: (discoveryData) => api.post('/devices/discover', discoveryData),
};

// Rules API
export const rulesAPI = {
  getAll: () => api.get('/rules/'),
  getById: (id) => api.get(`/rules/${id}`),
  create: (rule) => api.post('/rules/', rule),
  update: (id, rule) => api.put(`/rules/${id}`, rule),
  delete: (id) => api.delete(`/rules/${id}`),
  toggle: (id) => api.put(`/rules/${id}/toggle`),
};

// Audit API
export const auditAPI = {
  run: (auditRequest) => api.post('/audit/', auditRequest),
  getResults: () => api.get('/audit/results'),
  getResultsByDevice: (deviceId) => api.get(`/audit/results/${deviceId}`),
  getCompliance: () => api.get('/audit/compliance'),
  cleanup: (days) => api.delete(`/audit/results/cleanup?days=${days}`),
};

// Health API
export const healthAPI = {
  checkDevice: (deviceId, force = false) => api.post(`/health/check/${deviceId}?force=${force}`),
  checkAll: () => api.post('/health/check-all'),
  getHistory: (deviceId, limit = 10) => api.get(`/health/history/${deviceId}?limit=${limit}`),
  getSummary: () => api.get('/health/summary'),
};

// System Health
export const systemAPI = {
  healthCheck: () => api.get('/api/health-check'),
};

// Discovery Groups API
export const discoveryGroupsAPI = {
  getAll: () => api.get('/discovery-groups/'),
  getById: (id) => api.get(`/discovery-groups/${id}`),
  create: (group) => api.post('/discovery-groups/', group),
  update: (id, group) => api.put(`/discovery-groups/${id}`, group),
  delete: (id) => api.delete(`/discovery-groups/${id}`),
  discover: (id) => api.post(`/discovery-groups/${id}/discover`),
};

// Device Groups API
export const deviceGroupsAPI = {
  getAll: () => api.get('/device-groups/'),
  getById: (id) => api.get(`/device-groups/${id}`),
  create: (group) => api.post('/device-groups/', group),
  update: (id, group) => api.put(`/device-groups/${id}`, group),
  delete: (id) => api.delete(`/device-groups/${id}`),
  addDevice: (groupId, deviceId) => api.post(`/device-groups/${groupId}/devices/${deviceId}`),
  removeDevice: (groupId, deviceId) => api.delete(`/device-groups/${groupId}/devices/${deviceId}`),
  getDevices: (groupId) => api.get(`/device-groups/${groupId}/devices`),
};

// Audit Schedules API
export const auditSchedulesAPI = {
  getAll: () => api.get('/audit-schedules/'),
  getById: (id) => api.get(`/audit-schedules/${id}`),
  create: (schedule) => api.post('/audit-schedules/', schedule),
  update: (id, schedule) => api.put(`/audit-schedules/${id}`, schedule),
  delete: (id) => api.delete(`/audit-schedules/${id}`),
  run: (id) => api.post(`/audit-schedules/${id}/run`),
};

// Config Backups API
export const configBackupsAPI = {
  getAll: (deviceId = null) => {
    const url = deviceId ? `/config-backups/device/${deviceId}/history` : '/config-backups/';
    return api.get(url);
  },
  getById: (id) => api.get(`/config-backups/${id}`),
  create: (backupData) => api.post('/config-backups/', backupData),
  getDevicesSummary: (includeAuto = false) => api.get(`/config-backups/devices/summary?include_auto=${includeAuto}`),
  getDeviceHistory: (deviceId, limit = 50, includeAuto = false) => api.get(`/config-backups/device/${deviceId}/history?limit=${limit}&include_auto=${includeAuto}`),
  getDeviceChanges: (deviceId, limit = 50) => api.get(`/config-backups/device/${deviceId}/changes?limit=${limit}`),
  compare: (backupId1, backupId2) => api.get(`/config-backups/compare/${backupId1}/${backupId2}`),
  delete: (id) => api.delete(`/config-backups/${id}`),
};

// Notifications API
export const notificationsAPI = {
  getWebhooks: (activeOnly = false) => api.get(`/notifications/webhooks${activeOnly ? '?active_only=true' : ''}`),
  getWebhookById: (id) => api.get(`/notifications/webhooks/${id}`),
  createWebhook: (webhook) => api.post('/notifications/webhooks', webhook),
  updateWebhook: (id, webhook) => api.patch(`/notifications/webhooks/${id}`, webhook),
  deleteWebhook: (id) => api.delete(`/notifications/webhooks/${id}`),
  testWebhook: (id, testData) => api.post(`/notifications/webhooks/${id}/test`, testData),
  getHistory: (webhookId = null, limit = 100) => {
    const params = new URLSearchParams();
    if (webhookId) params.append('webhook_id', webhookId);
    params.append('limit', limit);
    return api.get(`/notifications/history?${params}`);
  },
  getStats: () => api.get('/notifications/stats'),
};

// Device Import API
export const deviceImportAPI = {
  downloadTemplate: () => api.get('/device-import/template', { responseType: 'blob' }),
  validate: (csvContent) => api.post('/device-import/validate', { csv_content: csvContent }),
  uploadFile: (file, updateExisting = false) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/device-import/upload?update_existing=${updateExisting}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  importCSV: (csvContent, updateExisting = false) =>
    api.post('/device-import/csv', { csv_content: csvContent, update_existing: updateExisting }),
  export: () => api.get('/device-import/export', { responseType: 'blob' }),
};

// Drift Detection API
export const driftDetectionAPI = {
  getSummary: () => api.get('/drift-detection/summary'),
  scanAll: () => api.get('/drift-detection/scan'),
  checkDevice: (deviceId) => api.get(`/drift-detection/device/${deviceId}`),
  setBaseline: (deviceId, backupId = null) =>
    api.post(`/drift-detection/device/${deviceId}/baseline`, { backup_id: backupId }),
  autoScan: () => api.post('/drift-detection/auto-scan'),
};

// Rule Templates API
export const ruleTemplatesAPI = {
  initialize: () => api.post('/rule-templates/initialize'),
  getAll: (vendor = null, category = null, framework = null) => {
    const params = new URLSearchParams();
    if (vendor) params.append('vendor', vendor);
    if (category) params.append('category', category);
    if (framework) params.append('compliance_framework', framework);
    const queryString = params.toString();
    return api.get(`/rule-templates/${queryString ? '?' + queryString : ''}`);
  },
  getById: (id) => api.get(`/rule-templates/${id}`),
  getCategories: () => api.get('/rule-templates/categories'),
  getFrameworks: () => api.get('/rule-templates/frameworks'),
  create: (template) => api.post('/rule-templates/', template),
  applyTemplate: (templateId, customName = null) =>
    api.post('/rule-templates/apply', { template_id: templateId, custom_name: customName }),
  applyFramework: (framework, vendor) =>
    api.post('/rule-templates/apply-framework', { framework, vendor }),
  getByVendor: (vendor) => api.get(`/rule-templates/vendor/${vendor}`),
  delete: (id) => api.delete(`/rule-templates/${id}`),
};

// Integrations API
export const integrationsAPI = {
  getAll: (params = {}) => api.get('/integrations/', { params }),
  getById: (id) => api.get(`/integrations/${id}`),
  create: (integration) => api.post('/integrations/', integration),
  update: (id, integration) => api.put(`/integrations/${id}`, integration),
  delete: (id) => api.delete(`/integrations/${id}`),
  test: (id) => api.post(`/integrations/${id}/test`),
  sync: (id, force = false) => api.post(`/integrations/${id}/sync`, { force }),
  getLogs: (id, limit = 100) => api.get(`/integrations/${id}/logs?limit=${limit}`)
};

// Licensing API
export const licensingAPI = {
  getAll: (params = {}) => api.get('/licensing/', { params }),
  getById: (id) => api.get(`/licensing/${id}`),
  create: (license) => api.post('/licensing/', license),
  update: (id, license) => api.put(`/licensing/${id}`, license),
  delete: (id) => api.delete(`/licensing/${id}`),
  verify: (id) => api.post(`/licensing/${id}/verify`),
  getAlerts: (params = {}) => api.get('/licensing/alerts/', { params }),
  acknowledgeAlert: (id, user) => api.post(`/licensing/alerts/${id}/acknowledge`, { acknowledged_by: user }),
  getSoftware: (params = {}) => api.get('/licensing/software/', { params }),
  getStats: () => api.get('/licensing/stats/summary')
};

// Topology API
export const topologyAPI = {
  getGraph: (activeOnly = true) => api.get('/topology/graph', { params: { active_only: activeOnly } }),
  listNodes: (params = {}) => api.get('/topology/nodes', { params }),
  startDiscovery: (seedDeviceIds, maxDepth = 5) =>
    api.post('/topology/discover', { seed_device_ids: seedDeviceIds, max_depth: maxDepth }),
  getDiscoveryStatus: (sessionId) => api.get(`/topology/discovery/${sessionId}`)
};

// Config Templates API
export const configTemplatesAPI = {
  initialize: () => api.post('/config-templates/initialize'),
  getAll: (params = {}) => api.get('/config-templates/', { params }),
  getById: (id) => api.get(`/config-templates/${id}`),
  create: (template) => api.post('/config-templates/', template),
  update: (id, template) => api.put(`/config-templates/${id}`, template),
  delete: (id) => api.delete(`/config-templates/${id}`),
  deploy: (templateId, deviceId, variables, dryRun = false) =>
    api.post('/config-templates/deploy', { template_id: templateId, device_id: deviceId, variables, dry_run: dryRun }),
  deployBulk: (templateId, deviceIds, variables, dryRun = false) =>
    api.post('/config-templates/deploy/bulk', { template_id: templateId, device_ids: deviceIds, variables, dry_run: dryRun }),
  deployToGroups: (templateId, groupIds, variables, dryRun = false) =>
    api.post('/config-templates/deploy/groups', { template_id: templateId, group_ids: groupIds, variables, dry_run: dryRun }),
  getCategories: () => api.get('/config-templates/categories/list')
};

// Analytics API
export const analyticsAPI = {
  getTrends: (params = {}) => api.get('/analytics/trends', { params }),
  createSnapshot: (deviceId = null) => api.post('/analytics/trends/snapshot', { device_id: deviceId }),
  getForecast: (params = {}) => api.get('/analytics/forecast', { params }),
  generateForecast: (deviceId = null, daysAhead = 7) =>
    api.post('/analytics/forecast/generate', { device_id: deviceId, days_ahead: daysAhead }),
  getAnomalies: (params = {}) => api.get('/analytics/anomalies', { params }),
  detectAnomalies: (deviceId = null) => api.post('/analytics/anomalies/detect', { device_id: deviceId }),
  acknowledgeAnomaly: (id, user) => api.post(`/analytics/anomalies/${id}/acknowledge`, { acknowledged_by: user }),
  getDashboardSummary: () => api.get('/analytics/dashboard/summary')
};

// Remediation API
export const remediationAPI = {
  pushRemediation: (deviceIds, dryRun = true) =>
    api.post('/remediation/push', { device_ids: deviceIds, dry_run: dryRun }),
  getStatus: (deviceId) => api.get(`/remediation/status/${deviceId}`)
};

// Workflows API
export const workflowsAPI = {
  // Workflow CRUD
  getAll: () => api.get('/workflows/'),
  getById: (id) => api.get(`/workflows/${id}`),
  create: (workflowData) => api.post('/workflows/', workflowData),
  update: (id, workflowData) => api.put(`/workflows/${id}`, workflowData),
  delete: (id) => api.delete(`/workflows/${id}`),

  // Workflow Execution
  execute: (id, executionRequest) => api.post(`/workflows/${id}/execute`, executionRequest),

  // Executions
  getExecutions: (params = {}) => api.get('/workflows/executions/', { params }),
  getExecutionById: (id) => api.get(`/workflows/executions/${id}`),
  getExecutionSteps: (id) => api.get(`/workflows/executions/${id}/steps`),
  cancelExecution: (id) => api.post(`/workflows/executions/${id}/cancel`),

  // Schedules
  getSchedules: (workflowId) => api.get(`/workflows/${workflowId}/schedules`),
  createSchedule: (workflowId, scheduleData) => api.post(`/workflows/${workflowId}/schedules`, scheduleData),
  deleteSchedule: (scheduleId) => api.delete(`/workflows/schedules/${scheduleId}`)
};

// Hardware Inventory API
export const hardwareInventoryAPI = {
  getInventory: (vendor = null, chassisModel = null) => {
    const params = new URLSearchParams();
    if (vendor) params.append('vendor', vendor);
    if (chassisModel) params.append('chassis_model', chassisModel);
    return api.get(`/hardware/inventory?${params}`);
  },
  getChassisModels: (vendor = null) => {
    const params = new URLSearchParams();
    if (vendor) params.append('vendor', vendor);
    return api.get(`/hardware/chassis-models?${params}`);
  },
  getDeviceInventory: (deviceId, componentType = null) => {
    const params = new URLSearchParams();
    if (componentType) params.append('component_type', componentType);
    return api.get(`/hardware/inventory/${deviceId}?${params}`);
  },
  scanDevice: (deviceId) => api.post(`/hardware/scan/${deviceId}`),
  scanAll: () => api.post('/hardware/scan-all')
};

export default api;
