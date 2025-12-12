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
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  Collapse,
  CircularProgress,
  Tooltip,
  InputAdornment,
  FormControlLabel,
  Switch,
  Checkbox,
} from '@mui/material';
import {
  Refresh,
  Visibility,
  KeyboardArrowDown,
  KeyboardArrowUp,
  Backup as BackupIcon,
  Search as SearchIcon,
  Compare as CompareIcon,
} from '@mui/icons-material';
import { configBackupsAPI } from '../api/api';
import { useAuth } from '../contexts/AuthContext';
import { useHasPermission } from './RoleBasedAccess';

// Component for individual backup rows within expanded device section
const BackupRow = ({ backup, onView, selected, onSelect }) => {
  const getTypeColor = (type) => {
    const colors = {
      auto: 'default',
      manual: 'primary',
      pre_change: 'warning',
      post_change: 'success',
      pre_remediation: 'info',
      pre_template: 'secondary',
    };
    return colors[type] || 'default';
  };

  const formatSize = (bytes) => {
    if (!bytes) return 'N/A';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <TableRow hover>
      <TableCell padding="checkbox">
        <Checkbox
          checked={selected}
          onChange={(e) => onSelect(backup.id, e.target.checked)}
        />
      </TableCell>
      <TableCell>{new Date(backup.timestamp).toLocaleString()}</TableCell>
      <TableCell>
        <Chip
          label={backup.backup_type}
          size="small"
          color={getTypeColor(backup.backup_type)}
        />
      </TableCell>
      <TableCell>{formatSize(backup.size_bytes)}</TableCell>
      <TableCell>{backup.triggered_by || 'System'}</TableCell>
      <TableCell>
        {backup.config_hash ? (
          <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>
            {backup.config_hash.substring(0, 12)}...
          </Typography>
        ) : (
          'N/A'
        )}
      </TableCell>
      <TableCell align="right">
        <Tooltip title="View Configuration">
          <IconButton onClick={() => onView(backup)} size="small">
            <Visibility fontSize="small" />
          </IconButton>
        </Tooltip>
      </TableCell>
    </TableRow>
  );
};

// Component for device row with expandable backup history
const DeviceBackupRow = ({ deviceSummary, onCreateBackup, onViewBackup, selectedBackups, onSelectBackup, canCreateBackup }) => {
  const [open, setOpen] = useState(false);
  const [backups, setBackups] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchDeviceBackups = async () => {
    if (backups.length > 0) return; // Already loaded

    setLoading(true);
    try {
      // Include auto backups
      const response = await configBackupsAPI.getDeviceHistory(deviceSummary.device_id, 30, true);
      setBackups(response.data);
      setError('');
    } catch (err) {
      setError('Failed to fetch backup history');
    }
    setLoading(false);
  };

  const handleToggle = () => {
    if (!open && backups.length === 0) {
      fetchDeviceBackups();
    }
    setOpen(!open);
  };

  return (
    <>
      <TableRow hover sx={{ backgroundColor: '#fafafa' }}>
        <TableCell>
          <IconButton size="small" onClick={handleToggle}>
            {open ? <KeyboardArrowUp /> : <KeyboardArrowDown />}
          </IconButton>
        </TableCell>
        <TableCell>
          <Box>
            <Typography variant="body1" fontWeight="medium">
              {deviceSummary.device_name}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {deviceSummary.device_ip || 'No IP'} • {deviceSummary.vendor}
            </Typography>
          </Box>
        </TableCell>
        <TableCell>
          <Chip
            label={deviceSummary.total_backups}
            color={deviceSummary.total_backups > 0 ? 'primary' : 'default'}
            size="small"
            variant="outlined"
          />
        </TableCell>
        <TableCell>
          {deviceSummary.latest_backup ? (
            <Typography variant="body2">
              {new Date(deviceSummary.latest_backup.timestamp).toLocaleString()}
            </Typography>
          ) : (
            <Typography variant="body2" color="text.secondary">
              No backups yet
            </Typography>
          )}
        </TableCell>
        <TableCell align="right">
          {canCreateBackup ? (
            <Tooltip title="Create Manual Backup">
              <Button
                variant="outlined"
                size="small"
                startIcon={<BackupIcon />}
                onClick={(e) => {
                  e.stopPropagation();
                  onCreateBackup(deviceSummary.device_id);
                }}
              >
                Backup Now
              </Button>
            </Tooltip>
          ) : (
            <Typography variant="body2" color="textSecondary">
              View only
            </Typography>
          )}
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={5}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ margin: 2 }}>
              <Typography variant="h6" gutterBottom>
                Backup History (Last 30)
              </Typography>
              {loading ? (
                <Box display="flex" justifyContent="center" p={3}>
                  <CircularProgress size={30} />
                </Box>
              ) : error ? (
                <Alert severity="error">{error}</Alert>
              ) : backups.length === 0 ? (
                <Typography variant="body2" color="text.secondary" align="center" sx={{ p: 2 }}>
                  No backups found for this device. Click "Backup Now" to create one.
                </Typography>
              ) : (
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell padding="checkbox">Select</TableCell>
                        <TableCell><strong>Timestamp</strong></TableCell>
                        <TableCell><strong>Type</strong></TableCell>
                        <TableCell><strong>Size</strong></TableCell>
                        <TableCell><strong>Created By</strong></TableCell>
                        <TableCell><strong>Config Hash</strong></TableCell>
                        <TableCell align="right"><strong>Actions</strong></TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {backups.map((backup) => (
                        <BackupRow
                          key={backup.id}
                          backup={backup}
                          onView={onViewBackup}
                          selected={selectedBackups.has(backup.id)}
                          onSelect={onSelectBackup}
                        />
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  );
};

export default function ConfigBackups() {
  const { user } = useAuth(); // Get current user
  const canCreateBackups = useHasPermission('create_backups');
  const [deviceSummaries, setDeviceSummaries] = useState([]);
  const [loading, setLoading] = useState(false);
  const [viewDialog, setViewDialog] = useState(false);
  const [selectedBackup, setSelectedBackup] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedBackups, setSelectedBackups] = useState(new Set());
  const [compareDialog, setCompareDialog] = useState(false);
  const [compareData, setCompareData] = useState(null);
  const [comparing, setComparing] = useState(false);

  useEffect(() => {
    fetchDeviceSummaries();
  }, []);

  const fetchDeviceSummaries = async () => {
    setLoading(true);
    try {
      // Include auto backups in summary
      const response = await configBackupsAPI.getDevicesSummary(true);
      setDeviceSummaries(response.data);
      setError('');
    } catch (err) {
      setError('Failed to fetch backup summaries');
    }
    setLoading(false);
  };

  const createBackup = async (deviceId) => {
    try {
      await configBackupsAPI.create({
        device_id: deviceId,
        backup_type: 'manual',
        created_by: user?.username || 'unknown', // Use actual username
      });
      setSuccess('Backup created successfully');
      fetchDeviceSummaries();
    } catch (err) {
      setError('Failed to create backup: ' + (err.response?.data?.detail || err.message));
    }
  };

  const viewBackup = async (backup) => {
    setLoading(true);
    try {
      const response = await configBackupsAPI.getById(backup.id);
      setSelectedBackup(response.data);
      setViewDialog(true);
      setError('');
    } catch (err) {
      setError('Failed to fetch backup details');
    }
    setLoading(false);
  };

  const handleSelectBackup = (backupId, checked) => {
    const newSelected = new Set(selectedBackups);
    if (checked) {
      newSelected.add(backupId);
    } else {
      newSelected.delete(backupId);
    }
    setSelectedBackups(newSelected);
  };

  const handleCompare = async () => {
    if (selectedBackups.size !== 2) {
      setError('Please select exactly 2 backups to compare');
      return;
    }

    setComparing(true);
    try {
      const [id1, id2] = Array.from(selectedBackups);
      const response = await configBackupsAPI.compare(id1, id2);
      setCompareData(response.data);
      setCompareDialog(true);
      setError('');
    } catch (err) {
      setError('Failed to compare backups: ' + (err.response?.data?.detail || err.message));
    }
    setComparing(false);
  };

  // Filter device summaries based on search query
  const filteredSummaries = deviceSummaries.filter((summary) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      summary.device_name?.toLowerCase().includes(query) ||
      summary.device_ip?.toLowerCase().includes(query) ||
      summary.vendor?.toLowerCase().includes(query)
    );
  });

  if (loading && deviceSummaries.length === 0) {
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
          <BackupIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          Configuration Backups
        </Typography>
        <Button
          variant="outlined"
          startIcon={<Refresh />}
          onClick={fetchDeviceSummaries}
          disabled={loading}
        >
          Refresh
        </Button>
      </Box>

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

      {/* Search Bar and Compare Button */}
      <Paper sx={{ p: 2, mb: 2, display: 'flex', gap: 2, alignItems: 'center' }}>
        <TextField
          placeholder="Search by device name, IP, or vendor..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          size="small"
          sx={{ flexGrow: 1 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
        />
        {selectedBackups.size > 0 && (
          <>
            <Chip
              label={`${selectedBackups.size} selected`}
              color="primary"
              onDelete={() => setSelectedBackups(new Set())}
            />
            <Tooltip title="Select exactly 2 backups to compare">
              <span>
                <Button
                  variant="outlined"
                  color="primary"
                  startIcon={<CompareIcon />}
                  onClick={handleCompare}
                  disabled={selectedBackups.size !== 2 || comparing}
                >
                  Compare
                </Button>
              </span>
            </Tooltip>
          </>
        )}
      </Paper>

      <Card>
        <CardContent>
          <Typography variant="body2" color="text.secondary" paragraph>
            View and manage device configuration backups grouped by device.
            Click on a device to view its last 30 backups. Select 2 backups to compare them.
          </Typography>

          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                  <TableCell width="50px" />
                  <TableCell><strong>Device</strong></TableCell>
                  <TableCell><strong>Total Backups</strong></TableCell>
                  <TableCell><strong>Latest Backup</strong></TableCell>
                  <TableCell align="right"><strong>Actions</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredSummaries.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      <Typography variant="body2" color="text.secondary" sx={{ py: 3 }}>
                        {searchQuery
                          ? `No devices found matching "${searchQuery}"`
                          : 'No devices found. Add devices first to create backups.'}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredSummaries.map((summary) => (
                    <DeviceBackupRow
                      key={summary.device_id}
                      deviceSummary={summary}
                      onCreateBackup={createBackup}
                      onViewBackup={viewBackup}
                      selectedBackups={selectedBackups}
                      onSelectBackup={handleSelectBackup}
                      canCreateBackup={canCreateBackups}
                    />
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* View Backup Dialog */}
      <Dialog open={viewDialog} onClose={() => setViewDialog(false)} maxWidth="lg" fullWidth>
        <DialogTitle>
          Configuration Backup Details
          {selectedBackup && (
            <Typography variant="body2" color="text.secondary">
              Created: {new Date(selectedBackup.timestamp).toLocaleString()}
            </Typography>
          )}
        </DialogTitle>
        <DialogContent>
          {selectedBackup && (
            <Box>
              <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
                <Chip
                  label={`Type: ${selectedBackup.backup_type}`}
                  color="primary"
                  size="small"
                />
                {selectedBackup.size_bytes && (
                  <Chip
                    label={`Size: ${(selectedBackup.size_bytes / 1024).toFixed(2)} KB`}
                    size="small"
                  />
                )}
                {selectedBackup.triggered_by && (
                  <Chip
                    label={`Created by: ${selectedBackup.triggered_by}`}
                    size="small"
                  />
                )}
                {selectedBackup.config_hash && (
                  <Chip
                    label={`Hash: ${selectedBackup.config_hash.substring(0, 16)}...`}
                    size="small"
                    variant="outlined"
                  />
                )}
              </Box>
              <TextField
                multiline
                fullWidth
                rows={25}
                value={selectedBackup.config_data || 'No configuration data'}
                InputProps={{
                  readOnly: true,
                  style: { fontFamily: 'monospace', fontSize: '12px' },
                }}
                sx={{ mt: 2 }}
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setViewDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Compare Backups Dialog */}
      <Dialog open={compareDialog} onClose={() => setCompareDialog(false)} maxWidth="lg" fullWidth>
        <DialogTitle>
          Configuration Comparison
          {compareData && (
            <Typography variant="body2" color="text.secondary">
              Comparing backup #{compareData.backup1.id} vs #{compareData.backup2.id}
            </Typography>
          )}
        </DialogTitle>
        <DialogContent>
          {compareData && (
            <Box>
              <Box sx={{ display: 'flex', gap: 2, mb: 2, justifyContent: 'space-between' }}>
                <Box>
                  <Typography variant="subtitle2" gutterBottom>
                    Backup 1 (Older)
                  </Typography>
                  <Chip
                    label={new Date(compareData.backup1.timestamp).toLocaleString()}
                    size="small"
                    color="info"
                  />
                </Box>
                <Box>
                  <Typography variant="subtitle2" gutterBottom>
                    Backup 2 (Newer)
                  </Typography>
                  <Chip
                    label={new Date(compareData.backup2.timestamp).toLocaleString()}
                    size="small"
                    color="success"
                  />
                </Box>
              </Box>

              <Box sx={{ mb: 2, display: 'flex', gap: 2 }}>
                <Chip
                  label={`Lines Added: ${compareData.summary.lines_added}`}
                  color="success"
                  size="small"
                />
                <Chip
                  label={`Lines Removed: ${compareData.summary.lines_removed}`}
                  color="error"
                  size="small"
                />
                <Chip
                  label={`Total Changes: ${compareData.summary.lines_changed}`}
                  color="warning"
                  size="small"
                />
                <Chip
                  label={`Time Diff: ${Math.abs(compareData.summary.time_diff_seconds / 60).toFixed(0)} min`}
                  size="small"
                  variant="outlined"
                />
              </Box>

              <Typography variant="subtitle2" gutterBottom>
                Unified Diff:
              </Typography>
              <Paper
                variant="outlined"
                sx={{
                  p: 2,
                  maxHeight: 600,
                  overflow: 'auto',
                  backgroundColor: '#f5f5f5',
                  fontFamily: 'monospace',
                  fontSize: '12px',
                }}
              >
                {compareData.diff ? (
                  compareData.diff.split('\n').map((line, idx) => {
                    let color = 'inherit';
                    let backgroundColor = 'transparent';
                    let fontWeight = 'normal';

                    if (line.startsWith('+++') || line.startsWith('---')) {
                      // File headers
                      color = '#666';
                      fontWeight = 'bold';
                    } else if (line.startsWith('@@')) {
                      // Diff position markers
                      color = '#1976d2';
                      backgroundColor = '#e3f2fd';
                      fontWeight = 'bold';
                    } else if (line.startsWith('+')) {
                      // Added lines
                      color = '#2e7d32';
                      backgroundColor = '#e8f5e9';
                    } else if (line.startsWith('-')) {
                      // Removed lines
                      color = '#c62828';
                      backgroundColor = '#ffebee';
                    }

                    return (
                      <Box
                        key={idx}
                        sx={{
                          color,
                          backgroundColor,
                          fontWeight,
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-all',
                          py: 0.25,
                          px: 1,
                          borderRadius: 0.5,
                        }}
                      >
                        {line || '\u00A0'}
                      </Box>
                    );
                  })
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No differences found
                  </Typography>
                )}
              </Paper>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCompareDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
