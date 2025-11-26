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
  Card,
  CardContent,
  Grid,
  LinearProgress
} from '@mui/material';
import {
  Add as AddIcon,
  Refresh as RefreshIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  AttachMoney as MoneyIcon,
  DateRange as DateIcon
} from '@mui/icons-material';
import { licensingAPI } from '../api/api';

function Licensing() {
  const [licenses, setLicenses] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [software, setSoftware] = useState([]);
  const [stats, setStats] = useState({
    total_licenses: 0,
    active_licenses: 0,
    expiring_licenses: 0,
    expired_licenses: 0,
    total_cost: 0,
    pending_alerts: 0
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingLicense, setEditingLicense] = useState(null);
  const [currentTab, setCurrentTab] = useState(0);
  const [formData, setFormData] = useState({
    device_id: '',
    license_type: 'perpetual',
    license_name: '',
    license_key: '',
    expiration_date: '',
    capacity_total: 0,
    capacity_used: 0,
    cost: 0,
    vendor: '',
    purchase_date: '',
    renewal_date: ''
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [licensesRes, alertsRes, softwareRes, statsRes] = await Promise.all([
        licensingAPI.getAll(),
        licensingAPI.getAlerts(),
        licensingAPI.getSoftware(),
        licensingAPI.getStats()
      ]);
      setLicenses(licensesRes.data);
      setAlerts(alertsRes.data);
      setSoftware(softwareRes.data);
      setStats(statsRes.data);
      setError(null);
    } catch (err) {
      setError('Failed to load licensing data: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (license = null) => {
    if (license) {
      setEditingLicense(license);
      setFormData({
        device_id: license.device_id || '',
        license_type: license.license_type || 'perpetual',
        license_name: license.license_name || '',
        license_key: license.license_key || '',
        expiration_date: license.expiration_date || '',
        capacity_total: license.capacity_total || 0,
        capacity_used: license.capacity_used || 0,
        cost: license.cost || 0,
        vendor: license.vendor || '',
        purchase_date: license.purchase_date || '',
        renewal_date: license.renewal_date || ''
      });
    } else {
      setEditingLicense(null);
      setFormData({
        device_id: '',
        license_type: 'perpetual',
        license_name: '',
        license_key: '',
        expiration_date: '',
        capacity_total: 0,
        capacity_used: 0,
        cost: 0,
        vendor: '',
        purchase_date: '',
        renewal_date: ''
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingLicense(null);
  };

  const handleSave = async () => {
    try {
      if (editingLicense) {
        await licensingAPI.update(editingLicense.id, formData);
      } else {
        await licensingAPI.create(formData);
      }
      handleCloseDialog();
      loadData();
    } catch (err) {
      setError('Failed to save license: ' + err.message);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this license?')) {
      try {
        await licensingAPI.delete(id);
        loadData();
      } catch (err) {
        setError('Failed to delete license: ' + err.message);
      }
    }
  };

  const handleAcknowledgeAlert = async (id) => {
    try {
      const user = 'admin'; // In real app, get from auth context
      await licensingAPI.acknowledgeAlert(id, user);
      loadData();
    } catch (err) {
      setError('Failed to acknowledge alert: ' + err.message);
    }
  };

  const getDaysUntilExpiration = (expirationDate) => {
    if (!expirationDate) return null;
    const now = new Date();
    const expDate = new Date(expirationDate);
    const diffTime = expDate - now;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  const getExpirationChip = (expirationDate) => {
    const daysLeft = getDaysUntilExpiration(expirationDate);
    if (daysLeft === null) {
      return <Chip label="Perpetual" size="small" color="success" />;
    } else if (daysLeft < 0) {
      return <Chip icon={<ErrorIcon />} label="Expired" size="small" color="error" />;
    } else if (daysLeft <= 30) {
      return <Chip icon={<WarningIcon />} label={`${daysLeft}d left`} size="small" color="warning" />;
    } else if (daysLeft <= 90) {
      return <Chip label={`${daysLeft}d left`} size="small" color="info" />;
    } else {
      return <Chip label={`${daysLeft}d left`} size="small" color="success" />;
    }
  };

  const getCapacityUsagePercent = (license) => {
    if (!license.capacity_total || license.capacity_total === 0) return 0;
    return Math.round((license.capacity_used / license.capacity_total) * 100);
  };

  const getCapacityColor = (percent) => {
    if (percent >= 90) return 'error';
    if (percent >= 75) return 'warning';
    return 'success';
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
          License Management
        </Typography>
        <Box>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadData}
            sx={{ mr: 1 }}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => handleOpenDialog()}
          >
            Add License
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Statistics Cards */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    Total Licenses
                  </Typography>
                  <Typography variant="h4">{stats.total_licenses}</Typography>
                </Box>
                <CheckCircleIcon sx={{ fontSize: 40, color: 'primary.main' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    Active
                  </Typography>
                  <Typography variant="h4" color="success.main">
                    {stats.active_licenses}
                  </Typography>
                </Box>
                <CheckCircleIcon sx={{ fontSize: 40, color: 'success.main' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    Expiring Soon
                  </Typography>
                  <Typography variant="h4" color="warning.main">
                    {stats.expiring_licenses}
                  </Typography>
                </Box>
                <WarningIcon sx={{ fontSize: 40, color: 'warning.main' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    Total Cost
                  </Typography>
                  <Typography variant="h4">${stats.total_cost.toLocaleString()}</Typography>
                </Box>
                <MoneyIcon sx={{ fontSize: 40, color: 'primary.main' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Paper sx={{ mb: 3 }}>
        <Tabs value={currentTab} onChange={(e, v) => setCurrentTab(v)}>
          <Tab label={`Licenses (${licenses.length})`} />
          <Tab label={`Alerts (${alerts.length})`} />
          <Tab label={`Software Inventory (${software.length})`} />
        </Tabs>

        {currentTab === 0 && (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>License Name</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Vendor</TableCell>
                  <TableCell>Expiration</TableCell>
                  <TableCell>Capacity</TableCell>
                  <TableCell>Cost</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {licenses.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} align="center">
                      <Typography variant="body2" color="text.secondary" py={3}>
                        No licenses found. Click "Add License" to get started.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  licenses.map((license) => (
                    <TableRow key={license.id}>
                      <TableCell>
                        <Typography variant="body2" fontWeight="medium">
                          {license.license_name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={license.license_type}
                          size="small"
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>{license.vendor || 'N/A'}</TableCell>
                      <TableCell>
                        {getExpirationChip(license.expiration_date)}
                      </TableCell>
                      <TableCell>
                        {license.capacity_total ? (
                          <Box>
                            <Box display="flex" alignItems="center" mb={0.5}>
                              <Typography variant="caption">
                                {license.capacity_used} / {license.capacity_total}
                              </Typography>
                              <Typography variant="caption" ml={1} color="text.secondary">
                                ({getCapacityUsagePercent(license)}%)
                              </Typography>
                            </Box>
                            <LinearProgress
                              variant="determinate"
                              value={getCapacityUsagePercent(license)}
                              color={getCapacityColor(getCapacityUsagePercent(license))}
                              sx={{ height: 6, borderRadius: 3 }}
                            />
                          </Box>
                        ) : (
                          'N/A'
                        )}
                      </TableCell>
                      <TableCell>
                        {license.cost ? `$${license.cost.toLocaleString()}` : 'N/A'}
                      </TableCell>
                      <TableCell>
                        <IconButton
                          size="small"
                          onClick={() => handleOpenDialog(license)}
                          title="Edit"
                        >
                          <EditIcon />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={() => handleDelete(license.id)}
                          title="Delete"
                          color="error"
                        >
                          <DeleteIcon />
                        </IconButton>
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
            {alerts.length === 0 ? (
              <Typography variant="body2" color="text.secondary" align="center">
                No pending alerts
              </Typography>
            ) : (
              <Box>
                {alerts.map((alert) => (
                  <Alert
                    key={alert.id}
                    severity={alert.severity}
                    sx={{ mb: 2 }}
                    action={
                      !alert.acknowledged && (
                        <Button
                          color="inherit"
                          size="small"
                          onClick={() => handleAcknowledgeAlert(alert.id)}
                        >
                          Acknowledge
                        </Button>
                      )
                    }
                  >
                    <Typography variant="body2" fontWeight="medium">
                      {alert.alert_type}: {alert.license_name}
                    </Typography>
                    <Typography variant="caption">
                      {alert.message}
                    </Typography>
                  </Alert>
                ))}
              </Box>
            )}
          </Box>
        )}

        {currentTab === 2 && (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Software Name</TableCell>
                  <TableCell>Version</TableCell>
                  <TableCell>Vendor</TableCell>
                  <TableCell>Device</TableCell>
                  <TableCell>Discovered</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {software.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      <Typography variant="body2" color="text.secondary" py={3}>
                        No software inventory data available
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  software.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell>{item.software_name}</TableCell>
                      <TableCell>{item.version}</TableCell>
                      <TableCell>{item.vendor}</TableCell>
                      <TableCell>{item.device_id}</TableCell>
                      <TableCell>
                        {new Date(item.discovered_at).toLocaleDateString()}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>

      {/* Add/Edit License Dialog */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingLicense ? 'Edit License' : 'Add New License'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="License Name"
                value={formData.license_name}
                onChange={(e) => setFormData({ ...formData, license_name: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>License Type</InputLabel>
                <Select
                  value={formData.license_type}
                  onChange={(e) => setFormData({ ...formData, license_type: e.target.value })}
                  label="License Type"
                >
                  <MenuItem value="perpetual">Perpetual</MenuItem>
                  <MenuItem value="subscription">Subscription</MenuItem>
                  <MenuItem value="term">Term-Based</MenuItem>
                  <MenuItem value="evaluation">Evaluation</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Vendor"
                value={formData.vendor}
                onChange={(e) => setFormData({ ...formData, vendor: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Device ID"
                type="number"
                value={formData.device_id}
                onChange={(e) => setFormData({ ...formData, device_id: e.target.value })}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="License Key"
                value={formData.license_key}
                onChange={(e) => setFormData({ ...formData, license_key: e.target.value })}
                type="password"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Purchase Date"
                type="date"
                value={formData.purchase_date}
                onChange={(e) => setFormData({ ...formData, purchase_date: e.target.value })}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Expiration Date"
                type="date"
                value={formData.expiration_date}
                onChange={(e) => setFormData({ ...formData, expiration_date: e.target.value })}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Capacity Total"
                type="number"
                value={formData.capacity_total}
                onChange={(e) => setFormData({ ...formData, capacity_total: parseInt(e.target.value) || 0 })}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Capacity Used"
                type="number"
                value={formData.capacity_used}
                onChange={(e) => setFormData({ ...formData, capacity_used: parseInt(e.target.value) || 0 })}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Cost ($)"
                type="number"
                value={formData.cost}
                onChange={(e) => setFormData({ ...formData, cost: parseFloat(e.target.value) || 0 })}
                inputProps={{ step: 0.01 }}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSave} variant="contained" disabled={!formData.license_name}>
            {editingLicense ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}

export default Licensing;
