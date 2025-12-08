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
  Chip,
  Alert,
  CircularProgress,
  Paper,
  IconButton,
  Collapse,
  Grid,
} from '@mui/material';
import {
  Refresh,
  NetworkCheck,
  CheckCircle,
  Error,
  Warning,
  KeyboardArrowDown,
  KeyboardArrowUp,
  Router,
} from '@mui/icons-material';
import { healthAPI, devicesAPI } from '../api/api';

const DeviceHealthRow = ({ device, onCheckHealth }) => {
  const [open, setOpen] = useState(false);
  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [latestStatus, setLatestStatus] = useState(device.status);

  const fetchHistory = async () => {
    setLoadingHistory(true);
    try {
      const response = await healthAPI.getHistory(device.id, 5);
      const historyData = response.data.history || [];
      setHistory(historyData);
      // Update latest status from most recent health check
      if (historyData.length > 0) {
        setLatestStatus(historyData[0].overall_status);
      }
    } catch (err) {
      console.error('Failed to fetch history:', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleToggle = () => {
    if (!open && history.length === 0) {
      fetchHistory();
    }
    setOpen(!open);
  };

  // Fetch history on mount to get latest status
  useEffect(() => {
    fetchHistory();
  }, [device.id]);

  const getStatusIcon = (status) => {
    switch (status) {
      case 'online':
      case 'healthy':
        return <CheckCircle sx={{ color: '#4caf50' }} />;
      case 'degraded':
        return <Warning sx={{ color: '#ff9800' }} />;
      case 'offline':
      case 'unreachable':
        return <Error sx={{ color: '#f44336' }} />;
      case 'unhealthy':
      case 'error':
        return <Error sx={{ color: '#d32f2f' }} />;
      case 'discovered':
      case 'registered':
        return <Warning sx={{ color: '#9e9e9e' }} />;
      default:
        return <Warning sx={{ color: '#9e9e9e' }} />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'online':
      case 'healthy':
        return 'success';
      case 'degraded':
        return 'warning';
      case 'offline':
      case 'unreachable':
      case 'unhealthy':
      case 'error':
        return 'error';
      case 'discovered':
      case 'registered':
        return 'default';
      default:
        return 'default';
    }
  };

  return (
    <>
      <TableRow hover>
        <TableCell>
          <IconButton size="small" onClick={handleToggle}>
            {open ? <KeyboardArrowUp /> : <KeyboardArrowDown />}
          </IconButton>
        </TableCell>
        <TableCell>{getStatusIcon(latestStatus)}</TableCell>
        <TableCell>{device.hostname}</TableCell>
        <TableCell>{device.ip || 'N/A'}</TableCell>
        <TableCell>
          <Chip
            label={device.vendor}
            size="small"
            color="primary"
            variant="outlined"
          />
        </TableCell>
        <TableCell>
          <Chip
            label={latestStatus || 'unknown'}
            size="small"
            color={getStatusColor(latestStatus)}
          />
        </TableCell>
        <TableCell>{device.last_audit || 'Never'}</TableCell>
        <TableCell align="center">
          <Button
            size="small"
            variant="outlined"
            startIcon={<NetworkCheck />}
            onClick={() => onCheckHealth(device.id)}
          >
            Check
          </Button>
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={8}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ margin: 2 }}>
              <Typography variant="h6" gutterBottom component="div">
                Health Check History
              </Typography>
              {loadingHistory ? (
                <CircularProgress size={24} />
              ) : history.length > 0 ? (
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Timestamp</TableCell>
                      <TableCell>Ping Status</TableCell>
                      <TableCell>Ping Latency</TableCell>
                      <TableCell>NETCONF Status</TableCell>
                      <TableCell>SSH Status</TableCell>
                      <TableCell>Overall Status</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {history.map((check, idx) => (
                      <TableRow key={idx}>
                        <TableCell>{new Date(check.timestamp).toLocaleString()}</TableCell>
                        <TableCell>
                          <Chip
                            label={check.ping_status ? 'OK' : 'Failed'}
                            size="small"
                            color={check.ping_status ? 'success' : 'error'}
                          />
                        </TableCell>
                        <TableCell>
                          {check.ping_latency ? `${check.ping_latency.toFixed(2)} ms` : 'N/A'}
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={check.netconf_status ? 'OK' : 'Failed'}
                            size="small"
                            color={check.netconf_status ? 'success' : 'error'}
                          />
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={check.ssh_status ? 'OK' : 'Failed'}
                            size="small"
                            color={check.ssh_status ? 'success' : 'error'}
                          />
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={check.overall_status}
                            size="small"
                            color={getStatusColor(check.overall_status)}
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <Typography variant="body2" color="textSecondary">
                  No health check history available
                </Typography>
              )}
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  );
};

const DeviceHealth = () => {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [checkingAll, setCheckingAll] = useState(false);
  const [healthSummary, setHealthSummary] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);

  const fetchDevices = async () => {
    setLoading(true);
    try {
      const [devicesRes, summaryRes] = await Promise.all([
        devicesAPI.getAll(),
        healthAPI.getSummary(),
      ]);
      setDevices(devicesRes.data);
      setHealthSummary(summaryRes.data);
      setError(null);
      setLastRefresh(new Date());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDevices();
    
    if (autoRefreshEnabled) {
      const interval = setInterval(fetchDevices, 30000); // Refresh every 30 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefreshEnabled]);

  const handleCheckDevice = async (deviceId) => {
    try {
      await healthAPI.checkDevice(deviceId, true); // Force check, bypass backoff
      setSuccess('Health check initiated successfully');
      setTimeout(fetchDevices, 2000); // Refresh after 2 seconds
    } catch (err) {
      setError(err.message);
    }
  };

  const handleCheckAll = async () => {
    setCheckingAll(true);
    try {
      await healthAPI.checkAll();
      setSuccess('Health check initiated for all devices');
      setTimeout(fetchDevices, 3000); // Refresh after 3 seconds
    } catch (err) {
      setError(err.message);
    } finally {
      setCheckingAll(false);
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
        <Box display="flex" alignItems="center" gap={2}>
          <Typography variant="h4" fontWeight="bold">
            <Router sx={{ mr: 1, verticalAlign: 'middle' }} />
            Device Health Monitoring
          </Typography>
          {autoRefreshEnabled && (
            <Chip
              label={`Auto-refresh: ${lastRefresh.toLocaleTimeString()}`}
              color="primary"
              size="small"
              icon={<Refresh />}
            />
          )}
        </Box>
        <Box>
          <Button
            variant={autoRefreshEnabled ? "outlined" : "contained"}
            startIcon={<Refresh />}
            onClick={() => setAutoRefreshEnabled(!autoRefreshEnabled)}
            sx={{ mr: 1 }}
          >
            Auto-refresh: {autoRefreshEnabled ? 'ON' : 'OFF'}
          </Button>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={fetchDevices}
            disabled={loading}
            sx={{ mr: 1 }}
          >
            Refresh Now
          </Button>
          <Button
            variant="contained"
            startIcon={<NetworkCheck />}
            onClick={handleCheckAll}
            disabled={checkingAll}
          >
            {checkingAll ? 'Checking...' : 'Check All Devices'}
          </Button>
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
      {healthSummary && (
        <Grid container spacing={2} mb={3}>
          <Grid item xs={12} sm={6} md={3}>
            <Card sx={{ background: 'linear-gradient(135deg, #4caf50 0%, #81c784 100%)' }}>
              <CardContent>
                <Typography variant="h4" color="white" fontWeight="bold">
                  {healthSummary.healthy}
                </Typography>
                <Typography variant="body2" color="rgba(255,255,255,0.9)">
                  Healthy Devices
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card sx={{ background: 'linear-gradient(135deg, #ff9800 0%, #ffb74d 100%)' }}>
              <CardContent>
                <Typography variant="h4" color="white" fontWeight="bold">
                  {healthSummary.degraded}
                </Typography>
                <Typography variant="body2" color="rgba(255,255,255,0.9)">
                  Degraded Devices
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card sx={{ background: 'linear-gradient(135deg, #f44336 0%, #e57373 100%)' }}>
              <CardContent>
                <Typography variant="h4" color="white" fontWeight="bold">
                  {healthSummary.unreachable}
                </Typography>
                <Typography variant="body2" color="rgba(255,255,255,0.9)">
                  Unreachable Devices
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card sx={{ background: 'linear-gradient(135deg, #9c27b0 0%, #ba68c8 100%)' }}>
              <CardContent>
                <Typography variant="h4" color="white" fontWeight="bold">
                  {healthSummary.health_percentage}%
                </Typography>
                <Typography variant="body2" color="rgba(255,255,255,0.9)">
                  Health Score
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
              <TableCell />
              <TableCell><strong>Status</strong></TableCell>
              <TableCell><strong>Hostname</strong></TableCell>
              <TableCell><strong>IP Address</strong></TableCell>
              <TableCell><strong>Vendor</strong></TableCell>
              <TableCell><strong>Health</strong></TableCell>
              <TableCell><strong>Last Audit</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {devices.map((device) => (
              <DeviceHealthRow
                key={device.id}
                device={device}
                onCheckHealth={handleCheckDevice}
              />
            ))}
            {devices.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} align="center">
                  <Typography variant="body2" color="textSecondary">
                    No devices found.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default DeviceHealth;
