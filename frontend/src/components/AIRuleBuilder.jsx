import React, { useState, useEffect } from 'react';
import {
  Box, Paper, Typography, TextField, Button, Card, CardContent,
  Select, MenuItem, FormControl, InputLabel, Chip, Alert, CircularProgress,
  Accordion, AccordionSummary, AccordionDetails, Grid,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import { aiAPI } from '../api/api';
import { useCanModify } from './RoleBasedAccess';

const AIRuleBuilder = () => {
  const canModify = useCanModify();
  const [description, setDescription] = useState('');
  const [vendor, setVendor] = useState('');
  const [severity, setSeverity] = useState('');
  const [category, setCategory] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [drafts, setDrafts] = useState([]);
  const [loadingDrafts, setLoadingDrafts] = useState(false);

  useEffect(() => {
    fetchDrafts();
  }, []);

  const fetchDrafts = async () => {
    setLoadingDrafts(true);
    try {
      const response = await aiAPI.getRuleDrafts();
      setDrafts(response.data);
    } catch (err) {
      console.error('Failed to fetch drafts:', err);
    } finally {
      setLoadingDrafts(false);
    }
  };

  const handleGenerate = async () => {
    if (!description.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await aiAPI.generateRule({
        description: description.trim(),
        vendor: vendor || null,
        severity: severity || null,
        category: category || null,
      });
      setResult(response.data);
      fetchDrafts();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate rule. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDraftAction = async (draftId, action) => {
    try {
      await aiAPI.actionRuleDraft(draftId, { action });
      setSuccess(`Rule ${action}d successfully!`);
      fetchDrafts();
      if (action === 'approve') setResult(null);
    } catch (err) {
      setError(err.response?.data?.detail || `Failed to ${action} draft.`);
    }
  };

  const getConfidenceColor = (score) => {
    if (score >= 0.8) return 'success';
    if (score >= 0.6) return 'warning';
    return 'error';
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, gap: 1 }}>
        <AutoFixHighIcon sx={{ fontSize: 32, color: 'primary.main' }} />
        <Typography variant="h5" fontWeight="bold">AI Rule Builder</Typography>
        <Chip label="AI-Powered" color="primary" size="small" />
      </Box>

      {error && <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>{error}</Alert>}
      {success && <Alert severity="success" onClose={() => setSuccess(null)} sx={{ mb: 2 }}>{success}</Alert>}

      {/* Rule Generation Form */}
      <Paper elevation={2} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Typography variant="h6" gutterBottom>Describe Your Compliance Check</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Describe what you want to check in plain English. The AI will generate the technical rule definition.
        </Typography>

        <TextField
          fullWidth
          multiline
          rows={3}
          placeholder='e.g., "Ensure all BGP peers have MD5 authentication enabled" or "Check that NTP is configured with at least 2 servers"'
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          sx={{ mb: 2 }}
        />

        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid item xs={12} sm={4}>
            <FormControl fullWidth size="small">
              <InputLabel>Vendor (optional)</InputLabel>
              <Select value={vendor} onChange={(e) => setVendor(e.target.value)} label="Vendor (optional)">
                <MenuItem value="">Both vendors</MenuItem>
                <MenuItem value="cisco_xr">Cisco IOS-XR</MenuItem>
                <MenuItem value="nokia_sros">Nokia SR OS</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={4}>
            <FormControl fullWidth size="small">
              <InputLabel>Severity (optional)</InputLabel>
              <Select value={severity} onChange={(e) => setSeverity(e.target.value)} label="Severity (optional)">
                <MenuItem value="">Auto-detect</MenuItem>
                <MenuItem value="critical">Critical</MenuItem>
                <MenuItem value="high">High</MenuItem>
                <MenuItem value="medium">Medium</MenuItem>
                <MenuItem value="low">Low</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={4}>
            <FormControl fullWidth size="small">
              <InputLabel>Category (optional)</InputLabel>
              <Select value={category} onChange={(e) => setCategory(e.target.value)} label="Category (optional)">
                <MenuItem value="">Auto-detect</MenuItem>
                <MenuItem value="Security">Security</MenuItem>
                <MenuItem value="Authentication">Authentication</MenuItem>
                <MenuItem value="Routing">Routing</MenuItem>
                <MenuItem value="Management">Management</MenuItem>
                <MenuItem value="Monitoring">Monitoring</MenuItem>
                <MenuItem value="Access-Control">Access Control</MenuItem>
                <MenuItem value="Encryption">Encryption</MenuItem>
              </Select>
            </FormControl>
          </Grid>
        </Grid>

        <Button
          variant="contained"
          startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <AutoFixHighIcon />}
          onClick={handleGenerate}
          disabled={!description.trim() || loading || !canModify}
          size="large"
        >
          {loading ? 'Generating Rule...' : 'Generate Rule'}
        </Button>
      </Paper>

      {/* Generated Result */}
      {result && (
        <Paper elevation={3} sx={{ p: 3, mb: 3, borderRadius: 2, border: '2px solid', borderColor: 'primary.main' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">Generated Rule</Typography>
            <Chip
              label={`Confidence: ${Math.round(result.confidence_score * 100)}%`}
              color={getConfidenceColor(result.confidence_score)}
              size="small"
            />
          </Box>

          <Card variant="outlined" sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="subtitle1" fontWeight="bold">{result.generated_rule.name}</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>{result.generated_rule.description}</Typography>
              <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
                <Chip label={result.generated_rule.severity} size="small" color={
                  result.generated_rule.severity === 'critical' ? 'error' :
                  result.generated_rule.severity === 'high' ? 'warning' : 'default'
                } />
                <Chip label={result.generated_rule.category} size="small" variant="outlined" />
                {result.generated_rule.vendors.map((v) => (
                  <Chip key={v} label={v} size="small" variant="outlined" color="info" />
                ))}
              </Box>
            </CardContent>
          </Card>

          {/* Checks Detail */}
          {result.generated_rule.checks.map((check, idx) => (
            <Accordion key={idx} variant="outlined" sx={{ mb: 1 }}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="body2" fontWeight="bold">Check {idx + 1}: {check.name}</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Typography variant="body2"><strong>Comparison:</strong> {check.comparison}</Typography>
                {check.filter_xml && (
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="caption" color="text.secondary">XML Filter:</Typography>
                    <Paper sx={{ p: 1, bgcolor: 'grey.100', fontFamily: 'monospace', fontSize: '0.75rem', overflow: 'auto' }}>
                      {check.filter_xml}
                    </Paper>
                  </Box>
                )}
                {check.xpath && (
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="caption" color="text.secondary">XPath:</Typography>
                    <Paper sx={{ p: 1, bgcolor: 'grey.100', fontFamily: 'monospace', fontSize: '0.75rem' }}>
                      {check.xpath}
                    </Paper>
                  </Box>
                )}
                {check.reference_value && (
                  <Typography variant="body2" sx={{ mt: 1 }}><strong>Expected:</strong> {check.reference_value}</Typography>
                )}
                <Typography variant="body2" color="error.main" sx={{ mt: 1 }}>{check.error_message}</Typography>
                <Typography variant="body2" color="success.main">{check.success_message}</Typography>
              </AccordionDetails>
            </Accordion>
          ))}

          <Typography variant="body2" color="text.secondary" sx={{ mt: 2, mb: 2 }}>
            <strong>AI Explanation:</strong> {result.explanation}
          </Typography>

          {canModify && (
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                variant="contained"
                color="success"
                startIcon={<CheckCircleIcon />}
                onClick={() => handleDraftAction(result.draft_id, 'approve')}
              >
                Approve & Create Rule
              </Button>
              <Button
                variant="outlined"
                color="error"
                startIcon={<CancelIcon />}
                onClick={() => handleDraftAction(result.draft_id, 'reject')}
              >
                Reject
              </Button>
            </Box>
          )}
        </Paper>
      )}

      {/* Previous Drafts */}
      <Paper elevation={2} sx={{ p: 3, borderRadius: 2 }}>
        <Typography variant="h6" gutterBottom>Rule Drafts History</Typography>
        {loadingDrafts ? (
          <CircularProgress size={24} />
        ) : drafts.length === 0 ? (
          <Typography variant="body2" color="text.secondary">No AI-generated drafts yet.</Typography>
        ) : (
          drafts.map((draft) => (
            <Card key={draft.id} variant="outlined" sx={{ mb: 1 }}>
              <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box>
                    <Typography variant="body2" fontWeight="bold">
                      {draft.generated_rule?.name || 'Unnamed Rule'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      "{draft.source_prompt?.substring(0, 80)}..."
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', gap: 0.5 }}>
                    <Chip
                      label={draft.status}
                      size="small"
                      color={
                        draft.status === 'approved' ? 'success' :
                        draft.status === 'rejected' ? 'error' : 'default'
                      }
                    />
                    <Chip
                      label={`${Math.round(draft.confidence_score * 100)}%`}
                      size="small"
                      variant="outlined"
                    />
                  </Box>
                </Box>
              </CardContent>
            </Card>
          ))
        )}
      </Paper>
    </Box>
  );
};

export default AIRuleBuilder;
