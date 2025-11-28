import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Alert,
  Button,
  Chip,
  LinearProgress,
} from '@mui/material';
import {
  CheckCircle,
  Error,
  Warning,
  Assessment,
  Security,
  Devices as DevicesIcon,
  Refresh,
} from '@mui/icons-material';
import { auditAPI, healthAPI, systemAPI, devicesAPI } from '../api/api';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const Dashboard = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [compliance, setCompliance] = useState(null);
  const [healthSummary, setHealthSummary] = useState(null);
  const [systemHealth, setSystemHealth] = useState(null);
  const [deviceCount, setDeviceCount] = useState(0);
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [complianceRes, healthRes, systemRes, devicesRes] = await Promise.all([
        auditAPI.getCompliance(),
        healthAPI.getSummary(),
        systemAPI.healthCheck(),
        devicesAPI.getAll(),
      ]);
      setCompliance(complianceRes.data);
      setHealthSummary(healthRes.data);
      setSystemHealth(systemRes.data);
      setDeviceCount(devicesRes.data.length);
      setLastRefresh(new Date());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    
    if (autoRefreshEnabled) {
      const interval = setInterval(fetchDashboardData, 30000); // Refresh every 30 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefreshEnabled]);

  if (loading && !compliance) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        Error loading dashboard: {error}
      </Alert>
    );
  }

  const severityColors = {
    critical: '#f44336',
    high: '#ff9800',
    medium: '#ff5722',
    low: '#ffc107',
  };

  const severityData = compliance?.by_severity
    ? Object.entries(compliance.by_severity).map(([severity, data]) => ({
        name: severity.charAt(0).toUpperCase() + severity.slice(1),
        total: data.total,
        failed: data.failed,
        passed: data.total - data.failed,
      }))
    : [];

  const complianceData = [
    { name: 'Compliant', value: compliance?.overall_compliance || 0, color: '#4caf50' },
    { name: 'Non-Compliant', value: 100 - (compliance?.overall_compliance || 0), color: '#f44336' },
  ];

  const healthData = healthSummary
    ? [
        { name: 'Healthy', value: healthSummary.healthy, color: '#4caf50' },
        { name: 'Degraded', value: healthSummary.degraded, color: '#ff9800' },
        { name: 'Unreachable', value: healthSummary.unreachable, color: '#f44336' },
        { name: 'Unhealthy', value: healthSummary.unhealthy, color: '#d32f2f' },
      ]
    : [];

  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box display="flex" alignItems="center" gap={2}>
          <Typography variant="h4" fontWeight="bold">
            Network Audit Dashboard
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
            variant="contained"
            startIcon={<Refresh />}
            onClick={fetchDashboardData}
            disabled={loading}
          >
            Refresh Now
          </Button>
        </Box>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography variant="h3" color="white" fontWeight="bold">
                    {deviceCount}
                  </Typography>
                  <Typography variant="body2" color="rgba(255,255,255,0.8)">
                    Total Devices
                  </Typography>
                </Box>
                <DevicesIcon sx={{ fontSize: 48, color: 'rgba(255,255,255,0.5)' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' }}>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography variant="h3" color="white" fontWeight="bold">
                    {compliance?.overall_compliance || 0}%
                  </Typography>
                  <Typography variant="body2" color="rgba(255,255,255,0.8)">
                    Compliance Score
                  </Typography>
                </Box>
                <Assessment sx={{ fontSize: 48, color: 'rgba(255,255,255,0.5)' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)' }}>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography variant="h3" color="white" fontWeight="bold">
                    {compliance?.audited_devices || 0}
                  </Typography>
                  <Typography variant="body2" color="rgba(255,255,255,0.8)">
                    Audited Devices
                  </Typography>
                </Box>
                <Security sx={{ fontSize: 48, color: 'rgba(255,255,255,0.5)' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)' }}>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography variant="h3" color="white" fontWeight="bold">
                    {compliance?.critical_issues || 0}
                  </Typography>
                  <Typography variant="body2" color="rgba(255,255,255,0.8)">
                    Critical Issues
                  </Typography>
                </Box>
                <Error sx={{ fontSize: 48, color: 'rgba(255,255,255,0.5)' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Charts */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Overall Compliance
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={complianceData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={(entry) => `${entry.name}: ${entry.value}%`}
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {complianceData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Device Health Status
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={healthData.filter((d) => d.value > 0)}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={(entry) => `${entry.name}: ${entry.value}`}
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {healthData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Issues by Severity
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={severityData}>
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="passed" stackId="a" fill="#4caf50" name="Passed" />
                  <Bar dataKey="failed" stackId="a" fill="#f44336" name="Failed" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* System Health */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                System Status
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={3}>
                  <Chip
                    icon={<CheckCircle />}
                    label={`Database: ${systemHealth?.database || 'unknown'}`}
                    color="success"
                    sx={{ width: '100%' }}
                  />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Chip
                    icon={<DevicesIcon />}
                    label={`Devices: ${systemHealth?.devices || 0}`}
                    color="primary"
                    sx={{ width: '100%' }}
                  />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Chip
                    icon={<Assessment />}
                    label={`Rules: ${systemHealth?.rules || 0}`}
                    color="info"
                    sx={{ width: '100%' }}
                  />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Chip
                    icon={<Security />}
                    label={`Audits: ${systemHealth?.audit_results || 0}`}
                    color="secondary"
                    sx={{ width: '100%' }}
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;
