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
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  OutlinedInput,
  Checkbox,
  ListItemText,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  Group as GroupIcon,
  Refresh,
  Search as SearchIcon,
} from '@mui/icons-material';
import InputAdornment from '@mui/material/InputAdornment';
import { deviceGroupsAPI, devicesAPI } from '../api/api';
import { useHasPermission } from './RoleBasedAccess';

const DeviceGroups = () => {
  const canCreateGroups = useHasPermission('create_groups');
  const canModifyGroups = useHasPermission('modify_groups');
  const canDeleteGroups = useHasPermission('delete_groups');
  const [groups, setGroups] = useState([]);
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [openDialog, setOpenDialog] = useState(false);
  const [editingGroup, setEditingGroup] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    device_ids: [],
  });

  const fetchGroups = async () => {
    setLoading(true);
    try {
      const response = await deviceGroupsAPI.getAll();
      setGroups(response.data);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchDevices = async () => {
    try {
      const response = await devicesAPI.getAll();
      setDevices(response.data);
    } catch (err) {
      console.error('Error fetching devices:', err);
    }
  };

  useEffect(() => {
    fetchGroups();
    fetchDevices();
  }, []);

  const handleOpenDialog = (group = null) => {
    if (group) {
      setEditingGroup(group);
      setFormData({
        name: group.name,
        description: group.description || '',
        device_ids: group.device_ids || [],
      });
    } else {
      setEditingGroup(null);
      setFormData({
        name: '',
        description: '',
        device_ids: [],
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
    if (!formData.name) {
      setError('Please enter a group name');
      return;
    }

    try {
      if (editingGroup) {
        await deviceGroupsAPI.update(editingGroup.id, formData);
        setSuccess('Device group updated successfully');
      } else {
        await deviceGroupsAPI.create(formData);
        setSuccess('Device group created successfully');
      }
      handleCloseDialog();
      fetchGroups();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this device group?')) {
      try {
        await deviceGroupsAPI.delete(id);
        setSuccess('Device group deleted successfully');
        fetchGroups();
      } catch (err) {
        setError(err.response?.data?.detail || err.message);
      }
    }
  };

  const getDeviceNamesForGroup = (deviceIds) => {
    if (!deviceIds || deviceIds.length === 0) return 'No devices';
    return devices
      .filter(d => deviceIds.includes(d.id))
      .map(d => d.hostname || d.ip_address)
      .join(', ');
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
          <GroupIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          Device Groups
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
          {canCreateGroups && (
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => handleOpenDialog()}
            >
              Add Group
            </Button>
          )}
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

      {/* Search Bar */}
      <TextField
        fullWidth
        variant="outlined"
        placeholder="Search by group name or description..."
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        sx={{ mb: 3 }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon />
            </InputAdornment>
          ),
        }}
      />

      {/* Summary Cards - Groups Overview */}
      <Grid container spacing={2} mb={3}>
        <Grid item xs={12} sm={6} md={4}>
          <Card sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
            <CardContent>
              <Typography variant="h4" color="white" fontWeight="bold">
                {groups.length}
              </Typography>
              <Typography variant="body2" color="rgba(255,255,255,0.9)">
                Total Groups
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {loading ? (
        <Box display="flex" justifyContent="center" p={4}>
          <CircularProgress />
        </Box>
      ) : (
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
              <TableCell><strong>Name</strong></TableCell>
              <TableCell><strong>Description</strong></TableCell>
              <TableCell><strong>Device Count</strong></TableCell>
              <TableCell><strong>Devices</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {groups
              .filter((group) => {
                if (!searchQuery) return true;
                const query = searchQuery.toLowerCase();
                return (
                  group.name?.toLowerCase().includes(query) ||
                  group.description?.toLowerCase().includes(query)
                );
              })
              .map((group) => (
              <TableRow key={group.id} hover>
                <TableCell>
                  <Typography variant="body2" fontWeight="bold">{group.name}</Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2" color="textSecondary">
                    {group.description || '-'}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Chip
                    label={group.device_ids?.length || 0}
                    color="primary"
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  <Typography variant="caption" sx={{ maxWidth: 400, display: 'block' }}>
                    {getDeviceNamesForGroup(group.device_ids)}
                  </Typography>
                </TableCell>
                <TableCell align="center">
                  {canModifyGroups && (
                    <IconButton
                      size="small"
                      onClick={() => handleOpenDialog(group)}
                      color="primary"
                      title="Edit"
                    >
                      <Edit />
                    </IconButton>
                  )}
                  {canDeleteGroups && (
                    <IconButton
                      size="small"
                      onClick={() => handleDelete(group.id)}
                      color="error"
                      title="Delete"
                    >
                      <Delete />
                    </IconButton>
                  )}
                  {!canModifyGroups && !canDeleteGroups && (
                    <Typography variant="body2" color="textSecondary">
                      View only
                    </Typography>
                  )}
                </TableCell>
              </TableRow>
            ))}
            {groups.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  <Typography variant="body2" color="textSecondary">
                    No device groups found. Click "Add Group" to create one.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
      )}

      {/* Add/Edit Dialog */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingGroup ? 'Edit Device Group' : 'Add New Device Group'}
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
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Select Devices</InputLabel>
                <Select
                  multiple
                  value={formData.device_ids}
                  onChange={(e) => setFormData({ ...formData, device_ids: e.target.value })}
                  input={<OutlinedInput label="Select Devices" />}
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((deviceId) => {
                        const device = devices.find(d => d.id === deviceId);
                        return (
                          <Chip
                            key={deviceId}
                            label={device ? (device.hostname || device.ip_address) : deviceId}
                            size="small"
                          />
                        );
                      })}
                    </Box>
                  )}
                >
                  {devices.map((device) => (
                    <MenuItem key={device.id} value={device.id}>
                      <Checkbox checked={formData.device_ids.indexOf(device.id) > -1} />
                      <ListItemText
                        primary={device.hostname || device.ip_address}
                        secondary={device.device_type || 'Unknown'}
                      />
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
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

export default DeviceGroups;
