import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Alert,
  Grid,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  Add,
  PlayArrow,
  ExpandMore,
  Refresh,
  CheckCircle,
} from '@mui/icons-material';
import { ruleTemplatesAPI } from '../api/api';

export default function RuleTemplates() {
  const [templates, setTemplates] = useState([]);
  const [filteredTemplates, setFilteredTemplates] = useState([]);
  const [frameworks, setFrameworks] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [applyFrameworkDialog, setApplyFrameworkDialog] = useState(false);
  const [selectedFramework, setSelectedFramework] = useState('');
  const [selectedVendor, setSelectedVendor] = useState('');
  const [filterVendor, setFilterVendor] = useState('');
  const [filterFramework, setFilterFramework] = useState('');

  useEffect(() => {
    fetchFrameworks();
    fetchCategories();
    fetchTemplates();
  }, []);

  useEffect(() => {
    filterTemplatesLocal();
  }, [templates, filterVendor, filterFramework]);

  const fetchTemplates = async () => {
    setLoading(true);
    try {
      const response = await ruleTemplatesAPI.getAll();
      setTemplates(response.data);
      setError('');
    } catch (err) {
      setError('Failed to fetch templates');
    }
    setLoading(false);
  };

  const fetchFrameworks = async () => {
    try {
      const response = await ruleTemplatesAPI.getFrameworks();
      setFrameworks(response.data.frameworks);
    } catch (err) {
      console.error('Failed to fetch frameworks');
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await ruleTemplatesAPI.getCategories();
      setCategories(response.data.categories);
    } catch (err) {
      console.error('Failed to fetch categories');
    }
  };

  const filterTemplatesLocal = () => {
    let filtered = [...templates];

    if (filterVendor) {
      filtered = filtered.filter((t) => t.vendor === filterVendor);
    }

    if (filterFramework) {
      filtered = filtered.filter((t) => t.compliance_framework === filterFramework);
    }

    setFilteredTemplates(filtered);
  };

  const initializeTemplates = async () => {
    setLoading(true);
    try {
      const response = await ruleTemplatesAPI.initialize();
      setSuccess(`Initialized ${response.data.templates_created} built-in templates`);
      fetchTemplates();
      setError('');
    } catch (err) {
      setError('Failed to initialize templates');
    }
    setLoading(false);
  };

  const applyTemplate = async (templateId) => {
    setLoading(true);
    try {
      await ruleTemplatesAPI.applyTemplate(templateId);
      setSuccess('Template applied successfully! Rule created.');
      setError('');
    } catch (err) {
      setError('Failed to apply template');
    }
    setLoading(false);
  };

  const applyFramework = async () => {
    if (!selectedFramework || !selectedVendor) {
      setError('Please select both framework and vendor');
      return;
    }

    setLoading(true);
    try {
      const response = await ruleTemplatesAPI.applyFramework(selectedFramework, selectedVendor);
      setSuccess(`Applied ${response.data.length} rules from ${selectedFramework} framework`);
      setApplyFrameworkDialog(false);
      setError('');
    } catch (err) {
      setError('Failed to apply framework');
    }
    setLoading(false);
  };

  const getSeverityColor = (severity) => {
    const colors = {
      low: 'info',
      medium: 'warning',
      high: 'error',
      critical: 'error',
    };
    return colors[severity] || 'default';
  };

  // Group templates by framework
  const groupedTemplates = filteredTemplates.reduce((acc, template) => {
    const framework = template.compliance_framework;
    if (!acc[framework]) {
      acc[framework] = [];
    }
    acc[framework].push(template);
    return acc;
  }, {});

  return (
    <Box sx={{ p: 3 }}>
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h5" gutterBottom>
                Rule Template Library
              </Typography>
              <Typography variant="body2" color="text.secondary" paragraph>
                Pre-built audit rules for industry compliance frameworks (CIS, PCI-DSS, NIST, Best Practices).
              </Typography>

              {error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {error}
                </Alert>
              )}

              {success && (
                <Alert severity="success" sx={{ mb: 2 }}>
                  {success}
                </Alert>
              )}

              <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
                <Button
                  variant="contained"
                  startIcon={<Add />}
                  onClick={initializeTemplates}
                  disabled={loading}
                >
                  Initialize Built-in Templates
                </Button>

                <Button
                  variant="outlined"
                  onClick={() => setApplyFrameworkDialog(true)}
                  disabled={loading}
                >
                  Apply Compliance Framework
                </Button>

                <Button
                  variant="outlined"
                  startIcon={<Refresh />}
                  onClick={fetchTemplates}
                  disabled={loading}
                >
                  Refresh
                </Button>
              </Box>

              <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
                <TextField
                  select
                  label="Filter by Vendor"
                  value={filterVendor}
                  onChange={(e) => setFilterVendor(e.target.value)}
                  SelectProps={{ native: true }}
                  sx={{ minWidth: 200 }}
                  size="small"
                >
                  <option value="">All Vendors</option>
                  <option value="CISCO_XR">Cisco XR</option>
                  <option value="NOKIA_SROS">Nokia SROS</option>
                </TextField>

                <TextField
                  select
                  label="Filter by Framework"
                  value={filterFramework}
                  onChange={(e) => setFilterFramework(e.target.value)}
                  SelectProps={{ native: true }}
                  sx={{ minWidth: 200 }}
                  size="small"
                >
                  <option value="">All Frameworks</option>
                  {frameworks.map((fw) => (
                    <option key={fw} value={fw}>
                      {fw}
                    </option>
                  ))}
                </TextField>
              </Box>

              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Showing {filteredTemplates.length} of {templates.length} templates
              </Typography>

              {/* Grouped Templates */}
              {Object.keys(groupedTemplates).map((framework) => (
                <Accordion key={framework} defaultExpanded={framework === 'CIS'}>
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Typography variant="h6">
                      {framework} ({groupedTemplates[framework].length} templates)
                    </Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <TableContainer component={Paper} variant="outlined">
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Name</TableCell>
                            <TableCell>Vendor</TableCell>
                            <TableCell>Category</TableCell>
                            <TableCell>Severity</TableCell>
                            <TableCell align="right">Action</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {groupedTemplates[framework].map((template) => (
                            <TableRow key={template.id}>
                              <TableCell>
                                <Typography variant="body2" fontWeight={500}>
                                  {template.name}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  {template.description}
                                </Typography>
                              </TableCell>
                              <TableCell>
                                <Chip label={template.vendor} size="small" />
                              </TableCell>
                              <TableCell>{template.category}</TableCell>
                              <TableCell>
                                <Chip
                                  label={template.severity}
                                  color={getSeverityColor(template.severity)}
                                  size="small"
                                />
                              </TableCell>
                              <TableCell align="right">
                                <Button
                                  size="small"
                                  startIcon={<PlayArrow />}
                                  onClick={() => applyTemplate(template.id)}
                                  disabled={loading}
                                >
                                  Apply
                                </Button>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </AccordionDetails>
                </Accordion>
              ))}

              {filteredTemplates.length === 0 && (
                <Alert severity="info">
                  No templates found. Click "Initialize Built-in Templates" to load pre-built templates.
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Apply Framework Dialog */}
      <Dialog open={applyFrameworkDialog} onClose={() => setApplyFrameworkDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Apply Compliance Framework</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Alert severity="info">
              This will create audit rules for all templates in the selected framework and vendor.
            </Alert>

            <TextField
              select
              label="Compliance Framework"
              value={selectedFramework}
              onChange={(e) => setSelectedFramework(e.target.value)}
              SelectProps={{ native: true }}
              fullWidth
              required
            >
              <option value="">Select Framework</option>
              {frameworks.map((fw) => (
                <option key={fw} value={fw}>
                  {fw}
                </option>
              ))}
            </TextField>

            <TextField
              select
              label="Vendor"
              value={selectedVendor}
              onChange={(e) => setSelectedVendor(e.target.value)}
              SelectProps={{ native: true }}
              fullWidth
              required
            >
              <option value="">Select Vendor</option>
              <option value="CISCO_XR">Cisco XR</option>
              <option value="NOKIA_SROS">Nokia SROS</option>
            </TextField>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setApplyFrameworkDialog(false)}>Cancel</Button>
          <Button onClick={applyFramework} variant="contained" disabled={loading}>
            Apply Framework
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
