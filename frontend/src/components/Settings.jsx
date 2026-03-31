import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Switch,
  FormControlLabel,
  Select,
  MenuItem,
  TextField,
  Button,
  Divider,
  Grid,
  Alert,
  Snackbar,
  Chip,
  InputLabel,
  FormControl,
} from '@mui/material';
import {
  Brightness4,
  Brightness7,
  Notifications as NotificationsIcon,
  Speed as PerformanceIcon,
  Palette as ThemeIcon,
  Save as SaveIcon,
  RestartAlt as ResetIcon,
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';

const DEFAULT_SETTINGS = {
  dashboardRefreshInterval: 30,
  enableAutoRefresh: true,
  enableNotificationSound: false,
  enableDesktopNotifications: false,
  compactSidebar: false,
  defaultAuditView: 'all',
  pageSize: 25,
  dateFormat: 'relative',
  showAIInsights: true,
  enableCommandPalette: true,
};

const Settings = () => {
  const { user } = useAuth();
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem('nap_user_settings');
    if (stored) {
      try {
        setSettings({ ...DEFAULT_SETTINGS, ...JSON.parse(stored) });
      } catch { /* ignore */ }
    }
  }, []);

  const handleChange = (key, value) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = () => {
    localStorage.setItem('nap_user_settings', JSON.stringify(settings));
    setSaved(true);
    // Dispatch event so other components can react to settings changes
    window.dispatchEvent(new CustomEvent('nap-settings-changed', { detail: settings }));
  };

  const handleReset = () => {
    setSettings(DEFAULT_SETTINGS);
    localStorage.removeItem('nap_user_settings');
    window.dispatchEvent(new CustomEvent('nap-settings-changed', { detail: DEFAULT_SETTINGS }));
    setSaved(true);
  };

  return (
    <Box sx={{ p: 3, maxWidth: 900, mx: 'auto' }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" fontWeight="bold">
            Settings
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Customize your NAP experience
          </Typography>
        </Box>
        <Chip label={`${user?.username || 'User'} - ${user?.role || 'viewer'}`} color="primary" variant="outlined" />
      </Box>

      {/* Appearance */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box display="flex" alignItems="center" gap={1} mb={2}>
            <ThemeIcon color="primary" />
            <Typography variant="h6" fontWeight="bold">
              Appearance
            </Typography>
          </Box>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.compactSidebar}
                    onChange={(e) => handleChange('compactSidebar', e.target.checked)}
                  />
                }
                label="Compact sidebar (collapse section labels)"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth size="small">
                <InputLabel>Date format</InputLabel>
                <Select
                  value={settings.dateFormat}
                  label="Date format"
                  onChange={(e) => handleChange('dateFormat', e.target.value)}
                >
                  <MenuItem value="relative">Relative (e.g., 2h ago)</MenuItem>
                  <MenuItem value="absolute">Absolute (e.g., 2026-03-18 14:30)</MenuItem>
                  <MenuItem value="both">Both</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth size="small">
                <InputLabel>Default page size</InputLabel>
                <Select
                  value={settings.pageSize}
                  label="Default page size"
                  onChange={(e) => handleChange('pageSize', e.target.value)}
                >
                  <MenuItem value={10}>10</MenuItem>
                  <MenuItem value={25}>25</MenuItem>
                  <MenuItem value={50}>50</MenuItem>
                  <MenuItem value={100}>100</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Dashboard & Performance */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box display="flex" alignItems="center" gap={1} mb={2}>
            <PerformanceIcon color="primary" />
            <Typography variant="h6" fontWeight="bold">
              Dashboard & Performance
            </Typography>
          </Box>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.enableAutoRefresh}
                    onChange={(e) => handleChange('enableAutoRefresh', e.target.checked)}
                  />
                }
                label="Auto-refresh dashboard data"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                size="small"
                label="Refresh interval (seconds)"
                type="number"
                value={settings.dashboardRefreshInterval}
                onChange={(e) => handleChange('dashboardRefreshInterval', parseInt(e.target.value) || 30)}
                disabled={!settings.enableAutoRefresh}
                inputProps={{ min: 10, max: 300 }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth size="small">
                <InputLabel>Default audit view</InputLabel>
                <Select
                  value={settings.defaultAuditView}
                  label="Default audit view"
                  onChange={(e) => handleChange('defaultAuditView', e.target.value)}
                >
                  <MenuItem value="all">All Results</MenuItem>
                  <MenuItem value="failures">Failures Only</MenuItem>
                  <MenuItem value="critical">Critical Only</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Notifications */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box display="flex" alignItems="center" gap={1} mb={2}>
            <NotificationsIcon color="primary" />
            <Typography variant="h6" fontWeight="bold">
              Notifications
            </Typography>
          </Box>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.enableNotificationSound}
                    onChange={(e) => handleChange('enableNotificationSound', e.target.checked)}
                  />
                }
                label="Play sound on new notifications"
              />
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.enableDesktopNotifications}
                    onChange={(e) => {
                      if (e.target.checked && 'Notification' in window) {
                        Notification.requestPermission();
                      }
                      handleChange('enableDesktopNotifications', e.target.checked);
                    }}
                  />
                }
                label="Enable browser desktop notifications"
              />
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* AI Features */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box display="flex" alignItems="center" gap={1} mb={2}>
            <PerformanceIcon color="primary" />
            <Typography variant="h6" fontWeight="bold">
              AI Features
            </Typography>
          </Box>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.showAIInsights}
                    onChange={(e) => handleChange('showAIInsights', e.target.checked)}
                  />
                }
                label="Show AI insights on dashboard"
              />
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.enableCommandPalette}
                    onChange={(e) => handleChange('enableCommandPalette', e.target.checked)}
                  />
                }
                label="Enable command palette (Ctrl+K)"
              />
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Actions */}
      <Box display="flex" gap={2} justifyContent="flex-end">
        <Button variant="outlined" startIcon={<ResetIcon />} onClick={handleReset}>
          Reset to Defaults
        </Button>
        <Button variant="contained" startIcon={<SaveIcon />} onClick={handleSave}>
          Save Settings
        </Button>
      </Box>

      <Snackbar
        open={saved}
        autoHideDuration={3000}
        onClose={() => setSaved(false)}
        message="Settings saved successfully"
      />
    </Box>
  );
};

export default Settings;
