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
  IconButton,
  Tooltip,
  LinearProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Lightbulb as InsightIcon,
  Warning as WarningIcon,
  Security as RiskIcon,
  Schedule as ScheduleIcon,
  PlayArrow as RunIcon,
  CheckCircle as CheckIcon,
  Cancel as DismissIcon,
  TrendingUp as TrendIcon,
  BugReport as AnomalyIcon,
  Psychology as MLIcon,
  Speed as SpeedIcon,
  Info as InfoIcon,
  ArrowUpward,
  ArrowDownward
} from '@mui/icons-material';
import { mlInsightsAPI } from '../api/api';

function MLInsights() {
  const [insights, setInsights] = useState([]);
  const [insightsSummary, setInsightsSummary] = useState(null);
  const [riskScores, setRiskScores] = useState([]);
  const [riskSummary, setRiskSummary] = useState(null);
  const [schedulerStatus, setSchedulerStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [currentTab, setCurrentTab] = useState(0);
  const [selectedInsight, setSelectedInsight] = useState(null);
  const [openDetailDialog, setOpenDetailDialog] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [insightsRes, insightsSummaryRes, riskRes, riskSummaryRes, schedulerRes] = await Promise.all([
        mlInsightsAPI.getInsights({ limit: 50 }),
        mlInsightsAPI.getInsightsSummary(),
        mlInsightsAPI.getRiskScores({ limit: 100 }),
        mlInsightsAPI.getRiskSummary(),
        mlInsightsAPI.getSchedulerStatus()
      ]);
      setInsights(insightsRes.data);
      setInsightsSummary(insightsSummaryRes.data);
      setRiskScores(riskRes.data);
      setRiskSummary(riskSummaryRes.data);
      setSchedulerStatus(schedulerRes.data);
      setError(null);
    } catch (err) {
      setError('Failed to load ML insights: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleDismissInsight = async (id) => {
    try {
      await mlInsightsAPI.dismissInsight(id, 'admin');
      setSuccess('Insight dismissed');
      loadData();
    } catch (err) {
      setError('Failed to dismiss insight: ' + err.message);
    }
  };

  const handleMarkActionTaken = async (id) => {
    try {
      await mlInsightsAPI.markActionTaken(id);
      setSuccess('Action marked as taken');
      loadData();
    } catch (err) {
      setError('Failed to mark action: ' + err.message);
    }
  };

  const handleRunJob = async (jobId) => {
    try {
      setSuccess(`Running ${jobId}...`);
      await mlInsightsAPI.runSchedulerJob(jobId);
      setSuccess(`Job ${jobId} completed successfully`);
      loadData();
    } catch (err) {
      setError(`Failed to run job: ${err.message}`);
    }
  };

  const handleGenerateInsights = async () => {
    try {
      setSuccess('Generating insights...');
      const res = await mlInsightsAPI.generateInsights();
      setSuccess(`Generated ${res.data.insights?.length || 0} insights`);
      loadData();
    } catch (err) {
      setError('Failed to generate insights: ' + err.message);
    }
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

  const getRiskLevelColor = (level) => {
    const colors = {
      critical: '#f44336',
      high: '#ff9800',
      medium: '#ffc107',
      low: '#4caf50'
    };
    return colors[level] || '#9e9e9e';
  };

  const getInsightIcon = (type) => {
    const icons = {
      trend: <TrendIcon />,
      anomaly: <AnomalyIcon />,
      prediction: <MLIcon />,
      recommendation: <InsightIcon />
    };
    return icons[type] || <InfoIcon />;
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  if (loading && !insightsSummary) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box display="flex" alignItems="center" gap={1}>
          <MLIcon sx={{ fontSize: 32, color: 'primary.main' }} />
          <Typography variant="h4" component="h1">
            ML Intelligence
          </Typography>
        </Box>
        <Box>
          <Button
            variant="contained"
            startIcon={<InsightIcon />}
            onClick={handleGenerateInsights}
            sx={{ mr: 1 }}
          >
            Generate Insights
          </Button>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadData}
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

      {/* Summary Cards */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography variant="h3" color="white" fontWeight="bold">
                    {insightsSummary?.total_insights || 0}
                  </Typography>
                  <Typography variant="body2" color="rgba(255,255,255,0.8)">
                    Active Insights
                  </Typography>
                </Box>
                <InsightIcon sx={{ fontSize: 48, color: 'rgba(255,255,255,0.5)' }} />
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
                    {insightsSummary?.actionable_insights || 0}
                  </Typography>
                  <Typography variant="body2" color="rgba(255,255,255,0.8)">
                    Actionable Items
                  </Typography>
                </Box>
                <CheckIcon sx={{ fontSize: 48, color: 'rgba(255,255,255,0.5)' }} />
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
                    {(insightsSummary?.critical_count || 0) + (insightsSummary?.high_count || 0)}
                  </Typography>
                  <Typography variant="body2" color="rgba(255,255,255,0.8)">
                    High Priority
                  </Typography>
                </Box>
                <WarningIcon sx={{ fontSize: 48, color: 'rgba(255,255,255,0.5)' }} />
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
                    {riskSummary?.high_risk_devices?.length || 0}
                  </Typography>
                  <Typography variant="body2" color="rgba(255,255,255,0.8)">
                    High-Risk Devices
                  </Typography>
                </Box>
                <RiskIcon sx={{ fontSize: 48, color: 'rgba(255,255,255,0.5)' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Paper sx={{ mb: 3 }}>
        <Tabs value={currentTab} onChange={(e, v) => setCurrentTab(v)}>
          <Tab label={`Insights (${insights.length})`} icon={<InsightIcon />} iconPosition="start" />
          <Tab label={`Risk Scores (${riskScores.length})`} icon={<RiskIcon />} iconPosition="start" />
          <Tab label="ML Scheduler" icon={<ScheduleIcon />} iconPosition="start" />
        </Tabs>

        {/* Insights Tab */}
        {currentTab === 0 && (
          <Box>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Type</TableCell>
                    <TableCell>Severity</TableCell>
                    <TableCell>Title</TableCell>
                    <TableCell>Category</TableCell>
                    <TableCell>Confidence</TableCell>
                    <TableCell>Generated</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {insights.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} align="center">
                        <Typography variant="body2" color="text.secondary" py={3}>
                          No insights available. Click "Generate Insights" to analyze your data.
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    insights.map((insight) => (
                      <TableRow
                        key={insight.id}
                        hover
                        onClick={() => { setSelectedInsight(insight); setOpenDetailDialog(true); }}
                        sx={{ cursor: 'pointer' }}
                      >
                        <TableCell>
                          <Chip
                            icon={getInsightIcon(insight.type)}
                            label={insight.type}
                            size="small"
                            color="primary"
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={insight.severity}
                            size="small"
                            color={getSeverityColor(insight.severity)}
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" fontWeight="medium">
                            {insight.title}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip label={insight.category || 'general'} size="small" variant="outlined" />
                        </TableCell>
                        <TableCell>
                          <Box display="flex" alignItems="center" gap={1}>
                            <LinearProgress
                              variant="determinate"
                              value={(insight.confidence || 0) * 100}
                              sx={{ width: 60, height: 6, borderRadius: 3 }}
                            />
                            <Typography variant="body2">
                              {((insight.confidence || 0) * 100).toFixed(0)}%
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>{formatDate(insight.generated_at)}</TableCell>
                        <TableCell onClick={(e) => e.stopPropagation()}>
                          {insight.is_actionable && !insight.action_taken && (
                            <Tooltip title="Mark action taken">
                              <IconButton
                                size="small"
                                color="success"
                                onClick={() => handleMarkActionTaken(insight.id)}
                              >
                                <CheckIcon />
                              </IconButton>
                            </Tooltip>
                          )}
                          <Tooltip title="Dismiss">
                            <IconButton
                              size="small"
                              color="default"
                              onClick={() => handleDismissInsight(insight.id)}
                            >
                              <DismissIcon />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}

        {/* Risk Scores Tab */}
        {currentTab === 1 && (
          <Box>
            {/* Risk Distribution */}
            {riskSummary && (
              <Box p={2}>
                <Grid container spacing={2}>
                  {Object.entries(riskSummary.risk_distribution || {}).map(([level, count]) => (
                    <Grid item xs={6} sm={3} key={level}>
                      <Card variant="outlined">
                        <CardContent sx={{ textAlign: 'center' }}>
                          <Typography variant="h4" sx={{ color: getRiskLevelColor(level) }}>
                            {count}
                          </Typography>
                          <Typography variant="body2" color="text.secondary" textTransform="capitalize">
                            {level} Risk
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              </Box>
            )}

            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Device ID</TableCell>
                    <TableCell>Risk Level</TableCell>
                    <TableCell>Overall Risk</TableCell>
                    <TableCell>Compliance</TableCell>
                    <TableCell>Health</TableCell>
                    <TableCell>Drift</TableCell>
                    <TableCell>Top Risk Factor</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {riskScores.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} align="center">
                        <Typography variant="body2" color="text.secondary" py={3}>
                          No risk scores available. Risk scoring runs automatically every 6 hours.
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    riskScores.map((score) => (
                      <TableRow key={score.id}>
                        <TableCell>
                          <Typography variant="body2" fontWeight="medium">
                            Device #{score.device_id}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={score.risk_level}
                            size="small"
                            sx={{
                              backgroundColor: getRiskLevelColor(score.risk_level),
                              color: 'white',
                              textTransform: 'capitalize'
                            }}
                          />
                        </TableCell>
                        <TableCell>
                          <Box display="flex" alignItems="center" gap={1}>
                            <LinearProgress
                              variant="determinate"
                              value={score.overall_risk * 100}
                              color={score.risk_level === 'low' ? 'success' : score.risk_level === 'medium' ? 'warning' : 'error'}
                              sx={{ width: 60, height: 6, borderRadius: 3 }}
                            />
                            <Typography variant="body2">
                              {(score.overall_risk * 100).toFixed(0)}%
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <RiskBar value={score.compliance_risk} />
                        </TableCell>
                        <TableCell>
                          <RiskBar value={score.health_risk} />
                        </TableCell>
                        <TableCell>
                          <RiskBar value={score.drift_risk} />
                        </TableCell>
                        <TableCell>
                          {score.risk_factors?.[0] ? (
                            <Typography variant="body2" color="text.secondary">
                              {score.risk_factors[0].factor}
                            </Typography>
                          ) : (
                            <Typography variant="body2" color="success.main">
                              Healthy
                            </Typography>
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

        {/* Scheduler Tab */}
        {currentTab === 2 && (
          <Box p={2}>
            <Alert severity="info" sx={{ mb: 2 }}>
              ML analytics jobs run automatically on schedule. You can manually trigger jobs below.
            </Alert>

            <Grid container spacing={2}>
              {schedulerStatus?.jobs?.map((job) => (
                <Grid item xs={12} md={6} key={job.id}>
                  <Card variant="outlined">
                    <CardContent>
                      <Box display="flex" justifyContent="space-between" alignItems="flex-start">
                        <Box>
                          <Typography variant="h6" gutterBottom>
                            {job.name}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            <strong>ID:</strong> {job.id}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            <strong>Next Run:</strong> {job.next_run ? formatDate(job.next_run) : 'Not scheduled'}
                          </Typography>
                        </Box>
                        <Button
                          variant="contained"
                          size="small"
                          startIcon={<RunIcon />}
                          onClick={() => handleRunJob(job.id)}
                        >
                          Run Now
                        </Button>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>

            {(!schedulerStatus?.jobs || schedulerStatus.jobs.length === 0) && (
              <Typography variant="body2" color="text.secondary" textAlign="center" py={3}>
                No scheduled jobs found. The scheduler may not be running.
              </Typography>
            )}
          </Box>
        )}
      </Paper>

      {/* Insight Detail Dialog */}
      <Dialog
        open={openDetailDialog}
        onClose={() => setOpenDetailDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        {selectedInsight && (
          <>
            <DialogTitle>
              <Box display="flex" alignItems="center" gap={1}>
                {getInsightIcon(selectedInsight.type)}
                {selectedInsight.title}
              </Box>
            </DialogTitle>
            <DialogContent>
              <Box mb={2}>
                <Chip
                  label={selectedInsight.severity}
                  color={getSeverityColor(selectedInsight.severity)}
                  size="small"
                  sx={{ mr: 1 }}
                />
                <Chip
                  label={selectedInsight.type}
                  variant="outlined"
                  size="small"
                  sx={{ mr: 1 }}
                />
                <Chip
                  label={selectedInsight.category || 'general'}
                  variant="outlined"
                  size="small"
                />
              </Box>

              <Typography variant="body1" paragraph>
                {selectedInsight.description}
              </Typography>

              <Divider sx={{ my: 2 }} />

              <Typography variant="subtitle2" gutterBottom>
                Details
              </Typography>
              <List dense>
                <ListItem>
                  <ListItemIcon><SpeedIcon /></ListItemIcon>
                  <ListItemText
                    primary="Confidence Score"
                    secondary={`${((selectedInsight.confidence || 0) * 100).toFixed(0)}%`}
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon><ScheduleIcon /></ListItemIcon>
                  <ListItemText
                    primary="Generated"
                    secondary={formatDate(selectedInsight.generated_at)}
                  />
                </ListItem>
                {selectedInsight.device_id && (
                  <ListItem>
                    <ListItemIcon><RiskIcon /></ListItemIcon>
                    <ListItemText
                      primary="Related Device"
                      secondary={`Device #${selectedInsight.device_id}`}
                    />
                  </ListItem>
                )}
              </List>

              {selectedInsight.metrics && Object.keys(selectedInsight.metrics).length > 0 && (
                <>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="subtitle2" gutterBottom>
                    Related Metrics
                  </Typography>
                  <Box sx={{ bgcolor: 'grey.100', p: 1, borderRadius: 1 }}>
                    <pre style={{ margin: 0, fontSize: '0.85rem' }}>
                      {JSON.stringify(selectedInsight.metrics, null, 2)}
                    </pre>
                  </Box>
                </>
              )}
            </DialogContent>
            <DialogActions>
              {selectedInsight.is_actionable && !selectedInsight.action_taken && (
                <Button
                  startIcon={<CheckIcon />}
                  onClick={() => {
                    handleMarkActionTaken(selectedInsight.id);
                    setOpenDetailDialog(false);
                  }}
                >
                  Mark Action Taken
                </Button>
              )}
              <Button
                startIcon={<DismissIcon />}
                onClick={() => {
                  handleDismissInsight(selectedInsight.id);
                  setOpenDetailDialog(false);
                }}
              >
                Dismiss
              </Button>
              <Button onClick={() => setOpenDetailDialog(false)}>Close</Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Container>
  );
}

// Helper component for risk bars
function RiskBar({ value }) {
  const percentage = (value || 0) * 100;
  const color = percentage > 50 ? 'error' : percentage > 30 ? 'warning' : 'success';

  return (
    <Box display="flex" alignItems="center" gap={1}>
      <LinearProgress
        variant="determinate"
        value={percentage}
        color={color}
        sx={{ width: 40, height: 6, borderRadius: 3 }}
      />
      <Typography variant="body2" fontSize="0.75rem">
        {percentage.toFixed(0)}%
      </Typography>
    </Box>
  );
}

export default MLInsights;
