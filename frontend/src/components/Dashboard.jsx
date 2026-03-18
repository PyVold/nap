import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  CardActionArea,
  Typography,
  CircularProgress,
  Alert,
  Button,
  Chip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Avatar,
  LinearProgress,
  Divider,
  IconButton,
  Skeleton,
} from '@mui/material';
import {
  CheckCircle,
  Error as ErrorIcon,
  Assessment,
  Security,
  Devices as DevicesIcon,
  Refresh,
  TrendingUp,
  TrendingDown,
  SmartToy as AIIcon,
  CompareArrows,
  Backup,
  PlayArrow,
  Add,
  ArrowForward,
  Warning,
  Timeline,
  Shield,
  Speed,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { auditAPI, healthAPI, systemAPI, devicesAPI, activityFeedAPI, dashboardAPI } from '../api/api';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, AreaChart, Area } from 'recharts';

const QUICK_ACTIONS = [
  { label: 'Run Audit', icon: <PlayArrow />, path: '/audits', color: '#667eea' },
  { label: 'Add Device', icon: <Add />, path: '/devices', color: '#4caf50' },
  { label: 'AI Chat', icon: <AIIcon />, path: '/ai-chat', color: '#f093fb' },
  { label: 'View Drift', icon: <CompareArrows />, path: '/drift-detection', color: '#ff9800' },
  { label: 'Backup', icon: <Backup />, path: '/config-backups', color: '#4facfe' },
  { label: 'Analytics', icon: <Timeline />, path: '/analytics', color: '#764ba2' },
];

const ACTION_ICONS = {
  create_device: <DevicesIcon fontSize="small" />,
  run_audit: <Assessment fontSize="small" />,
  delete_rule: <Security fontSize="small" />,
  create_rule: <Security fontSize="small" />,
  login: <Shield fontSize="small" />,
  config_backup: <Backup fontSize="small" />,
  drift_scan: <CompareArrows fontSize="small" />,
};

const ACTION_COLORS = {
  create_device: '#4caf50',
  run_audit: '#667eea',
  delete_rule: '#f44336',
  create_rule: '#4caf50',
  login: '#2196f3',
  config_backup: '#ff9800',
};

const formatTimeAgo = (isoString) => {
  if (!isoString) return '';
  const d = new Date(isoString);
  const now = new Date();
  const diffMs = now - d;
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDays = Math.floor(diffHr / 24);
  return `${diffDays}d ago`;
};

const Dashboard = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [compliance, setCompliance] = useState(null);
  const [healthSummary, setHealthSummary] = useState(null);
  const [systemHealth, setSystemHealth] = useState(null);
  const [deviceCount, setDeviceCount] = useState(0);
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);
  const [activityFeed, setActivityFeed] = useState([]);
  const [extendedStats, setExtendedStats] = useState(null);
  const navigate = useNavigate();

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

  // Fetch extended stats and activity (non-blocking)
  const fetchExtendedData = async () => {
    try {
      const [activityRes, statsRes] = await Promise.allSettled([
        activityFeedAPI.getActivity({ limit: 10 }),
        dashboardAPI.getExtended(),
      ]);
      if (activityRes.status === 'fulfilled') setActivityFeed(activityRes.value.data?.items || []);
      if (statsRes.status === 'fulfilled') setExtendedStats(statsRes.value.data);
    } catch { /* non-critical */ }
  };

  useEffect(() => {
    fetchDashboardData();
    fetchExtendedData();

    if (autoRefreshEnabled) {
      const interval = setInterval(() => {
        fetchDashboardData();
        fetchExtendedData();
      }, 30000);
      return () => clearInterval(interval);
    }
  }, [autoRefreshEnabled]); // eslint-disable-line react-hooks/exhaustive-deps

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

  const complianceScore = compliance?.overall_compliance || 0;

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box display="flex" alignItems="center" gap={2}>
          <Typography variant="h4" fontWeight="bold">
            Network Audit Dashboard
          </Typography>
          {autoRefreshEnabled && (
            <Chip
              label={`Live: ${lastRefresh.toLocaleTimeString()}`}
              color="success"
              size="small"
              variant="outlined"
              icon={<Speed />}
            />
          )}
        </Box>
        <Box>
          <Button
            variant={autoRefreshEnabled ? 'outlined' : 'contained'}
            startIcon={<Refresh />}
            onClick={() => setAutoRefreshEnabled(!autoRefreshEnabled)}
            sx={{ mr: 1 }}
            size="small"
          >
            Auto-refresh: {autoRefreshEnabled ? 'ON' : 'OFF'}
          </Button>
          <Button
            variant="contained"
            startIcon={<Refresh />}
            onClick={() => { fetchDashboardData(); fetchExtendedData(); }}
            disabled={loading}
            size="small"
          >
            Refresh
          </Button>
        </Box>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={2} mb={3}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', cursor: 'pointer' }} onClick={() => navigate('/devices')}>
            <CardContent sx={{ py: 2 }}>
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
          <Card
            sx={{
              background: complianceScore >= 80
                ? 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)'
                : complianceScore >= 50
                ? 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
                : 'linear-gradient(135deg, #f44336 0%, #d32f2f 100%)',
              cursor: 'pointer',
            }}
            onClick={() => navigate('/audits')}
          >
            <CardContent sx={{ py: 2 }}>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography variant="h3" color="white" fontWeight="bold">
                    {complianceScore}%
                  </Typography>
                  <Typography variant="body2" color="rgba(255,255,255,0.8)">
                    Compliance Score
                  </Typography>
                </Box>
                {complianceScore >= 80 ? (
                  <TrendingUp sx={{ fontSize: 48, color: 'rgba(255,255,255,0.5)' }} />
                ) : (
                  <TrendingDown sx={{ fontSize: 48, color: 'rgba(255,255,255,0.5)' }} />
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', cursor: 'pointer' }} onClick={() => navigate('/audits')}>
            <CardContent sx={{ py: 2 }}>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography variant="h3" color="white" fontWeight="bold">
                    {compliance?.audited_devices || 0}
                  </Typography>
                  <Typography variant="body2" color="rgba(255,255,255,0.8)">
                    Audited Devices
                  </Typography>
                </Box>
                <Assessment sx={{ fontSize: 48, color: 'rgba(255,255,255,0.5)' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)', cursor: 'pointer' }} onClick={() => navigate('/audits')}>
            <CardContent sx={{ py: 2 }}>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography variant="h3" color="white" fontWeight="bold">
                    {compliance?.critical_issues || 0}
                  </Typography>
                  <Typography variant="body2" color="rgba(255,255,255,0.8)">
                    Critical Issues
                  </Typography>
                </Box>
                <ErrorIcon sx={{ fontSize: 48, color: 'rgba(255,255,255,0.5)' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Quick Actions */}
      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ py: 2 }}>
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1, textTransform: 'uppercase', letterSpacing: 1 }}>
            Quick Actions
          </Typography>
          <Box display="flex" gap={1.5} flexWrap="wrap">
            {QUICK_ACTIONS.map((action) => (
              <Button
                key={action.label}
                variant="outlined"
                startIcon={action.icon}
                onClick={() => navigate(action.path)}
                sx={{
                  borderColor: action.color,
                  color: action.color,
                  '&:hover': { borderColor: action.color, backgroundColor: `${action.color}15` },
                }}
                size="small"
              >
                {action.label}
              </Button>
            ))}
          </Box>
        </CardContent>
      </Card>

      <Grid container spacing={3}>
        {/* Left column: Charts */}
        <Grid item xs={12} md={8}>
          <Grid container spacing={3}>
            {/* Compliance Chart */}
            <Grid item xs={12} md={6}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Overall Compliance
                  </Typography>
                  <ResponsiveContainer width="100%" height={250}>
                    <PieChart>
                      <Pie
                        data={complianceData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={90}
                        fill="#8884d8"
                        dataKey="value"
                        paddingAngle={2}
                      >
                        {complianceData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                  <Box textAlign="center" mt={-4}>
                    <Typography variant="h4" fontWeight="bold" color={complianceScore >= 80 ? 'success.main' : 'error.main'}>
                      {complianceScore}%
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>

            {/* Health Chart */}
            <Grid item xs={12} md={6}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Device Health
                  </Typography>
                  <ResponsiveContainer width="100%" height={250}>
                    <PieChart>
                      <Pie
                        data={healthData.filter((d) => d.value > 0)}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={90}
                        fill="#8884d8"
                        dataKey="value"
                        paddingAngle={2}
                      >
                        {healthData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                  <Box display="flex" justifyContent="center" gap={1} mt={-3} flexWrap="wrap">
                    {healthData.filter(d => d.value > 0).map(d => (
                      <Chip key={d.name} label={`${d.name}: ${d.value}`} size="small" sx={{ backgroundColor: d.color, color: 'white', fontSize: 11 }} />
                    ))}
                  </Box>
                </CardContent>
              </Card>
            </Grid>

            {/* Severity Bar Chart */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Issues by Severity
                  </Typography>
                  <ResponsiveContainer width="100%" height={250}>
                    <BarChart data={severityData} barGap={4}>
                      <XAxis dataKey="name" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="passed" stackId="a" fill="#4caf50" name="Passed" radius={[0, 0, 0, 0]} />
                      <Bar dataKey="failed" stackId="a" fill="#f44336" name="Failed" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </Grid>

            {/* Top Failing Rules */}
            {extendedStats?.top_failing_rules?.length > 0 && (
              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                      <Typography variant="h6">Top Failing Rules</Typography>
                      <Button size="small" endIcon={<ArrowForward />} onClick={() => navigate('/rules')}>
                        View All
                      </Button>
                    </Box>
                    {extendedStats.top_failing_rules.map((rule, idx) => (
                      <Box key={rule.rule_id} sx={{ mb: 1 }}>
                        <Box display="flex" justifyContent="space-between" alignItems="center" mb={0.5}>
                          <Box display="flex" alignItems="center" gap={1}>
                            <Chip
                              label={rule.severity || 'medium'}
                              size="small"
                              color={
                                rule.severity === 'critical' ? 'error' :
                                rule.severity === 'high' ? 'warning' : 'default'
                              }
                              sx={{ fontSize: 10, height: 20 }}
                            />
                            <Typography variant="body2" noWrap sx={{ maxWidth: 300 }}>
                              {rule.name}
                            </Typography>
                          </Box>
                          <Chip label={`${rule.failure_count} failures`} size="small" variant="outlined" color="error" sx={{ fontSize: 11 }} />
                        </Box>
                        <LinearProgress
                          variant="determinate"
                          value={Math.min((rule.failure_count / (extendedStats.top_failing_rules[0]?.failure_count || 1)) * 100, 100)}
                          color="error"
                          sx={{ height: 4, borderRadius: 2 }}
                        />
                      </Box>
                    ))}
                  </CardContent>
                </Card>
              </Grid>
            )}
          </Grid>
        </Grid>

        {/* Right column: Activity Feed & System Status */}
        <Grid item xs={12} md={4}>
          {/* Activity Feed */}
          <Card sx={{ mb: 3 }}>
            <CardContent sx={{ pb: 1 }}>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                <Typography variant="h6">Recent Activity</Typography>
                <Chip label="Live" size="small" color="success" variant="outlined" sx={{ fontSize: 10, height: 20 }} />
              </Box>
              {activityFeed.length > 0 ? (
                <List dense disablePadding>
                  {activityFeed.slice(0, 8).map((item, idx) => (
                    <React.Fragment key={item.id}>
                      <ListItem disablePadding sx={{ py: 0.5 }}>
                        <ListItemIcon sx={{ minWidth: 32 }}>
                          <Avatar sx={{ width: 24, height: 24, bgcolor: ACTION_COLORS[item.action] || '#667eea', fontSize: 12 }}>
                            {ACTION_ICONS[item.action] || <Assessment sx={{ fontSize: 14 }} />}
                          </Avatar>
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Typography variant="body2" noWrap sx={{ fontSize: 12 }}>
                              <strong>{item.username || 'system'}</strong> {item.action?.replace(/_/g, ' ')}
                            </Typography>
                          }
                          secondary={
                            <Typography variant="caption" color="text.disabled">
                              {formatTimeAgo(item.timestamp)}
                              {item.resource_type && ` - ${item.resource_type}`}
                            </Typography>
                          }
                        />
                      </ListItem>
                      {idx < Math.min(activityFeed.length - 1, 7) && <Divider variant="inset" component="li" />}
                    </React.Fragment>
                  ))}
                </List>
              ) : (
                <Box sx={{ py: 3, textAlign: 'center' }}>
                  <Typography variant="body2" color="text.secondary">
                    No recent activity
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>

          {/* System Status */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                System Status
              </Typography>
              <Box display="flex" flexDirection="column" gap={1}>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Typography variant="body2" color="text.secondary">Database</Typography>
                  <Chip
                    icon={<CheckCircle />}
                    label={systemHealth?.database || 'unknown'}
                    color="success"
                    size="small"
                    variant="outlined"
                  />
                </Box>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Typography variant="body2" color="text.secondary">Devices</Typography>
                  <Chip label={systemHealth?.devices || 0} size="small" color="primary" variant="outlined" />
                </Box>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Typography variant="body2" color="text.secondary">Rules</Typography>
                  <Chip label={systemHealth?.rules || 0} size="small" color="info" variant="outlined" />
                </Box>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Typography variant="body2" color="text.secondary">Audit Results</Typography>
                  <Chip label={systemHealth?.audit_results || 0} size="small" color="secondary" variant="outlined" />
                </Box>
              </Box>
            </CardContent>
          </Card>

          {/* Extended Stats Summary */}
          {extendedStats && (
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  24h Summary
                </Typography>
                <Box display="flex" flexDirection="column" gap={1.5}>
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Typography variant="body2" color="text.secondary">Audits Run</Typography>
                    <Typography variant="body2" fontWeight="bold">{extendedStats.activity?.audits_last_24h || 0}</Typography>
                  </Box>
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Typography variant="body2" color="text.secondary">Backups</Typography>
                    <Typography variant="body2" fontWeight="bold">{extendedStats.activity?.backups_last_24h || 0}</Typography>
                  </Box>
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Typography variant="body2" color="text.secondary">Config Changes (7d)</Typography>
                    <Typography variant="body2" fontWeight="bold" color={extendedStats.activity?.changes_last_7d > 0 ? 'warning.main' : 'text.primary'}>
                      {extendedStats.activity?.changes_last_7d || 0}
                    </Typography>
                  </Box>
                  <Divider />
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Typography variant="body2" color="text.secondary">Active Rules</Typography>
                    <Typography variant="body2" fontWeight="bold">
                      {extendedStats.rules?.enabled || 0}/{extendedStats.rules?.total || 0}
                    </Typography>
                  </Box>
                  {extendedStats.devices?.by_vendor && Object.entries(extendedStats.devices.by_vendor).map(([vendor, count]) => (
                    <Box key={vendor} display="flex" justifyContent="space-between" alignItems="center">
                      <Typography variant="body2" color="text.secondary">{vendor}</Typography>
                      <Chip label={count} size="small" variant="outlined" />
                    </Box>
                  ))}
                </Box>
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;
