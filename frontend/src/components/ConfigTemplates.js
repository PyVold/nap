import React, { useState, useEffect } from 'react';
import {
  Container,
  Paper,
  Typography,
  Box,
  Button,
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
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  Grid,
  Card,
  CardContent,
  CardActions,
  Divider,
  Checkbox,
  FormControlLabel,
  Radio,
  RadioGroup,
  FormLabel,
  List,
  ListItem,
  ListItemText
} from '@mui/material';
import {
  Add as AddIcon,
  Refresh as RefreshIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  FileCopy as CopyIcon,
  PlayArrow as DeployIcon,
  Code as CodeIcon,
  Category as CategoryIcon,
  Remove as RemoveIcon
} from '@mui/icons-material';
import { configTemplatesAPI, devicesAPI, deviceGroupsAPI } from '../api/api';

const CategoryIcons = {
  security: '🔒',
  qos: '⚡',
  routing: '🔀',
  interfaces: '🔌',
  system: '⚙️',
  monitoring: '📊',
  vpn: '🔐',
  acl: '🛡️'
};

function ConfigTemplates() {
  const [templates, setTemplates] = useState([]);
  const [devices, setDevices] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [openDeployDialog, setOpenDeployDialog] = useState(false);
  const [openPreviewDialog, setOpenPreviewDialog] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState(null);
  const [deployingTemplate, setDeployingTemplate] = useState(null);
  const [previewContent, setPreviewContent] = useState('');
  const [currentTab, setCurrentTab] = useState(0);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [formData, setFormData] = useState({
    name: '',
    category: 'security',
    template_content: '',
    xpath: '',
    variables: [],
    description: '',
    vendor: 'cisco',
    is_builtin: false
  });
  const [deployForm, setDeployForm] = useState({
    deployment_type: 'single', // 'single', 'bulk', 'groups'
    device_id: '',
    device_ids: [],
    group_ids: [],
    variables: {}
  });
  const [deviceGroups, setDeviceGroups] = useState([]);

  useEffect(() => {
    initializeTemplates();
    loadCategories();
    loadDevices();
    loadDeviceGroups();
  }, []);

  const initializeTemplates = async () => {
    try {
      setLoading(true);
      // Initialize built-in templates first
      await configTemplatesAPI.initialize();
      // Then load all templates
      const response = await configTemplatesAPI.getAll();
      setTemplates(response.data);
      setError(null);
    } catch (err) {
      // Silently load templates even if initialization fails
      try {
        const response = await configTemplatesAPI.getAll();
        setTemplates(response.data);
      } catch (loadErr) {
        setError('Failed to load templates: ' + loadErr.message);
      }
    } finally {
      setLoading(false);
    }
  };

  const loadTemplates = async () => {
    try {
      setLoading(true);
      const response = await configTemplatesAPI.getAll();
      setTemplates(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to load templates: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadCategories = async () => {
    try {
      const response = await configTemplatesAPI.getCategories();
      setCategories(response.data.categories || []);
    } catch (err) {
      console.error('Failed to load categories:', err);
    }
  };

  const loadDevices = async () => {
    try {
      const response = await devicesAPI.getAll();
      setDevices(response.data);
    } catch (err) {
      console.error('Failed to load devices:', err);
    }
  };

  const loadDeviceGroups = async () => {
    try {
      const response = await deviceGroupsAPI.getAll();
      setDeviceGroups(response.data);
    } catch (err) {
      console.error('Failed to load device groups:', err);
    }
  };

  const handleOpenDialog = (template = null) => {
    if (template) {
      setEditingTemplate(template);
      setFormData({
        name: template.name,
        category: template.category,
        template_content: template.template_content,
        xpath: template.xpath || '',
        variables: template.variables || [],
        description: template.description || '',
        vendor: template.vendor || 'cisco',
        is_builtin: template.is_builtin || false
      });
    } else {
      setEditingTemplate(null);
      setFormData({
        name: '',
        category: 'security',
        template_content: '',
        xpath: '',
        variables: [],
        description: '',
        vendor: 'cisco',
        is_builtin: false
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingTemplate(null);
  };

  const handleSave = async () => {
    try {
      if (editingTemplate) {
        await configTemplatesAPI.update(editingTemplate.id, formData);
        setSuccess('Template updated successfully');
      } else {
        await configTemplatesAPI.create(formData);
        setSuccess('Template created successfully');
      }
      handleCloseDialog();
      loadTemplates();
    } catch (err) {
      setError('Failed to save template: ' + err.message);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this template?')) {
      try {
        await configTemplatesAPI.delete(id);
        setSuccess('Template deleted successfully');
        loadTemplates();
      } catch (err) {
        setError('Failed to delete template: ' + err.message);
      }
    }
  };

  const handleCopy = (template) => {
    handleOpenDialog({
      ...template,
      id: null,
      name: `${template.name} (Copy)`,
      is_builtin: false
    });
  };

  const handleOpenDeployDialog = (template) => {
    setDeployingTemplate(template);
    // Initialize variables object from template variables
    const varsObj = {};
    if (template.variables) {
      template.variables.forEach(v => {
        varsObj[v.name] = v.default_value || '';
      });
    }
    setDeployForm({
      deployment_type: 'single',
      device_id: '',
      device_ids: [],
      group_ids: [],
      variables: varsObj
    });
    setOpenDeployDialog(true);
  };

  const handleDeploy = async () => {
    try {
      if (deployForm.deployment_type === 'single') {
        await configTemplatesAPI.deploy(
          deployingTemplate.id,
          parseInt(deployForm.device_id),
          deployForm.variables
        );
        setSuccess('Template deployed to device successfully');
      } else if (deployForm.deployment_type === 'bulk') {
        await configTemplatesAPI.deployBulk(
          deployingTemplate.id,
          deployForm.device_ids,
          deployForm.variables
        );
        setSuccess(`Template deployed to ${deployForm.device_ids.length} devices successfully`);
      } else if (deployForm.deployment_type === 'groups') {
        await configTemplatesAPI.deployToGroups(
          deployingTemplate.id,
          deployForm.group_ids,
          deployForm.variables
        );
        setSuccess(`Template deployed to ${deployForm.group_ids.length} device groups successfully`);
      }
      setOpenDeployDialog(false);
    } catch (err) {
      setError('Failed to deploy template: ' + err.message);
    }
  };

  const handlePreview = (template) => {
    setPreviewContent(template.template_content);
    setOpenPreviewDialog(true);
  };

  const handleAddVariable = () => {
    const newVariable = {
      name: '',
      description: '',
      type: 'string',
      default_value: '',
      required: false
    };
    setFormData({
      ...formData,
      variables: [...formData.variables, newVariable]
    });
  };

  const handleRemoveVariable = (index) => {
    const updatedVariables = formData.variables.filter((_, i) => i !== index);
    setFormData({ ...formData, variables: updatedVariables });
  };

  const handleVariableChange = (index, field, value) => {
    const updatedVariables = [...formData.variables];
    updatedVariables[index] = {
      ...updatedVariables[index],
      [field]: value
    };
    setFormData({ ...formData, variables: updatedVariables });
  };

  const getFilteredTemplates = () => {
    if (selectedCategory === 'all') {
      return templates;
    }
    return templates.filter(t => t.category === selectedCategory);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Configuration Templates
        </Typography>
        <Box>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadTemplates}
            sx={{ mr: 1 }}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => handleOpenDialog()}
          >
            Create Template
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

      {/* Category Filter */}
      <Paper sx={{ mb: 3, p: 2 }}>
        <Box display="flex" alignItems="center" gap={1} flexWrap="wrap">
          <CategoryIcon />
          <Typography variant="body2" fontWeight="medium">Categories:</Typography>
          <Chip
            label="All"
            onClick={() => setSelectedCategory('all')}
            color={selectedCategory === 'all' ? 'primary' : 'default'}
            variant={selectedCategory === 'all' ? 'filled' : 'outlined'}
          />
          {categories.map(cat => (
            <Chip
              key={cat}
              label={`${CategoryIcons[cat] || '📄'} ${cat}`}
              onClick={() => setSelectedCategory(cat)}
              color={selectedCategory === cat ? 'primary' : 'default'}
              variant={selectedCategory === cat ? 'filled' : 'outlined'}
            />
          ))}
        </Box>
      </Paper>

      <Paper sx={{ mb: 3 }}>
        <Tabs value={currentTab} onChange={(e, v) => setCurrentTab(v)}>
          <Tab label={`Templates (${getFilteredTemplates().length})`} />
          <Tab label="Browse by Category" />
        </Tabs>

        {currentTab === 0 && (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Template Name</TableCell>
                  <TableCell>Category</TableCell>
                  <TableCell>Vendor</TableCell>
                  <TableCell>Variables</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {getFilteredTemplates().length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <Typography variant="body2" color="text.secondary" py={3}>
                        No templates found. Click "Create Template" to get started.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  getFilteredTemplates().map((template) => (
                    <TableRow key={template.id}>
                      <TableCell>
                        <Box display="flex" alignItems="center">
                          <CodeIcon sx={{ mr: 1, color: 'text.secondary' }} />
                          <Box>
                            <Typography variant="body2" fontWeight="medium">
                              {template.name}
                            </Typography>
                            {template.description && (
                              <Typography variant="caption" color="text.secondary">
                                {template.description}
                              </Typography>
                            )}
                          </Box>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={template.category}
                          size="small"
                          color="primary"
                          variant="outlined"
                          icon={<span>{CategoryIcons[template.category] || '📄'}</span>}
                        />
                      </TableCell>
                      <TableCell>
                        <Chip label={template.vendor || 'cisco'} size="small" />
                      </TableCell>
                      <TableCell>
                        {template.variables && template.variables.length > 0 ? (
                          <Chip
                            label={`${template.variables.length} vars`}
                            size="small"
                            color="info"
                          />
                        ) : (
                          <Typography variant="caption" color="text.secondary">
                            No variables
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        {template.is_builtin ? (
                          <Chip label="Built-in" size="small" color="success" />
                        ) : (
                          <Chip label="Custom" size="small" />
                        )}
                      </TableCell>
                      <TableCell>
                        <IconButton
                          size="small"
                          onClick={() => handlePreview(template)}
                          title="Preview"
                        >
                          <CodeIcon />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={() => handleOpenDeployDialog(template)}
                          title="Deploy"
                          color="primary"
                        >
                          <DeployIcon />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={() => handleCopy(template)}
                          title="Copy"
                        >
                          <CopyIcon />
                        </IconButton>
                        {!template.is_builtin && (
                          <>
                            <IconButton
                              size="small"
                              onClick={() => handleOpenDialog(template)}
                              title="Edit"
                            >
                              <EditIcon />
                            </IconButton>
                            <IconButton
                              size="small"
                              onClick={() => handleDelete(template.id)}
                              title="Delete"
                              color="error"
                            >
                              <DeleteIcon />
                            </IconButton>
                          </>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {currentTab === 1 && (
          <Box p={3}>
            <Grid container spacing={3}>
              {categories.map(category => {
                const categoryTemplates = templates.filter(t => t.category === category);
                if (categoryTemplates.length === 0) return null;

                return (
                  <Grid item xs={12} key={category}>
                    <Typography variant="h6" gutterBottom>
                      {CategoryIcons[category] || '📄'} {category.toUpperCase()}
                    </Typography>
                    <Grid container spacing={2}>
                      {categoryTemplates.map(template => (
                        <Grid item xs={12} sm={6} md={4} key={template.id}>
                          <Card variant="outlined">
                            <CardContent>
                              <Typography variant="body1" fontWeight="medium" gutterBottom>
                                {template.name}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                {template.description || 'No description'}
                              </Typography>
                              <Box mt={1}>
                                <Chip label={template.vendor || 'cisco'} size="small" sx={{ mr: 1 }} />
                                {template.is_builtin && (
                                  <Chip label="Built-in" size="small" color="success" />
                                )}
                              </Box>
                            </CardContent>
                            <Divider />
                            <CardActions>
                              <Button
                                size="small"
                                startIcon={<CodeIcon />}
                                onClick={() => handlePreview(template)}
                              >
                                View
                              </Button>
                              <Button
                                size="small"
                                startIcon={<DeployIcon />}
                                onClick={() => handleOpenDeployDialog(template)}
                              >
                                Deploy
                              </Button>
                            </CardActions>
                          </Card>
                        </Grid>
                      ))}
                    </Grid>
                  </Grid>
                );
              })}
            </Grid>
          </Box>
        )}
      </Paper>

      {/* Create/Edit Template Dialog */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingTemplate ? 'Edit Template' : 'Create New Template'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Template Name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Category</InputLabel>
                <Select
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  label="Category"
                >
                  {categories.map(cat => (
                    <MenuItem key={cat} value={cat}>
                      {CategoryIcons[cat] || '📄'} {cat}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
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
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Vendor</InputLabel>
                <Select
                  value={formData.vendor}
                  onChange={(e) => setFormData({ ...formData, vendor: e.target.value })}
                  label="Vendor"
                >
                  <MenuItem value="cisco">Cisco</MenuItem>
                  <MenuItem value="nokia">Nokia SROS</MenuItem>
                  <MenuItem value="juniper">Juniper</MenuItem>
                  <MenuItem value="arista">Arista</MenuItem>
                  <MenuItem value="paloalto">Palo Alto</MenuItem>
                  <MenuItem value="generic">Generic</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            {formData.vendor === 'nokia' && (
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="XPath (Nokia SROS)"
                  value={formData.xpath}
                  onChange={(e) => setFormData({ ...formData, xpath: e.target.value })}
                  placeholder="/configure/system/security/ssh/server"
                  helperText="XPath for pysros candidate.set() - leave empty for CLI mode"
                />
              </Grid>
            )}
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Template Content"
                value={formData.template_content}
                onChange={(e) => setFormData({ ...formData, template_content: e.target.value })}
                multiline
                rows={10}
                placeholder={formData.vendor === 'nokia' && formData.xpath
                  ? 'For Nokia with XPath: Enter JSON format config, e.g., {"admin-state": "enable"}'
                  : 'Enter configuration template here. Use {{variable_name}} for variables.'}
                helperText={formData.vendor === 'nokia' && formData.xpath
                  ? 'Nokia with XPath: Use JSON format. Variables: {{variable_name}}'
                  : 'Use {{variable_name}} syntax for variable substitution'}
                required
              />
            </Grid>

            {/* Variables Section */}
            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="subtitle1" fontWeight="medium">
                  Template Variables
                </Typography>
                <Button
                  startIcon={<AddIcon />}
                  onClick={handleAddVariable}
                  size="small"
                  variant="outlined"
                >
                  Add Variable
                </Button>
              </Box>

              {formData.variables && formData.variables.length === 0 && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  No variables defined. Click "Add Variable" to add placeholders for dynamic values in your template.
                  Use variables in template content with syntax: {`{{variable_name}}`}
                </Alert>
              )}

              {formData.variables && formData.variables.map((variable, index) => (
                <Paper key={index} variant="outlined" sx={{ p: 2, mb: 2 }}>
                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        fullWidth
                        label="Variable Name"
                        value={variable.name || ''}
                        onChange={(e) => handleVariableChange(index, 'name', e.target.value)}
                        placeholder="e.g., interface_name"
                        required
                        size="small"
                      />
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        fullWidth
                        label="Default Value"
                        value={variable.default_value || ''}
                        onChange={(e) => handleVariableChange(index, 'default_value', e.target.value)}
                        placeholder="Optional default value"
                        size="small"
                      />
                    </Grid>
                    <Grid item xs={12} sm={8}>
                      <TextField
                        fullWidth
                        label="Description"
                        value={variable.description || ''}
                        onChange={(e) => handleVariableChange(index, 'description', e.target.value)}
                        placeholder="What this variable is used for"
                        size="small"
                      />
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <Box display="flex" alignItems="center" gap={1}>
                        <FormControlLabel
                          control={
                            <Checkbox
                              checked={variable.required || false}
                              onChange={(e) => handleVariableChange(index, 'required', e.target.checked)}
                              size="small"
                            />
                          }
                          label="Required"
                        />
                        <IconButton
                          color="error"
                          onClick={() => handleRemoveVariable(index)}
                          size="small"
                          title="Remove Variable"
                        >
                          <RemoveIcon />
                        </IconButton>
                      </Box>
                    </Grid>
                  </Grid>
                </Paper>
              ))}
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSave} variant="contained" disabled={!formData.name || !formData.template_content}>
            {editingTemplate ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Deploy Template Dialog */}
      <Dialog open={openDeployDialog} onClose={() => setOpenDeployDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Deploy Template: {deployingTemplate?.name}</DialogTitle>
        <DialogContent>
          <FormControl component="fieldset" sx={{ mt: 2, mb: 2 }}>
            <FormLabel component="legend">Deployment Type</FormLabel>
            <RadioGroup
              value={deployForm.deployment_type}
              onChange={(e) => setDeployForm({ ...deployForm, deployment_type: e.target.value, device_id: '', device_ids: [], group_ids: [] })}
              row
            >
              <FormControlLabel value="single" control={<Radio />} label="Single Device" />
              <FormControlLabel value="bulk" control={<Radio />} label="Multiple Devices" />
              <FormControlLabel value="groups" control={<Radio />} label="Device Groups" />
            </RadioGroup>
          </FormControl>

          {deployForm.deployment_type === 'single' && (
            <FormControl fullWidth margin="normal" required>
              <InputLabel>Select Device</InputLabel>
              <Select
                value={deployForm.device_id}
                onChange={(e) => setDeployForm({ ...deployForm, device_id: e.target.value })}
                label="Select Device"
              >
                {devices.map((device) => (
                  <MenuItem key={device.id} value={device.id}>
                    {device.hostname} ({device.ip || 'No IP'}) - {device.vendor}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

          {deployForm.deployment_type === 'bulk' && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2" gutterBottom>Select Devices</Typography>
              <Paper variant="outlined" sx={{ maxHeight: 300, overflow: 'auto', p: 1 }}>
                {devices.map((device) => (
                  <FormControlLabel
                    key={device.id}
                    control={
                      <Checkbox
                        checked={deployForm.device_ids.includes(device.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setDeployForm({ ...deployForm, device_ids: [...deployForm.device_ids, device.id] });
                          } else {
                            setDeployForm({ ...deployForm, device_ids: deployForm.device_ids.filter(id => id !== device.id) });
                          }
                        }}
                      />
                    }
                    label={`${device.hostname} (${device.ip || 'No IP'}) - ${device.vendor}`}
                    sx={{ display: 'block' }}
                  />
                ))}
              </Paper>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                Selected: {deployForm.device_ids.length} device(s)
              </Typography>
            </Box>
          )}

          {deployForm.deployment_type === 'groups' && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2" gutterBottom>Select Device Groups</Typography>
              <Paper variant="outlined" sx={{ maxHeight: 300, overflow: 'auto', p: 1 }}>
                {deviceGroups.map((group) => (
                  <FormControlLabel
                    key={group.id}
                    control={
                      <Checkbox
                        checked={deployForm.group_ids.includes(group.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setDeployForm({ ...deployForm, group_ids: [...deployForm.group_ids, group.id] });
                          } else {
                            setDeployForm({ ...deployForm, group_ids: deployForm.group_ids.filter(id => id !== group.id) });
                          }
                        }}
                      />
                    }
                    label={`${group.name} (${group.device_ids?.length || 0} devices)`}
                    sx={{ display: 'block' }}
                  />
                ))}
              </Paper>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                Selected: {deployForm.group_ids.length} group(s)
              </Typography>
            </Box>
          )}

          {deployingTemplate?.variables && deployingTemplate.variables.length > 0 && (
            <>
              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle2" gutterBottom>
                Template Variables
              </Typography>
              {deployingTemplate.variables.map((variable, idx) => (
                <TextField
                  key={idx}
                  fullWidth
                  label={variable.name}
                  value={deployForm.variables[variable.name] || ''}
                  onChange={(e) => setDeployForm({
                    ...deployForm,
                    variables: {
                      ...deployForm.variables,
                      [variable.name]: e.target.value
                    }
                  })}
                  margin="normal"
                  helperText={variable.description || `Enter value for ${variable.name}`}
                />
              ))}
            </>
          )}

          <Alert severity="info" sx={{ mt: 2 }}>
            This will apply the template configuration to the selected device. Review the template carefully before deploying.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDeployDialog(false)}>Cancel</Button>
          <Button
            onClick={handleDeploy}
            variant="contained"
            disabled={
              (deployForm.deployment_type === 'single' && !deployForm.device_id) ||
              (deployForm.deployment_type === 'bulk' && deployForm.device_ids.length === 0) ||
              (deployForm.deployment_type === 'groups' && deployForm.group_ids.length === 0)
            }
          >
            Deploy
          </Button>
        </DialogActions>
      </Dialog>

      {/* Preview Template Dialog */}
      <Dialog open={openPreviewDialog} onClose={() => setOpenPreviewDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Template Preview</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            multiline
            rows={15}
            value={previewContent}
            InputProps={{
              readOnly: true,
              sx: { fontFamily: 'monospace', fontSize: '0.875rem' }
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenPreviewDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}

export default ConfigTemplates;
