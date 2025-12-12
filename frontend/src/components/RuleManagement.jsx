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
import { Search as SearchIcon } from '@mui/icons-material';
import InputAdornment from '@mui/material/InputAdornment';
import { rulesAPI } from '../api/api';
import { useCanModify, useHasPermission } from './RoleBasedAccess';

const RuleManagement = () => {
  const canModify = useCanModify();
  const canCreateRules = useHasPermission('modify_rules');
  const canDeleteRules = useHasPermission('delete_rules');
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
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
    filter: '',
    reference_value: '',
    reference_config: '',
  });

  const [editingCheckIndex, setEditingCheckIndex] = useState(null);

  const fetchRules = async () => {
    setLoading(true);
    setError(null);
    try {
      console.log('Fetching rules...');
      const response = await rulesAPI.getAll();
      console.log('Rules response:', response);
      console.log('Rules data:', response.data);
      
      // Ensure we always set an array
      const rulesData = Array.isArray(response.data) ? response.data : [];
      setRules(rulesData);
      console.log('Rules set successfully:', rulesData.length);
      setError(null);
    } catch (err) {
      console.error('Error fetching rules:', err);
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to fetch rules';
      setError(errorMessage);
      setRules([]); // Set empty array on error
    } finally {
      setLoading(false);
      console.log('Fetch rules completed');
    }
  };

  useEffect(() => {
    console.log('RuleManagement component mounted');
    fetchRules();
  }, []);
  
  useEffect(() => {
    console.log('Rules state updated:', rules);
  }, [rules]);
  
  useEffect(() => {
    console.log('Loading state updated:', loading);
  }, [loading]);

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
      filter: '',
      reference_value: '',
      reference_config: '',
    });
  };

  const handleAddCheck = () => {
    // Parse filter JSON if it's provided
    let parsedFilter = null;
    if (checkForm.filter && checkForm.filter.trim()) {
      try {
        parsedFilter = JSON.parse(checkForm.filter);
      } catch (e) {
        setError('Invalid JSON format for filter. Please check your syntax.');
        return;
      }
    }

    const checkData = {
      name: checkForm.name,
      filter_xml: checkForm.filter_xml || null,
      xpath: checkForm.xpath || null,
      filter: parsedFilter,
      reference_value: checkForm.reference_value || null,
      reference_config: checkForm.reference_config || null,
      comparison: 'exact',
      error_message: 'Check failed',
      success_message: 'Check passed',
    };

    if (editingCheckIndex !== null) {
      // Update existing check
      const updatedChecks = [...formData.checks];
      updatedChecks[editingCheckIndex] = checkData;
      setFormData({
        ...formData,
        checks: updatedChecks,
      });
      setEditingCheckIndex(null);
    } else {
      // Add new check
      setFormData({
        ...formData,
        checks: [...formData.checks, checkData],
      });
    }
    setCheckForm({
      name: '',
      filter_xml: '',
      xpath: '',
      filter: '',
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
      filter: typeof check.filter === 'object' ? JSON.stringify(check.filter, null, 2) : (check.filter || ''),
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
          filter: '',
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
      filter: '',
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
        {canCreateRules && (
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => handleOpenDialog()}
          >
            Add New Rule
          </Button>
        )}
      </Box>

      {/* Search Bar */}
      <TextField
        fullWidth
        variant="outlined"
        placeholder="Search by rule name, description, category, or severity..."
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

      {/* Debug Info - Remove after testing */}
      {process.env.NODE_ENV === 'development' && (
        <Alert severity="info" sx={{ mb: 2 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="body2">
              Debug: Loaded {rules.length} rules. Loading: {loading ? 'Yes' : 'No'}
            </Typography>
            <Button size="small" variant="outlined" onClick={fetchRules}>
              Refresh
            </Button>
          </Box>
        </Alert>
      )}

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
            {rules
              .filter((rule) => {
                if (!searchQuery) return true;
                const query = searchQuery.toLowerCase();
                return (
                  rule.name?.toLowerCase().includes(query) ||
                  rule.description?.toLowerCase().includes(query) ||
                  rule.category?.toLowerCase().includes(query) ||
                  rule.severity?.toLowerCase().includes(query)
                );
              })
              .map((rule) => (
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
                  {canCreateRules && (
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
                    </>
                  )}
                  {canDeleteRules && (
                    <IconButton
                      size="small"
                      onClick={() => handleDelete(rule.id)}
                      color="error"
                    >
                      <Delete />
                    </IconButton>
                  )}
                  {!canCreateRules && !canDeleteRules && (
                    <Typography variant="body2" color="textSecondary">
                      View only
                    </Typography>
                  )}
                </TableCell>
              </TableRow>
            ))}
            {rules.length === 0 && !loading && (
              <TableRow>
                <TableCell colSpan={8} align="center" sx={{ py: 4 }}>
                  <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
                    No audit rules found. Get started by creating your first rule or importing rule templates.
                  </Typography>
                  {canModify && (
                    <Button
                      variant="outlined"
                      startIcon={<Add />}
                      onClick={() => handleOpenDialog()}
                      size="small"
                    >
                      Create First Rule
                    </Button>
                  )}
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

            {/* Show Nokia-specific fields only if Nokia is selected */}
            {formData.vendors.includes('nokia_sros') && (
              <>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="XPath (Nokia)"
                    multiline
                    rows={2}
                    value={checkForm.xpath}
                    onChange={(e) => setCheckForm({ ...checkForm, xpath: e.target.value })}
                    helperText="For Nokia SROS devices - Path to configuration element"
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Filter (Nokia - JSON format)"
                    multiline
                    rows={3}
                    value={checkForm.filter}
                    onChange={(e) => setCheckForm({ ...checkForm, filter: e.target.value })}
                    helperText='Filter dict in JSON format (e.g., {"service-name": "\\"", "admin-state": {}, "interface": {"interface-name": {}}})'
                    placeholder='{"service-name": "\\"", "admin-state": {}}'
                  />
                </Grid>
              </>
            )}

            {/* Show Cisco/other vendor fields only if Cisco or other vendors selected */}
            {(formData.vendors.includes('cisco_xr') || formData.vendors.length === 0 || !formData.vendors.includes('nokia_sros')) && (
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="XML Filter (Cisco XR / NETCONF)"
                  multiline
                  rows={3}
                  value={checkForm.filter_xml}
                  onChange={(e) => setCheckForm({ ...checkForm, filter_xml: e.target.value })}
                  helperText="For Cisco XR and other NETCONF devices - XML subtree filter"
                />
              </Grid>
            )}
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
                        {formData.vendors.includes('nokia_sros') && (
                          <>
                            <TableCell><strong>XPath (Nokia)</strong></TableCell>
                            <TableCell><strong>Filter (Nokia)</strong></TableCell>
                          </>
                        )}
                        {(formData.vendors.includes('cisco_xr') || !formData.vendors.includes('nokia_sros')) && (
                          <TableCell><strong>Filter XML (Cisco/NETCONF)</strong></TableCell>
                        )}
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
                          {formData.vendors.includes('nokia_sros') && (
                            <>
                              <TableCell>
                                <Typography variant="caption" sx={{ maxWidth: 150, display: 'block', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                  {check.xpath || '-'}
                                </Typography>
                              </TableCell>
                              <TableCell>
                                <Typography variant="caption" sx={{ maxWidth: 150, display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'pre-wrap' }}>
                                  {check.filter ? JSON.stringify(check.filter, null, 0) : '-'}
                                </Typography>
                              </TableCell>
                            </>
                          )}
                          {(formData.vendors.includes('cisco_xr') || !formData.vendors.includes('nokia_sros')) && (
                            <TableCell>
                              <Typography variant="caption" sx={{ maxWidth: 150, display: 'block', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                {check.filter_xml || '-'}
                              </Typography>
                            </TableCell>
                          )}
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
