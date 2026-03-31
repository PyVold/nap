import React, { useState, useEffect } from 'react';
import {
  Box, Paper, Typography, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Chip, Card, CardContent, Grid, CircularProgress,
  FormControl, InputLabel, Select, MenuItem, Alert, TablePagination,
} from '@mui/material';
import HistoryIcon from '@mui/icons-material/History';
import ThumbUpIcon from '@mui/icons-material/ThumbUp';
import ThumbDownIcon from '@mui/icons-material/ThumbDown';
import TokenIcon from '@mui/icons-material/DataUsage';
import { aiAPI } from '../api/api';

const AIHistory = () => {
  const [stats, setStats] = useState(null);
  const [interactions, setInteractions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [featureFilter, setFeatureFilter] = useState('');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    fetchStats();
  }, []);

  useEffect(() => {
    fetchInteractions();
  }, [featureFilter, page, rowsPerPage]); // eslint-disable-line react-hooks/exhaustive-deps

  const fetchStats = async () => {
    try {
      const response = await aiAPI.getFeedbackStats();
      setStats(response.data);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  };

  const fetchInteractions = async () => {
    setLoading(true);
    try {
      const params = {
        limit: rowsPerPage,
        offset: page * rowsPerPage,
      };
      if (featureFilter) params.feature_type = featureFilter;

      const response = await aiAPI.getAIHistory(params);
      setInteractions(response.data.interactions);
      setTotal(response.data.total);
    } catch (err) {
      setError('Failed to load interaction history');
    } finally {
      setLoading(false);
    }
  };

  const getFeatureLabel = (type) => {
    const labels = {
      rule_builder: 'Rule Builder',
      chat_query: 'AI Chat',
      remediation: 'Remediation',
      report: 'Reports',
      anomaly: 'Anomaly Detection',
      impact_analysis: 'Impact Analysis',
      compliance_prediction: 'Compliance Prediction',
      config_optimization: 'Config Optimizer',
      config_search: 'Config Search',
      multi_agent: 'Multi-Agent',
      adaptive_monitoring: 'Monitoring',
      knowledge_base_query: 'Knowledge Base',
      feedback: 'Feedback',
    };
    return labels[type] || type;
  };

  const getFeedbackChip = (feedback) => {
    if (!feedback) return <Chip label="No feedback" size="small" variant="outlined" />;
    if (feedback === 'positive' || feedback === 'accepted') {
      return <Chip icon={<ThumbUpIcon />} label={feedback} size="small" color="success" />;
    }
    if (feedback === 'negative' || feedback === 'rejected') {
      return <Chip icon={<ThumbDownIcon />} label={feedback} size="small" color="error" />;
    }
    return <Chip label={feedback} size="small" />;
  };

  const positiveCount = stats?.feedback_breakdown?.positive || 0;
  const negativeCount = stats?.feedback_breakdown?.negative || 0;
  const totalFeedback = positiveCount + negativeCount;

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, gap: 1 }}>
        <HistoryIcon sx={{ fontSize: 32, color: 'primary.main' }} />
        <Typography variant="h5" fontWeight="bold">AI Interaction History</Typography>
        <Chip label="Analytics" color="primary" size="small" />
      </Box>

      {error && <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>{error}</Alert>}

      {/* Stats Cards */}
      {stats && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="overline" color="text.secondary">Total Interactions</Typography>
                <Typography variant="h4" fontWeight="bold">{stats.total_interactions}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="overline" color="text.secondary">Positive Feedback</Typography>
                <Typography variant="h4" fontWeight="bold" color="success.main">
                  {totalFeedback > 0 ? Math.round(positiveCount / totalFeedback * 100) : 0}%
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {positiveCount} of {totalFeedback} rated
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="overline" color="text.secondary">Feedback Rate</Typography>
                <Typography variant="h4" fontWeight="bold">{stats.feedback_rate}%</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <TokenIcon fontSize="small" color="action" />
                  <Typography variant="overline" color="text.secondary">Tokens Used</Typography>
                </Box>
                <Typography variant="h4" fontWeight="bold">
                  {stats.total_tokens_used > 1000000
                    ? `${(stats.total_tokens_used / 1000000).toFixed(1)}M`
                    : stats.total_tokens_used > 1000
                    ? `${(stats.total_tokens_used / 1000).toFixed(1)}K`
                    : stats.total_tokens_used}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Feature Type Breakdown */}
      {stats?.by_feature_type && (
        <Paper elevation={2} sx={{ p: 2, mb: 3, borderRadius: 2 }}>
          <Typography variant="subtitle2" gutterBottom>Usage by Feature</Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {Object.entries(stats.by_feature_type).map(([type, count]) => (
              <Chip
                key={type}
                label={`${getFeatureLabel(type)}: ${count}`}
                variant={featureFilter === type ? 'filled' : 'outlined'}
                color={featureFilter === type ? 'primary' : 'default'}
                onClick={() => setFeatureFilter(featureFilter === type ? '' : type)}
                size="small"
              />
            ))}
          </Box>
        </Paper>
      )}

      {/* Interactions Table */}
      <Paper elevation={2} sx={{ borderRadius: 2 }}>
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">Interaction Log</Typography>
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>Filter by Feature</InputLabel>
            <Select
              value={featureFilter}
              onChange={(e) => { setFeatureFilter(e.target.value); setPage(0); }}
              label="Filter by Feature"
            >
              <MenuItem value="">All Features</MenuItem>
              <MenuItem value="rule_builder">Rule Builder</MenuItem>
              <MenuItem value="chat_query">AI Chat</MenuItem>
              <MenuItem value="remediation">Remediation</MenuItem>
              <MenuItem value="report">Reports</MenuItem>
              <MenuItem value="anomaly">Anomaly Detection</MenuItem>
              <MenuItem value="impact_analysis">Impact Analysis</MenuItem>
              <MenuItem value="compliance_prediction">Compliance Prediction</MenuItem>
              <MenuItem value="config_optimization">Config Optimizer</MenuItem>
              <MenuItem value="multi_agent">Multi-Agent</MenuItem>
              <MenuItem value="knowledge_base_query">Knowledge Base</MenuItem>
            </Select>
          </FormControl>
        </Box>

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Time</TableCell>
                    <TableCell>Feature</TableCell>
                    <TableCell>Input</TableCell>
                    <TableCell>Model</TableCell>
                    <TableCell align="right">Tokens</TableCell>
                    <TableCell>Feedback</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {interactions.map((interaction) => (
                    <TableRow key={interaction.id} hover>
                      <TableCell>
                        <Typography variant="caption">
                          {interaction.created_at
                            ? new Date(interaction.created_at).toLocaleString()
                            : 'N/A'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={getFeatureLabel(interaction.interaction_type)}
                          size="small"
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell sx={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        <Typography variant="body2">{interaction.input_prompt}</Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption">{interaction.model_used}</Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="caption">{interaction.tokens_used}</Typography>
                      </TableCell>
                      <TableCell>{getFeedbackChip(interaction.feedback)}</TableCell>
                    </TableRow>
                  ))}
                  {interactions.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={6} align="center">
                        <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                          No interactions found
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
            <TablePagination
              component="div"
              count={total}
              page={page}
              onPageChange={(_, newPage) => setPage(newPage)}
              rowsPerPage={rowsPerPage}
              onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0); }}
              rowsPerPageOptions={[10, 25, 50]}
            />
          </>
        )}
      </Paper>
    </Box>
  );
};

export default AIHistory;
