import React, { useState, useEffect } from 'react';
import {
  Container,
  Paper,
  Typography,
  Box,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Alert,
  CircularProgress,
  Tabs,
  Tab
} from '@mui/material';
import {
  Add as AddIcon,
  Refresh as RefreshIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  PlayArrow as TestIcon,
  Sync as SyncIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon
} from '@mui/icons-material';
import { integrationsAPI } from '../api/api';

const IntegrationTypeIcons = {
  netbox: '📦',
  git: '🔧',
  ansible: '⚙️',
  servicenow: '🎫',
  prometheus: '📊'
};

function Integrations() {
  const [integrations, setIntegrations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingIntegration, setEditingIntegration] = useState(null);
  const [currentTab, setCurrentTab] = useState(0);
  const [logs, setLogs] = useState([]);
  const [formData, setFormData] = useState({
    name: '',
    integration_type: 'netbox',
    config: {},
    enabled: true,
    auto_sync: false,
    sync_interval_minutes: 60
  });

  useEffect(() => {
    loadIntegrations();
  }, []);

  const loadIntegrations = async () => {
    try {
      setLoading(true);
      const response = await integrationsAPI.getAll();
      setIntegrations(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to load integrations: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (integration = null) => {
    if (integration) {
      setEditingIntegration(integration);
      setFormData({
        name: integration.name,
        integration_type: integration.integration_type,
        config: integration.config || {},
        enabled: integration.enabled,
        auto_sync: integration.auto_sync,
        sync_interval_minutes: integration.sync_interval_minutes || 60
      });
    } else {
      setEditingIntegration(null);
      setFormData({
        name: '',
        integration_type: 'netbox',
        config: {},
        enabled: true,
        auto_sync: false,
        sync_interval_minutes: 60
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingIntegration(null);
  };

  const handleSave = async () => {
    try {
      if (editingIntegration) {
        await integrationsAPI.update(editingIntegration.id, formData);
      } else {
        await integrationsAPI.create(formData);
      }
      handleCloseDialog();
      loadIntegrations();
    } catch (err) {
      setError('Failed to save integration: ' + err.message);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this integration?')) {
      try {
        await integrationsAPI.delete(id);
        loadIntegrations();
      } catch (err) {
        setError('Failed to delete integration: ' + err.message);
      }
    }
  };

  const handleTest = async (id) => {
    try {
      const response = await integrationsAPI.test(id);
      alert(response.data.success ? 'Integration test successful!' : 'Integration test failed: ' + response.data.message);
    } catch (err) {
      alert('Test failed: ' + err.message);
    }
  };

  const handleSync = async (id, force = false) => {
    try {
      await integrationsAPI.sync(id, force);
      alert('Sync initiated successfully');
      loadIntegrations();
    } catch (err) {
      setError('Failed to sync: ' + err.message);
    }
  };

  const loadLogs = async (id) => {
    try {
      const response = await integrationsAPI.getLogs(id);
      setLogs(response.data);
    } catch (err) {
      setError('Failed to load logs: ' + err.message);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'active':
        return <CheckCircleIcon color="success" />;
      case 'error':
        return <ErrorIcon color="error" />;
      case 'warning':
        return <WarningIcon color="warning" />;
      default:
        return null;
    }
  };

  const renderConfigFields = () => {
    const { integration_type } = formData;

    switch (integration_type) {
      case 'netbox':
        return (
          <>
            <TextField
              fullWidth
              label="NetBox URL"
              value={formData.config.url || ''}
              onChange={(e) => setFormData({
                ...formData,
                config: { ...formData.config, url: e.target.value }
              })}
              margin="normal"
              placeholder="https://netbox.example.com"
            />
            <TextField
              fullWidth
              label="API Token"
              type="password"
              value={formData.config.token || ''}
              onChange={(e) => setFormData({
                ...formData,
                config: { ...formData.config, token: e.target.value }
              })}
              margin="normal"
            />
          </>
        );
      case 'git':
        return (
          <>
            <TextField
              fullWidth
              label="Repository URL"
              value={formData.config.repo_url || ''}
              onChange={(e) => setFormData({
                ...formData,
                config: { ...formData.config, repo_url: e.target.value }
              })}
              margin="normal"
              placeholder="https://github.com/user/repo.git"
            />
            <TextField
              fullWidth
              label="Branch"
              value={formData.config.branch || 'main'}
              onChange={(e) => setFormData({
                ...formData,
                config: { ...formData.config, branch: e.target.value }
              })}
              margin="normal"
            />
            <TextField
              fullWidth
              label="Access Token"
              type="password"
              value={formData.config.token || ''}
              onChange={(e) => setFormData({
                ...formData,
                config: { ...formData.config, token: e.target.value }
              })}
              margin="normal"
            />
          </>
        );
      case 'ansible':
        return (
          <>
            <TextField
              fullWidth
              label="Ansible Tower/AWX URL"
              value={formData.config.url || ''}
              onChange={(e) => setFormData({
                ...formData,
                config: { ...formData.config, url: e.target.value }
              })}
              margin="normal"
              placeholder="https://tower.example.com"
            />
            <TextField
              fullWidth
              label="Username"
              value={formData.config.username || ''}
              onChange={(e) => setFormData({
                ...formData,
                config: { ...formData.config, username: e.target.value }
              })}
              margin="normal"
            />
            <TextField
              fullWidth
              label="Password"
              type="password"
              value={formData.config.password || ''}
              onChange={(e) => setFormData({
                ...formData,
                config: { ...formData.config, password: e.target.value }
              })}
              margin="normal"
            />
          </>
        );
      case 'servicenow':
        return (
          <>
            <TextField
              fullWidth
              label="ServiceNow Instance URL"
              value={formData.config.instance_url || ''}
              onChange={(e) => setFormData({
                ...formData,
                config: { ...formData.config, instance_url: e.target.value }
              })}
              margin="normal"
              placeholder="https://instance.service-now.com"
            />
            <TextField
              fullWidth
              label="Username"
              value={formData.config.username || ''}
              onChange={(e) => setFormData({
                ...formData,
                config: { ...formData.config, username: e.target.value }
              })}
              margin="normal"
            />
            <TextField
              fullWidth
              label="Password"
              type="password"
              value={formData.config.password || ''}
              onChange={(e) => setFormData({
                ...formData,
                config: { ...formData.config, password: e.target.value }
              })}
              margin="normal"
            />
          </>
        );
      case 'prometheus':
        return (
          <>
            <TextField
              fullWidth
              label="Pushgateway URL"
              value={formData.config.pushgateway_url || ''}
              onChange={(e) => setFormData({
                ...formData,
                config: { ...formData.config, pushgateway_url: e.target.value }
              })}
              margin="normal"
              placeholder="http://pushgateway:9091"
            />
            <TextField
              fullWidth
              label="Job Name"
              value={formData.config.job_name || 'network_audit'}
              onChange={(e) => setFormData({
                ...formData,
                config: { ...formData.config, job_name: e.target.value }
              })}
              margin="normal"
            />
          </>
        );
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Integration Hub
        </Typography>
        <Box>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadIntegrations}
            sx={{ mr: 1 }}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => handleOpenDialog()}
          >
            Add Integration
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Paper sx={{ mb: 3 }}>
        <Tabs value={currentTab} onChange={(e, v) => setCurrentTab(v)}>
          <Tab label="All Integrations" />
          <Tab label="Logs" />
        </Tabs>

        {currentTab === 0 && (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Auto-Sync</TableCell>
                  <TableCell>Last Sync</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {integrations.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <Typography variant="body2" color="text.secondary" py={3}>
                        No integrations configured. Click "Add Integration" to get started.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  integrations.map((integration) => (
                    <TableRow key={integration.id}>
                      <TableCell>
                        <Box display="flex" alignItems="center">
                          <span style={{ fontSize: '1.5rem', marginRight: '8px' }}>
                            {IntegrationTypeIcons[integration.integration_type] || '🔌'}
                          </span>
                          {integration.name}
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={integration.integration_type.toUpperCase()}
                          size="small"
                          color="primary"
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>
                        {integration.enabled ? (
                          <Chip
                            icon={<CheckCircleIcon />}
                            label="Active"
                            size="small"
                            color="success"
                          />
                        ) : (
                          <Chip
                            label="Disabled"
                            size="small"
                          />
                        )}
                      </TableCell>
                      <TableCell>
                        {integration.auto_sync ? (
                          <Chip label={`Every ${integration.sync_interval_minutes}m`} size="small" color="info" />
                        ) : (
                          <Chip label="Manual" size="small" />
                        )}
                      </TableCell>
                      <TableCell>
                        {integration.last_sync
                          ? new Date(integration.last_sync).toLocaleString()
                          : 'Never'}
                      </TableCell>
                      <TableCell>
                        <IconButton
                          size="small"
                          onClick={() => handleTest(integration.id)}
                          title="Test Connection"
                        >
                          <TestIcon />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={() => handleSync(integration.id)}
                          title="Sync Now"
                        >
                          <SyncIcon />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={() => handleOpenDialog(integration)}
                          title="Edit"
                        >
                          <EditIcon />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={() => handleDelete(integration.id)}
                          title="Delete"
                          color="error"
                        >
                          <DeleteIcon />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {currentTab === 1 && (
          <Box p={3}>
            <Typography variant="body2" color="text.secondary">
              Integration logs will appear here. Select an integration above to view its logs.
            </Typography>
          </Box>
        )}
      </Paper>

      {/* Add/Edit Integration Dialog */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingIntegration ? 'Edit Integration' : 'Add New Integration'}
        </DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Integration Name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            margin="normal"
            required
          />

          <FormControl fullWidth margin="normal">
            <InputLabel>Integration Type</InputLabel>
            <Select
              value={formData.integration_type}
              onChange={(e) => setFormData({ ...formData, integration_type: e.target.value })}
              label="Integration Type"
            >
              <MenuItem value="netbox">NetBox (IPAM/DCIM)</MenuItem>
              <MenuItem value="git">Git (Config Version Control)</MenuItem>
              <MenuItem value="ansible">Ansible Tower/AWX</MenuItem>
              <MenuItem value="servicenow">ServiceNow (ITSM)</MenuItem>
              <MenuItem value="prometheus">Prometheus (Metrics)</MenuItem>
            </Select>
          </FormControl>

          {renderConfigFields()}

          <FormControlLabel
            control={
              <Switch
                checked={formData.enabled}
                onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
              />
            }
            label="Enabled"
            sx={{ mt: 2 }}
          />

          <FormControlLabel
            control={
              <Switch
                checked={formData.auto_sync}
                onChange={(e) => setFormData({ ...formData, auto_sync: e.target.checked })}
              />
            }
            label="Auto-Sync"
            sx={{ mt: 1 }}
          />

          {formData.auto_sync && (
            <TextField
              fullWidth
              type="number"
              label="Sync Interval (minutes)"
              value={formData.sync_interval_minutes}
              onChange={(e) => setFormData({
                ...formData,
                sync_interval_minutes: parseInt(e.target.value)
              })}
              margin="normal"
              inputProps={{ min: 5, max: 1440 }}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSave} variant="contained" disabled={!formData.name}>
            {editingIntegration ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}

export default Integrations;
