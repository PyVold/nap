import React, { useState } from 'react';
import {
  Box, Paper, Typography, TextField, Button, Chip, Alert, CircularProgress,
  Grid, Card, CardContent, List, ListItem, ListItemIcon, ListItemText,
  Divider,
} from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import TrendingFlatIcon from '@mui/icons-material/TrendingFlat';
import WarningIcon from '@mui/icons-material/Warning';
import LightbulbIcon from '@mui/icons-material/Lightbulb';
import DevicesIcon from '@mui/icons-material/Devices';
import { aiAPI } from '../api/api';

const trendIcons = {
  improving: <TrendingUpIcon color="success" />,
  declining: <TrendingDownIcon color="error" />,
  stable: <TrendingFlatIcon color="info" />,
};

const CompliancePrediction = () => {
  const [forecastDays, setForecastDays] = useState(30);
  const [deviceId, setDeviceId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [whatIfScenario, setWhatIfScenario] = useState('');
  const [whatIfResult, setWhatIfResult] = useState(null);
  const [whatIfLoading, setWhatIfLoading] = useState(false);

  const handlePredict = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await aiAPI.predictCompliance({
        device_id: deviceId ? parseInt(deviceId) : undefined,
        forecast_days: forecastDays,
      });
      setResult(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to predict compliance.');
    } finally {
      setLoading(false);
    }
  };

  const handleWhatIf = async () => {
    if (!whatIfScenario) return;
    setWhatIfLoading(true);
    try {
      const response = await aiAPI.whatIfAnalysis(whatIfScenario);
      setWhatIfResult(response.data);
    } catch (err) {
      setError('What-if analysis failed.');
    } finally {
      setWhatIfLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 90) return '#4caf50';
    if (score >= 70) return '#ff9800';
    return '#f44336';
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, gap: 1 }}>
        <TrendingUpIcon sx={{ fontSize: 32, color: 'primary.main' }} />
        <Typography variant="h5" fontWeight="bold">Compliance Prediction</Typography>
        <Chip label="Phase 3" color="secondary" size="small" />
      </Box>

      {error && <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>{error}</Alert>}

      {/* Prediction Controls */}
      <Paper elevation={2} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Typography variant="h6" gutterBottom>Forecast Compliance</Typography>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={3}>
            <TextField fullWidth size="small" label="Forecast Days" type="number"
              value={forecastDays} onChange={(e) => setForecastDays(parseInt(e.target.value) || 30)}
              inputProps={{ min: 1, max: 365 }} />
          </Grid>
          <Grid item xs={12} sm={3}>
            <TextField fullWidth size="small" label="Device ID (optional)" type="number"
              value={deviceId} onChange={(e) => setDeviceId(e.target.value)}
              placeholder="All devices" />
          </Grid>
          <Grid item xs={12} sm={3}>
            <Button variant="contained" fullWidth onClick={handlePredict} disabled={loading}
              startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <TrendingUpIcon />}>
              {loading ? 'Predicting...' : 'Predict'}
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {/* Prediction Results */}
      {result && result.predicted_score !== undefined && (
        <>
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={6} sm={3}>
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <Typography variant="caption" color="text.secondary">Current Score</Typography>
                  <Typography variant="h3" fontWeight="bold" sx={{ color: getScoreColor(result.current_score) }}>
                    {result.current_score?.toFixed(1) || 'N/A'}%
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <Typography variant="caption" color="text.secondary">Predicted ({forecastDays}d)</Typography>
                  <Typography variant="h3" fontWeight="bold" sx={{ color: getScoreColor(result.predicted_score) }}>
                    {result.predicted_score?.toFixed(1)}%
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <Typography variant="caption" color="text.secondary">Trend</Typography>
                  <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 1, mt: 1 }}>
                    {trendIcons[result.trend_direction] || trendIcons.stable}
                    <Typography variant="h5" fontWeight="bold" sx={{ textTransform: 'capitalize' }}>
                      {result.trend_direction}
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <Typography variant="caption" color="text.secondary">Days Until Threshold</Typography>
                  <Typography variant="h3" fontWeight="bold" color={result.days_until_threshold <= 14 ? 'error.main' : 'text.primary'}>
                    {result.days_until_threshold || 'N/A'}
                  </Typography>
                  <Typography variant="caption">below {result.threshold}%</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {result.narrative && (
            <Alert severity="info" sx={{ mb: 2 }}>{result.narrative}</Alert>
          )}

          <Grid container spacing={2} sx={{ mb: 3 }}>
            {result.risk_factors?.length > 0 && (
              <Grid item xs={12} sm={6}>
                <Paper elevation={2} sx={{ p: 2, borderRadius: 2 }}>
                  <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Risk Factors</Typography>
                  <List dense>
                    {result.risk_factors.map((rf, idx) => (
                      <ListItem key={idx}>
                        <ListItemIcon><WarningIcon color="warning" fontSize="small" /></ListItemIcon>
                        <ListItemText primary={rf} />
                      </ListItem>
                    ))}
                  </List>
                </Paper>
              </Grid>
            )}
            {result.preventive_actions?.length > 0 && (
              <Grid item xs={12} sm={6}>
                <Paper elevation={2} sx={{ p: 2, borderRadius: 2 }}>
                  <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Preventive Actions</Typography>
                  <List dense>
                    {result.preventive_actions.map((pa, idx) => (
                      <ListItem key={idx}>
                        <ListItemIcon><LightbulbIcon color="success" fontSize="small" /></ListItemIcon>
                        <ListItemText primary={pa} />
                      </ListItem>
                    ))}
                  </List>
                </Paper>
              </Grid>
            )}
          </Grid>

          {result.at_risk_devices?.length > 0 && (
            <Paper elevation={2} sx={{ p: 2, mb: 3, borderRadius: 2 }}>
              <Typography variant="subtitle1" fontWeight="bold" gutterBottom>At-Risk Devices</Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                {result.at_risk_devices.map((d, idx) => (
                  <Chip key={idx} icon={<DevicesIcon />} label={d} color="warning" variant="outlined" />
                ))}
              </Box>
            </Paper>
          )}
        </>
      )}

      <Divider sx={{ my: 3 }} />

      {/* What-If Analysis */}
      <Paper elevation={2} sx={{ p: 3, borderRadius: 2 }}>
        <Typography variant="h6" gutterBottom>What-If Scenario Analysis</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Describe a hypothetical scenario to see how it would affect compliance.
        </Typography>
        <TextField fullWidth multiline rows={2} label="Scenario"
          placeholder='e.g., "What if we enable SSH key-only authentication on all routers?"'
          value={whatIfScenario} onChange={(e) => setWhatIfScenario(e.target.value)} sx={{ mb: 2 }} />
        <Button variant="outlined" onClick={handleWhatIf} disabled={!whatIfScenario || whatIfLoading}
          startIcon={whatIfLoading ? <CircularProgress size={20} /> : <LightbulbIcon />}>
          {whatIfLoading ? 'Analyzing...' : 'Run What-If'}
        </Button>

        {whatIfResult && (
          <Paper sx={{ p: 2, mt: 2, bgcolor: 'grey.50', borderRadius: 2 }}>
            <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
              {typeof whatIfResult === 'string' ? whatIfResult : JSON.stringify(whatIfResult, null, 2)}
            </Typography>
          </Paper>
        )}
      </Paper>
    </Box>
  );
};

export default CompliancePrediction;
