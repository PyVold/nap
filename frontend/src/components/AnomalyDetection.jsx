import React, { useState, useEffect } from 'react';
import {
  Box, Paper, Typography, Button, Card, CardContent, Chip, Alert, CircularProgress,
  Grid, Slider, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, LinearProgress, Tooltip,
} from '@mui/material';
import SecurityIcon from '@mui/icons-material/Security';
import { aiAPI } from '../api/api';

const severityColors = {
  routine: { bg: '#e8f5e9', color: '#2e7d32', label: 'Routine' },
  notable: { bg: '#fff3e0', color: '#e65100', label: 'Notable' },
  suspicious: { bg: '#fff8e1', color: '#f57f17', label: 'Suspicious' },
  critical: { bg: '#ffebee', color: '#c62828', label: 'Critical' },
};

const AnomalyDetection = () => {
  const [anomalies, setAnomalies] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hoursBack, setHoursBack] = useState(24);
  const [minScore, setMinScore] = useState(0.3);

  const handleDetect = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await aiAPI.detectAnomalies({
        hours_back: hoursBack,
        min_score: minScore,
      });
      setAnomalies(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to run anomaly detection.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleDetect();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const getScoreColor = (score) => {
    if (score >= 0.8) return '#c62828';
    if (score >= 0.5) return '#f57f17';
    if (score >= 0.3) return '#e65100';
    return '#2e7d32';
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, gap: 1 }}>
        <SecurityIcon sx={{ fontSize: 32, color: 'warning.main' }} />
        <Typography variant="h5" fontWeight="bold">Anomaly Detection</Typography>
        <Chip label="AI-Powered" color="primary" size="small" />
      </Box>

      {error && <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>{error}</Alert>}

      {/* Controls */}
      <Paper elevation={2} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Grid container spacing={3} alignItems="center">
          <Grid item xs={12} sm={4}>
            <Typography variant="body2" gutterBottom>Time Window: {hoursBack} hours</Typography>
            <Slider
              value={hoursBack}
              onChange={(e, v) => setHoursBack(v)}
              min={1}
              max={168}
              step={1}
              valueLabelDisplay="auto"
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <Typography variant="body2" gutterBottom>Min Anomaly Score: {minScore}</Typography>
            <Slider
              value={minScore}
              onChange={(e, v) => setMinScore(v)}
              min={0}
              max={1}
              step={0.05}
              valueLabelDisplay="auto"
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <Button
              variant="contained"
              startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <SecurityIcon />}
              onClick={handleDetect}
              disabled={loading}
              fullWidth
              size="large"
            >
              {loading ? 'Analyzing...' : 'Run Detection'}
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {/* Summary Cards */}
      {anomalies && (
        <>
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={6} sm={3}>
              <Card sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white' }}>
                <CardContent>
                  <Typography variant="body2" sx={{ opacity: 0.8 }}>Changes Analyzed</Typography>
                  <Typography variant="h4" fontWeight="bold">{anomalies.total_changes_analyzed}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card sx={{ background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', color: 'white' }}>
                <CardContent>
                  <Typography variant="body2" sx={{ opacity: 0.8 }}>Anomalies Found</Typography>
                  <Typography variant="h4" fontWeight="bold">{anomalies.anomalies_found}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card sx={{ background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', color: 'white' }}>
                <CardContent>
                  <Typography variant="body2" sx={{ opacity: 0.8 }}>Time Window</Typography>
                  <Typography variant="h4" fontWeight="bold">{anomalies.analysis_window_hours}h</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card sx={{ background: anomalies.anomalies_found > 0 ? 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)' : 'linear-gradient(135deg, #a8e063 0%, #56ab2f 100%)', color: 'white' }}>
                <CardContent>
                  <Typography variant="body2" sx={{ opacity: 0.8 }}>Detection Rate</Typography>
                  <Typography variant="h4" fontWeight="bold">
                    {anomalies.total_changes_analyzed > 0
                      ? Math.round((anomalies.anomalies_found / anomalies.total_changes_analyzed) * 100)
                      : 0}%
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Anomalies Table */}
          {anomalies.anomalies.length > 0 ? (
            <Paper elevation={2} sx={{ borderRadius: 2 }}>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Score</TableCell>
                      <TableCell>Severity</TableCell>
                      <TableCell>Device</TableCell>
                      <TableCell>Change Summary</TableCell>
                      <TableCell>Reasons</TableCell>
                      <TableCell>Time</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {anomalies.anomalies.map((anomaly, idx) => {
                      const sev = severityColors[anomaly.severity] || severityColors.routine;
                      return (
                        <TableRow key={idx} sx={{ '&:hover': { bgcolor: 'action.hover' } }}>
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 100 }}>
                              <LinearProgress
                                variant="determinate"
                                value={anomaly.score * 100}
                                sx={{
                                  flex: 1,
                                  height: 8,
                                  borderRadius: 4,
                                  '& .MuiLinearProgress-bar': { bgcolor: getScoreColor(anomaly.score) },
                                }}
                              />
                              <Typography variant="body2" fontWeight="bold" sx={{ color: getScoreColor(anomaly.score) }}>
                                {Math.round(anomaly.score * 100)}
                              </Typography>
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={sev.label}
                              size="small"
                              sx={{ bgcolor: sev.bg, color: sev.color, fontWeight: 'bold' }}
                            />
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" fontWeight="bold">{anomaly.device_name}</Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">{anomaly.change_summary}</Typography>
                          </TableCell>
                          <TableCell>
                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                              {anomaly.reasons.slice(0, 3).map((reason, rIdx) => (
                                <Typography key={rIdx} variant="caption">{reason}</Typography>
                              ))}
                              {anomaly.reasons.length > 3 && (
                                <Tooltip title={anomaly.reasons.slice(3).join('\n')}>
                                  <Typography variant="caption" color="primary" sx={{ cursor: 'pointer' }}>
                                    +{anomaly.reasons.length - 3} more
                                  </Typography>
                                </Tooltip>
                              )}
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Typography variant="caption">
                              {anomaly.timestamp ? new Date(anomaly.timestamp).toLocaleString() : '-'}
                            </Typography>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          ) : (
            <Paper elevation={2} sx={{ p: 4, textAlign: 'center', borderRadius: 2 }}>
              <Typography variant="h6" color="success.main" gutterBottom>No Anomalies Detected</Typography>
              <Typography variant="body2" color="text.secondary">
                All configuration changes in the last {hoursBack} hours appear normal.
              </Typography>
            </Paper>
          )}
        </>
      )}
    </Box>
  );
};

export default AnomalyDetection;
