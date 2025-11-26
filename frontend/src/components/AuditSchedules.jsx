import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
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
  Switch,
  FormControlLabel,
  RadioGroup,
  Radio,
  FormLabel,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  PlayArrow,
  Refresh,
  CalendarMonth,
} from '@mui/icons-material';
import { auditSchedulesAPI, deviceGroupsAPI, devicesAPI, rulesAPI } from '../api/api';

const AuditSchedules = () => {
  const [schedules, setSchedules] = useState([]);
  const [deviceGroups, setDeviceGroups] = useState([]);
  const [devices, setDevices] = useState([]);
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    target_type: 'all', // 'all', 'group', 'devices'
    device_group_id: null,
    device_ids: [],
    rule_ids: [],
    schedule_enabled: false,
    schedule_interval: 60,
  });

  const fetchSchedules = async () => {
    setLoading(true);
    try {
      const response = await auditSchedulesAPI.getAll();
      setSchedules(response.data);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchDeviceGroups = async () => {
    try {
      const response = await deviceGroupsAPI.getAll();
      setDeviceGroups(response.data);
    } catch (err) {
      console.error('Error fetching device groups:', err);
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

  const fetchRules = async () => {
    try {
      const response = await rulesAPI.getAll();
      setRules(response.data);
    } catch (err) {
      console.error('Error fetching rules:', err);
    }
  };

  useEffect(() => {
    fetchSchedules();
    fetchDeviceGroups();
    fetchDevices();
    fetchRules();
  }, []);

  const handleOpenDialog = (schedule = null) => {
    if (schedule) {
      setEditingSchedule(schedule);
      let targetType = 'all';
      if (schedule.device_group_id) {
        targetType = 'group';
      } else if (schedule.device_ids && schedule.device_ids.length > 0) {
        targetType = 'devices';
      }

      setFormData({
        name: schedule.name,
        description: schedule.description || '',
        target_type: targetType,
        device_group_id: schedule.device_group_id || null,
        device_ids: schedule.device_ids || [],
        rule_ids: schedule.rule_ids || [],
        schedule_enabled: schedule.schedule_enabled,
        schedule_interval: schedule.schedule_interval,
      });
    } else {
      setEditingSchedule(null);
      setFormData({
        name: '',
        description: '',
        target_type: 'all',
        device_group_id: null,
        device_ids: [],
        rule_ids: [],
        schedule_enabled: false,
        schedule_interval: 60,
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingSchedule(null);
    setError(null);
  };

  const handleSave = async () => {
    if (!formData.name) {
      setError('Please enter a schedule name');
      return;
    }

    // Prepare data based on target type
    const dataToSend = {
      name: formData.name,
      description: formData.description,
      schedule_enabled: formData.schedule_enabled,
      schedule_interval: formData.schedule_interval,
      rule_ids: formData.rule_ids.length > 0 ? formData.rule_ids : null,
    };

    if (formData.target_type === 'group') {
      dataToSend.device_group_id = formData.device_group_id;
      dataToSend.device_ids = null;
    } else if (formData.target_type === 'devices') {
      dataToSend.device_ids = formData.device_ids;
      dataToSend.device_group_id = null;
    } else {
      // All devices
      dataToSend.device_group_id = null;
      dataToSend.device_ids = null;
    }

    try {
      if (editingSchedule) {
        await auditSchedulesAPI.update(editingSchedule.id, dataToSend);
        setSuccess('Audit schedule updated successfully');
      } else {
        await auditSchedulesAPI.create(dataToSend);
        setSuccess('Audit schedule created successfully');
      }
      handleCloseDialog();
      fetchSchedules();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this audit schedule?')) {
      try {
        await auditSchedulesAPI.delete(id);
        setSuccess('Audit schedule deleted successfully');
        fetchSchedules();
      } catch (err) {
        setError(err.response?.data?.detail || err.message);
      }
    }
  };

  const handleRun = async (id) => {
    try {
      const response = await auditSchedulesAPI.run(id);
      setSuccess(response.data.message || 'Audit started');
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const getTargetDisplay = (schedule) => {
    if (schedule.device_group_id) {
      const group = deviceGroups.find(g => g.id === schedule.device_group_id);
      return group ? `Group: ${group.name}` : 'Group (deleted)';
    } else if (schedule.device_ids && schedule.device_ids.length > 0) {
      return `${schedule.device_ids.length} device(s)`;
    } else {
      return 'All devices';
    }
  };

  const getRulesDisplay = (schedule) => {
    if (!schedule.rule_ids || schedule.rule_ids.length === 0) {
      return 'All enabled rules';
    }
    return `${schedule.rule_ids.length} rule(s)`;
  };

  if (loading && schedules.length === 0) {
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
          <CalendarMonth sx={{ mr: 1, verticalAlign: 'middle' }} />
          Audit Schedules
        </Typography>
        <Box>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={fetchSchedules}
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
            Add Schedule
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
              <TableCell><strong>Target</strong></TableCell>
              <TableCell><strong>Rules</strong></TableCell>
              <TableCell><strong>Schedule</strong></TableCell>
              <TableCell><strong>Last Run</strong></TableCell>
              <TableCell><strong>Next Run</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {schedules.map((schedule) => (
              <TableRow key={schedule.id} hover>
                <TableCell>
                  <Typography variant="body2" fontWeight="bold">{schedule.name}</Typography>
                  {schedule.description && (
                    <Typography variant="caption" color="textSecondary">{schedule.description}</Typography>
                  )}
                </TableCell>
                <TableCell>{getTargetDisplay(schedule)}</TableCell>
                <TableCell>{getRulesDisplay(schedule)}</TableCell>
                <TableCell>
                  {schedule.schedule_enabled ? (
                    <Chip
                      label={`Every ${schedule.schedule_interval} min`}
                      color="success"
                      size="small"
                    />
                  ) : (
                    <Chip label="Disabled" size="small" />
                  )}
                </TableCell>
                <TableCell>
                  {schedule.last_run ? new Date(schedule.last_run).toLocaleString() : 'Never'}
                </TableCell>
                <TableCell>
                  {schedule.next_run ? new Date(schedule.next_run).toLocaleString() : 'N/A'}
                </TableCell>
                <TableCell align="center">
                  <IconButton
                    size="small"
                    onClick={() => handleRun(schedule.id)}
                    color="success"
                    title="Run Now"
                  >
                    <PlayArrow />
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={() => handleOpenDialog(schedule)}
                    color="primary"
                    title="Edit"
                  >
                    <Edit />
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={() => handleDelete(schedule.id)}
                    color="error"
                    title="Delete"
                  >
                    <Delete />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
            {schedules.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  <Typography variant="body2" color="textSecondary">
                    No audit schedules found. Click "Add Schedule" to create one.
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
          {editingSchedule ? 'Edit Audit Schedule' : 'Add New Audit Schedule'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Schedule Name"
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
              <FormControl component="fieldset">
                <FormLabel component="legend">Audit Target</FormLabel>
                <RadioGroup
                  value={formData.target_type}
                  onChange={(e) => setFormData({ ...formData, target_type: e.target.value })}
                >
                  <FormControlLabel value="all" control={<Radio />} label="All Devices" />
                  <FormControlLabel value="group" control={<Radio />} label="Device Group" />
                  <FormControlLabel value="devices" control={<Radio />} label="Specific Devices" />
                </RadioGroup>
              </FormControl>
            </Grid>

            {formData.target_type === 'group' && (
              <Grid item xs={12}>
                <FormControl fullWidth>
                  <InputLabel>Device Group</InputLabel>
                  <Select
                    value={formData.device_group_id || ''}
                    onChange={(e) => setFormData({ ...formData, device_group_id: e.target.value })}
                    label="Device Group"
                  >
                    {deviceGroups.map((group) => (
                      <MenuItem key={group.id} value={group.id}>
                        {group.name} ({group.device_ids?.length || 0} devices)
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
            )}

            {formData.target_type === 'devices' && (
              <Grid item xs={12}>
                <FormControl fullWidth>
                  <InputLabel>Select Devices</InputLabel>
                  <Select
                    multiple
                    value={formData.device_ids}
                    onChange={(e) => setFormData({ ...formData, device_ids: e.target.value })}
                    input={<OutlinedInput label="Select Devices" />}
                    renderValue={(selected) => `${selected.length} device(s) selected`}
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
            )}

            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Rules (optional)</InputLabel>
                <Select
                  multiple
                  value={formData.rule_ids}
                  onChange={(e) => setFormData({ ...formData, rule_ids: e.target.value })}
                  input={<OutlinedInput label="Rules (optional)" />}
                  renderValue={(selected) =>
                    selected.length === 0 ? 'All enabled rules' : `${selected.length} rule(s) selected`
                  }
                >
                  {rules.map((rule) => (
                    <MenuItem key={rule.id} value={rule.id}>
                      <Checkbox checked={formData.rule_ids.indexOf(rule.id) > -1} />
                      <ListItemText
                        primary={rule.name}
                        secondary={rule.enabled ? 'Enabled' : 'Disabled'}
                      />
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.schedule_enabled}
                    onChange={(e) => setFormData({ ...formData, schedule_enabled: e.target.checked })}
                  />
                }
                label="Enable Scheduled Execution"
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
                  helperText="How often to run the audit automatically"
                />
              </Grid>
            )}
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSave} variant="contained">
            {editingSchedule ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AuditSchedules;
