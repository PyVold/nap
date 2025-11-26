import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  Grid,
  Switch,
  FormControlLabel,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  Send,
} from '@mui/icons-material';
import { notificationsAPI } from '../api/api';

export default function Notifications() {
  const [webhooks, setWebhooks] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingWebhook, setEditingWebhook] = useState(null);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    name: '',
    webhook_url: '',
    webhook_type: 'slack',
    is_active: true,
    events: {
      audit_failure: { enabled: false, threshold: 80 },
      compliance_drop: { enabled: false, threshold: 10 },
      config_change: { enabled: false },
    },
  });

  useEffect(() => {
    fetchWebhooks();
    fetchStats();
  }, []);

  const fetchWebhooks = async () => {
    setLoading(true);
    try {
      const response = await notificationsAPI.getWebhooks();
      setWebhooks(response.data);
      setError('');
    } catch (err) {
      setError('Failed to fetch webhooks');
    }
    setLoading(false);
  };

  const fetchStats = async () => {
    try {
      const response = await notificationsAPI.getStats();
      setStats(response.data);
    } catch (err) {
      console.error('Failed to fetch stats');
    }
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      const apiEvents = {};
      if (formData.events.audit_failure.enabled) {
        apiEvents.audit_failure = { threshold: formData.events.audit_failure.threshold };
      }
      if (formData.events.compliance_drop.enabled) {
        apiEvents.compliance_drop = { threshold: formData.events.compliance_drop.threshold };
      }
      if (formData.events.config_change.enabled) {
        apiEvents.config_change = {};
      }

      const payload = {
        name: formData.name,
        webhook_url: formData.webhook_url,
        webhook_type: formData.webhook_type,
        is_active: formData.is_active,
        events: apiEvents,
      };

      if (editingWebhook) {
        await notificationsAPI.updateWebhook(editingWebhook.id, payload);
      } else {
        await notificationsAPI.createWebhook(payload);
      }

      fetchWebhooks();
      fetchStats();
      setDialogOpen(false);
      resetForm();
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save webhook');
    }
    setLoading(false);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this webhook?')) return;

    setLoading(true);
    try {
      await notificationsAPI.deleteWebhook(id);
      fetchWebhooks();
      fetchStats();
      setError('');
    } catch (err) {
      setError('Failed to delete webhook');
    }
    setLoading(false);
  };

  const handleTest = async (id) => {
    setLoading(true);
    try {
      await notificationsAPI.testWebhook(id, {
        event_type: 'test',
        data: { message: 'Test notification from Network Audit Platform' },
      });
      alert('Test notification sent successfully!');
      setError('');
    } catch (err) {
      setError('Failed to send test notification');
    }
    setLoading(false);
  };

  const resetForm = () => {
    setFormData({
      name: '',
      webhook_url: '',
      webhook_type: 'slack',
      is_active: true,
      events: {
        audit_failure: { enabled: false, threshold: 80 },
        compliance_drop: { enabled: false, threshold: 10 },
        config_change: { enabled: false },
      },
    });
    setEditingWebhook(null);
  };

  const openEditDialog = (webhook) => {
    setEditingWebhook(webhook);
    setFormData({
      name: webhook.name,
      webhook_url: webhook.webhook_url,
      webhook_type: webhook.webhook_type,
      is_active: webhook.is_active,
      events: {
        audit_failure: {
          enabled: !!webhook.events.audit_failure,
          threshold: webhook.events.audit_failure?.threshold || 80,
        },
        compliance_drop: {
          enabled: !!webhook.events.compliance_drop,
          threshold: webhook.events.compliance_drop?.threshold || 10,
        },
        config_change: {
          enabled: !!webhook.events.config_change,
        },
      },
    });
    setDialogOpen(true);
  };

  return (
    <Box sx={{ p: 3 }}>
      <Grid container spacing={3}>
        {stats && (
          <>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom>Total Webhooks</Typography>
                  <Typography variant="h4">{stats.total_webhooks}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom>Active Webhooks</Typography>
                  <Typography variant="h4">{stats.active_webhooks}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom>Notifications Sent</Typography>
                  <Typography variant="h4">{stats.total_notifications_sent}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom>Success Rate</Typography>
                  <Typography variant="h4">{stats.success_rate}%</Typography>
                </CardContent>
              </Card>
            </Grid>
          </>
        )}

        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                <Typography variant="h5">Notification Webhooks</Typography>
                <Button variant="contained" startIcon={<Add />} onClick={() => { resetForm(); setDialogOpen(true); }}>
                  Add Webhook
                </Button>
              </Box>

              {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

              <TableContainer component={Paper}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Name</TableCell>
                      <TableCell>Type</TableCell>
                      <TableCell>Events</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell align="right">Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {webhooks.length === 0 ? (
                      <TableRow><TableCell colSpan={5} align="center">No webhooks configured</TableCell></TableRow>
                    ) : (
                      webhooks.map((webhook) => (
                        <TableRow key={webhook.id}>
                          <TableCell>{webhook.name}</TableCell>
                          <TableCell><Chip label={webhook.webhook_type} size="small" /></TableCell>
                          <TableCell>
                            {Object.keys(webhook.events || {}).map((event) => (
                              <Chip key={event} label={event} size="small" sx={{ mr: 0.5 }} />
                            ))}
                          </TableCell>
                          <TableCell>
                            <Chip label={webhook.is_active ? 'Active' : 'Inactive'} color={webhook.is_active ? 'success' : 'default'} size="small" />
                          </TableCell>
                          <TableCell align="right">
                            <IconButton onClick={() => handleTest(webhook.id)} size="small" title="Test"><Send /></IconButton>
                            <IconButton onClick={() => openEditDialog(webhook)} size="small" title="Edit"><Edit /></IconButton>
                            <IconButton onClick={() => handleDelete(webhook.id)} size="small" title="Delete"><Delete /></IconButton>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingWebhook ? 'Edit Webhook' : 'Add Webhook'}</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField label="Name" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} fullWidth required />
            <TextField label="Webhook URL" value={formData.webhook_url} onChange={(e) => setFormData({ ...formData, webhook_url: e.target.value })} fullWidth required />
            <TextField select label="Webhook Type" value={formData.webhook_type} onChange={(e) => setFormData({ ...formData, webhook_type: e.target.value })} SelectProps={{ native: true }} fullWidth>
              <option value="slack">Slack</option>
              <option value="teams">Microsoft Teams</option>
              <option value="discord">Discord</option>
              <option value="generic">Generic</option>
            </TextField>
            <FormControlLabel control={<Switch checked={formData.is_active} onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })} />} label="Active" />
            <Typography variant="subtitle2" sx={{ mt: 2 }}>Events</Typography>
            <FormControlLabel control={<Switch checked={formData.events.audit_failure.enabled} onChange={(e) => setFormData({ ...formData, events: { ...formData.events, audit_failure: { ...formData.events.audit_failure, enabled: e.target.checked } } })} />} label="Audit Failure" />
            {formData.events.audit_failure.enabled && (
              <TextField label="Compliance Threshold (%)" type="number" value={formData.events.audit_failure.threshold} onChange={(e) => setFormData({ ...formData, events: { ...formData.events, audit_failure: { ...formData.events.audit_failure, threshold: parseInt(e.target.value) } } })} fullWidth size="small" />
            )}
            <FormControlLabel control={<Switch checked={formData.events.compliance_drop.enabled} onChange={(e) => setFormData({ ...formData, events: { ...formData.events, compliance_drop: { ...formData.events.compliance_drop, enabled: e.target.checked } } })} />} label="Compliance Drop" />
            {formData.events.compliance_drop.enabled && (
              <TextField label="Drop Threshold (%)" type="number" value={formData.events.compliance_drop.threshold} onChange={(e) => setFormData({ ...formData, events: { ...formData.events, compliance_drop: { ...formData.events.compliance_drop, threshold: parseInt(e.target.value) } } })} fullWidth size="small" />
            )}
            <FormControlLabel control={<Switch checked={formData.events.config_change.enabled} onChange={(e) => setFormData({ ...formData, events: { ...formData.events, config_change: { enabled: e.target.checked } } })} />} label="Configuration Change" />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSave} variant="contained" disabled={loading}>Save</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
