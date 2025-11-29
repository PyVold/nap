import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  LinearProgress,
  Alert,
  Chip,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Switch,
  FormControlLabel,
  Checkbox,
  List,
  ListItem,
  ListItemText,
  Divider,
} from '@mui/material';
import {
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Devices as DevicesIcon,
  People as PeopleIcon,
  Storage as StorageIcon,
  Extension as ExtensionIcon,
} from '@mui/icons-material';
import api from '../api/api';
import { useLicense } from '../contexts/LicenseContext';

export default function LicenseQuotaManager() {
  const { license, refetch: refetchLicense } = useLicense();
  const [quotas, setQuotas] = useState(null);
  const [availableModules, setAvailableModules] = useState([]);
  const [groups, setGroups] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [groupModuleAccess, setGroupModuleAccess] = useState({});
  const [moduleDialog, setModuleDialog] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchQuotas();
    fetchAvailableModules();
    fetchGroups();
  }, []);

  const fetchQuotas = async () => {
    try {
      const response = await api.get('/admin/license/quotas');
      setQuotas(response.data);
    } catch (err) {
      console.error('Error fetching quotas:', err);
      setError('Failed to fetch license quotas');
    }
  };

  const fetchAvailableModules = async () => {
    try {
      const response = await api.get('/admin/license/available-modules');
      setAvailableModules(response.data);
    } catch (err) {
      console.error('Error fetching available modules:', err);
      setError('Failed to fetch available modules');
    }
  };

  const fetchGroups = async () => {
    try {
      const response = await api.get('/user-management/groups');
      setGroups(response.data);
    } catch (err) {
      console.error('Error fetching groups:', err);
    }
  };

  const fetchGroupModuleAccess = async (groupId) => {
    try {
      const response = await api.get(`/admin/groups/${groupId}/module-access`);
      setGroupModuleAccess(response.data.module_access || {});
    } catch (err) {
      console.error('Error fetching group module access:', err);
      setError('Failed to fetch group module access');
    }
  };

  const handleOpenModuleDialog = async (group) => {
    setSelectedGroup(group);
    await fetchGroupModuleAccess(group.id);
    setModuleDialog(true);
  };

  const handleModuleToggle = (moduleKey) => {
    setGroupModuleAccess(prev => ({
      ...prev,
      [moduleKey]: !prev[moduleKey]
    }));
  };

  const handleSaveModuleAccess = async () => {
    if (!selectedGroup) return;

    setLoading(true);
    try {
      await api.put(`/admin/groups/${selectedGroup.id}/module-access`, {
        module_permissions: groupModuleAccess
      });
      
      setSuccess(`Module access updated for group: ${selectedGroup.name}`);
      setModuleDialog(false);
      setSelectedGroup(null);
    } catch (err) {
      console.error('Error saving module access:', err);
      setError(err.response?.data?.detail || 'Failed to save module access');
    } finally {
      setLoading(false);
    }
  };

  const getQuotaColor = (percentage) => {
    if (percentage >= 90) return 'error';
    if (percentage >= 75) return 'warning';
    return 'success';
  };

  const getQuotaStatus = (withinQuota) => {
    return withinQuota ? (
      <Chip icon={<CheckCircleIcon />} label="Within Quota" color="success" size="small" />
    ) : (
      <Chip icon={<ErrorIcon />} label="Quota Exceeded" color="error" size="small" />
    );
  };

  if (!license || !quotas) {
    return (
      <Box p={3}>
        <Alert severity="warning">
          No license information available. Please activate a license.
        </Alert>
      </Box>
    );
  }

  const devicePercentage = (quotas.devices.current / quotas.devices.max) * 100;
  const userPercentage = (quotas.users.current / quotas.users.max) * 100;
  const storagePercentage = quotas.storage.used_percentage;

  return (
    <Box>
      {error && (
        <Alert severity="error" onClose={() => setError('')} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" onClose={() => setSuccess('')} sx={{ mb: 2 }}>
          {success}
        </Alert>
      )}

      <Typography variant="h5" gutterBottom>
        License Quota Management
      </Typography>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        {/* Devices Quota */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <DevicesIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Devices</Typography>
              </Box>
              
              <Typography variant="h4" gutterBottom>
                {quotas.devices.current} / {quotas.devices.max}
              </Typography>
              
              <LinearProgress 
                variant="determinate" 
                value={Math.min(devicePercentage, 100)}
                color={getQuotaColor(devicePercentage)}
                sx={{ mb: 1, height: 8, borderRadius: 4 }}
              />
              
              <Typography variant="body2" color="textSecondary" gutterBottom>
                {quotas.devices.available_slots} slots available
              </Typography>
              
              {getQuotaStatus(quotas.devices.within_quota)}
            </CardContent>
          </Card>
        </Grid>

        {/* Users Quota */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <PeopleIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Users</Typography>
              </Box>
              
              <Typography variant="h4" gutterBottom>
                {quotas.users.current} / {quotas.users.max}
              </Typography>
              
              <LinearProgress 
                variant="determinate" 
                value={Math.min(userPercentage, 100)}
                color={getQuotaColor(userPercentage)}
                sx={{ mb: 1, height: 8, borderRadius: 4 }}
              />
              
              <Typography variant="body2" color="textSecondary" gutterBottom>
                {quotas.users.max - quotas.users.current} users remaining
              </Typography>
              
              {getQuotaStatus(quotas.users.within_quota)}
            </CardContent>
          </Card>
        </Grid>

        {/* Storage Quota */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <StorageIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Storage</Typography>
              </Box>
              
              <Typography variant="h4" gutterBottom>
                {quotas.storage.current_gb} / {quotas.storage.max_gb} GB
              </Typography>
              
              <LinearProgress 
                variant="determinate" 
                value={Math.min(storagePercentage, 100)}
                color={getQuotaColor(storagePercentage)}
                sx={{ mb: 1, height: 8, borderRadius: 4 }}
              />
              
              <Typography variant="body2" color="textSecondary" gutterBottom>
                {storagePercentage.toFixed(1)}% used
              </Typography>
              
              {getQuotaStatus(quotas.storage.within_quota)}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Module Management Section */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box display="flex" alignItems="center" mb={2}>
          <ExtensionIcon color="primary" sx={{ mr: 1 }} />
          <Typography variant="h6">Module Access Control</Typography>
        </Box>
        
        <Typography variant="body2" color="textSecondary" paragraph>
          Manage which modules are accessible to user groups based on your license tier.
          Only modules available in your {license.tier_display} tier can be granted.
        </Typography>

        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Group Name</TableCell>
                <TableCell>Description</TableCell>
                <TableCell>Active</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {groups.map(group => (
                <TableRow key={group.id}>
                  <TableCell>{group.name}</TableCell>
                  <TableCell>{group.description || '-'}</TableCell>
                  <TableCell>
                    {group.is_active ? (
                      <Chip label="Active" color="success" size="small" />
                    ) : (
                      <Chip label="Inactive" size="small" />
                    )}
                  </TableCell>
                  <TableCell align="right">
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => handleOpenModuleDialog(group)}
                    >
                      Manage Modules
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Available Modules Info */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Available Modules in Your License
        </Typography>
        
        <Grid container spacing={1}>
          {availableModules.map(module => (
            <Grid item key={module.key}>
              <Chip
                label={module.name}
                color={module.available ? 'success' : 'default'}
                icon={module.available ? <CheckCircleIcon /> : <ErrorIcon />}
                variant={module.available ? 'filled' : 'outlined'}
              />
            </Grid>
          ))}
        </Grid>
      </Paper>

      {/* Module Access Dialog */}
      <Dialog 
        open={moduleDialog} 
        onClose={() => setModuleDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Manage Module Access - {selectedGroup?.name}
        </DialogTitle>
        <DialogContent>
          <Alert severity="info" sx={{ mb: 2 }}>
            Only modules available in your license tier can be granted.
            Modules not in your tier are disabled.
          </Alert>

          <List>
            {availableModules.map(module => (
              <React.Fragment key={module.key}>
                <ListItem>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={groupModuleAccess[module.key] || false}
                        onChange={() => handleModuleToggle(module.key)}
                        disabled={!module.available}
                      />
                    }
                    label={
                      <Box>
                        <Typography variant="body1">
                          {module.name}
                        </Typography>
                        {!module.available && (
                          <Typography variant="caption" color="error">
                            Not available in current license tier
                          </Typography>
                        )}
                      </Box>
                    }
                  />
                </ListItem>
                <Divider />
              </React.Fragment>
            ))}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setModuleDialog(false)}>
            Cancel
          </Button>
          <Button 
            onClick={handleSaveModuleAccess}
            variant="contained"
            disabled={loading}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
