import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
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
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  CircularProgress,
  Paper,
  Grid,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  Search,
  Devices as DevicesIcon,
  Refresh,
  Timer,
  CheckCircle,
  Warning,
} from '@mui/icons-material';
import { devicesAPI } from '../api/api';
import { useCanModify } from './RoleBasedAccess';

const DeviceManagement = () => {
  const canModify = useCanModify();
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [openDiscoveryDialog, setOpenDiscoveryDialog] = useState(false);
  const [editingDevice, setEditingDevice] = useState(null);
  const [discovering, setDiscovering] = useState(false);
  const [formData, setFormData] = useState({
    hostname: '',
    vendor: 'cisco_xr',
    ip: '',
    port: 830,
    username: '',
    password: '',
  });
  const [discoveryData, setDiscoveryData] = useState({
    subnet: '',
    username: '',
    password: '',
    port: 830,
  });

  const fetchDevices = async () => {
    setLoading(true);
    try {
      const response = await devicesAPI.getAll();
      setDevices(response.data || []);
      setError(null);
    } catch (err) {
      console.error('Error fetching devices:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to fetch devices');
      setDevices([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDevices();

    // Auto-refresh every 30 seconds to pick up hostname changes from scheduled discoveries
    const intervalId = setInterval(() => {
      fetchDevices();
    }, 30000); // 30 seconds

    // Cleanup interval on component unmount
    return () => clearInterval(intervalId);
  }, []);

  const handleOpenDialog = (device = null) => {
    if (device) {
      setEditingDevice(device);
      setFormData({
        hostname: device.hostname,
        vendor: device.vendor,
        ip: device.ip || '',
        port: device.port || 830,
        username: device.username || '',
        password: device.password || '',
      });
    } else {
      setEditingDevice(null);
      setFormData({
        hostname: '',
        vendor: 'cisco_xr',
        ip: '',
        port: 830,
        username: '',
        password: '',
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingDevice(null);
  };

  const handleSave = async () => {
    try {
      if (editingDevice) {
        await devicesAPI.update(editingDevice.id, formData);
        setSuccess('Device updated successfully');
      } else {
        await devicesAPI.create(formData);
        setSuccess('Device added successfully');
      }
      handleCloseDialog();
      fetchDevices();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this device?')) {
      try {
        await devicesAPI.delete(id);
        setSuccess('Device deleted successfully');
        fetchDevices();
      } catch (err) {
        setError(err.message);
      }
    }
  };

  const handleOpenDiscoveryDialog = () => {
    setOpenDiscoveryDialog(true);
  };

  const handleCloseDiscoveryDialog = () => {
    setOpenDiscoveryDialog(false);
  };

  const handleDiscover = async () => {
    if (!discoveryData.subnet || !discoveryData.username || !discoveryData.password) {
      setError('Please fill in all required discovery fields');
      return;
    }

    setDiscovering(true);
    setOpenDiscoveryDialog(false);
    try {
      const response = await devicesAPI.discover(discoveryData);
      setSuccess(
        `Discovery complete! Found ${response.data.discovered} devices, added ${response.data.added} new devices.`
      );
      fetchDevices();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setDiscovering(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'online':
        return 'success';
      case 'degraded':
        return 'warning';
      case 'offline':
        return 'error';
      case 'discovered':
        return 'info';
      case 'registered':
        return 'warning';
      default:
        return 'default';
    }
  };

  if (loading && devices.length === 0) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" fontWeight="bold">
          <DevicesIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          Device Management
        </Typography>
        <Box>
          <Button
            variant="outlined"
            startIcon={discovering ? <CircularProgress size={20} /> : <Search />}
            onClick={handleOpenDiscoveryDialog}
            disabled={discovering}
            sx={{ mr: 1 }}
          >
            {discovering ? 'Discovering...' : 'Discover Devices'}
          </Button>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={fetchDevices}
            disabled={loading}
            sx={{ mr: 1 }}
          >
            Refresh
          </Button>
          {canModify && (
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => handleOpenDialog()}
            >
              Add Device
            </Button>
          )}
        </Box>
      </Box>

      {error && (
        <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" onClose={() => setSuccess(null)} sx={{ mb: 2 }}>
          {success}
        </Alert>
      )}

      {/* Summary Cards */}
      <Grid container spacing={2} mb={3}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
            <CardContent>
              <Typography variant="h4" color="white" fontWeight="bold">
                {devices.length}
              </Typography>
              <Typography variant="body2" color="rgba(255,255,255,0.9)">
                Total Devices
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #4caf50 0%, #81c784 100%)' }}>
            <CardContent>
              <Typography variant="h4" color="white" fontWeight="bold">
                {devices.filter((d) => d.status === 'online').length}
              </Typography>
              <Typography variant="body2" color="rgba(255,255,255,0.9)">
                Online Devices
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #ff9800 0%, #ffb74d 100%)' }}>
            <CardContent>
              <Typography variant="h4" color="white" fontWeight="bold">
                {devices.filter((d) => d.vendor === 'cisco_xr').length}
              </Typography>
              <Typography variant="body2" color="rgba(255,255,255,0.9)">
                Cisco XR
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #2196f3 0%, #64b5f6 100%)' }}>
            <CardContent>
              <Typography variant="h4" color="white" fontWeight="bold">
                {devices.filter((d) => d.vendor === 'nokia_sros').length}
              </Typography>
              <Typography variant="body2" color="rgba(255,255,255,0.9)">
                Nokia SROS
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
              <TableCell><strong>Hostname</strong></TableCell>
              <TableCell><strong>IP Address</strong></TableCell>
              <TableCell><strong>Vendor</strong></TableCell>
              <TableCell><strong>Port</strong></TableCell>
              <TableCell><strong>Status</strong></TableCell>
              <TableCell><strong>Health Check</strong></TableCell>
              <TableCell><strong>Compliance</strong></TableCell>
              <TableCell><strong>Last Audit</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {devices.map((device) => (
              <TableRow key={device.id} hover>
                <TableCell>{device.hostname}</TableCell>
                <TableCell>{device.ip || 'N/A'}</TableCell>
                <TableCell>
                  <Chip
                    label={device.vendor === 'cisco_xr' ? 'Cisco XR' : 'Nokia SROS'}
                    size="small"
                    color="primary"
                    variant="outlined"
                  />
                </TableCell>
                <TableCell>{device.port}</TableCell>
                <TableCell>
                  <Chip
                    label={device.status}
                    size="small"
                    color={getStatusColor(device.status)}
                  />
                </TableCell>
                <TableCell>
                  {device.backoff_status && device.backoff_status.is_backed_off ? (
                    <Chip
                      icon={<Timer />}
                      label={`Backed off (${device.backoff_status.minutes_remaining}min)`}
                      size="small"
                      color="warning"
                      title={device.backoff_status.message}
                    />
                  ) : device.backoff_status && device.backoff_status.consecutive_failures > 0 ? (
                    <Chip
                      icon={<Warning />}
                      label={`${device.backoff_status.consecutive_failures} failures`}
                      size="small"
                      color="default"
                      title={device.backoff_status.message}
                    />
                  ) : (
                    <Chip
                      icon={<CheckCircle />}
                      label="Normal"
                      size="small"
                      color="success"
                      title="Health checks running normally"
                    />
                  )}
                </TableCell>
                <TableCell>
                  <Box display="flex" alignItems="center">
                    <Box
                      sx={{
                        width: 60,
                        height: 8,
                        backgroundColor: '#e0e0e0',
                        borderRadius: 4,
                        mr: 1,
                      }}
                    >
                      <Box
                        sx={{
                          width: `${device.compliance}%`,
                          height: '100%',
                          backgroundColor:
                            device.compliance >= 80
                              ? '#4caf50'
                              : device.compliance >= 50
                              ? '#ff9800'
                              : '#f44336',
                          borderRadius: 4,
                        }}
                      />
                    </Box>
                    <Typography variant="body2">{device.compliance}%</Typography>
                  </Box>
                </TableCell>
                <TableCell>{device.last_audit || 'Never'}</TableCell>
                <TableCell align="center">
                  {canModify ? (
                    <>
                      <IconButton
                        size="small"
                        onClick={() => handleOpenDialog(device)}
                        color="primary"
                      >
                        <Edit />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => handleDelete(device.id)}
                        color="error"
                      >
                        <Delete />
                      </IconButton>
                    </>
                  ) : (
                    <Typography variant="body2" color="textSecondary">
                      View only
                    </Typography>
                  )}
                </TableCell>
              </TableRow>
            ))}
            {devices.length === 0 && (
              <TableRow>
                <TableCell colSpan={9} align="center">
                  <Typography variant="body2" color="textSecondary">
                    No devices found. Click "Add Device" or "Discover Devices" to get started.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Add/Edit Device Dialog */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingDevice ? 'Edit Device' : 'Add New Device'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Hostname"
                value={formData.hostname}
                onChange={(e) => setFormData({ ...formData, hostname: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="IP Address"
                value={formData.ip}
                onChange={(e) => setFormData({ ...formData, ip: e.target.value })}
                helperText="Optional - can use hostname instead"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Vendor</InputLabel>
                <Select
                  value={formData.vendor}
                  label="Vendor"
                  onChange={(e) => setFormData({ ...formData, vendor: e.target.value })}
                >
                  <MenuItem value="cisco_xr">Cisco XR</MenuItem>
                  <MenuItem value="nokia_sros">Nokia SROS</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Port"
                value={formData.port}
                onChange={(e) => setFormData({ ...formData, port: parseInt(e.target.value) })}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Username"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                type="password"
                label="Password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSave} variant="contained" disabled={!formData.hostname}>
            {editingDevice ? 'Update' : 'Add'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Discovery Dialog */}
      <Dialog open={openDiscoveryDialog} onClose={handleCloseDiscoveryDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          Discover Devices via Subnet Scanning
        </DialogTitle>
        <DialogContent>
          <Alert severity="info" sx={{ mb: 2 }}>
            Discovery will ping all IPs in the subnet and attempt NETCONF connections to identify devices.
          </Alert>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Subnet (CIDR)"
                value={discoveryData.subnet}
                onChange={(e) => setDiscoveryData({ ...discoveryData, subnet: e.target.value })}
                placeholder="e.g., 192.168.1.0/24"
                helperText="Enter subnet in CIDR notation"
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="NETCONF Username"
                value={discoveryData.username}
                onChange={(e) => setDiscoveryData({ ...discoveryData, username: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                type="password"
                label="NETCONF Password"
                value={discoveryData.password}
                onChange={(e) => setDiscoveryData({ ...discoveryData, password: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                type="number"
                label="NETCONF Port"
                value={discoveryData.port}
                onChange={(e) => setDiscoveryData({ ...discoveryData, port: parseInt(e.target.value) })}
                helperText="Default: 830"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDiscoveryDialog}>Cancel</Button>
          <Button
            onClick={handleDiscover}
            variant="contained"
            disabled={!discoveryData.subnet || !discoveryData.username || !discoveryData.password}
          >
            Start Discovery
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DeviceManagement;
