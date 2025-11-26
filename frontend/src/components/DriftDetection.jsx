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
  Alert,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
} from '@mui/material';
import {
  Refresh,
  Warning,
  CheckCircle,
  Verified,
  CompareArrows,
} from '@mui/icons-material';
import { driftDetectionAPI, devicesAPI } from '../api/api';

export default function DriftDetection() {
  const [drifts, setDrifts] = useState([]);
  const [summary, setSummary] = useState(null);
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [driftDialog, setDriftDialog] = useState(false);
  const [selectedDrift, setSelectedDrift] = useState(null);

  useEffect(() => {
    fetchSummary();
    fetchDevices();
  }, []);

  const fetchSummary = async () => {
    try {
      const response = await driftDetectionAPI.getSummary();
      setSummary(response.data);
    } catch (err) {
      console.error('Failed to fetch summary');
    }
  };

  const fetchDevices = async () => {
    try {
      const response = await devicesAPI.getAll();
      setDevices(response.data);
    } catch (err) {
      setError('Failed to fetch devices');
    }
  };

  const scanAllDevices = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await driftDetectionAPI.scanAll();
      setDrifts(response.data);
      if (response.data.length === 0) {
        setError('No drift detected on any device');
      }
      fetchSummary();
    } catch (err) {
      setError('Failed to scan devices');
    }
    setLoading(false);
  };

  const checkDeviceDrift = async (deviceId) => {
    setLoading(true);
    setError('');
    try {
      const response = await driftDetectionAPI.checkDevice(deviceId);
      if (response.data) {
        setSelectedDrift(response.data);
        setDriftDialog(true);
      } else {
        setError('No drift detected on this device');
      }
    } catch (err) {
      setError('Failed to check drift');
    }
    setLoading(false);
  };

  const setBaseline = async (deviceId) => {
    if (!window.confirm('Set the latest configuration as baseline for this device?')) return;

    setLoading(true);
    try {
      await driftDetectionAPI.setBaseline(deviceId);
      alert('Baseline set successfully');
      fetchSummary();
      setError('');
    } catch (err) {
      setError('Failed to set baseline');
    }
    setLoading(false);
  };

  const getSeverityColor = (severity) => {
    const colors = {
      low: 'info',
      medium: 'warning',
      high: 'error',
    };
    return colors[severity] || 'default';
  };

  return (
    <Box sx={{ p: 3 }}>
      <Grid container spacing={3}>
        {/* Summary Cards */}
        {summary && (
          <>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom>
                    Total Devices
                  </Typography>
                  <Typography variant="h4">{summary.total_devices}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom>
                    With Baseline
                  </Typography>
                  <Typography variant="h4">{summary.devices_with_baseline}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom>
                    Changes (24h)
                  </Typography>
                  <Typography variant="h4">{summary.recent_changes_24h}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom>
                    High Severity (24h)
                  </Typography>
                  <Typography variant="h4" color="error">
                    {summary.high_severity_changes_24h}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </>
        )}

        {/* Drift Detection Actions */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h5" gutterBottom>
                Configuration Drift Detection
              </Typography>
              <Typography variant="body2" color="text.secondary" paragraph>
                Detect unauthorized or unexpected configuration changes by comparing current configurations with baseline.
              </Typography>

              {error && (
                <Alert severity={drifts.length === 0 ? 'info' : 'error'} sx={{ mb: 2 }}>
                  {error}
                </Alert>
              )}

              <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
                <Button
                  variant="contained"
                  startIcon={<Refresh />}
                  onClick={scanAllDevices}
                  disabled={loading}
                >
                  Scan All Devices
                </Button>
              </Box>

              {drifts.length > 0 && (
                <TableContainer component={Paper}>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Device</TableCell>
                        <TableCell>Baseline Time</TableCell>
                        <TableCell>Current Time</TableCell>
                        <TableCell>Lines Changed</TableCell>
                        <TableCell>Severity</TableCell>
                        <TableCell align="right">Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {drifts.map((drift) => (
                        <TableRow key={drift.device_id}>
                          <TableCell>{drift.device_name}</TableCell>
                          <TableCell>{new Date(drift.baseline_timestamp).toLocaleString()}</TableCell>
                          <TableCell>{new Date(drift.current_timestamp).toLocaleString()}</TableCell>
                          <TableCell>{drift.lines_changed}</TableCell>
                          <TableCell>
                            <Chip
                              label={drift.severity}
                              color={getSeverityColor(drift.severity)}
                              size="small"
                            />
                          </TableCell>
                          <TableCell align="right">
                            <Button
                              size="small"
                              onClick={() => {
                                setSelectedDrift(drift);
                                setDriftDialog(true);
                              }}
                            >
                              View Details
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Device Baseline Management */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Baseline Management
              </Typography>
              <Typography variant="body2" color="text.secondary" paragraph>
                Set baseline configurations for each device to enable drift detection.
              </Typography>

              <TableContainer component={Paper}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Device</TableCell>
                      <TableCell>Vendor</TableCell>
                      <TableCell align="right">Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {devices.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={3} align="center">
                          No devices found
                        </TableCell>
                      </TableRow>
                    ) : (
                      devices.slice(0, 10).map((device) => (
                        <TableRow key={device.id}>
                          <TableCell>{device.hostname}</TableCell>
                          <TableCell>{device.vendor}</TableCell>
                          <TableCell align="right">
                            <Button
                              size="small"
                              variant="outlined"
                              startIcon={<Verified />}
                              onClick={() => setBaseline(device.id)}
                              disabled={loading}
                            >
                              Set Baseline
                            </Button>
                            <Button
                              size="small"
                              sx={{ ml: 1 }}
                              onClick={() => checkDeviceDrift(device.id)}
                              disabled={loading}
                            >
                              Check Drift
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Drift Details Dialog */}
      <Dialog open={driftDialog} onClose={() => setDriftDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Configuration Drift Details</DialogTitle>
        <DialogContent>
          {selectedDrift && (
            <Box>
              <Grid container spacing={2} sx={{ mb: 2 }}>
                <Grid item xs={6}>
                  <Typography variant="body2">
                    <strong>Device:</strong> {selectedDrift.device_name}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2">
                    <strong>Severity:</strong>{' '}
                    <Chip
                      label={selectedDrift.severity}
                      color={getSeverityColor(selectedDrift.severity)}
                      size="small"
                    />
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2">
                    <strong>Lines Changed:</strong> {selectedDrift.lines_changed}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2">
                    <strong>Time:</strong> {new Date(selectedDrift.current_timestamp).toLocaleString()}
                  </Typography>
                </Grid>
              </Grid>

              {selectedDrift.diff && (
                <>
                  <Typography variant="subtitle2" gutterBottom>
                    Configuration Diff:
                  </Typography>
                  <TextField
                    multiline
                    fullWidth
                    rows={15}
                    value={selectedDrift.diff}
                    InputProps={{
                      readOnly: true,
                      style: { fontFamily: 'monospace', fontSize: '12px' },
                    }}
                  />
                </>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDriftDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
