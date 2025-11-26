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
  Chip,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  Card,
  CardContent,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  LinearProgress
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Warning as WarningIcon,
  Timeline as TimelineIcon,
  BubbleChart as AnomalyIcon,
  Assessment as AssessmentIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Info as InfoIcon
} from '@mui/icons-material';
import { analyticsAPI } from '../api/api';

function Analytics() {
  const [trends, setTrends] = useState([]);
  const [forecasts, setForecasts] = useState([]);
  const [anomalies, setAnomalies] = useState([]);
  const [summary, setSummary] = useState({
    recent_anomalies: 0,
    average_compliance_7d: 0,
    devices_at_risk: 0,
    total_trends: 0
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [currentTab, setCurrentTab] = useState(0);
  const [timeRange, setTimeRange] = useState('7d');
  const [openForecastDialog, setOpenForecastDialog] = useState(false);
  const [forecastForm, setForecastForm] = useState({
    device_id: '',
    days_ahead: 7
  });

  useEffect(() => {
    loadData();
  }, [timeRange]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [trendsRes, forecastsRes, anomaliesRes, summaryRes] = await Promise.all([
        analyticsAPI.getTrends({ days: parseInt(timeRange) || 7 }),
        analyticsAPI.getForecast(),
        analyticsAPI.getAnomalies({ acknowledged: false }),
        analyticsAPI.getDashboardSummary()
      ]);
      setTrends(trendsRes.data);
      setForecasts(forecastsRes.data);
      setAnomalies(anomaliesRes.data);
      setSummary(summaryRes.data);
      setError(null);
    } catch (err) {
      setError('Failed to load analytics data: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSnapshot = async () => {
    try {
      await analyticsAPI.createSnapshot();
      setSuccess('Snapshot created successfully');
      loadData();
    } catch (err) {
      setError('Failed to create snapshot: ' + err.message);
    }
  };

  const handleGenerateForecast = async () => {
    try {
      const deviceId = forecastForm.device_id ? parseInt(forecastForm.device_id) : null;
      await analyticsAPI.generateForecast(deviceId, forecastForm.days_ahead);
      setSuccess('Forecast generated successfully');
      setOpenForecastDialog(false);
      loadData();
    } catch (err) {
      setError('Failed to generate forecast: ' + err.message);
    }
  };

  const handleDetectAnomalies = async () => {
    try {
      await analyticsAPI.detectAnomalies();
      setSuccess('Anomaly detection completed');
      loadData();
    } catch (err) {
      setError('Failed to detect anomalies: ' + err.message);
    }
  };

  const handleAcknowledgeAnomaly = async (id) => {
    try {
      const user = 'admin'; // In real app, get from auth context
      await analyticsAPI.acknowledgeAnomaly(id, user);
      setSuccess('Anomaly acknowledged');
      loadData();
    } catch (err) {
      setError('Failed to acknowledge anomaly: ' + err.message);
    }
  };

  const getTrendIcon = (change) => {
    if (change > 0) return <TrendingUpIcon color="success" />;
    if (change < 0) return <TrendingDownIcon color="error" />;
    return <TimelineIcon color="action" />;
  };

  const getSeverityColor = (severity) => {
    const colors = {
      critical: 'error',
      high: 'warning',
      medium: 'info',
      low: 'default'
    };
    return colors[severity] || 'default';
  };

  const getComplianceColor = (score) => {
    if (score >= 90) return 'success';
    if (score >= 70) return 'warning';
    return 'error';
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
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
          Analytics & Forecasting
        </Typography>
        <Box>
          <FormControl size="small" sx={{ minWidth: 120, mr: 1 }}>
            <InputLabel>Time Range</InputLabel>
            <Select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              label="Time Range"
            >
              <MenuItem value="7d">7 Days</MenuItem>
              <MenuItem value="14d">14 Days</MenuItem>
              <MenuItem value="30d">30 Days</MenuItem>
              <MenuItem value="90d">90 Days</MenuItem>
            </Select>
          </FormControl>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadData}
            sx={{ mr: 1 }}
          >
            Refresh
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

      {/* Statistics Cards */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    Avg Compliance (7d)
                  </Typography>
                  <Typography variant="h4" color={getComplianceColor(summary.average_compliance_7d)}>
                    {summary.average_compliance_7d.toFixed(1)}%
                  </Typography>
                </Box>
                <AssessmentIcon sx={{ fontSize: 40, color: 'primary.main' }} />
              </Box>
              <LinearProgress
                variant="determinate"
                value={summary.average_compliance_7d}
                color={getComplianceColor(summary.average_compliance_7d)}
                sx={{ mt: 2, height: 6, borderRadius: 3 }}
              />
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    Recent Anomalies
                  </Typography>
                  <Typography variant="h4" color="warning.main">
                    {summary.recent_anomalies}
                  </Typography>
                </Box>
                <AnomalyIcon sx={{ fontSize: 40, color: 'warning.main' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    Devices at Risk
                  </Typography>
                  <Typography variant="h4" color="error.main">
                    {summary.devices_at_risk}
                  </Typography>
                </Box>
                <ErrorIcon sx={{ fontSize: 40, color: 'error.main' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    Total Trends
                  </Typography>
                  <Typography variant="h4">{summary.total_trends}</Typography>
                </Box>
                <TimelineIcon sx={{ fontSize: 40, color: 'info.main' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Paper sx={{ mb: 3 }}>
        <Tabs value={currentTab} onChange={(e, v) => setCurrentTab(v)}>
          <Tab label={`Trends (${trends.length})`} icon={<TimelineIcon />} iconPosition="start" />
          <Tab label={`Forecasts (${forecasts.length})`} icon={<TrendingUpIcon />} iconPosition="start" />
          <Tab label={`Anomalies (${anomalies.length})`} icon={<AnomalyIcon />} iconPosition="start" />
        </Tabs>

        {currentTab === 0 && (
          <Box>
            <Box p={2} display="flex" justifyContent="flex-end">
              <Button
                variant="contained"
                size="small"
                onClick={handleCreateSnapshot}
              >
                Create Snapshot
              </Button>
            </Box>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Date</TableCell>
                    <TableCell>Overall Compliance</TableCell>
                    <TableCell>Change</TableCell>
                    <TableCell>Total Devices</TableCell>
                    <TableCell>Compliant Devices</TableCell>
                    <TableCell>Failed Devices</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {trends.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} align="center">
                        <Typography variant="body2" color="text.secondary" py={3}>
                          No trend data available. Create snapshots to track compliance over time.
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    trends.map((trend, idx) => (
                      <TableRow key={idx}>
                        <TableCell>{formatDate(trend.snapshot_date)}</TableCell>
                        <TableCell>
                          <Box display="flex" alignItems="center">
                            <Typography variant="body2" fontWeight="medium" mr={1}>
                              {trend.overall_compliance?.toFixed(1)}%
                            </Typography>
                            <LinearProgress
                              variant="determinate"
                              value={trend.overall_compliance || 0}
                              color={getComplianceColor(trend.overall_compliance || 0)}
                              sx={{ width: 100, height: 6, borderRadius: 3 }}
                            />
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Box display="flex" alignItems="center">
                            {getTrendIcon(trend.compliance_change)}
                            <Typography variant="body2" ml={1}>
                              {trend.compliance_change > 0 ? '+' : ''}
                              {trend.compliance_change?.toFixed(1) || '0'}%
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>{trend.total_devices || 0}</TableCell>
                        <TableCell>
                          <Chip
                            label={trend.compliant_devices || 0}
                            size="small"
                            color="success"
                            icon={<CheckCircleIcon />}
                          />
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={trend.failed_devices || 0}
                            size="small"
                            color="error"
                            icon={<ErrorIcon />}
                          />
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}

        {currentTab === 1 && (
          <Box>
            <Box p={2} display="flex" justifyContent="flex-end">
              <Button
                variant="contained"
                size="small"
                onClick={() => setOpenForecastDialog(true)}
              >
                Generate Forecast
              </Button>
            </Box>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Forecast Date</TableCell>
                    <TableCell>Predicted Compliance</TableCell>
                    <TableCell>Confidence</TableCell>
                    <TableCell>Device</TableCell>
                    <TableCell>Generated</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {forecasts.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} align="center">
                        <Typography variant="body2" color="text.secondary" py={3}>
                          No forecast data available. Generate forecasts to predict future compliance trends.
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    forecasts.map((forecast, idx) => (
                      <TableRow key={idx}>
                        <TableCell>{formatDate(forecast.forecast_date)}</TableCell>
                        <TableCell>
                          <Box display="flex" alignItems="center">
                            <Typography variant="body2" fontWeight="medium" mr={1}>
                              {forecast.predicted_compliance?.toFixed(1)}%
                            </Typography>
                            <LinearProgress
                              variant="determinate"
                              value={forecast.predicted_compliance || 0}
                              color={getComplianceColor(forecast.predicted_compliance || 0)}
                              sx={{ width: 100, height: 6, borderRadius: 3 }}
                            />
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={`${(forecast.confidence_score * 100)?.toFixed(0)}%`}
                            size="small"
                            color={forecast.confidence_score > 0.7 ? 'success' : 'warning'}
                          />
                        </TableCell>
                        <TableCell>{forecast.device_id || 'All Devices'}</TableCell>
                        <TableCell>{formatDate(forecast.created_at)}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}

        {currentTab === 2 && (
          <Box>
            <Box p={2} display="flex" justifyContent="flex-end">
              <Button
                variant="contained"
                size="small"
                onClick={handleDetectAnomalies}
              >
                Run Anomaly Detection
              </Button>
            </Box>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Type</TableCell>
                    <TableCell>Severity</TableCell>
                    <TableCell>Device</TableCell>
                    <TableCell>Description</TableCell>
                    <TableCell>Z-Score</TableCell>
                    <TableCell>Detected</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {anomalies.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} align="center">
                        <Typography variant="body2" color="text.secondary" py={3}>
                          No anomalies detected. Run anomaly detection to identify unusual patterns.
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    anomalies.map((anomaly) => (
                      <TableRow key={anomaly.id}>
                        <TableCell>
                          <Chip
                            label={anomaly.anomaly_type}
                            size="small"
                            color="primary"
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={anomaly.severity}
                            size="small"
                            color={getSeverityColor(anomaly.severity)}
                            icon={<WarningIcon />}
                          />
                        </TableCell>
                        <TableCell>{anomaly.device_id || 'N/A'}</TableCell>
                        <TableCell>
                          <Typography variant="body2">
                            {anomaly.description || 'No description'}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          {anomaly.z_score ? (
                            <Chip
                              label={anomaly.z_score.toFixed(2)}
                              size="small"
                              color={Math.abs(anomaly.z_score) > 3 ? 'error' : 'warning'}
                            />
                          ) : (
                            'N/A'
                          )}
                        </TableCell>
                        <TableCell>{formatDate(anomaly.detected_at)}</TableCell>
                        <TableCell>
                          {anomaly.acknowledged ? (
                            <Chip
                              label="Acknowledged"
                              size="small"
                              color="success"
                              icon={<CheckCircleIcon />}
                            />
                          ) : (
                            <Chip
                              label="New"
                              size="small"
                              color="warning"
                            />
                          )}
                        </TableCell>
                        <TableCell>
                          {!anomaly.acknowledged && (
                            <Button
                              size="small"
                              variant="outlined"
                              onClick={() => handleAcknowledgeAnomaly(anomaly.id)}
                            >
                              Acknowledge
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}
      </Paper>

      {/* Generate Forecast Dialog */}
      <Dialog open={openForecastDialog} onClose={() => setOpenForecastDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Generate Compliance Forecast</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Device ID (optional)"
            type="number"
            value={forecastForm.device_id}
            onChange={(e) => setForecastForm({ ...forecastForm, device_id: e.target.value })}
            margin="normal"
            helperText="Leave empty to forecast for all devices"
          />

          <FormControl fullWidth margin="normal">
            <InputLabel>Forecast Period</InputLabel>
            <Select
              value={forecastForm.days_ahead}
              onChange={(e) => setForecastForm({ ...forecastForm, days_ahead: e.target.value })}
              label="Forecast Period"
            >
              <MenuItem value={7}>7 days ahead</MenuItem>
              <MenuItem value={14}>14 days ahead</MenuItem>
              <MenuItem value={30}>30 days ahead</MenuItem>
              <MenuItem value={90}>90 days ahead</MenuItem>
            </Select>
          </FormControl>

          <Alert severity="info" sx={{ mt: 2 }}>
            <Typography variant="body2">
              Forecasting uses historical compliance data to predict future trends. More historical data will improve accuracy.
            </Typography>
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenForecastDialog(false)}>Cancel</Button>
          <Button onClick={handleGenerateForecast} variant="contained">
            Generate
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}

export default Analytics;
