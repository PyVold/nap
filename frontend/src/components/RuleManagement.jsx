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
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Switch,
  FormControlLabel,
  Alert,
  CircularProgress,
  Paper,
  Grid,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  ToggleOff,
  ToggleOn,
  Security,
} from '@mui/icons-material';
import { rulesAPI } from '../api/api';
import { useCanModify } from './RoleBasedAccess';

const RuleManagement = () => {
  const canModify = useCanModify();
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    severity: 'medium',
    category: '',
    enabled: true,
    vendors: [],
    checks: [],
  });

  const [checkForm, setCheckForm] = useState({
    name: '',
    filter_xml: '',
    xpath: '',
    reference_value: '',
    reference_config: '',
  });

  const [editingCheckIndex, setEditingCheckIndex] = useState(null);

  const fetchRules = async () => {
    setLoading(true);
    try {
      const response = await rulesAPI.getAll();
      setRules(response.data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRules();
  }, []);

  const handleOpenDialog = (rule = null) => {
    if (rule) {
      setEditingRule(rule);
      setFormData(rule);
    } else {
      setEditingRule(null);
      setFormData({
        name: '',
        description: '',
        severity: 'medium',
        category: '',
        enabled: true,
        vendors: [],
        checks: [],
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingRule(null);
    setEditingCheckIndex(null);
    setCheckForm({
      name: '',
      filter_xml: '',
      xpath: '',
      reference_value: '',
      reference_config: '',
    });
  };

  const handleAddCheck = () => {
    if (editingCheckIndex !== null) {
      // Update existing check
      const updatedChecks = [...formData.checks];
      updatedChecks[editingCheckIndex] = {
        ...checkForm,
        comparison: 'exact',
        error_message: 'Check failed',
        success_message: 'Check passed',
      };
      setFormData({
        ...formData,
        checks: updatedChecks,
      });
      setEditingCheckIndex(null);
    } else {
      // Add new check
      setFormData({
        ...formData,
        checks: [...formData.checks, {
          ...checkForm,
          comparison: 'exact',
          error_message: 'Check failed',
          success_message: 'Check passed',
        }],
      });
    }
    setCheckForm({
      name: '',
      filter_xml: '',
      xpath: '',
      reference_value: '',
      reference_config: '',
    });
  };

  const handleEditCheck = (index) => {
    const check = formData.checks[index];
    setCheckForm({
      name: check.name || '',
      filter_xml: check.filter_xml || '',
      xpath: check.xpath || '',
      reference_value: check.reference_value || '',
      reference_config: check.reference_config || '',
    });
    setEditingCheckIndex(index);
  };

  const handleDeleteCheck = (index) => {
    if (window.confirm('Are you sure you want to delete this check?')) {
      const updatedChecks = formData.checks.filter((_, i) => i !== index);
      setFormData({
        ...formData,
        checks: updatedChecks,
      });
      // Reset if we were editing this check
      if (editingCheckIndex === index) {
        setEditingCheckIndex(null);
        setCheckForm({
          name: '',
          filter_xml: '',
          xpath: '',
          reference_value: '',
          reference_config: '',
        });
      }
    }
  };

  const handleCancelEditCheck = () => {
    setEditingCheckIndex(null);
    setCheckForm({
      name: '',
      filter_xml: '',
      xpath: '',
      reference_value: '',
      reference_config: '',
    });
  };

  const handleSave = async () => {
    try {
      if (editingRule) {
        await rulesAPI.update(editingRule.id, formData);
        setSuccess('Rule updated successfully');
      } else {
        await rulesAPI.create(formData);
        setSuccess('Rule created successfully');
      }
      handleCloseDialog();
      fetchRules();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this rule?')) {
      try {
        await rulesAPI.delete(id);
        setSuccess('Rule deleted successfully');
        fetchRules();
      } catch (err) {
        setError(err.message);
      }
    }
  };

  const handleToggle = async (id) => {
    try {
      await rulesAPI.toggle(id);
      setSuccess('Rule toggled successfully');
      fetchRules();
    } catch (err) {
      setError(err.message);
    }
  };

  const severityColors = {
    critical: 'error',
    high: 'warning',
    medium: 'info',
    low: 'success',
  };

  if (loading && rules.length === 0) {
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
          <Security sx={{ mr: 1, verticalAlign: 'middle' }} />
          Audit Rules Management
        </Typography>
        {canModify && (
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => handleOpenDialog()}
          >
            Add New Rule
          </Button>
        )}
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
              <TableCell><strong>Description</strong></TableCell>
              <TableCell><strong>Severity</strong></TableCell>
              <TableCell><strong>Category</strong></TableCell>
              <TableCell><strong>Vendors</strong></TableCell>
              <TableCell><strong>Checks</strong></TableCell>
              <TableCell><strong>Status</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rules.map((rule) => (
              <TableRow key={rule.id} hover>
                <TableCell>{rule.name}</TableCell>
                <TableCell>{rule.description}</TableCell>
                <TableCell>
                  <Chip
                    label={rule.severity}
                    color={severityColors[rule.severity]}
                    size="small"
                  />
                </TableCell>
                <TableCell>{rule.category}</TableCell>
                <TableCell>
                  {rule.vendors.map((vendor, idx) => (
                    <Chip key={idx} label={vendor} size="small" sx={{ mr: 0.5, mb: 0.5 }} />
                  ))}
                </TableCell>
                <TableCell>{rule.checks?.length || 0}</TableCell>
                <TableCell>
                  <Chip
                    label={rule.enabled ? 'Enabled' : 'Disabled'}
                    color={rule.enabled ? 'success' : 'default'}
                    size="small"
                  />
                </TableCell>
                <TableCell align="center">
                  {canModify ? (
                    <>
                      <IconButton
                        size="small"
                        onClick={() => handleToggle(rule.id)}
                        color={rule.enabled ? 'success' : 'default'}
                      >
                        {rule.enabled ? <ToggleOn /> : <ToggleOff />}
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => handleOpenDialog(rule)}
                        color="primary"
                      >
                        <Edit />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => handleDelete(rule.id)}
                        color="error"
                      >
                        <Delete />
                      </IconButton>
                    </>
                  ) : (
                    <Typography variant="body2" color="textSecondary">
                      View only
                    </Typography>
                  )}
                </TableCell>
              </TableRow>
            ))}
            {rules.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} align="center">
                  <Typography variant="body2" color="textSecondary">
                    No rules found. Click "Add New Rule" to create one.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Add/Edit Rule Dialog */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingRule ? 'Edit Rule' : 'Add New Rule'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Rule Name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Description"
                multiline
                rows={2}
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Severity</InputLabel>
                <Select
                  value={formData.severity}
                  label="Severity"
                  onChange={(e) => setFormData({ ...formData, severity: e.target.value })}
                >
                  <MenuItem value="critical">Critical</MenuItem>
                  <MenuItem value="high">High</MenuItem>
                  <MenuItem value="medium">Medium</MenuItem>
                  <MenuItem value="low">Low</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Category"
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              />
            </Grid>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Vendors</InputLabel>
                <Select
                  multiple
                  value={formData.vendors}
                  label="Vendors"
                  onChange={(e) => setFormData({ ...formData, vendors: e.target.value })}
                  renderValue={(selected) => selected.join(', ')}
                >
                  <MenuItem value="cisco_xr">Cisco XR</MenuItem>
                  <MenuItem value="nokia_sros">Nokia SROS</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.enabled}
                    onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                  />
                }
                label="Enabled"
              />
            </Grid>

            <Grid item xs={12}>
              <Typography variant="h6" sx={{ mt: 2, mb: 1 }}>
                Add Check
              </Typography>
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Check Name"
                value={checkForm.name}
                onChange={(e) => setCheckForm({ ...checkForm, name: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="XPath (Nokia)"
                multiline
                rows={2}
                value={checkForm.xpath}
                onChange={(e) => setCheckForm({ ...checkForm, xpath: e.target.value })}
                helperText="For Nokia SROS devices"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="XML Filter (Cisco)"
                multiline
                rows={2}
                value={checkForm.filter_xml}
                onChange={(e) => setCheckForm({ ...checkForm, filter_xml: e.target.value })}
                helperText="For Cisco XR devices"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Reference Config"
                multiline
                rows={3}
                value={checkForm.reference_config}
                onChange={(e) => setCheckForm({ ...checkForm, reference_config: e.target.value })}
              />
            </Grid>
            <Grid item xs={12}>
              <Box display="flex" gap={1}>
                <Button
                  variant="outlined"
                  onClick={handleAddCheck}
                  disabled={!checkForm.name}
                >
                  {editingCheckIndex !== null ? 'Update Check' : 'Add Check to Rule'}
                </Button>
                {editingCheckIndex !== null && (
                  <Button
                    variant="text"
                    onClick={handleCancelEditCheck}
                  >
                    Cancel Edit
                  </Button>
                )}
              </Box>
            </Grid>
            {formData.checks.length > 0 && (
              <Grid item xs={12}>
                <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>
                  Checks ({formData.checks.length})
                </Typography>
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell><strong>Check Name</strong></TableCell>
                        <TableCell><strong>XPath</strong></TableCell>
                        <TableCell><strong>Filter XML</strong></TableCell>
                        <TableCell align="center"><strong>Actions</strong></TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {formData.checks.map((check, idx) => (
                        <TableRow
                          key={idx}
                          sx={{
                            backgroundColor: editingCheckIndex === idx ? '#e3f2fd' : 'inherit'
                          }}
                        >
                          <TableCell>
                            <Typography variant="body2" fontWeight={editingCheckIndex === idx ? 'bold' : 'normal'}>
                              {check.name}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="caption" sx={{ maxWidth: 150, display: 'block', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {check.xpath || '-'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="caption" sx={{ maxWidth: 150, display: 'block', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {check.filter_xml || '-'}
                            </Typography>
                          </TableCell>
                          <TableCell align="center">
                            <IconButton
                              size="small"
                              onClick={() => handleEditCheck(idx)}
                              color="primary"
                              title="Edit Check"
                              disabled={editingCheckIndex !== null && editingCheckIndex !== idx}
                            >
                              <Edit fontSize="small" />
                            </IconButton>
                            <IconButton
                              size="small"
                              onClick={() => handleDeleteCheck(idx)}
                              color="error"
                              title="Delete Check"
                            >
                              <Delete fontSize="small" />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Grid>
            )}
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSave} variant="contained" disabled={!formData.name}>
            {editingRule ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default RuleManagement;
