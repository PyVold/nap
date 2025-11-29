import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Collapse,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  Grid,
  Tooltip,
  Divider,
} from '@mui/material';
import {
  KeyboardArrowDown,
  KeyboardArrowUp,
  Memory as ChipIcon,
  Power as PowerIcon,
  Air as FanIcon,
  Storage as CardIcon,
  Refresh,
  Scanner as ScanIcon,
  CheckCircle,
  Error as ErrorIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { hardwareInventoryAPI } from '../api/api';

// Component Row for displaying hardware components
const ComponentRow = ({ component }) => {
  const getStatusIcon = (state) => {
    if (!state) return null;
    const stateLower = state.toLowerCase();
    if (stateLower === 'up' || stateLower === 'in-service') {
      return <CheckCircle sx={{ color: '#4caf50', fontSize: 18 }} />;
    }
    if (stateLower === 'down' || stateLower === 'out-of-service') {
      return <ErrorIcon sx={{ color: '#f44336', fontSize: 18 }} />;
    }
    return <WarningIcon sx={{ color: '#ff9800', fontSize: 18 }} />;
  };

  const getComponentIcon = (type) => {
    switch (type) {
      case 'chassis':
        return <CardIcon sx={{ color: '#1976d2' }} />;
      case 'card':
      case 'mda':
      case 'rp':
        return <CardIcon sx={{ color: '#2e7d32' }} />;
      case 'power':
        return <PowerIcon sx={{ color: '#ed6c02' }} />;
      case 'fan':
        return <FanIcon sx={{ color: '#0288d1' }} />;
      default:
        return <ChipIcon sx={{ color: '#757575' }} />;
    }
  };

  return (
    <TableRow hover>
      <TableCell>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {getComponentIcon(component.component_type)}
          <Typography variant="body2" fontWeight="medium">
            {component.component_name}
          </Typography>
        </Box>
      </TableCell>
      <TableCell>
        <Chip
          label={(component.component_type || 'unknown').toUpperCase()}
          size="small"
          variant="outlined"
        />
      </TableCell>
      <TableCell>{component.slot_number || 'N/A'}</TableCell>
      <TableCell>
        <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>
          {component.part_number || 'N/A'}
        </Typography>
      </TableCell>
      <TableCell>
        <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>
          {component.serial_number || 'N/A'}
        </Typography>
      </TableCell>
      <TableCell>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {getStatusIcon(component.operational_state)}
          <Typography variant="caption">
            {component.operational_state || 'Unknown'}
          </Typography>
        </Box>
      </TableCell>
    </TableRow>
  );
};

// Device Row with expandable component view
const DeviceInventoryRow = ({ deviceSummary, onScan }) => {
  const [open, setOpen] = useState(false);
  const [components, setComponents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchComponents = async () => {
    if (components.length > 0) return;

    setLoading(true);
    try {
      const response = await hardwareInventoryAPI.getDeviceInventory(deviceSummary.device_id);
      setComponents(response.data);
      setError('');
    } catch (err) {
      setError('Failed to fetch components');
    }
    setLoading(false);
  };

  const handleToggle = () => {
    if (!open && components.length === 0) {
      fetchComponents();
    }
    setOpen(!open);
  };

  const formatDate = (date) => {
    if (!date) return 'Never';
    return new Date(date).toLocaleString();
  };

  // Group components by type
  const groupedComponents = {
    chassis: components.filter(c => c.component_type === 'chassis'),
    cards: components.filter(c => ['card', 'mda', 'rp'].includes(c.component_type)),
    power: components.filter(c => c.component_type === 'power'),
    fans: components.filter(c => c.component_type === 'fan'),
  };

  return (
    <>
      <TableRow hover sx={{ backgroundColor: '#fafafa' }}>
        <TableCell>
          <IconButton size="small" onClick={handleToggle}>
            {open ? <KeyboardArrowUp /> : <KeyboardArrowDown />}
          </IconButton>
        </TableCell>
        <TableCell>
          <Box>
            <Typography variant="body1" fontWeight="medium">
              {deviceSummary.device_name}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {deviceSummary.device_ip || 'No IP'} • {deviceSummary.vendor}
            </Typography>
          </Box>
        </TableCell>
        <TableCell>
          <Chip
            label={deviceSummary.chassis_model || 'Unknown'}
            color="primary"
            size="small"
          />
        </TableCell>
        <TableCell align="center">
          <Chip label={deviceSummary.total_components} size="small" variant="outlined" />
        </TableCell>
        <TableCell align="center">
          <Chip label={deviceSummary.cards_count} size="small" color="success" variant="outlined" />
        </TableCell>
        <TableCell align="center">
          <Chip label={deviceSummary.power_count} size="small" color="warning" variant="outlined" />
        </TableCell>
        <TableCell align="center">
          <Chip label={deviceSummary.fans_count} size="small" color="info" variant="outlined" />
        </TableCell>
        <TableCell>
          <Typography variant="caption">{formatDate(deviceSummary.last_scan)}</Typography>
        </TableCell>
        <TableCell align="right">
          <Tooltip title="Scan Device">
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                onScan(deviceSummary.device_id);
              }}
            >
              <ScanIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={9}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ margin: 2 }}>
              <Typography variant="h6" gutterBottom>
                Hardware Components
              </Typography>

              {loading ? (
                <Box display="flex" justifyContent="center" p={3}>
                  <CircularProgress size={30} />
                </Box>
              ) : error ? (
                <Alert severity="error">{error}</Alert>
              ) : components.length === 0 ? (
                <Typography variant="body2" color="text.secondary" align="center" sx={{ p: 2 }}>
                  No hardware inventory found. Click scan to collect data.
                </Typography>
              ) : (
                <Grid container spacing={2}>
                  {/* Chassis */}
                  {groupedComponents.chassis.length > 0 && (
                    <Grid item xs={12}>
                      <Paper variant="outlined" sx={{ p: 2 }}>
                        <Typography variant="subtitle2" gutterBottom color="primary">
                          Chassis
                        </Typography>
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell><strong>Name</strong></TableCell>
                              <TableCell><strong>Type</strong></TableCell>
                              <TableCell><strong>Slot</strong></TableCell>
                              <TableCell><strong>Part Number</strong></TableCell>
                              <TableCell><strong>Serial Number</strong></TableCell>
                              <TableCell><strong>Status</strong></TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {groupedComponents.chassis.map((comp) => (
                              <ComponentRow key={comp.id} component={comp} />
                            ))}
                          </TableBody>
                        </Table>
                      </Paper>
                    </Grid>
                  )}

                  {/* Cards */}
                  {groupedComponents.cards.length > 0 && (
                    <Grid item xs={12}>
                      <Paper variant="outlined" sx={{ p: 2 }}>
                        <Typography variant="subtitle2" gutterBottom color="success">
                          Cards / Modules ({groupedComponents.cards.length})
                        </Typography>
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell><strong>Name</strong></TableCell>
                              <TableCell><strong>Type</strong></TableCell>
                              <TableCell><strong>Slot</strong></TableCell>
                              <TableCell><strong>Part Number</strong></TableCell>
                              <TableCell><strong>Serial Number</strong></TableCell>
                              <TableCell><strong>Status</strong></TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {groupedComponents.cards.map((comp) => (
                              <ComponentRow key={comp.id} component={comp} />
                            ))}
                          </TableBody>
                        </Table>
                      </Paper>
                    </Grid>
                  )}

                  {/* Power & Fans */}
                  <Grid item xs={12} md={6}>
                    {groupedComponents.power.length > 0 && (
                      <Paper variant="outlined" sx={{ p: 2, height: '100%' }}>
                        <Typography variant="subtitle2" gutterBottom color="warning">
                          Power Supplies ({groupedComponents.power.length})
                        </Typography>
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell><strong>Name</strong></TableCell>
                              <TableCell><strong>Slot</strong></TableCell>
                              <TableCell><strong>Status</strong></TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {groupedComponents.power.map((comp) => (
                              <TableRow key={comp.id} hover>
                                <TableCell>
                                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <PowerIcon sx={{ color: '#ed6c02' }} />
                                    {comp.component_name}
                                  </Box>
                                </TableCell>
                                <TableCell>{comp.slot_number || 'N/A'}</TableCell>
                                <TableCell>
                                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    {comp.operational_state === 'up' ? (
                                      <CheckCircle sx={{ color: '#4caf50', fontSize: 18 }} />
                                    ) : (
                                      <ErrorIcon sx={{ color: '#f44336', fontSize: 18 }} />
                                    )}
                                    <Typography variant="caption">
                                      {comp.operational_state || 'Unknown'}
                                    </Typography>
                                  </Box>
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </Paper>
                    )}
                  </Grid>

                  <Grid item xs={12} md={6}>
                    {groupedComponents.fans.length > 0 && (
                      <Paper variant="outlined" sx={{ p: 2, height: '100%' }}>
                        <Typography variant="subtitle2" gutterBottom color="info">
                          Fans ({groupedComponents.fans.length})
                        </Typography>
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell><strong>Name</strong></TableCell>
                              <TableCell><strong>Slot</strong></TableCell>
                              <TableCell><strong>Status</strong></TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {groupedComponents.fans.map((comp) => (
                              <TableRow key={comp.id} hover>
                                <TableCell>
                                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <FanIcon sx={{ color: '#0288d1' }} />
                                    {comp.component_name}
                                  </Box>
                                </TableCell>
                                <TableCell>{comp.slot_number || 'N/A'}</TableCell>
                                <TableCell>
                                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    {comp.operational_state === 'up' ? (
                                      <CheckCircle sx={{ color: '#4caf50', fontSize: 18 }} />
                                    ) : (
                                      <ErrorIcon sx={{ color: '#f44336', fontSize: 18 }} />
                                    )}
                                    <Typography variant="caption">
                                      {comp.operational_state || 'Unknown'}
                                    </Typography>
                                  </Box>
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </Paper>
                    )}
                  </Grid>
                </Grid>
              )}
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  );
};

// Main Component
export default function HardwareInventory() {
  const [inventory, setInventory] = useState([]);
  const [chassisModels, setChassisModels] = useState([]);
  const [selectedVendor, setSelectedVendor] = useState('');
  const [selectedChassis, setSelectedChassis] = useState('');
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchInventory();
    fetchChassisModels();
  }, [selectedVendor, selectedChassis]);

  // Auto-refresh to pick up changes from background scans
  useEffect(() => {
    const intervalId = setInterval(() => {
      fetchInventory();
    }, 30000); // 30 seconds

    return () => clearInterval(intervalId);
  }, [selectedVendor, selectedChassis]);

  const fetchInventory = async () => {
    setLoading(true);
    try {
      const response = await hardwareInventoryAPI.getInventory(selectedVendor, selectedChassis);
      setInventory(response.data);
      setError('');
    } catch (err) {
      setError('Failed to fetch hardware inventory');
    }
    setLoading(false);
  };

  const fetchChassisModels = async () => {
    try {
      const response = await hardwareInventoryAPI.getChassisModels(selectedVendor);
      setChassisModels(response.data);
    } catch (err) {
      console.error('Failed to fetch chassis models:', err);
    }
  };

  const handleScanDevice = async (deviceId) => {
    setScanning(true);
    try {
      await hardwareInventoryAPI.scanDevice(deviceId);
      setSuccess('Device scan completed successfully');
      fetchInventory();
    } catch (err) {
      setError('Failed to scan device: ' + (err.response?.data?.detail || err.message));
    }
    setScanning(false);
  };

  const handleScanAll = async () => {
    setScanning(true);
    try {
      const response = await hardwareInventoryAPI.scanAll();
      setSuccess(`Scanned ${response.data.successful_scans}/${response.data.total_devices} devices`);
      fetchInventory();
    } catch (err) {
      setError('Failed to scan devices');
    }
    setScanning(false);
  };

  const filteredInventory = inventory;

  if (loading && inventory.length === 0) {
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
          <ChipIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          Hardware Inventory
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={fetchInventory}
            disabled={loading || scanning}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<ScanIcon />}
            onClick={handleScanAll}
            disabled={loading || scanning}
          >
            Scan All Devices
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" onClose={() => setError('')} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" onClose={() => setSuccess('')} sx={{ mb: 2 }}>
          {success}
        </Alert>
      )}

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth size="small">
              <InputLabel>Filter by Vendor</InputLabel>
              <Select
                value={selectedVendor}
                label="Filter by Vendor"
                onChange={(e) => {
                  setSelectedVendor(e.target.value);
                  setSelectedChassis(''); // Reset chassis filter
                }}
              >
                <MenuItem value="">All Vendors</MenuItem>
                <MenuItem value="nokia_sros">Nokia SROS</MenuItem>
                <MenuItem value="cisco_ios_xr">Cisco IOS-XR</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth size="small">
              <InputLabel>Filter by Chassis Model</InputLabel>
              <Select
                value={selectedChassis}
                label="Filter by Chassis Model"
                onChange={(e) => setSelectedChassis(e.target.value)}
                disabled={!selectedVendor}
              >
                <MenuItem value="">All Chassis Models</MenuItem>
                {chassisModels.map((model) => (
                  <MenuItem key={`${model.vendor}-${model.chassis_model}`} value={model.chassis_model}>
                    {model.chassis_model} ({model.device_count})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </Paper>

      {/* Summary Stats */}
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Total Devices
              </Typography>
              <Typography variant="h4">{filteredInventory.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Total Cards
              </Typography>
              <Typography variant="h4" color="success.main">
                {filteredInventory.reduce((sum, d) => sum + d.cards_count, 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Power Supplies
              </Typography>
              <Typography variant="h4" color="warning.main">
                {filteredInventory.reduce((sum, d) => sum + d.power_count, 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Fans
              </Typography>
              <Typography variant="h4" color="info.main">
                {filteredInventory.reduce((sum, d) => sum + d.fans_count, 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Device List */}
      <Card>
        <CardContent>
          <Typography variant="body2" color="text.secondary" paragraph>
            Click on a device to view detailed hardware inventory including chassis, cards, power supplies, and fans.
          </Typography>

          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                  <TableCell width="50px" />
                  <TableCell><strong>Device</strong></TableCell>
                  <TableCell><strong>Chassis Model</strong></TableCell>
                  <TableCell align="center"><strong>Total</strong></TableCell>
                  <TableCell align="center"><strong>Cards</strong></TableCell>
                  <TableCell align="center"><strong>Power</strong></TableCell>
                  <TableCell align="center"><strong>Fans</strong></TableCell>
                  <TableCell><strong>Last Scan</strong></TableCell>
                  <TableCell align="right"><strong>Actions</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredInventory.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} align="center">
                      <Typography variant="body2" color="text.secondary" sx={{ py: 3 }}>
                        No hardware inventory found. Click "Scan All Devices" to collect data.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredInventory.map((device) => (
                    <DeviceInventoryRow
                      key={device.device_id}
                      deviceSummary={device}
                      onScan={handleScanDevice}
                    />
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Box>
  );
}
