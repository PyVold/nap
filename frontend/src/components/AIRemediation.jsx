import React, { useState, useEffect } from 'react';
import {
  Box, Paper, Typography, Button, Card, CardContent, Chip, Alert, CircularProgress,
  Grid, TextField, Stepper, Step, StepLabel, StepContent, Divider,
  Dialog, DialogTitle, DialogContent, DialogActions,
} from '@mui/material';
import HealingIcon from '@mui/icons-material/Healing';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import { aiAPI } from '../api/api';
import { useCanModify } from './RoleBasedAccess';

const riskColors = {
  low: { bg: '#e8f5e9', color: '#2e7d32' },
  medium: { bg: '#fff3e0', color: '#e65100' },
  high: { bg: '#ffebee', color: '#c62828' },
};

const AIRemediation = () => {
  const canModify = useCanModify();
  const [deviceId, setDeviceId] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [plan, setPlan] = useState(null);
  const [drafts, setDrafts] = useState([]);
  const [selectedDraft, setSelectedDraft] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  useEffect(() => {
    fetchDrafts();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const fetchDrafts = async () => {
    try {
      const response = await aiAPI.getRemediationDrafts();
      setDrafts(response.data);
    } catch (err) {
      console.error('Failed to fetch drafts:', err);
    }
  };

  const handleGenerate = async () => {
    if (!deviceId) return;
    setLoading(true);
    setError(null);
    setPlan(null);

    try {
      const response = await aiAPI.generateRemediation({
        device_id: parseInt(deviceId),
        description: description || null,
      });
      setPlan(response.data);
      fetchDrafts();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate remediation plan.');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (draftId) => {
    try {
      await aiAPI.actionRemediationDraft(draftId, { action: 'approve' });
      setSuccess('Remediation plan approved! Ready for execution via workflow engine.');
      fetchDrafts();
      setPlan(null);
    } catch (err) {
      setError('Failed to approve plan.');
    }
  };

  const handleReject = async (draftId) => {
    try {
      await aiAPI.actionRemediationDraft(draftId, { action: 'reject' });
      setSuccess('Plan rejected.');
      fetchDrafts();
      setPlan(null);
    } catch (err) {
      setError('Failed to reject plan.');
    }
  };

  const viewDraft = (draft) => {
    setSelectedDraft(draft);
    setDialogOpen(true);
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, gap: 1 }}>
        <HealingIcon sx={{ fontSize: 32, color: 'primary.main' }} />
        <Typography variant="h5" fontWeight="bold">AI Remediation Advisor</Typography>
        <Chip label="AI-Powered" color="primary" size="small" />
        <Chip label="Human-in-the-Loop" color="warning" size="small" variant="outlined" />
      </Box>

      {error && <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>{error}</Alert>}
      {success && <Alert severity="success" onClose={() => setSuccess(null)} sx={{ mb: 2 }}>{success}</Alert>}

      {/* Generation Form */}
      <Paper elevation={2} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Typography variant="h6" gutterBottom>Generate Remediation Plan</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          AI will analyze the device, its audit findings, and config to generate a safe remediation plan.
          All plans require human approval before execution.
        </Typography>

        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid item xs={12} sm={4}>
            <TextField
              fullWidth size="small" label="Device ID" type="number"
              value={deviceId} onChange={(e) => setDeviceId(e.target.value)}
            />
          </Grid>
          <Grid item xs={12} sm={8}>
            <TextField
              fullWidth size="small" label="Issue Description (optional)"
              placeholder="e.g., BGP authentication missing on PE router"
              value={description} onChange={(e) => setDescription(e.target.value)}
            />
          </Grid>
        </Grid>

        <Button
          variant="contained"
          startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <HealingIcon />}
          onClick={handleGenerate}
          disabled={!deviceId || loading || !canModify}
          size="large"
        >
          {loading ? 'Generating Plan...' : 'Generate Remediation Plan'}
        </Button>
      </Paper>

      {/* Generated Plan */}
      {plan && (
        <Paper elevation={3} sx={{ p: 3, mb: 3, borderRadius: 2, border: '2px solid', borderColor: 'warning.main' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Box>
              <Typography variant="h6">Remediation Plan for {plan.plan.device_name}</Typography>
              <Typography variant="body2" color="text.secondary">{plan.plan.finding_summary}</Typography>
            </Box>
            <Chip
              label={`Confidence: ${Math.round(plan.confidence_score * 100)}%`}
              color={plan.confidence_score >= 0.7 ? 'success' : 'warning'}
            />
          </Box>

          {/* Warnings */}
          {plan.plan.warnings?.length > 0 && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              <strong>Warnings:</strong>
              <ul style={{ margin: '4px 0', paddingLeft: '20px' }}>
                {plan.plan.warnings.map((w, idx) => <li key={idx}>{w}</li>)}
              </ul>
            </Alert>
          )}

          {/* Prerequisites */}
          {plan.plan.prerequisites?.length > 0 && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle2" fontWeight="bold">Prerequisites:</Typography>
              {plan.plan.prerequisites.map((p, idx) => (
                <Chip key={idx} label={p} size="small" sx={{ mr: 0.5, mb: 0.5 }} />
              ))}
            </Box>
          )}

          {/* Steps */}
          <Stepper orientation="vertical" activeStep={-1}>
            {plan.plan.steps.map((step) => {
              const risk = riskColors[step.risk_level] || riskColors.medium;
              return (
                <Step key={step.step_number} active expanded>
                  <StepLabel>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography fontWeight="bold">{step.description}</Typography>
                      <Chip label={step.risk_level} size="small" sx={{ bgcolor: risk.bg, color: risk.color }} />
                      <Chip label={step.command_type} size="small" variant="outlined" />
                    </Box>
                  </StepLabel>
                  <StepContent>
                    {step.command && (
                      <Paper sx={{ p: 1.5, bgcolor: 'grey.900', color: 'grey.100', fontFamily: 'monospace', fontSize: '0.85rem', mb: 1, borderRadius: 1 }}>
                        $ {step.command}
                      </Paper>
                    )}
                    {step.verification && (
                      <Typography variant="caption" color="text.secondary">
                        Verify: <code>{step.verification}</code>
                      </Typography>
                    )}
                    {step.rollback_command && (
                      <Typography variant="caption" display="block" color="warning.main">
                        Rollback: <code>{step.rollback_command}</code>
                      </Typography>
                    )}
                  </StepContent>
                </Step>
              );
            })}
          </Stepper>

          {/* Risk Assessment */}
          <Divider sx={{ my: 2 }} />
          <Typography variant="subtitle2" fontWeight="bold">Risk Assessment:</Typography>
          <Typography variant="body2" sx={{ mb: 1 }}>{plan.plan.risk_assessment}</Typography>
          <Typography variant="subtitle2" fontWeight="bold">Estimated Impact:</Typography>
          <Typography variant="body2" sx={{ mb: 1 }}>{plan.plan.estimated_impact}</Typography>
          <Typography variant="subtitle2" fontWeight="bold">Rollback Plan:</Typography>
          <Typography variant="body2" sx={{ mb: 2 }}>{plan.plan.rollback_plan}</Typography>

          {/* Actions */}
          {canModify && (
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button variant="contained" color="success" startIcon={<CheckCircleIcon />}
                onClick={() => handleApprove(plan.draft_id)}>
                Approve Plan
              </Button>
              <Button variant="outlined" color="error" startIcon={<CancelIcon />}
                onClick={() => handleReject(plan.draft_id)}>
                Reject
              </Button>
            </Box>
          )}
        </Paper>
      )}

      {/* Drafts History */}
      <Paper elevation={2} sx={{ p: 3, borderRadius: 2 }}>
        <Typography variant="h6" gutterBottom>Remediation Drafts</Typography>
        {drafts.length === 0 ? (
          <Typography variant="body2" color="text.secondary">No remediation drafts yet.</Typography>
        ) : (
          drafts.map((draft) => (
            <Card key={draft.id} variant="outlined" sx={{ mb: 1, cursor: 'pointer' }} onClick={() => viewDraft(draft)}>
              <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box>
                    <Typography variant="body2" fontWeight="bold">
                      Device #{draft.device_id} - {draft.generated_plan?.finding_summary?.substring(0, 60) || 'Remediation Plan'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {draft.generated_plan?.steps?.length || 0} steps | {draft.created_at ? new Date(draft.created_at).toLocaleString() : ''}
                    </Typography>
                  </Box>
                  <Chip
                    label={draft.status}
                    size="small"
                    color={draft.status === 'approved' ? 'success' : draft.status === 'rejected' ? 'error' : 'warning'}
                  />
                </Box>
              </CardContent>
            </Card>
          ))
        )}
      </Paper>

      {/* Draft Detail Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
        {selectedDraft && (
          <>
            <DialogTitle>Remediation Plan Details</DialogTitle>
            <DialogContent>
              <Paper sx={{ p: 2, bgcolor: 'grey.50', fontFamily: 'monospace', fontSize: '0.8rem', whiteSpace: 'pre-wrap', maxHeight: 400, overflow: 'auto' }}>
                {JSON.stringify(selectedDraft.generated_plan, null, 2)}
              </Paper>
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

export default AIRemediation;
