import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Alert,
  Tabs,
  Tab,
  Grid,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Stepper,
  Step,
  StepLabel,
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Checkbox,
  ListItemText,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  PlayArrow as PlayIcon,
  Visibility as ViewIcon,
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  HourglassEmpty as PendingIcon,
  Cancel as CancelIcon,
} from '@mui/icons-material';
import { workflowsAPI, devicesAPI } from '../api/api';

function TabPanel({ children, value, index }) {
  return (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export default function Workflows() {
  const [tabValue, setTabValue] = useState(0);
  const [workflows, setWorkflows] = useState([]);
  const [executions, setExecutions] = useState([]);
  const [devices, setDevices] = useState([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Workflow dialog
  const [workflowDialog, setWorkflowDialog] = useState({ open: false, workflow: null });
  const [workflowForm, setWorkflowForm] = useState({
    name: '',
    description: '',
    workflow_yaml: '',
    execution_mode: 'sequential',
    is_active: true
  });

  // Execution dialog
  const [executionDialog, setExecutionDialog] = useState({ open: false, workflow: null });
  const [selectedDevices, setSelectedDevices] = useState([]);

  // Execution viewer dialog
  const [viewerDialog, setViewerDialog] = useState({ open: false, execution: null });
  const [stepLogs, setStepLogs] = useState([]);

  useEffect(() => {
    fetchWorkflows();
    fetchExecutions();
    fetchDevices();
  }, []);

  const fetchWorkflows = async () => {
    try {
      const response = await workflowsAPI.getAll();
      setWorkflows(response.data);
    } catch (error) {
      console.error('Error fetching workflows:', error);
      setError('Failed to fetch workflows');
    }
  };

  const fetchExecutions = async () => {
    try {
      const response = await workflowsAPI.getExecutions();
      setExecutions(response.data);
    } catch (error) {
      console.error('Error fetching executions:', error);
    }
  };

  const fetchDevices = async () => {
    try {
      const response = await devicesAPI.getAll();
      setDevices(response.data);
    } catch (error) {
      console.error('Error fetching devices:', error);
    }
  };

  // Workflow CRUD
  const handleOpenWorkflowDialog = (workflow = null) => {
    if (workflow) {
      setWorkflowForm({
        name: workflow.name,
        description: workflow.description || '',
        workflow_yaml: workflow.workflow_yaml,
        execution_mode: workflow.execution_mode,
        is_active: workflow.is_active
      });
    } else {
      setWorkflowForm({
        name: '',
        description: '',
        workflow_yaml: `name: "New Workflow"
description: "Workflow description"
execution_mode: "sequential"

variables:
  # Define global variables here

steps:
  - name: step1
    type: query
    command: "show version"
    output_var: version_info
`,
        execution_mode: 'sequential',
        is_active: true
      });
    }
    setWorkflowDialog({ open: true, workflow });
  };

  const handleSaveWorkflow = async () => {
    try {
      if (workflowDialog.workflow) {
        await workflowsAPI.update(workflowDialog.workflow.id, workflowForm);
        setSuccess('Workflow updated successfully');
      } else {
        await workflowsAPI.create(workflowForm);
        setSuccess('Workflow created successfully');
      }
      setWorkflowDialog({ open: false, workflow: null });
      fetchWorkflows();
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to save workflow');
    }
  };

  const handleDeleteWorkflow = async (id) => {
    if (window.confirm('Are you sure you want to delete this workflow?')) {
      try {
        await workflowsAPI.delete(id);
        setSuccess('Workflow deleted successfully');
        fetchWorkflows();
      } catch (error) {
        setError('Failed to delete workflow');
      }
    }
  };

  // Workflow execution
  const handleOpenExecutionDialog = (workflow) => {
    setExecutionDialog({ open: true, workflow });
    setSelectedDevices([]);
  };

  const handleExecuteWorkflow = async () => {
    try {
      await workflowsAPI.execute(executionDialog.workflow.id, {
        workflow_id: executionDialog.workflow.id,
        device_ids: selectedDevices,
        trigger_type: 'manual'
      });
      setSuccess(`Workflow execution started on ${selectedDevices.length} devices`);
      setExecutionDialog({ open: false, workflow: null });
      setTimeout(fetchExecutions, 1000);
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to execute workflow');
    }
  };

  // Execution viewer
  const handleViewExecution = async (execution) => {
    setViewerDialog({ open: true, execution });
    try {
      const response = await workflowsAPI.getExecutionSteps(execution.id);
      setStepLogs(response.data);
    } catch (error) {
      console.error('Error fetching step logs:', error);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'success';
      case 'running': return 'info';
      case 'failed': return 'error';
      case 'cancelled': return 'default';
      default: return 'warning';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed': return <CheckCircleIcon color="success" />;
      case 'running': return <PendingIcon color="info" />;
      case 'failed': return <ErrorIcon color="error" />;
      case 'cancelled': return <CancelIcon />;
      default: return <PendingIcon color="warning" />;
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Workflow Manager
      </Typography>

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

      <Paper>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
          <Tab label="Workflows" />
          <Tab label="Executions" />
        </Tabs>

        {/* Workflows Tab */}
        <TabPanel value={tabValue} index={0}>
          <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="h6">Workflows</Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => handleOpenWorkflowDialog()}
            >
              Create Workflow
            </Button>
          </Box>

          <Grid container spacing={2}>
            {workflows.map((workflow) => (
              <Grid item xs={12} md={6} lg={4} key={workflow.id}>
                <Card>
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="h6">{workflow.name}</Typography>
                      <Chip
                        label={workflow.is_active ? 'Active' : 'Inactive'}
                        color={workflow.is_active ? 'success' : 'default'}
                        size="small"
                      />
                    </Box>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      {workflow.description || 'No description'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Mode: {workflow.execution_mode}
                    </Typography>
                    <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                      <Button
                        size="small"
                        variant="contained"
                        color="primary"
                        startIcon={<PlayIcon />}
                        onClick={() => handleOpenExecutionDialog(workflow)}
                        disabled={!workflow.is_active}
                      >
                        Execute
                      </Button>
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<EditIcon />}
                        onClick={() => handleOpenWorkflowDialog(workflow)}
                      >
                        Edit
                      </Button>
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => handleDeleteWorkflow(workflow.id)}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </TabPanel>

        {/* Executions Tab */}
        <TabPanel value={tabValue} index={1}>
          <Typography variant="h6" gutterBottom>
            Recent Executions
          </Typography>

          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>ID</TableCell>
                  <TableCell>Workflow</TableCell>
                  <TableCell>Device</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Trigger</TableCell>
                  <TableCell>Started</TableCell>
                  <TableCell>Duration</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {executions.map((execution) => (
                  <TableRow key={execution.id}>
                    <TableCell>{execution.id}</TableCell>
                    <TableCell>{execution.workflow_id}</TableCell>
                    <TableCell>{execution.device_id}</TableCell>
                    <TableCell>
                      <Chip
                        icon={getStatusIcon(execution.status)}
                        label={execution.status}
                        color={getStatusColor(execution.status)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>{execution.trigger_type}</TableCell>
                    <TableCell>
                      {new Date(execution.start_time).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      {execution.end_time
                        ? `${Math.round((new Date(execution.end_time) - new Date(execution.start_time)) / 1000)}s`
                        : '-'}
                    </TableCell>
                    <TableCell>
                      <IconButton
                        size="small"
                        onClick={() => handleViewExecution(execution)}
                      >
                        <ViewIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </TabPanel>
      </Paper>

      {/* Workflow Create/Edit Dialog */}
      <Dialog open={workflowDialog.open} onClose={() => setWorkflowDialog({ open: false })} maxWidth="md" fullWidth>
        <DialogTitle>
          {workflowDialog.workflow ? 'Edit Workflow' : 'Create Workflow'}
        </DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Name"
            value={workflowForm.name}
            onChange={(e) => setWorkflowForm({ ...workflowForm, name: e.target.value })}
            margin="normal"
          />
          <TextField
            fullWidth
            label="Description"
            value={workflowForm.description}
            onChange={(e) => setWorkflowForm({ ...workflowForm, description: e.target.value })}
            margin="normal"
            multiline
            rows={2}
          />
          <FormControl fullWidth margin="normal">
            <InputLabel>Execution Mode</InputLabel>
            <Select
              value={workflowForm.execution_mode}
              onChange={(e) => setWorkflowForm({ ...workflowForm, execution_mode: e.target.value })}
            >
              <MenuItem value="sequential">Sequential</MenuItem>
              <MenuItem value="dag">DAG (Parallel)</MenuItem>
              <MenuItem value="hybrid">Hybrid</MenuItem>
            </Select>
          </FormControl>
          <TextField
            fullWidth
            label="Workflow YAML"
            value={workflowForm.workflow_yaml}
            onChange={(e) => setWorkflowForm({ ...workflowForm, workflow_yaml: e.target.value })}
            margin="normal"
            multiline
            rows={15}
            sx={{ fontFamily: 'monospace' }}
          />
          <FormControlLabel
            control={
              <Switch
                checked={workflowForm.is_active}
                onChange={(e) => setWorkflowForm({ ...workflowForm, is_active: e.target.checked })}
              />
            }
            label="Active"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setWorkflowDialog({ open: false })}>Cancel</Button>
          <Button onClick={handleSaveWorkflow} variant="contained">
            {workflowDialog.workflow ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Execution Dialog */}
      <Dialog open={executionDialog.open} onClose={() => setExecutionDialog({ open: false })} maxWidth="sm" fullWidth>
        <DialogTitle>
          Execute Workflow: {executionDialog.workflow?.name}
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" gutterBottom>
            Select devices to execute this workflow on:
          </Typography>
          <FormControl fullWidth margin="normal">
            <InputLabel>Devices</InputLabel>
            <Select
              multiple
              value={selectedDevices}
              onChange={(e) => setSelectedDevices(e.target.value)}
              renderValue={(selected) =>
                devices
                  .filter((d) => selected.includes(d.id))
                  .map((d) => d.hostname)
                  .join(', ')
              }
            >
              {devices.map((device) => (
                <MenuItem key={device.id} value={device.id}>
                  <Checkbox checked={selectedDevices.includes(device.id)} />
                  <ListItemText primary={device.hostname} secondary={device.ip_address} />
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setExecutionDialog({ open: false })}>Cancel</Button>
          <Button
            onClick={handleExecuteWorkflow}
            variant="contained"
            disabled={selectedDevices.length === 0}
          >
            Execute on {selectedDevices.length} Device(s)
          </Button>
        </DialogActions>
      </Dialog>

      {/* Execution Viewer Dialog */}
      <Dialog open={viewerDialog.open} onClose={() => setViewerDialog({ open: false })} maxWidth="lg" fullWidth>
        <DialogTitle>
          Workflow Execution Details
        </DialogTitle>
        <DialogContent>
          {viewerDialog.execution && (
            <>
              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={3}>
                  <Typography variant="caption" color="text.secondary">Status</Typography>
                  <Chip
                    icon={getStatusIcon(viewerDialog.execution.status)}
                    label={viewerDialog.execution.status}
                    color={getStatusColor(viewerDialog.execution.status)}
                  />
                </Grid>
                <Grid item xs={3}>
                  <Typography variant="caption" color="text.secondary">Started</Typography>
                  <Typography variant="body2">
                    {new Date(viewerDialog.execution.start_time).toLocaleString()}
                  </Typography>
                </Grid>
                <Grid item xs={3}>
                  <Typography variant="caption" color="text.secondary">Duration</Typography>
                  <Typography variant="body2">
                    {viewerDialog.execution.end_time
                      ? `${Math.round((new Date(viewerDialog.execution.end_time) - new Date(viewerDialog.execution.start_time)) / 1000)}s`
                      : 'Running...'}
                  </Typography>
                </Grid>
                <Grid item xs={3}>
                  <Typography variant="caption" color="text.secondary">Current Step</Typography>
                  <Typography variant="body2">
                    {viewerDialog.execution.current_step || 'N/A'}
                  </Typography>
                </Grid>
              </Grid>

              <Typography variant="h6" gutterBottom>
                Step Execution Logs
              </Typography>

              <Stepper orientation="vertical">
                {stepLogs.map((step, index) => (
                  <Step key={step.id} active={true} completed={step.status === 'completed'}>
                    <StepLabel
                      error={step.status === 'failed'}
                      icon={getStatusIcon(step.status)}
                    >
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Typography variant="subtitle2">
                          {step.step_name} ({step.step_type})
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {step.duration_ms ? `${step.duration_ms}ms` : '-'}
                        </Typography>
                      </Box>
                    </StepLabel>
                    {(step.output_data || step.error_message) && (
                      <Accordion>
                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                          <Typography variant="caption">View Details</Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                          {step.output_data && (
                            <Box>
                              <Typography variant="caption" color="text.secondary">Output:</Typography>
                              <pre style={{ fontSize: '12px', overflow: 'auto', maxHeight: '200px' }}>
                                {JSON.stringify(step.output_data, null, 2)}
                              </pre>
                            </Box>
                          )}
                          {step.error_message && (
                            <Alert severity="error">
                              {step.error_message}
                            </Alert>
                          )}
                        </AccordionDetails>
                      </Accordion>
                    )}
                  </Step>
                ))}
              </Stepper>
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setViewerDialog({ open: false })}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
