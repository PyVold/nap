import React, { useState, useEffect } from 'react';
import {
  Box, Paper, Typography, Button, Card, CardContent, CardActions,
  Select, MenuItem, FormControl, InputLabel, Chip, Alert, CircularProgress,
  Grid, Dialog, DialogTitle, DialogContent, DialogActions, TextField,
  Switch, FormControlLabel, Divider, List, ListItem, ListItemText,
  ListItemIcon,
} from '@mui/material';
import AssessmentIcon from '@mui/icons-material/Assessment';
import FindInPageIcon from '@mui/icons-material/FindInPage';
import RecommendIcon from '@mui/icons-material/Recommend';
import DownloadIcon from '@mui/icons-material/Download';
import { aiAPI } from '../api/api';
import AIFeedbackWidget from './AIFeedbackWidget';

const AIReports = () => {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [selectedReport, setSelectedReport] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  // Generation form
  const [reportType, setReportType] = useState('executive');
  const [framework, setFramework] = useState('');
  const [dateRange, setDateRange] = useState(30);
  const [includeTrends, setIncludeTrends] = useState(true);
  const [includeRecommendations, setIncludeRecommendations] = useState(true);

  useEffect(() => {
    fetchReports();
  }, []);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const response = await aiAPI.getReports();
      setReports(response.data);
    } catch (err) {
      console.error('Failed to fetch reports:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);

    try {
      const response = await aiAPI.generateReport({
        report_type: reportType,
        framework: framework || null,
        date_range_days: dateRange,
        include_trends: includeTrends,
        include_recommendations: includeRecommendations,
      });
      setSuccess('Report generated successfully!');
      setSelectedReport(response.data);
      setDialogOpen(true);
      fetchReports();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate report.');
    } finally {
      setGenerating(false);
    }
  };

  const handleViewReport = async (reportId) => {
    try {
      const response = await aiAPI.getReport(reportId);
      setSelectedReport(response.data);
      setDialogOpen(true);
    } catch (err) {
      setError('Failed to load report.');
    }
  };

  const handleDownload = () => {
    if (!selectedReport) return;
    const blob = new Blob([selectedReport.content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedReport.title.replace(/\s+/g, '_')}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getTypeColor = (type) => {
    switch (type) {
      case 'executive': return 'primary';
      case 'detailed': return 'secondary';
      case 'framework': return 'warning';
      default: return 'default';
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, gap: 1 }}>
        <AssessmentIcon sx={{ fontSize: 32, color: 'primary.main' }} />
        <Typography variant="h5" fontWeight="bold">AI Compliance Reports</Typography>
        <Chip label="AI-Powered" color="primary" size="small" />
      </Box>

      {error && <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>{error}</Alert>}
      {success && <Alert severity="success" onClose={() => setSuccess(null)} sx={{ mb: 2 }}>{success}</Alert>}

      {/* Report Generation */}
      <Paper elevation={2} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Typography variant="h6" gutterBottom>Generate New Report</Typography>

        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid item xs={12} sm={4}>
            <FormControl fullWidth size="small">
              <InputLabel>Report Type</InputLabel>
              <Select value={reportType} onChange={(e) => setReportType(e.target.value)} label="Report Type">
                <MenuItem value="executive">Executive Summary</MenuItem>
                <MenuItem value="detailed">Detailed Technical</MenuItem>
                <MenuItem value="framework">Framework Compliance</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={4}>
            <FormControl fullWidth size="small">
              <InputLabel>Framework</InputLabel>
              <Select value={framework} onChange={(e) => setFramework(e.target.value)} label="Framework">
                <MenuItem value="">General</MenuItem>
                <MenuItem value="SOX">SOX</MenuItem>
                <MenuItem value="PCI-DSS">PCI-DSS</MenuItem>
                <MenuItem value="NIST">NIST</MenuItem>
                <MenuItem value="ISO27001">ISO 27001</MenuItem>
                <MenuItem value="CIS">CIS Benchmarks</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={4}>
            <TextField
              fullWidth
              size="small"
              type="number"
              label="Date Range (days)"
              value={dateRange}
              onChange={(e) => setDateRange(parseInt(e.target.value) || 30)}
              inputProps={{ min: 1, max: 365 }}
            />
          </Grid>
        </Grid>

        <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
          <FormControlLabel
            control={<Switch checked={includeTrends} onChange={(e) => setIncludeTrends(e.target.checked)} />}
            label="Include Trends"
          />
          <FormControlLabel
            control={<Switch checked={includeRecommendations} onChange={(e) => setIncludeRecommendations(e.target.checked)} />}
            label="Include Recommendations"
          />
        </Box>

        <Button
          variant="contained"
          startIcon={generating ? <CircularProgress size={20} color="inherit" /> : <AssessmentIcon />}
          onClick={handleGenerate}
          disabled={generating}
          size="large"
        >
          {generating ? 'Generating Report...' : 'Generate Report'}
        </Button>
      </Paper>

      {/* Report History */}
      <Paper elevation={2} sx={{ p: 3, borderRadius: 2 }}>
        <Typography variant="h6" gutterBottom>Generated Reports</Typography>
        {loading ? (
          <CircularProgress size={24} />
        ) : reports.length === 0 ? (
          <Typography variant="body2" color="text.secondary">No reports generated yet.</Typography>
        ) : (
          <Grid container spacing={2}>
            {reports.map((report) => (
              <Grid item xs={12} sm={6} md={4} key={report.id}>
                <Card variant="outlined" sx={{ height: '100%' }}>
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Chip label={report.report_type} color={getTypeColor(report.report_type)} size="small" />
                      {report.framework && <Chip label={report.framework} size="small" variant="outlined" />}
                    </Box>
                    <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
                      {report.title}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      display: '-webkit-box',
                      WebkitLineClamp: 3,
                      WebkitBoxOrient: 'vertical',
                    }}>
                      {report.executive_summary}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                      {report.created_at ? new Date(report.created_at).toLocaleString() : ''}
                    </Typography>
                  </CardContent>
                  <CardActions>
                    <Button size="small" onClick={() => handleViewReport(report.id)}>View Report</Button>
                  </CardActions>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}
      </Paper>

      {/* Report Viewer Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="lg" fullWidth>
        {selectedReport && (
          <>
            <DialogTitle>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="h6">{selectedReport.title}</Typography>
                <Button startIcon={<DownloadIcon />} onClick={handleDownload} size="small">
                  Download
                </Button>
              </Box>
            </DialogTitle>
            <DialogContent dividers>
              {/* Executive Summary */}
              {selectedReport.executive_summary && (
                <Paper sx={{ p: 2, mb: 2, bgcolor: 'primary.light', color: 'primary.contrastText', borderRadius: 2 }}>
                  <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Executive Summary</Typography>
                  <Typography variant="body2">{selectedReport.executive_summary}</Typography>
                </Paper>
              )}

              {/* Key Findings */}
              {selectedReport.key_findings?.length > 0 && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Key Findings</Typography>
                  <List dense>
                    {selectedReport.key_findings.map((finding, idx) => (
                      <ListItem key={idx}>
                        <ListItemIcon><FindInPageIcon color="warning" fontSize="small" /></ListItemIcon>
                        <ListItemText primary={finding} />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}

              {/* Recommendations */}
              {selectedReport.recommendations?.length > 0 && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Recommendations</Typography>
                  <List dense>
                    {selectedReport.recommendations.map((rec, idx) => (
                      <ListItem key={idx}>
                        <ListItemIcon><RecommendIcon color="success" fontSize="small" /></ListItemIcon>
                        <ListItemText primary={rec} />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}

              <Divider sx={{ my: 2 }} />

              {/* Full Report Content */}
              <Typography variant="subtitle1" fontWeight="bold" gutterBottom>Full Report</Typography>
              <Paper sx={{ p: 2, bgcolor: 'grey.50', whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.85rem', maxHeight: '500px', overflow: 'auto' }}>
                {selectedReport.content}
              </Paper>

              <AIFeedbackWidget featureType="report" responseData={selectedReport?.executive_summary} />
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setDialogOpen(false)}>Close</Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  );
};

export default AIReports;
