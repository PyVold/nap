import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  CircularProgress,
  Paper,
  Grid,
  Switch,
  FormControlLabel,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  PlayArrow,
  Refresh,
  Schedule as ScheduleIcon,
} from '@mui/icons-material';
import { discoveryGroupsAPI } from '../api/api';

const DiscoveryGroups = () => {
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingGroup, setEditingGroup] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    subnet: '',
    excluded_ips: '',
    username: '',
    password: '',
    port: 830,
    schedule_enabled: false,
    schedule_interval: 60,
  });

  const fetchGroups = async () => {
    setLoading(true);
    try {
      const response = await discoveryGroupsAPI.getAll();
      setGroups(response.data);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGroups();
  }, []);

  const handleOpenDialog = (group = null) => {
    if (group) {
      setEditingGroup(group);
      setFormData({
        name: group.name,
        description: group.description || '',
        subnet: group.subnet,
        excluded_ips: (group.excluded_ips || []).join(', '),
        username: group.username,
        password: '',  // Don't populate password for security
        port: group.port,
        schedule_enabled: group.schedule_enabled,
        schedule_interval: group.schedule_interval,
      });
    } else {
      setEditingGroup(null);
      setFormData({
        name: '',
        description: '',
        subnet: '',
        excluded_ips: '',
        username: '',
        password: '',
        port: 830,
        schedule_enabled: false,
        schedule_interval: 60,
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingGroup(null);
    setError(null);
  };

  const handleSave = async () => {
    if (!formData.name || !formData.subnet || !formData.username) {
      setError('Please fill in all required fields');
      return;
    }

    // Parse excluded_ips from comma-separated string to array
    const excluded_ips_array = formData.excluded_ips
      ? formData.excluded_ips.split(',').map(ip => ip.trim()).filter(ip => ip.length > 0)
      : [];

    // If editing and password is empty, don't include it in the update
    const dataToSend = {
      ...formData,
      excluded_ips: excluded_ips_array
    };
    if (editingGroup && !formData.password) {
      delete dataToSend.password;
    }

    try {
      if (editingGroup) {
        await discoveryGroupsAPI.update(editingGroup.id, dataToSend);
        setSuccess('Discovery group updated successfully');
      } else {
        if (!formData.password) {
          setError('Password is required for new groups');
          return;
        }
        await discoveryGroupsAPI.create(dataToSend);
        setSuccess('Discovery group created successfully');
      }
      handleCloseDialog();
      fetchGroups();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this discovery group?')) {
      try {
        await discoveryGroupsAPI.delete(id);
        setSuccess('Discovery group deleted successfully');
        fetchGroups();
      } catch (err) {
        setError(err.response?.data?.detail || err.message);
      }
    }
  };

  const handleDiscover = async (id) => {
    try {
      const response = await discoveryGroupsAPI.discover(id);
      setSuccess(response.data.message || 'Discovery started');
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  if (loading && groups.length === 0) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" fontWeight="bold">
          <ScheduleIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          Discovery Groups
        </Typography>
        <Box>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={fetchGroups}
            disabled={loading}
            sx={{ mr: 1 }}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => handleOpenDialog()}
          >
            Add Group
          </Button>
        </Box>
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

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
              <TableCell><strong>Name</strong></TableCell>
              <TableCell><strong>Subnet</strong></TableCell>
              <TableCell><strong>Username</strong></TableCell>
              <TableCell><strong>Port</strong></TableCell>
              <TableCell><strong>Schedule</strong></TableCell>
              <TableCell><strong>Last Run</strong></TableCell>
              <TableCell><strong>Next Run</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {groups.map((group) => (
              <TableRow key={group.id} hover>
                <TableCell>
                  <Typography variant="body2" fontWeight="bold">{group.name}</Typography>
                  {group.description && (
                    <Typography variant="caption" color="textSecondary">{group.description}</Typography>
                  )}
                </TableCell>
                <TableCell>{group.subnet}</TableCell>
                <TableCell>{group.username}</TableCell>
                <TableCell>{group.port}</TableCell>
                <TableCell>
                  {group.schedule_enabled ? (
                    <Chip
                      label={`Every ${group.schedule_interval} min`}
                      color="success"
                      size="small"
                    />
                  ) : (
                    <Chip label="Disabled" size="small" />
                  )}
                </TableCell>
                <TableCell>
                  {group.last_run ? new Date(group.last_run).toLocaleString() : 'Never'}
                </TableCell>
                <TableCell>
                  {group.next_run ? new Date(group.next_run).toLocaleString() : 'N/A'}
                </TableCell>
                <TableCell align="center">
                  <IconButton
                    size="small"
                    onClick={() => handleDiscover(group.id)}
                    color="success"
                    title="Run Discovery Now"
                  >
                    <PlayArrow />
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={() => handleOpenDialog(group)}
                    color="primary"
                    title="Edit"
                  >
                    <Edit />
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={() => handleDelete(group.id)}
                    color="error"
                    title="Delete"
                  >
                    <Delete />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
            {groups.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} align="center">
                  <Typography variant="body2" color="textSecondary">
                    No discovery groups found. Click "Add Group" to create one.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Add/Edit Dialog */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingGroup ? 'Edit Discovery Group' : 'Add New Discovery Group'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Group Name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                multiline
                rows={2}
              />
            </Grid>
            <Grid item xs={12} sm={8}>
              <TextField
                fullWidth
                label="Subnet (CIDR)"
                value={formData.subnet}
                onChange={(e) => setFormData({ ...formData, subnet: e.target.value })}
                placeholder="e.g., 192.168.1.0/24"
                required
                helperText="Enter subnet in CIDR notation"
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="Port"
                value={formData.port}
                onChange={(e) => setFormData({ ...formData, port: parseInt(e.target.value) })}
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Excluded IP Addresses (Optional)"
                value={formData.excluded_ips}
                onChange={(e) => setFormData({ ...formData, excluded_ips: e.target.value })}
                placeholder="e.g., 192.168.1.1, 192.168.1.254"
                helperText="Comma-separated list of IPs to exclude from discovery"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="NETCONF Username"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="password"
                label="NETCONF Password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                required={!editingGroup}
                helperText={editingGroup ? "Leave blank to keep existing password" : "Required"}
              />
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.schedule_enabled}
                    onChange={(e) => setFormData({ ...formData, schedule_enabled: e.target.checked })}
                  />
                }
                label="Enable Scheduled Discovery"
              />
            </Grid>
            {formData.schedule_enabled && (
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  type="number"
                  label="Schedule Interval (minutes)"
                  value={formData.schedule_interval}
                  onChange={(e) => setFormData({ ...formData, schedule_interval: parseInt(e.target.value) })}
                  inputProps={{ min: 1 }}
                  helperText="How often to run discovery automatically"
                />
              </Grid>
            )}
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSave} variant="contained">
            {editingGroup ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DiscoveryGroups;
