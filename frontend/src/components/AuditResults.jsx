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
  Chip,
  Alert,
  CircularProgress,
  Paper,
  IconButton,
  Collapse,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  OutlinedInput,
  Checkbox,
  ListItemText,
  TextField,
  InputAdornment,
  Tooltip,
  Badge,
} from '@mui/material';
import {
  PlayArrow,
  Refresh,
  KeyboardArrowDown,
  KeyboardArrowUp,
  CheckCircle,
  Error,
  Warning,
  Assessment,
  Search as SearchIcon,
  CheckBox as CheckBoxIcon,
  CheckBoxOutlineBlank as CheckBoxOutlineBlankIcon,
  Build as FixIcon,
} from '@mui/icons-material';
import { auditAPI, devicesAPI, rulesAPI, remediationAPI } from '../api/api';

const AuditFindingRow = ({ finding }) => {
  const [open, setOpen] = useState(false);

  const getStatusIcon = (status) => {
    switch (status) {
      case 'pass':
        return <CheckCircle sx={{ color: '#4caf50' }} />;
      case 'fail':
        return <Error sx={{ color: '#f44336' }} />;
      case 'warning':
        return <Warning sx={{ color: '#ff9800' }} />;
      default:
        return <Warning sx={{ color: '#9e9e9e' }} />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'pass':
        return 'success';
      case 'fail':
        return 'error';
      case 'warning':
        return 'warning';
      default:
        return 'default';
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical':
        return 'error';
      case 'high':
        return 'warning';
      case 'medium':
        return 'info';
      case 'low':
        return 'success';
      default:
        return 'default';
    }
  };

  const hasConfigDetails = finding.actual_config || finding.expected_config || finding.comparison_details;

  return (
    <>
      <TableRow>
        <TableCell>
          {hasConfigDetails ? (
            <IconButton size="small" onClick={() => setOpen(!open)}>
              {open ? <KeyboardArrowUp /> : <KeyboardArrowDown />}
            </IconButton>
          ) : (
            getStatusIcon(finding.status)
          )}
        </TableCell>
        <TableCell>{finding.rule}</TableCell>
        <TableCell>
          <Chip label={finding.status} color={getStatusColor(finding.status)} size="small" />
        </TableCell>
        <TableCell>
          <Chip label={finding.severity} color={getSeverityColor(finding.severity)} size="small" />
        </TableCell>
        <TableCell sx={{ maxWidth: 300, whiteSpace: 'normal', wordWrap: 'break-word' }}>
          {finding.message || 'No message'}
        </TableCell>
        <TableCell>{finding.details || '-'}</TableCell>
      </TableRow>
      {hasConfigDetails && (
        <TableRow>
          <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={6}>
            <Collapse in={open} timeout="auto" unmountOnExit>
              <Box sx={{ margin: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
                {finding.actual_config && (
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      Actual Configuration:
                    </Typography>
                    <Paper sx={{ p: 1, backgroundColor: '#fff3e0', fontFamily: 'monospace', fontSize: '12px', overflow: 'auto', maxHeight: 200 }}>
                      <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{finding.actual_config}</pre>
                    </Paper>
                  </Box>
                )}

                {finding.expected_config && (
                  <Box>
                    <Typography variant="subtitle2" color="success.main" gutterBottom>
                      Expected Configuration:
                    </Typography>
                    <Paper sx={{ p: 1, backgroundColor: '#e8f5e9', fontFamily: 'monospace', fontSize: '12px', overflow: 'auto', maxHeight: 200 }}>
                      <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{finding.expected_config}</pre>
                    </Paper>
                  </Box>
                )}

                {finding.comparison_details && (
                  <Box>
                    <Typography variant="subtitle2" color="error" gutterBottom>
                      Comparison/Diff:
                    </Typography>
                    <Paper sx={{ p: 1, backgroundColor: '#fff', fontFamily: 'monospace', fontSize: '12px', overflow: 'auto', maxHeight: 200 }}>
                      <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{finding.comparison_details}</pre>
                    </Paper>
                  </Box>
                )}
              </Box>
            </Collapse>
          </TableCell>
        </TableRow>
      )}
    </>
  );
};

const AuditResultRow = ({ result, selected, onSelect }) => {
  const [open, setOpen] = useState(false);

  return (
    <>
      <TableRow hover>
        <TableCell padding="checkbox">
          <Checkbox
            checked={selected}
            onChange={(e) => onSelect(result, e.target.checked)}
          />
        </TableCell>
        <TableCell>
          <IconButton size="small" onClick={() => setOpen(!open)}>
            {open ? <KeyboardArrowUp /> : <KeyboardArrowDown />}
          </IconButton>
        </TableCell>
        <TableCell>
          <Typography variant="body2" fontWeight="medium">
            {result.device_name}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {result.device_ip || 'No IP'}
          </Typography>
        </TableCell>
        <TableCell>{new Date(result.timestamp).toLocaleString()}</TableCell>
        <TableCell>
          <Box display="flex" alignItems="center">
            <Box
              sx={{
                width: '100%',
                maxWidth: 200,
                height: 8,
                backgroundColor: '#e0e0e0',
                borderRadius: 4,
                mr: 1,
              }}
            >
              <Box
                sx={{
                  width: `${result.compliance}%`,
                  height: '100%',
                  backgroundColor: result.compliance >= 80 ? '#4caf50' : result.compliance >= 50 ? '#ff9800' : '#f44336',
                  borderRadius: 4,
                }}
              />
            </Box>
            <Typography variant="body2" fontWeight="bold">
              {result.compliance}%
            </Typography>
          </Box>
        </TableCell>
        <TableCell>{result.findings?.length || 0}</TableCell>
        <TableCell>
          <Chip
            label={result.findings?.filter((f) => f.status === 'fail').length || 0}
            color={result.findings?.filter((f) => f.status === 'fail').length > 0 ? 'error' : 'default'}
            size="small"
          />
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={7}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ margin: 2 }}>
              <Typography variant="h6" gutterBottom>
                Audit Findings
              </Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Status</TableCell>
                    <TableCell>Rule</TableCell>
                    <TableCell>Result</TableCell>
                    <TableCell>Severity</TableCell>
                    <TableCell>Message</TableCell>
                    <TableCell>Details</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {result.findings?.map((finding, idx) => (
                    <AuditFindingRow key={idx} finding={finding} />
                  ))}
                </TableBody>
              </Table>
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  );
};

const AuditResults = () => {
  const [results, setResults] = useState([]);
  const [devices, setDevices] = useState([]);
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [selectedDevices, setSelectedDevices] = useState([]);
  const [selectedRules, setSelectedRules] = useState([]);
  const [runningAudit, setRunningAudit] = useState(false);

  // New state for search and selection
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedResults, setSelectedResults] = useState(new Set());
  
  // Polling state for auto-refresh
  const [isPolling, setIsPolling] = useState(false);
  const [pollInterval, setPollInterval] = useState(null);
  
  // Auto-refresh state (continuous periodic refresh)
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);
  const [autoRefreshInterval, setAutoRefreshInterval] = useState(null);

  const fetchResults = async () => {
    setLoading(true);
    setError(null);
    try {
      console.log('Fetching audit results data...');
      
      // Fetch all data in parallel with individual error handling
      const [resultsRes, devicesRes, rulesRes] = await Promise.all([
        auditAPI.getResults().catch(err => {
          console.error('Error fetching audit results:', err);
          return { data: [] };
        }),
        devicesAPI.getAll().catch(err => {
          console.error('Error fetching devices:', err);
          return { data: [] };
        }),
        rulesAPI.getAll().catch(err => {
          console.error('Error fetching rules:', err);
          return { data: [] };
        }),
      ]);
      
      console.log('Audit results fetched:', resultsRes.data?.length || 0);
      console.log('Devices fetched:', devicesRes.data?.length || 0);
      console.log('Rules fetched:', rulesRes.data?.length || 0);
      
      setResults(Array.isArray(resultsRes.data) ? resultsRes.data : []);
      setDevices(Array.isArray(devicesRes.data) ? devicesRes.data : []);
      setRules(Array.isArray(rulesRes.data) ? rulesRes.data : []);
      setError(null);
      setLastRefresh(new Date());
      console.log('Audit page loaded successfully');
    } catch (err) {
      console.error('Critical error in fetchResults:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to fetch audit results');
      // Set empty arrays to prevent white page
      setResults([]);
      setDevices([]);
      setRules([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    console.log('AuditResults component mounted');
    fetchResults();
    
    // Cleanup on unmount
    return () => {
      if (pollInterval) {
        clearInterval(pollInterval);
      }
      if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
      }
    };
  }, []);
  
  // Continuous auto-refresh effect
  useEffect(() => {
    if (autoRefreshEnabled) {
      const interval = setInterval(() => {
        console.log('Auto-refreshing audit results...');
        fetchResults();
      }, 30000); // Refresh every 30 seconds
      
      setAutoRefreshInterval(interval);
      
      return () => {
        clearInterval(interval);
      };
    } else {
      if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        setAutoRefreshInterval(null);
      }
    }
  }, [autoRefreshEnabled]);
  
  useEffect(() => {
    console.log('Results state updated:', results.length, 'results');
  }, [results]);
  
  useEffect(() => {
    console.log('Loading state updated:', loading);
  }, [loading]);

  // Start polling for new results
  const startPolling = (maxAttempts = 12) => {
    let attempts = 0;
    setIsPolling(true);
    
    const interval = setInterval(async () => {
      attempts++;
      console.log(`Polling for results... Attempt ${attempts}/${maxAttempts}`);
      
      try {
        await fetchResults();
      } catch (err) {
        console.error('Polling error:', err);
      }
      
      // Stop polling after max attempts (12 attempts = 60 seconds with 5s interval)
      if (attempts >= maxAttempts) {
        console.log('Polling stopped - max attempts reached');
        clearInterval(interval);
        setIsPolling(false);
        setPollInterval(null);
      }
    }, 5000); // Poll every 5 seconds
    
    setPollInterval(interval);
  };

  // Stop polling
  const stopPolling = () => {
    if (pollInterval) {
      clearInterval(pollInterval);
      setPollInterval(null);
      setIsPolling(false);
    }
  };

  const handleRunAudit = async () => {
    setRunningAudit(true);
    try {
      const auditRequest = {
        device_ids: selectedDevices.length > 0 ? selectedDevices : null,
        rule_ids: selectedRules.length > 0 ? selectedRules : null,
      };
      await auditAPI.run(auditRequest);
      setSuccess('Audit started successfully. Results will appear automatically...');
      setOpenDialog(false);
      
      // Start polling for results
      startPolling();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setRunningAudit(false);
    }
  };

  // Filter results based on search query
  const filteredResults = results.filter((result) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      result.device_name?.toLowerCase().includes(query) ||
      result.device_ip?.toLowerCase().includes(query)
    );
  });

  // Handle individual selection
  const handleSelectResult = (result, checked) => {
    const newSelected = new Set(selectedResults);
    const key = `${result.device_id}-${result.timestamp}`;

    if (checked) {
      newSelected.add(key);
    } else {
      newSelected.delete(key);
    }

    setSelectedResults(newSelected);
  };

  // Handle select all
  const handleSelectAll = (checked) => {
    if (checked) {
      const allKeys = filteredResults.map(r => `${r.device_id}-${r.timestamp}`);
      setSelectedResults(new Set(allKeys));
    } else {
      setSelectedResults(new Set());
    }
  };

  // Check if result is selected
  const isResultSelected = (result) => {
    const key = `${result.device_id}-${result.timestamp}`;
    return selectedResults.has(key);
  };

  // Re-audit selected devices
  const handleReAuditSelected = async () => {
    if (selectedResults.size === 0) {
      setError('Please select at least one device to re-audit');
      return;
    }

    setRunningAudit(true);
    try {
      // Extract unique device IDs from selected results
      const deviceIds = [...selectedResults].map(key => {
        const [deviceId] = key.split('-');
        return parseInt(deviceId);
      });
      const uniqueDeviceIds = [...new Set(deviceIds)];

      // Extract unique rule names from selected results' findings
      const ruleNames = new Set();
      results.forEach(result => {
        const key = `${result.device_id}-${result.timestamp}`;
        if (selectedResults.has(key)) {
          result.findings?.forEach(finding => {
            if (finding.rule) {
              ruleNames.add(finding.rule);
            }
          });
        }
      });

      // Convert rule names to rule IDs
      const ruleIds = rules
        .filter(rule => ruleNames.has(rule.name))
        .map(rule => rule.id);

      const auditRequest = {
        device_ids: uniqueDeviceIds,
        rule_ids: ruleIds.length > 0 ? ruleIds : null,
      };
      await auditAPI.run(auditRequest);
      setSuccess(`Re-audit started for ${uniqueDeviceIds.length} device(s). Results will appear automatically...`);
      setSelectedResults(new Set()); // Clear selection
      
      // Start polling for results
      startPolling();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setRunningAudit(false);
    }
  };

  // Push remediation config
  const handlePushRemediation = async (dryRun = true) => {
    if (selectedResults.size === 0) {
      setError('Please select at least one device to push remediation');
      return;
    }

    setRunningAudit(true);
    try {
      // Extract unique device IDs from selected results
      const deviceIds = [...selectedResults].map(key => {
        const [deviceId] = key.split('-');
        return parseInt(deviceId);
      });
      const uniqueDeviceIds = [...new Set(deviceIds)];

      const result = await remediationAPI.pushRemediation(uniqueDeviceIds, dryRun);

      if (result.data.success) {
        const message = dryRun
          ? `Remediation validated for ${result.data.successful}/${result.data.total_devices} device(s). Review results and apply if ready.`
          : `Remediation applied to ${result.data.successful}/${result.data.total_devices} device(s). Results will appear automatically...`;

        setSuccess(message);
        setSelectedResults(new Set()); // Clear selection

        // If not dry run, start polling for updated results
        if (!dryRun) {
          // Auto re-audit after remediation
          const auditRequest = {
            device_ids: uniqueDeviceIds,
            rule_ids: null,
          };
          await auditAPI.run(auditRequest);
          startPolling();
        }
      } else {
        setError(`Remediation failed: ${result.data.failed} device(s) failed`);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to push remediation');
    } finally {
      setRunningAudit(false);
    }
  };

  const isAllSelected = filteredResults.length > 0 && selectedResults.size === filteredResults.length;
  const isSomeSelected = selectedResults.size > 0 && selectedResults.size < filteredResults.length;

  if (loading && results.length === 0) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box display="flex" alignItems="center" gap={2}>
          <Typography variant="h4" fontWeight="bold">
            <Assessment sx={{ mr: 1, verticalAlign: 'middle' }} />
            Audit Results
          </Typography>
          {autoRefreshEnabled && !isPolling && (
            <Chip
              label={`Auto-refresh: ${lastRefresh.toLocaleTimeString()}`}
              color="primary"
              size="small"
              icon={<Refresh />}
            />
          )}
          {isPolling && (
            <Chip
              label="Polling for results..."
              color="secondary"
              size="small"
              icon={<CircularProgress size={16} sx={{ color: 'white !important' }} />}
            />
          )}
        </Box>
        <Box>
          <Button
            variant={autoRefreshEnabled ? "outlined" : "contained"}
            startIcon={<Refresh />}
            onClick={() => setAutoRefreshEnabled(!autoRefreshEnabled)}
            sx={{ mr: 1 }}
          >
            Auto-refresh: {autoRefreshEnabled ? 'ON' : 'OFF'}
          </Button>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={() => {
              stopPolling();
              fetchResults();
            }}
            disabled={loading}
            sx={{ mr: 1 }}
          >
            Refresh Now
          </Button>
          <Button
            variant="contained"
            startIcon={<PlayArrow />}
            onClick={() => setOpenDialog(true)}
          >
            Run Audit
          </Button>
        </Box>
      </Box>

      {/* Debug Info - Remove after testing */}
      {process.env.NODE_ENV === 'development' && (
        <Alert severity="info" sx={{ mb: 2 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="body2">
              Debug: {results.length} results, {devices.length} devices, {rules.length} rules. Loading: {loading ? 'Yes' : 'No'}
            </Typography>
            <Button size="small" variant="outlined" onClick={fetchResults}>
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

      {/* Search and Bulk Actions Bar */}
      <Paper sx={{ p: 2, mb: 2, display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
        <TextField
          placeholder="Search by hostname or IP address..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          size="small"
          sx={{ minWidth: 300, flexGrow: 1 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
        />

        {selectedResults.size > 0 && (
          <>
            <Chip
              label={`${selectedResults.size} selected`}
              color="primary"
              onDelete={() => setSelectedResults(new Set())}
            />
            <Tooltip title="Re-audit selected devices">
              <Button
                variant="outlined"
                color="primary"
                startIcon={<PlayArrow />}
                onClick={handleReAuditSelected}
                disabled={runningAudit}
              >
                Re-Audit Selected
              </Button>
            </Tooltip>
            <Tooltip title="Validate remediation - shows what would be fixed without applying">
              <Button
                variant="outlined"
                color="success"
                startIcon={<FixIcon />}
                onClick={() => handlePushRemediation(true)}
                disabled={runningAudit}
                sx={{ mr: 1 }}
              >
                Validate Fix
              </Button>
            </Tooltip>
            <Tooltip title="Apply remediation - automatically fixes failed checks">
              <Button
                variant="contained"
                color="success"
                startIcon={<FixIcon />}
                onClick={() => handlePushRemediation(false)}
                disabled={runningAudit}
              >
                Apply Fix
              </Button>
            </Tooltip>
          </>
        )}
      </Paper>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
              <TableCell padding="checkbox">
                <Checkbox
                  indeterminate={isSomeSelected}
                  checked={isAllSelected}
                  onChange={(e) => handleSelectAll(e.target.checked)}
                />
              </TableCell>
              <TableCell />
              <TableCell><strong>Device</strong></TableCell>
              <TableCell><strong>Timestamp</strong></TableCell>
              <TableCell><strong>Compliance</strong></TableCell>
              <TableCell><strong>Total Checks</strong></TableCell>
              <TableCell><strong>Failed Checks</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredResults.map((result, idx) => (
              <AuditResultRow
                key={idx}
                result={result}
                selected={isResultSelected(result)}
                onSelect={handleSelectResult}
              />
            ))}
            {filteredResults.length === 0 && !loading && (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  <Typography variant="body2" color="textSecondary">
                    {searchQuery
                      ? `No results found matching "${searchQuery}"`
                      : 'No audit results found. Click "Run Audit" to start.'}
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Run Audit Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Run Audit</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Devices (leave empty for all)</InputLabel>
              <Select
                multiple
                value={selectedDevices}
                onChange={(e) => setSelectedDevices(e.target.value)}
                input={<OutlinedInput label="Devices (leave empty for all)" />}
                renderValue={(selected) =>
                  selected
                    .map((id) => devices.find((d) => d.id === id)?.hostname)
                    .join(', ')
                }
              >
                {devices.map((device) => (
                  <MenuItem key={device.id} value={device.id}>
                    <Checkbox checked={selectedDevices.includes(device.id)} />
                    <ListItemText primary={device.hostname} secondary={device.ip} />
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl fullWidth>
              <InputLabel>Rules (leave empty for all enabled rules)</InputLabel>
              <Select
                multiple
                value={selectedRules}
                onChange={(e) => setSelectedRules(e.target.value)}
                input={<OutlinedInput label="Rules (leave empty for all enabled rules)" />}
                renderValue={(selected) =>
                  selected
                    .map((id) => rules.find((r) => r.id === id)?.name)
                    .join(', ')
                }
              >
                {rules.map((rule) => (
                  <MenuItem key={rule.id} value={rule.id}>
                    <Checkbox checked={selectedRules.includes(rule.id)} />
                    <ListItemText
                      primary={rule.name}
                      secondary={rule.enabled ? 'Enabled' : 'Disabled'}
                    />
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button onClick={handleRunAudit} variant="contained" disabled={runningAudit}>
            {runningAudit ? <CircularProgress size={20} /> : 'Run Audit'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AuditResults;
