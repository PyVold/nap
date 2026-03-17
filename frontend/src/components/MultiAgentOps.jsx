import React, { useState } from 'react';
import {
  Box, Paper, Typography, TextField, Button, Chip, Alert, CircularProgress,
  Grid, Card, CardContent, Divider,
} from '@mui/material';
import PrecisionManufacturingIcon from '@mui/icons-material/PrecisionManufacturing';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import MonitorHeartIcon from '@mui/icons-material/MonitorHeart';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';
import { aiAPI } from '../api/api';
import { useCanModify } from './RoleBasedAccess';

const MultiAgentOps = () => {
  const canModify = useCanModify();
  const [request, setRequest] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [monitorResult, setMonitorResult] = useState(null);
  const [monitorLoading, setMonitorLoading] = useState(false);
  const [recommendations, setRecommendations] = useState(null);

  const handleOrchestrate = async () => {
    if (!request) return;
    setLoading(true); setError(null); setResult(null);
    try {
      const response = await aiAPI.orchestrate(request);
      setResult(response.data);
    } catch (err) { setError(err.response?.data?.detail || 'Operation failed.'); }
    finally { setLoading(false); }
  };

  const handleEvaluateMonitoring = async () => {
    setMonitorLoading(true); setError(null);
    try {
      const response = await aiAPI.evaluateMonitoring();
      setMonitorResult(response.data);
    } catch (err) { setError('Monitoring evaluation failed.'); }
    finally { setMonitorLoading(false); }
  };

  const handleGetRecommendations = async () => {
    try {
      const response = await aiAPI.getMonitoringRecommendations();
      setRecommendations(response.data);
    } catch (err) { setError('Failed to get recommendations.'); }
  };

  const presetOperations = [
    { label: 'Full Network Health Check', prompt: 'Run a comprehensive health check on all devices, check compliance, and generate a summary report.' },
    { label: 'Pre-Change Assessment', prompt: 'Assess the current state of all PE routers: check health, verify compliance, backup configs, and generate a pre-change baseline report.' },
    { label: 'Incident Investigation', prompt: 'Investigate potential issues: check all device health, look for recent config changes, check for compliance drift, and compile an incident report.' },
    { label: 'Compliance Deep Dive', prompt: 'Run full compliance audit on all devices, analyze findings by severity, check config drift, and generate a detailed compliance report.' },
  ];

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, gap: 1 }}>
        <PrecisionManufacturingIcon sx={{ fontSize: 32, color: 'primary.main' }} />
        <Typography variant="h5" fontWeight="bold">Multi-Agent Operations</Typography>
        <Chip label="Phase 4" color="error" size="small" />
      </Box>

      {error && <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>{error}</Alert>}

      {/* Orchestrator */}
      <Paper elevation={2} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Typography variant="h6" gutterBottom>AI Orchestrator</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Describe a complex network operation. The AI will plan and delegate to specialized agents
          (Audit, Config, Health, Report) that work in parallel.
        </Typography>

        <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
          {presetOperations.map((op, idx) => (
            <Chip key={idx} label={op.label} onClick={() => setRequest(op.prompt)}
              variant={request === op.prompt ? 'filled' : 'outlined'} color="primary" clickable />
          ))}
        </Box>

        <TextField fullWidth multiline rows={3} label="Operation Request"
          placeholder="Describe the operation you want to perform..."
          value={request} onChange={(e) => setRequest(e.target.value)} sx={{ mb: 2 }} />

        <Button variant="contained" onClick={handleOrchestrate} disabled={!request || loading || !canModify}
          startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <PlayArrowIcon />} size="large">
          {loading ? 'Orchestrating...' : 'Execute Operation'}
        </Button>
      </Paper>

      {/* Results */}
      {result && (
        <Paper elevation={3} sx={{ p: 3, mb: 3, borderRadius: 2, border: '2px solid', borderColor: 'primary.main' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="h6">Operation Results</Typography>
            <Chip label={`${result.tasks_executed}/${result.tasks_total} tasks`} color="success" />
          </Box>

          {result.plan && (
            <Alert severity="info" sx={{ mb: 2 }}><strong>Plan:</strong> {result.plan}</Alert>
          )}

          {result.summary && (
            <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50', borderRadius: 2 }}>
              <Typography variant="subtitle2" fontWeight="bold" gutterBottom>Summary</Typography>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{result.summary}</Typography>
            </Paper>
          )}

          {result.results && Object.entries(result.results).map(([taskId, taskResult]) => (
            <Card key={taskId} variant="outlined" sx={{ mb: 1 }}>
              <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" fontWeight="bold">{taskId}</Typography>
                  <Chip label={taskResult.agent || taskResult.action || 'completed'} size="small" variant="outlined" />
                </Box>
                {taskResult.error && <Typography variant="caption" color="error.main">{taskResult.error}</Typography>}
                {taskResult.report && <Typography variant="caption" sx={{ display: 'block', mt: 0.5 }}>{taskResult.report.substring(0, 200)}...</Typography>}
              </CardContent>
            </Card>
          ))}
        </Paper>
      )}

      <Divider sx={{ my: 3 }} />

      {/* Adaptive Monitoring */}
      <Grid container spacing={2}>
        <Grid item xs={12} sm={6}>
          <Paper elevation={2} sx={{ p: 3, borderRadius: 2 }}>
            <Typography variant="h6" gutterBottom>
              <MonitorHeartIcon fontSize="small" sx={{ mr: 0.5, verticalAlign: 'middle' }} />
              Adaptive Monitoring
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Evaluate current network state and dynamically adjust monitoring intervals.
            </Typography>
            <Button variant="contained" onClick={handleEvaluateMonitoring} disabled={monitorLoading || !canModify}
              startIcon={monitorLoading ? <CircularProgress size={20} color="inherit" /> : <MonitorHeartIcon />}>
              {monitorLoading ? 'Evaluating...' : 'Evaluate & Adapt'}
            </Button>

            {monitorResult && (
              <Paper sx={{ p: 2, mt: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                <Typography variant="caption" fontWeight="bold">Adaptations: {monitorResult.adaptations?.length || 0}</Typography>
                {monitorResult.adaptations?.map((a, idx) => (
                  <Box key={idx} sx={{ mt: 1 }}>
                    <Chip label={a.trigger} size="small" color="warning" sx={{ mr: 0.5 }} />
                    <Typography variant="caption">{a.detail}</Typography>
                  </Box>
                ))}
                {monitorResult.ai_assessment && (
                  <Typography variant="body2" sx={{ mt: 1 }}>{monitorResult.ai_assessment}</Typography>
                )}
              </Paper>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} sm={6}>
          <Paper elevation={2} sx={{ p: 3, borderRadius: 2 }}>
            <Typography variant="h6" gutterBottom>
              <AutoFixHighIcon fontSize="small" sx={{ mr: 0.5, verticalAlign: 'middle' }} />
              Monitoring Recommendations
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Get AI recommendations for optimal monitoring configuration.
            </Typography>
            <Button variant="outlined" onClick={handleGetRecommendations}
              startIcon={<AutoFixHighIcon />}>
              Get Recommendations
            </Button>

            {recommendations && (
              <Paper sx={{ p: 2, mt: 2, bgcolor: 'grey.50', borderRadius: 1, maxHeight: 300, overflow: 'auto' }}>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                  {recommendations.overall_assessment || JSON.stringify(recommendations, null, 2)}
                </Typography>
              </Paper>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default MultiAgentOps;
