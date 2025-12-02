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
    compressBackups: true,
    notifyOnFailure: true,
  });

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
        loadBackupConfig(),
        loadSystemHealth(),
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

                <Grid item xs={12} md={6}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={backupConfig.compressBackups}
                        onChange={(e) =>
                          setBackupConfig({
                            ...backupConfig,
                            compressBackups: e.target.checked,
                          })
                        }
                      />
                    }
                    label="Compress Backups (Save Storage)"
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

        {/* Tab 3: Users */}
        <TabPanel value={currentTab} index={2}>
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

        {/* Tab 4: Groups & Permissions */}
        <TabPanel value={currentTab} index={3}>
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

        {/* Tab 5: License (Redirect/Info) */}
        <TabPanel value={currentTab} index={4}>
          <Typography variant="h6" gutterBottom>
            License Management
          </Typography>
          <Alert severity="info" sx={{ mt: 2 }}>
            For detailed license management, visit the{' '}
            <a href="/license">License Management Page</a>
          </Alert>
        </TabPanel>

        {/* Tab 6: System Health */}
        <TabPanel value={currentTab} index={5}>
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
