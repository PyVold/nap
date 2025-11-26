import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Alert,
  Grid,
  Paper,
  List,
  ListItem,
  ListItemText,
  Switch,
  FormControlLabel,
  LinearProgress,
} from '@mui/material';
import {
  CloudUpload,
  Download,
  CheckCircle,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { deviceImportAPI } from '../api/api';

export default function DeviceImport() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [result, setResult] = useState(null);
  const [updateExisting, setUpdateExisting] = useState(false);

  const downloadTemplate = async () => {
    try {
      const response = await deviceImportAPI.downloadTemplate();
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'device_import_template.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
      setSuccess('Template downloaded successfully');
      setError('');
    } catch (err) {
      setError('Failed to download template');
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.name.endsWith('.csv')) {
      setError('Please upload a CSV file');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');
    setResult(null);

    try {
      const response = await deviceImportAPI.uploadFile(file, updateExisting);

      setResult(response.data);
      if (response.data.errors.length === 0) {
        setSuccess(
          `Import successful! Created: ${response.data.created}, Updated: ${response.data.updated}`
        );
      } else {
        setError('Import completed with errors');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to import devices');
    }

    setLoading(false);
    event.target.value = null; // Reset file input
  };

  const exportDevices = async () => {
    setLoading(true);
    try {
      const response = await deviceImportAPI.export();
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `devices_export_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      setSuccess('Devices exported successfully');
      setError('');
    } catch (err) {
      setError('Failed to export devices');
    }
    setLoading(false);
  };

  return (
    <Box sx={{ p: 3 }}>
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h5" gutterBottom>
                Bulk Device Import/Export
              </Typography>
              <Typography variant="body2" color="text.secondary" paragraph>
                Import multiple devices from a CSV file or export existing devices.
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

              {loading && <LinearProgress sx={{ mb: 2 }} />}

              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Paper sx={{ p: 3, textAlign: 'center', height: '100%' }}>
                    <CloudUpload sx={{ fontSize: 60, color: 'primary.main', mb: 2 }} />
                    <Typography variant="h6" gutterBottom>
                      Import Devices
                    </Typography>
                    <Typography variant="body2" color="text.secondary" paragraph>
                      Upload a CSV file with device information
                    </Typography>

                    <FormControlLabel
                      control={
                        <Switch
                          checked={updateExisting}
                          onChange={(e) => setUpdateExisting(e.target.checked)}
                        />
                      }
                      label="Update existing devices"
                      sx={{ mb: 2 }}
                    />

                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                      <Button
                        variant="outlined"
                        startIcon={<Download />}
                        onClick={downloadTemplate}
                        disabled={loading}
                      >
                        Download CSV Template
                      </Button>

                      <Button
                        variant="contained"
                        component="label"
                        startIcon={<CloudUpload />}
                        disabled={loading}
                      >
                        Upload CSV File
                        <input
                          type="file"
                          hidden
                          accept=".csv"
                          onChange={handleFileUpload}
                        />
                      </Button>
                    </Box>
                  </Paper>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Paper sx={{ p: 3, textAlign: 'center', height: '100%' }}>
                    <Download sx={{ fontSize: 60, color: 'secondary.main', mb: 2 }} />
                    <Typography variant="h6" gutterBottom>
                      Export Devices
                    </Typography>
                    <Typography variant="body2" color="text.secondary" paragraph>
                      Export all devices to a CSV file
                    </Typography>

                    <Button
                      variant="contained"
                      startIcon={<Download />}
                      onClick={exportDevices}
                      disabled={loading}
                      sx={{ mt: 7 }}
                    >
                      Export All Devices
                    </Button>
                  </Paper>
                </Grid>
              </Grid>

              {/* Import Results */}
              {result && (
                <Paper sx={{ p: 3, mt: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    Import Results
                  </Typography>
                  <Grid container spacing={2} sx={{ mb: 2 }}>
                    <Grid item xs={4}>
                      <Box sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="success.main">
                          {result.created}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Created
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={4}>
                      <Box sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="info.main">
                          {result.updated}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Updated
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={4}>
                      <Box sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="error.main">
                          {result.errors.length}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Errors
                        </Typography>
                      </Box>
                    </Grid>
                  </Grid>

                  {result.errors.length > 0 && (
                    <>
                      <Typography variant="subtitle1" gutterBottom sx={{ mt: 2 }}>
                        Errors:
                      </Typography>
                      <List dense>
                        {result.errors.map((error, index) => (
                          <ListItem key={index}>
                            <ErrorIcon color="error" sx={{ mr: 1 }} />
                            <ListItemText primary={error} />
                          </ListItem>
                        ))}
                      </List>
                    </>
                  )}
                </Paper>
              )}

              {/* CSV Format Guide */}
              <Paper sx={{ p: 3, mt: 3, backgroundColor: 'background.default' }}>
                <Typography variant="h6" gutterBottom>
                  CSV Format Guide
                </Typography>
                <Typography variant="body2" paragraph>
                  <strong>Required fields:</strong> hostname, ip, vendor
                </Typography>
                <Typography variant="body2" paragraph>
                  <strong>Optional fields:</strong> port (default: 830), username, password, description, location, tags
                </Typography>
                <Typography variant="body2" paragraph>
                  <strong>Supported vendors:</strong> CISCO_XR, NOKIA_SROS
                </Typography>
                <Typography variant="body2">
                  <strong>Tags format:</strong> key1:value1,key2:value2
                </Typography>
              </Paper>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
