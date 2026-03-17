import React, { useState } from 'react';
import {
  Box, Paper, Typography, TextField, Button, Chip, Alert, CircularProgress,
  Grid,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
} from '@mui/material';
import BoltIcon from '@mui/icons-material/Bolt';
import WarningIcon from '@mui/icons-material/Warning';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { aiAPI } from '../api/api';

const riskColors = {
  low: '#4caf50', medium: '#ff9800', high: '#f44336', critical: '#9c27b0',
};

const ImpactAnalysis = () => {
  const [deviceId, setDeviceId] = useState('');
  const [proposedConfig, setProposedConfig] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const handleAnalyze = async () => {
    if (!deviceId || !proposedConfig) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await aiAPI.analyzeImpact({
        device_id: parseInt(deviceId),
        proposed_config: proposedConfig,
        description: description || null,
      });
      setResult(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to analyze impact.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, gap: 1 }}>
        <BoltIcon sx={{ fontSize: 32, color: 'warning.main' }} />
        <Typography variant="h5" fontWeight="bold">Config Impact Analysis</Typography>
        <Chip label="Phase 3" color="secondary" size="small" />
      </Box>

      {error && <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>{error}</Alert>}

      <Paper elevation={2} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Typography variant="h6" gutterBottom>Analyze Proposed Change</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Paste a proposed config change and AI will predict its blast radius, affected peers, and risk level.
        </Typography>

        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid item xs={12} sm={4}>
            <TextField fullWidth size="small" label="Device ID" type="number"
              value={deviceId} onChange={(e) => setDeviceId(e.target.value)} />
          </Grid>
          <Grid item xs={12} sm={8}>
            <TextField fullWidth size="small" label="Description (optional)"
              placeholder="e.g., Adding BGP peer for new transit provider"
              value={description} onChange={(e) => setDescription(e.target.value)} />
          </Grid>
        </Grid>

        <TextField fullWidth multiline rows={6} label="Proposed Configuration Change"
          placeholder="Paste the config diff or new config section here..."
          value={proposedConfig} onChange={(e) => setProposedConfig(e.target.value)} sx={{ mb: 2 }} />

        <Button variant="contained" startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <BoltIcon />}
          onClick={handleAnalyze} disabled={!deviceId || !proposedConfig || loading} size="large">
          {loading ? 'Analyzing Impact...' : 'Analyze Impact'}
        </Button>
      </Paper>

      {result && (
        <Paper elevation={3} sx={{ p: 3, borderRadius: 2, border: '2px solid', borderColor: riskColors[result.overall_risk] || '#ccc' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">Impact Analysis: {result.device_name}</Typography>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Chip label={`Risk: ${result.overall_risk}`}
                sx={{ bgcolor: riskColors[result.overall_risk], color: 'white', fontWeight: 'bold' }} />
              <Chip label={result.safe_to_apply ? 'Safe to Apply' : 'Review Required'}
                color={result.safe_to_apply ? 'success' : 'warning'}
                icon={result.safe_to_apply ? <CheckCircleIcon /> : <WarningIcon />} />
            </Box>
          </Box>

          {result.warnings?.length > 0 && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              {result.warnings.map((w, i) => <div key={i}>{w}</div>)}
            </Alert>
          )}

          {result.recommended_window && (
            <Alert severity="info" sx={{ mb: 2 }}>
              <strong>Recommended Window:</strong> {result.recommended_window}
            </Alert>
          )}

          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Area</TableCell>
                  <TableCell>Risk</TableCell>
                  <TableCell>Impact</TableCell>
                  <TableCell>Affected Peers</TableCell>
                  <TableCell>Mitigation</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {result.predictions.map((pred, idx) => (
                  <TableRow key={idx}>
                    <TableCell><strong>{pred.affected_area}</strong></TableCell>
                    <TableCell>
                      <Chip label={pred.risk_level} size="small"
                        sx={{ bgcolor: riskColors[pred.risk_level] + '20', color: riskColors[pred.risk_level], fontWeight: 'bold' }} />
                    </TableCell>
                    <TableCell>{pred.description}</TableCell>
                    <TableCell>
                      {pred.affected_peers?.map((p, i) => <Chip key={i} label={p} size="small" sx={{ mr: 0.5, mb: 0.5 }} variant="outlined" />)}
                    </TableCell>
                    <TableCell><Typography variant="caption">{pred.mitigation}</Typography></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}
    </Box>
  );
};

export default ImpactAnalysis;
