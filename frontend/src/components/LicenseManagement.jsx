import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Alert,
  Grid,
  Chip,
  LinearProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  IconButton,
  Tooltip,
  Paper,
  CircularProgress
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import InfoIcon from '@mui/icons-material/Info';
import KeyIcon from '@mui/icons-material/Key';
import UpgradeIcon from '@mui/icons-material/Upgrade';
import RefreshIcon from '@mui/icons-material/Refresh';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import WarningIcon from '@mui/icons-material/Warning';
import api from '../api/api';

export default function LicenseManagement() {
  const [license, setLicense] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activateDialogOpen, setActivateDialogOpen] = useState(false);
  const [newLicenseKey, setNewLicenseKey] = useState('');
  const [activating, setActivating] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    console.log('[LicenseManagement] Component mounted, fetching license status');
    fetchLicenseStatus();
  }, []);

  const fetchLicenseStatus = async () => {
    console.log('[LicenseManagement] Fetching license status...');
    setLoading(true);
    try {
      const response = await api.get('/license/status');
      console.log('[LicenseManagement] License status received:', response.data);
      setLicense(response.data);
      setError(null);
    } catch (err) {
      console.error('[LicenseManagement] Error fetching license:', err);
      if (err.response?.status === 404) {
        // No license activated
        console.log('[LicenseManagement] No license found (404)');
        setLicense(null);
      } else {
        console.error('[LicenseManagement] Failed to fetch license:', err.message);
        setError('Failed to fetch license status');
      }
    } finally {
      setLoading(false);
      console.log('[LicenseManagement] Loading complete');
    }
  };

  const handleActivateLicense = async () => {
    if (!newLicenseKey.trim()) return;

    setActivating(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await api.post('/license/activate', {
        license_key: newLicenseKey.trim()
      });

      setSuccess(response.data.message || 'License activated successfully!');
      setActivateDialogOpen(false);
      setNewLicenseKey('');
      
      // Refresh license status
      setTimeout(() => {
        fetchLicenseStatus();
        setSuccess(null);
      }, 2000);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'object') {
        setError(detail.message || 'License activation failed');
      } else {
        setError(detail || 'License activation failed');
      }
    } finally {
      setActivating(false);
    }
  };

  const handleDeactivateLicense = async () => {
    if (!window.confirm('Are you sure you want to deactivate the current license?')) {
      return;
    }

    try {
      await api.post('/license/deactivate');
      setSuccess('License deactivated');
      fetchLicenseStatus();
    } catch (err) {
      setError('Failed to deactivate license');
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setSuccess('Copied to clipboard!');
    setTimeout(() => setSuccess(null), 2000);
  };

  // Module definitions with descriptions
  const moduleDefinitions = {
    devices: {
      name: 'Device Management',
      description: 'Add, edit, and manage network devices',
      icon: '🖥️'
    },
    manual_audits: {
      name: 'Manual Audits',
      description: 'Run compliance audits on-demand',
      icon: '🔍'
    },
    scheduled_audits: {
      name: 'Scheduled Audits',
      description: 'Automate audits with cron scheduling',
      icon: '⏰'
    },
    basic_rules: {
      name: 'Basic Audit Rules',
      description: 'Create custom compliance rules',
      icon: '📋'
    },
    rule_templates: {
      name: 'Rule Templates',
      description: 'Pre-built compliance frameworks (CIS, PCI-DSS, NIST)',
      icon: '📚'
    },
    api_access: {
      name: 'API Access',
      description: 'RESTful API for integrations',
      icon: '🔌'
    },
    config_backups: {
      name: 'Config Backups',
      description: 'Automatic configuration versioning',
      icon: '💾'
    },
    drift_detection: {
      name: 'Drift Detection',
      description: 'Detect configuration changes and drift',
      icon: '🎯'
    },
    webhooks: {
      name: 'Webhook Notifications',
      description: 'Slack, Teams, Discord integrations',
      icon: '🔔'
    },
    health_checks: {
      name: 'Health Monitoring',
      description: 'Device health and connectivity checks',
      icon: '❤️'
    },
    device_groups: {
      name: 'Device Groups',
      description: 'Organize devices into logical groups',
      icon: '📁'
    },
    discovery: {
      name: 'Device Discovery',
      description: 'Automatic network device discovery',
      icon: '🔎'
    },
    workflow_automation: {
      name: 'Workflow Automation',
      description: 'Visual workflow builder and auto-remediation',
      icon: '⚙️'
    },
    topology: {
      name: 'Network Topology',
      description: 'Visual topology maps and LLDP/CDP discovery',
      icon: '🗺️'
    },
    ai_features: {
      name: 'AI-Powered Features',
      description: 'Anomaly detection and compliance forecasting',
      icon: '🤖'
    },
    integrations: {
      name: 'Advanced Integrations',
      description: 'NetBox, Git, Ansible, ServiceNow',
      icon: '🔗'
    },
    sso: {
      name: 'SSO & SAML',
      description: 'Single Sign-On and enterprise authentication',
      icon: '🔐'
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (!license) {
    return <NoLicenseView onActivate={() => setActivateDialogOpen(true)} />;
  }

  const deviceUsage = license.quotas?.devices?.max >= 999999 
    ? 0 
    : (license.quotas?.devices?.percentage || 0);
  
  const userUsage = license.quotas?.users?.max >= 999999
    ? 0
    : (license.quotas?.users?.percentage || 0);

  const isUnlimited = license.quotas?.devices?.max >= 999999;

  // Get all possible modules
  const allModules = Object.keys(moduleDefinitions);
  const enabledModules = license.enabled_modules?.includes('all') 
    ? allModules 
    : (license.enabled_modules || []);

  return (
    <Box p={3}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">
          License Management
        </Typography>
        <Box>
          <Tooltip title="Refresh">
            <IconButton onClick={fetchLicenseStatus} sx={{ mr: 1 }}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Button
            variant="outlined"
            startIcon={<KeyIcon />}
            onClick={() => setActivateDialogOpen(true)}
            sx={{ mr: 1 }}
          >
            Change License
          </Button>
        </Box>
      </Box>

      {/* License Warning Banner - shows when license is invalid/expired */}
      {license && !license.valid && (
        <Alert severity="error" icon={<WarningIcon />} sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            License {license.days_until_expiry <= 0 ? 'Expired' : 'Invalid'}
          </Typography>
          <Typography variant="body2">
            {license.days_until_expiry <= 0
              ? `Your license expired ${Math.abs(license.days_until_expiry)} days ago. All modules are now locked.`
              : 'Your license is invalid or corrupted. All modules are locked.'}
            {' '}Please activate a new license key or contact sales to renew your license.
          </Typography>
          {license.expires_at && (
            <Typography variant="caption" display="block" sx={{ mt: 1 }}>
              Original expiry date: {new Date(license.expires_at).toLocaleDateString()}
            </Typography>
          )}
        </Alert>
      )}

      {/* Alert Messages */}
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

      {/* Expiring Soon Warning */}
      {license.days_until_expiry !== undefined && license.days_until_expiry < 30 && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          ⚠️ Your license expires in <strong>{license.days_until_expiry} days</strong> on{' '}
          {new Date(license.expires_at).toLocaleDateString()}.
          Please contact sales to renew: <a href="mailto:sales@yourcompany.com">sales@yourcompany.com</a>
        </Alert>
      )}

      {/* License Not Valid */}
      {!license.valid && (
        <Alert severity="error" sx={{ mb: 3 }}>
          ❌ Your license is <strong>expired or invalid</strong>.
          Please contact sales to renew or activate a new license.
        </Alert>
      )}

      {/* License Overview */}
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Current Plan
              </Typography>
              <Chip
                label={license.tier.toUpperCase()}
                color="primary"
                size="large"
                sx={{ mt: 1, fontSize: '1rem', fontWeight: 'bold' }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Status
              </Typography>
              <Chip
                label={license.valid ? 'ACTIVE' : 'EXPIRED'}
                color={license.valid ? 'success' : 'error'}
                size="large"
                sx={{ mt: 1, fontSize: '1rem', fontWeight: 'bold' }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Expires In
              </Typography>
              <Typography
                variant="h4"
                color={(license.days_until_expiry < 30) ? 'error.main' : 'text.primary'}
                sx={{ mt: 1 }}
              >
                {license.days_until_expiry || 0} days
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {new Date(license.expires_at).toLocaleDateString()}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Licensed To
              </Typography>
              <Typography variant="body1" sx={{ mt: 1, fontWeight: 500 }}>
                {license.customer_name}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Usage Quotas */}
      <Typography variant="h5" gutterBottom sx={{ mt: 4, mb: 2 }}>
        Usage & Quotas
      </Typography>

      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Devices
              </Typography>
              <Box display="flex" alignItems="baseline" mb={1}>
                <Typography variant="h3">{license.quotas?.devices?.current || 0}</Typography>
                <Typography variant="h6" color="text.secondary" ml={1}>
                  / {isUnlimited ? '∞' : license.quotas?.devices?.max || 0}
                </Typography>
              </Box>
              {!isUnlimited && (
                <>
                  <LinearProgress
                    variant="determinate"
                    value={Math.min(deviceUsage, 100)}
                    color={deviceUsage > 80 ? 'warning' : 'primary'}
                    sx={{ height: 8, borderRadius: 4, mb: 1 }}
                  />
                  <Typography variant="caption" color="text.secondary">
                    {deviceUsage.toFixed(1)}% used
                  </Typography>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Users
              </Typography>
              <Box display="flex" alignItems="baseline" mb={1}>
                <Typography variant="h3">{license.quotas?.users?.current || 0}</Typography>
                <Typography variant="h6" color="text.secondary" ml={1}>
                  / {isUnlimited ? '∞' : license.quotas?.users?.max || 0}
                </Typography>
              </Box>
              {!isUnlimited && (
                <>
                  <LinearProgress
                    variant="determinate"
                    value={Math.min(userUsage, 100)}
                    color={userUsage > 80 ? 'warning' : 'primary'}
                    sx={{ height: 8, borderRadius: 4, mb: 1 }}
                  />
                  <Typography variant="caption" color="text.secondary">
                    {userUsage.toFixed(1)}% used
                  </Typography>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Storage
              </Typography>
              <Box display="flex" alignItems="baseline" mb={1}>
                <Typography variant="h3">
                  {(license.quotas?.storage_gb?.current || 0).toFixed(1)}
                </Typography>
                <Typography variant="h6" color="text.secondary" ml={1}>
                  / {isUnlimited ? '∞' : license.quotas?.storage_gb?.max || 0} GB
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Activated Modules */}
      <Typography variant="h5" gutterBottom sx={{ mt: 4, mb: 2 }}>
        Activated Modules
      </Typography>

      <Grid container spacing={2}>
        {allModules.map((moduleKey) => {
          const module = moduleDefinitions[moduleKey];
          const isEnabled = enabledModules.includes(moduleKey);

          return (
            <Grid item xs={12} sm={6} md={4} key={moduleKey}>
              <Card
                sx={{
                  height: '100%',
                  opacity: isEnabled ? 1 : 0.5,
                  border: isEnabled ? '2px solid' : '1px solid',
                  borderColor: isEnabled ? 'success.main' : 'divider'
                }}
              >
                <CardContent>
                  <Box display="flex" alignItems="flex-start" justifyContent="space-between">
                    <Box display="flex" alignItems="center" flex={1}>
                      <Typography variant="h4" sx={{ mr: 1 }}>
                        {module.icon}
                      </Typography>
                      <Box>
                        <Typography variant="subtitle1" fontWeight="bold">
                          {module.name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {module.description}
                        </Typography>
                      </Box>
                    </Box>
                    {isEnabled ? (
                      <CheckCircleIcon color="success" />
                    ) : (
                      <CancelIcon color="disabled" />
                    )}
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          );
        })}
      </Grid>

      {/* Upgrade CTA */}
      {license.tier !== 'enterprise' && (
        <Card sx={{ mt: 4, bgcolor: 'primary.main', color: 'white' }}>
          <CardContent sx={{ p: 3 }}>
            <Grid container alignItems="center" spacing={2}>
              <Grid item xs={12} md={8}>
                <Box display="flex" alignItems="center" mb={1}>
                  <UpgradeIcon sx={{ mr: 1, fontSize: 32 }} />
                  <Typography variant="h5">
                    Unlock More Features
                  </Typography>
                </Box>
                <Typography>
                  Upgrade to a higher tier to access advanced features like workflow automation,
                  AI-powered insights, network topology, and unlimited devices.
                </Typography>
              </Grid>
              <Grid item xs={12} md={4} textAlign={{ xs: 'left', md: 'right' }}>
                <Button
                  variant="contained"
                  color="secondary"
                  size="large"
                  href="mailto:sales@yourcompany.com"
                  sx={{ fontWeight: 'bold' }}
                >
                  Contact Sales
                </Button>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* License Activation Dialog */}
      <Dialog
        open={activateDialogOpen}
        onClose={() => !activating && setActivateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Activate License</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" paragraph>
            Enter your license key below. This will replace your current license if you have one active.
          </Typography>

          <TextField
            fullWidth
            label="License Key"
            multiline
            rows={6}
            value={newLicenseKey}
            onChange={(e) => setNewLicenseKey(e.target.value)}
            placeholder="Paste your license key here..."
            disabled={activating}
            sx={{ mt: 2 }}
          />

          <Alert severity="info" sx={{ mt: 2 }}>
            <strong>Note:</strong> Your license key is provided by your sales representative.
            Contact <a href="mailto:sales@yourcompany.com">sales@yourcompany.com</a> if you need assistance.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setActivateDialogOpen(false)} disabled={activating}>
            Cancel
          </Button>
          <Button
            onClick={handleActivateLicense}
            variant="contained"
            disabled={!newLicenseKey.trim() || activating}
          >
            {activating ? <CircularProgress size={24} /> : 'Activate'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

// Component shown when no license is active
function NoLicenseView({ onActivate }) {
  return (
    <Box
      display="flex"
      justifyContent="center"
      alignItems="center"
      minHeight="80vh"
      p={3}
    >
      <Card sx={{ maxWidth: 600, textAlign: 'center', p: 4 }}>
        <CardContent>
          <KeyIcon sx={{ fontSize: 80, color: 'text.secondary', mb: 2 }} />
          
          <Typography variant="h4" gutterBottom>
            No License Activated
          </Typography>
          
          <Typography variant="body1" color="text.secondary" paragraph>
            This platform requires a valid license to operate.
            Please activate your license key to continue.
          </Typography>

          <Button
            variant="contained"
            size="large"
            startIcon={<KeyIcon />}
            onClick={onActivate}
            sx={{ mt: 2 }}
          >
            Activate License
          </Button>

          <Box mt={4} p={2} bgcolor="grey.100" borderRadius={1} textAlign="left">
            <Typography variant="subtitle2" gutterBottom>
              <strong>Need a license?</strong>
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Contact sales: <a href="mailto:sales@yourcompany.com">sales@yourcompany.com</a>
            </Typography>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
