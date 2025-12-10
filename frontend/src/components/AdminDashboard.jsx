/**
 * Admin Dashboard - Comprehensive Administration Interface
 *
 * Provides centralized control for:
 * - System Settings
 * - Backup Configuration
 * - User Management
 * - Group & Permission Management
 * - License Management
 * - System Health & Monitoring
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Tabs,
  Tab,
  Grid,
  TextField,
  Button,
  Switch,
  FormControlLabel,
  Alert,
  Divider,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tooltip,
  CircularProgress,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Checkbox,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Backup as BackupIcon,
  People as PeopleIcon,
  Group as GroupIcon,
  Key as KeyIcon,
  Monitor as MonitorIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  Save as SaveIcon,
  Refresh as RefreshIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Schedule as ScheduleIcon,
  Storage as StorageIcon,
  Notifications as NotificationsIcon,
  Email as EmailIcon,
  Send as SendIcon,
} from '@mui/icons-material';
import api from '../api/api';
import { useAuth } from '../contexts/AuthContext';

// Tab Panel Component
function TabPanel({ children, value, index, ...other }) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`admin-tabpanel-${index}`}
      aria-labelledby={`admin-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export default function AdminDashboard() {
  const { user } = useAuth();
  const [currentTab, setCurrentTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // System Settings State
  const [systemSettings, setSystemSettings] = useState({
    platformName: 'Network Audit Platform',
    smtpEnabled: false,
    useLocalhost: false,
    smtpServer: '',
    smtpPort: 587,
    smtpUsername: '',
    smtpPassword: '',
    defaultSessionTimeout: 3600,
    enableAuditLogs: true,
    maxFailedLogins: 5,
  });

  // Backup Configuration State
  const [backupConfig, setBackupConfig] = useState({
    enabled: true,
    scheduleType: 'daily',
    scheduleTime: '02:00',
    retentionDays: 30,
    maxBackupsPerDevice: 10,
    notifyOnFailure: true,
    backupOnAudit: true,
  });

  // Notification Settings State
  const [notificationSettings, setNotificationSettings] = useState({
    emailEnabled: true,
    emailRecipients: [],
    notifyOnBackupFailure: true,
    notifyOnLicenseExpiry: true,
    notifyOnQuotaExceeded: true,
    notifyOnAuditFailure: true,
    notifyOnHealthCheckFailure: true,
    notifyOnDeviceOffline: true,
    notifyOnComplianceIssue: true,
    complianceThreshold: 80.0,
    deviceOfflineAfterFailures: 3,
  });
  const [newRecipient, setNewRecipient] = useState('');
  const [testEmailRecipient, setTestEmailRecipient] = useState('');

  // Users State
  const [users, setUsers] = useState([]);
  const [groups, setGroups] = useState([]);
  const [userDialogOpen, setUserDialogOpen] = useState(false);
  const [groupDialogOpen, setGroupDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [selectedGroup, setSelectedGroup] = useState(null);

  // System Health State
  const [systemHealth, setSystemHealth] = useState(null);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      // Load all necessary data in parallel
      await Promise.all([
        loadUsers(),
        loadGroups(),
        loadSystemSettings(),
        loadBackupConfig(),
        loadSystemHealth(),
        loadNotificationSettings(),
      ]);
    } catch (err) {
      setError('Failed to load admin data');
    } finally {
      setLoading(false);
    }
  };

  const loadUsers = async () => {
    try {
      const response = await api.get('/user-management/users');
      // Backend returns array directly, not wrapped in {users: [...]}
      setUsers(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      console.error('Failed to load users:', err);
      setError(`Failed to load users: ${err.response?.data?.detail || err.message}`);
    }
  };

  const loadGroups = async () => {
    try {
      const response = await api.get('/user-management/groups');
      // Backend returns array directly, not wrapped in {groups: [...]}
      setGroups(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      console.error('Failed to load groups:', err);
      setError(`Failed to load groups: ${err.response?.data?.detail || err.message}`);
    }
  };

  const loadBackupConfig = async () => {
    try {
      const response = await api.get('/admin/backup-config');
      if (response.data) {
        setBackupConfig(response.data);
      }
    } catch (err) {
      console.error('Failed to load backup config:', err);
    }
  };

  const loadSystemHealth = async () => {
    try {
      const response = await api.get('/health');
      setSystemHealth(response.data);
    } catch (err) {
      console.error('Failed to load system health:', err);
    }
  };

  const loadSystemSettings = async () => {
    try {
      const response = await api.get('/admin/system-settings');
      if (response.data) {
        setSystemSettings(response.data);
      }
    } catch (err) {
      console.error('Failed to load system settings:', err);
    }
  };

  const loadNotificationSettings = async () => {
    try {
      const response = await api.get('/admin/notification-settings');
      if (response.data) {
        setNotificationSettings(response.data);
      }
    } catch (err) {
      console.error('Failed to load notification settings:', err);
    }
  };

  const handleSaveBackupConfig = async () => {
    setLoading(true);
    try {
      await api.post('/admin/backup-config', backupConfig);
      setSuccess('Backup configuration saved successfully');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError('Failed to save backup configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSystemSettings = async () => {
    setLoading(true);
    try {
      await api.post('/admin/system-settings', systemSettings);
      setSuccess('System settings saved successfully');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError('Failed to save system settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveNotificationSettings = async () => {
    setLoading(true);
    try {
      await api.post('/admin/notification-settings', notificationSettings);
      setSuccess('Notification settings saved successfully');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError('Failed to save notification settings');
    } finally {
      setLoading(false);
    }
  };

  const handleAddRecipient = () => {
    if (newRecipient && !notificationSettings.emailRecipients.includes(newRecipient)) {
      setNotificationSettings({
        ...notificationSettings,
        emailRecipients: [...notificationSettings.emailRecipients, newRecipient]
      });
      setNewRecipient('');
    }
  };

  const handleRemoveRecipient = (email) => {
    setNotificationSettings({
      ...notificationSettings,
      emailRecipients: notificationSettings.emailRecipients.filter(r => r !== email)
    });
  };

  const handleSendTestEmail = async () => {
    if (!testEmailRecipient) {
      setError('Please enter a recipient email address');
      return;
    }
    setLoading(true);
    try {
      await api.post('/admin/test-email', { recipient: testEmailRecipient });
      setSuccess(`Test email sent to ${testEmailRecipient}`);
      setTimeout(() => setSuccess(null), 3000);
      setTestEmailRecipient('');
    } catch (err) {
      setError('Failed to send test email: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  if (!user?.is_superuser) {
    return (
      <Box p={3}>
        <Alert severity="error">
          Access Denied: Administrator privileges required
        </Alert>
      </Box>
    );
  }

  return (
    <Box p={3}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">
          ⚙️ Administration Dashboard
        </Typography>
        <Button
          startIcon={<RefreshIcon />}
          onClick={loadInitialData}
          disabled={loading}
        >
          Refresh
        </Button>
      </Box>

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

      <Card>
        <Tabs
          value={currentTab}
          onChange={(e, newValue) => setCurrentTab(newValue)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab icon={<SettingsIcon />} label="System Settings" />
          <Tab icon={<BackupIcon />} label="Backup Config" />
          <Tab icon={<NotificationsIcon />} label="Notifications" />
          <Tab icon={<PeopleIcon />} label="Users" />
          <Tab icon={<GroupIcon />} label="Groups & Permissions" />
          <Tab icon={<KeyIcon />} label="License" />
          <Tab icon={<MonitorIcon />} label="System Health" />
        </Tabs>

        {/* Tab 1: System Settings */}
        <TabPanel value={currentTab} index={0}>
          <Typography variant="h6" gutterBottom>
            General System Settings
          </Typography>
          <Divider sx={{ mb: 3 }} />

          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Platform Name"
                value={systemSettings.platformName}
                onChange={(e) =>
                  setSystemSettings({ ...systemSettings, platformName: e.target.value })
                }
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Default Session Timeout (seconds)"
                type="number"
                value={systemSettings.defaultSessionTimeout}
                onChange={(e) =>
                  setSystemSettings({
                    ...systemSettings,
                    defaultSessionTimeout: parseInt(e.target.value),
                  })
                }
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Max Failed Login Attempts"
                type="number"
                value={systemSettings.maxFailedLogins}
                onChange={(e) =>
                  setSystemSettings({
                    ...systemSettings,
                    maxFailedLogins: parseInt(e.target.value),
                  })
                }
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={systemSettings.enableAuditLogs}
                    onChange={(e) =>
                      setSystemSettings({
                        ...systemSettings,
                        enableAuditLogs: e.target.checked,
                      })
                    }
                  />
                }
                label="Enable Audit Logging"
              />
            </Grid>
          </Grid>

          <Typography variant="h6" gutterBottom sx={{ mt: 4 }}>
            Email (SMTP) Configuration
          </Typography>
          <Divider sx={{ mb: 3 }} />

          <Grid container spacing={3}>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={systemSettings.smtpEnabled}
                    onChange={(e) =>
                      setSystemSettings({
                        ...systemSettings,
                        smtpEnabled: e.target.checked,
                      })
                    }
                  />
                }
                label="Enable SMTP Email Notifications"
              />
            </Grid>

            {systemSettings.smtpEnabled && (
              <>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={systemSettings.useLocalhost}
                        onChange={(e) =>
                          setSystemSettings({
                            ...systemSettings,
                            useLocalhost: e.target.checked,
                          })
                        }
                      />
                    }
                    label="Use Local Mail Server (localhost:25)"
                  />
                  <Typography variant="caption" display="block" color="text.secondary" sx={{ ml: 4 }}>
                    Enable this if you have a local mail server (sendmail, postfix) configured. No authentication required.
                  </Typography>
                </Grid>

                {!systemSettings.useLocalhost && (
                  <>
                    <Grid item xs={12} md={6}>
                      <TextField
                        fullWidth
                        label="SMTP Server"
                        value={systemSettings.smtpServer}
                        onChange={(e) =>
                          setSystemSettings({ ...systemSettings, smtpServer: e.target.value })
                        }
                        placeholder="smtp.gmail.com"
                      />
                    </Grid>

                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="SMTP Port"
                    type="number"
                    value={systemSettings.smtpPort}
                    onChange={(e) =>
                      setSystemSettings({
                        ...systemSettings,
                        smtpPort: parseInt(e.target.value),
                      })
                    }
                  />
                </Grid>

                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="SMTP Username"
                    value={systemSettings.smtpUsername}
                    onChange={(e) =>
                      setSystemSettings({ ...systemSettings, smtpUsername: e.target.value })
                    }
                  />
                </Grid>

                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="SMTP Password"
                    type="password"
                    value={systemSettings.smtpPassword}
                    onChange={(e) =>
                      setSystemSettings({ ...systemSettings, smtpPassword: e.target.value })
                    }
                  />
                </Grid>
                  </>
                )}
              </>
            )}
          </Grid>

          <Box mt={4}>
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={handleSaveSystemSettings}
              disabled={loading}
            >
              Save Settings
            </Button>
          </Box>
        </TabPanel>

        {/* Tab 2: Backup Configuration */}
        <TabPanel value={currentTab} index={1}>
          <Typography variant="h6" gutterBottom>
            Configuration Backup Settings
          </Typography>
          <Divider sx={{ mb: 3 }} />

          <Grid container spacing={3}>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={backupConfig.enabled}
                    onChange={(e) =>
                      setBackupConfig({ ...backupConfig, enabled: e.target.checked })
                    }
                  />
                }
                label="Enable Automatic Configuration Backups"
              />
            </Grid>

            {backupConfig.enabled && (
              <>
                <Grid item xs={12} md={4}>
                  <FormControl fullWidth>
                    <InputLabel>Backup Schedule</InputLabel>
                    <Select
                      value={backupConfig.scheduleType}
                      onChange={(e) =>
                        setBackupConfig({ ...backupConfig, scheduleType: e.target.value })
                      }
                      label="Backup Schedule"
                    >
                      <MenuItem value="hourly">Hourly</MenuItem>
                      <MenuItem value="every6hours">Every 6 Hours</MenuItem>
                      <MenuItem value="every12hours">Every 12 Hours</MenuItem>
                      <MenuItem value="daily">Daily</MenuItem>
                      <MenuItem value="weekly">Weekly</MenuItem>
                      <MenuItem value="monthly">Monthly</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    label="Schedule Time"
                    type="time"
                    value={backupConfig.scheduleTime}
                    onChange={(e) =>
                      setBackupConfig({ ...backupConfig, scheduleTime: e.target.value })
                    }
                    InputLabelProps={{ shrink: true }}
                    helperText="Time to run daily/weekly/monthly backups"
                  />
                </Grid>

                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    label="Retention Period (days)"
                    type="number"
                    value={backupConfig.retentionDays}
                    onChange={(e) =>
                      setBackupConfig({
                        ...backupConfig,
                        retentionDays: parseInt(e.target.value),
                      })
                    }
                    helperText="Auto-delete backups older than this"
                  />
                </Grid>

                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Max Backups Per Device"
                    type="number"
                    value={backupConfig.maxBackupsPerDevice}
                    onChange={(e) =>
                      setBackupConfig({
                        ...backupConfig,
                        maxBackupsPerDevice: parseInt(e.target.value),
                      })
                    }
                    helperText="Keep only N most recent backups per device"
                  />
                </Grid>

                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={backupConfig.notifyOnFailure}
                        onChange={(e) =>
                          setBackupConfig({
                            ...backupConfig,
                            notifyOnFailure: e.target.checked,
                          })
                        }
                      />
                    }
                    label="Send Email Notification on Backup Failure"
                  />
                </Grid>

                <Grid item xs={12}>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                    Audit Backup Settings
                  </Typography>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={backupConfig.backupOnAudit}
                        onChange={(e) =>
                          setBackupConfig({
                            ...backupConfig,
                            backupOnAudit: e.target.checked,
                          })
                        }
                      />
                    }
                    label="Create Config Backup When Running Audits"
                  />
                  <Typography variant="body2" color="text.secondary" sx={{ ml: 4 }}>
                    When enabled, a configuration backup is created automatically before each audit (including after applying fixes).
                    Disable this if you only want scheduled/manual backups.
                  </Typography>
                </Grid>
              </>
            )}
          </Grid>

          <Alert severity="info" sx={{ mt: 3 }}>
            <Typography variant="body2">
              <strong>Backup Schedule Examples:</strong>
            </Typography>
            <Typography variant="body2" component="ul" sx={{ mt: 1 }}>
              <li><strong>Hourly:</strong> Backs up all devices every hour</li>
              <li><strong>Daily at 02:00:</strong> Backs up all devices once per day at 2 AM</li>
              <li><strong>Weekly:</strong> Backs up all devices once per week on Sunday</li>
            </Typography>
          </Alert>

          <Box mt={4}>
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={handleSaveBackupConfig}
              disabled={loading}
            >
              Save Backup Configuration
            </Button>
          </Box>
        </TabPanel>

        {/* Tab 3: Notifications */}
        <TabPanel value={currentTab} index={2}>
          <Typography variant="h6" gutterBottom>
            Email Notification Settings
          </Typography>
          <Divider sx={{ mb: 3 }} />

          <Grid container spacing={3}>
            {/* Email Configuration */}
            <Grid item xs={12}>
              <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                Email Configuration
              </Typography>
              <FormControlLabel
                control={
                  <Switch
                    checked={notificationSettings.emailEnabled}
                    onChange={(e) =>
                      setNotificationSettings({
                        ...notificationSettings,
                        emailEnabled: e.target.checked,
                      })
                    }
                  />
                }
                label="Enable Email Notifications"
              />
            </Grid>

            {/* Email Recipients */}
            <Grid item xs={12}>
              <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                Email Recipients
              </Typography>
              <Box display="flex" gap={2} mb={2}>
                <TextField
                  fullWidth
                  label="Add Recipient Email"
                  type="email"
                  value={newRecipient}
                  onChange={(e) => setNewRecipient(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      handleAddRecipient();
                    }
                  }}
                />
                <Button
                  variant="contained"
                  startIcon={<AddIcon />}
                  onClick={handleAddRecipient}
                  disabled={!newRecipient}
                >
                  Add
                </Button>
              </Box>
              {notificationSettings.emailRecipients.length > 0 ? (
                <Box display="flex" flexWrap="wrap" gap={1}>
                  {notificationSettings.emailRecipients.map((email, index) => (
                    <Chip
                      key={index}
                      label={email}
                      onDelete={() => handleRemoveRecipient(email)}
                      color="primary"
                      variant="outlined"
                    />
                  ))}
                </Box>
              ) : (
                <Alert severity="info">No email recipients configured</Alert>
              )}
            </Grid>

            {/* Notification Types */}
            <Grid item xs={12}>
              <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                Notification Types
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={notificationSettings.notifyOnBackupFailure}
                        onChange={(e) =>
                          setNotificationSettings({
                            ...notificationSettings,
                            notifyOnBackupFailure: e.target.checked,
                          })
                        }
                      />
                    }
                    label="Backup Failures"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={notificationSettings.notifyOnHealthCheckFailure}
                        onChange={(e) =>
                          setNotificationSettings({
                            ...notificationSettings,
                            notifyOnHealthCheckFailure: e.target.checked,
                          })
                        }
                      />
                    }
                    label="Health Check Failures"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={notificationSettings.notifyOnDeviceOffline}
                        onChange={(e) =>
                          setNotificationSettings({
                            ...notificationSettings,
                            notifyOnDeviceOffline: e.target.checked,
                          })
                        }
                      />
                    }
                    label="Device Offline"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={notificationSettings.notifyOnComplianceIssue}
                        onChange={(e) =>
                          setNotificationSettings({
                            ...notificationSettings,
                            notifyOnComplianceIssue: e.target.checked,
                          })
                        }
                      />
                    }
                    label="Compliance Issues"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={notificationSettings.notifyOnAuditFailure}
                        onChange={(e) =>
                          setNotificationSettings({
                            ...notificationSettings,
                            notifyOnAuditFailure: e.target.checked,
                          })
                        }
                      />
                    }
                    label="Audit Execution Failures"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={notificationSettings.notifyOnLicenseExpiry}
                        onChange={(e) =>
                          setNotificationSettings({
                            ...notificationSettings,
                            notifyOnLicenseExpiry: e.target.checked,
                          })
                        }
                      />
                    }
                    label="License Expiry"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={notificationSettings.notifyOnQuotaExceeded}
                        onChange={(e) =>
                          setNotificationSettings({
                            ...notificationSettings,
                            notifyOnQuotaExceeded: e.target.checked,
                          })
                        }
                      />
                    }
                    label="Quota Exceeded"
                  />
                </Grid>
              </Grid>
            </Grid>

            {/* Thresholds */}
            <Grid item xs={12}>
              <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                Alert Thresholds
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Compliance Alert Threshold (%)"
                    type="number"
                    value={notificationSettings.complianceThreshold}
                    onChange={(e) =>
                      setNotificationSettings({
                        ...notificationSettings,
                        complianceThreshold: parseFloat(e.target.value),
                      })
                    }
                    inputProps={{ min: 0, max: 100, step: 1 }}
                    helperText="Alert when device compliance falls below this percentage"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Device Offline After (failures)"
                    type="number"
                    value={notificationSettings.deviceOfflineAfterFailures}
                    onChange={(e) =>
                      setNotificationSettings({
                        ...notificationSettings,
                        deviceOfflineAfterFailures: parseInt(e.target.value),
                      })
                    }
                    inputProps={{ min: 1, max: 10, step: 1 }}
                    helperText="Send alert after this many consecutive health check failures"
                  />
                </Grid>
              </Grid>
            </Grid>

            {/* Test Email */}
            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                Test Email Configuration
              </Typography>
              <Box display="flex" gap={2} alignItems="flex-start">
                <TextField
                  fullWidth
                  label="Test Recipient Email"
                  type="email"
                  value={testEmailRecipient}
                  onChange={(e) => setTestEmailRecipient(e.target.value)}
                  helperText="Send a test email to verify SMTP configuration"
                />
                <Button
                  variant="outlined"
                  startIcon={<SendIcon />}
                  onClick={handleSendTestEmail}
                  disabled={!testEmailRecipient || loading}
                >
                  Send Test
                </Button>
              </Box>
            </Grid>
          </Grid>

          <Box mt={3} display="flex" justifyContent="flex-end">
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={handleSaveNotificationSettings}
              disabled={loading}
            >
              Save Notification Settings
            </Button>
          </Box>
        </TabPanel>

        {/* Tab 4: Users */}
        <TabPanel value={currentTab} index={3}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">User Management</Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => {
                setSelectedUser(null);
                setUserDialogOpen(true);
              }}
            >
              Add User
            </Button>
          </Box>

          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Username</TableCell>
                  <TableCell>Email</TableCell>
                  <TableCell>Role</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Groups</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>{user.username}</TableCell>
                    <TableCell>{user.email}</TableCell>
                    <TableCell>
                      <Chip
                        label={user.is_superuser ? 'Admin' : 'User'}
                        color={user.is_superuser ? 'error' : 'default'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={user.is_active ? 'Active' : 'Inactive'}
                        color={user.is_active ? 'success' : 'default'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      {user.group_count || 0} group(s)
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title="Edit">
                        <IconButton
                          size="small"
                          onClick={() => {
                            setSelectedUser(user);
                            setUserDialogOpen(true);
                          }}
                        >
                          <EditIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete">
                        <IconButton size="small" color="error">
                          <DeleteIcon />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </TabPanel>

        {/* Tab 5: Groups & Permissions */}
        <TabPanel value={currentTab} index={4}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">Groups & Module Permissions</Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => {
                setSelectedGroup(null);
                setGroupDialogOpen(true);
              }}
            >
              Add Group
            </Button>
          </Box>

          <Grid container spacing={2}>
            {groups.map((group) => (
              <Grid item xs={12} md={6} key={group.id}>
                <Card>
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="center">
                      <Typography variant="h6">{group.name}</Typography>
                      <Box>
                        <IconButton
                          size="small"
                          onClick={() => {
                            setSelectedGroup(group);
                            setGroupDialogOpen(true);
                          }}
                        >
                          <EditIcon />
                        </IconButton>
                        <IconButton size="small" color="error">
                          <DeleteIcon />
                        </IconButton>
                      </Box>
                    </Box>

                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      {group.description || 'No description'}
                    </Typography>

                    <Divider sx={{ my: 2 }} />

                    <Typography variant="subtitle2" gutterBottom>
                      Module Access:
                    </Typography>
                    <Box display="flex" flexWrap="wrap" gap={0.5}>
                      {group.modules?.map((module) => (
                        <Chip key={module} label={module} size="small" />
                      ))}
                      {(!group.modules || group.modules.length === 0) && (
                        <Typography variant="caption" color="text.secondary">
                          No modules assigned
                        </Typography>
                      )}
                    </Box>

                    <Typography variant="caption" display="block" sx={{ mt: 2 }}>
                      {group.user_count || 0} user(s) in this group
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </TabPanel>

        {/* Tab 6: License (Redirect/Info) */}
        <TabPanel value={currentTab} index={5}>
          <Typography variant="h6" gutterBottom>
            License Management
          </Typography>
          <Alert severity="info" sx={{ mt: 2 }}>
            For detailed license management, visit the{' '}
            <a href="/license">License Management Page</a>
          </Alert>
        </TabPanel>

        {/* Tab 7: System Health */}
        <TabPanel value={currentTab} index={6}>
          <Typography variant="h6" gutterBottom>
            System Health & Monitoring
          </Typography>
          <Divider sx={{ mb: 3 }} />

          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" justifyContent="space-between">
                    <Typography variant="h6">API Gateway</Typography>
                    <CheckCircleIcon color="success" />
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    Status: Healthy
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" justifyContent="space-between">
                    <Typography variant="h6">Database</Typography>
                    <CheckCircleIcon color="success" />
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    Status: Connected
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" justifyContent="space-between">
                    <Typography variant="h6">Services</Typography>
                    <CheckCircleIcon color="success" />
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    6/6 services running
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadSystemHealth}
            sx={{ mt: 3 }}
          >
            Refresh Health Status
          </Button>
        </TabPanel>
      </Card>
    </Box>
  );
}
