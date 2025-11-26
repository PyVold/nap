import React, { useState, useEffect, useRef } from 'react';
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
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  Card,
  CardContent,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  PlayArrow as StartIcon,
  Visibility as VisibilityIcon,
  Router as RouterIcon,
  DeviceHub as SwitchIcon,
  Security as FirewallIcon,
  Computer as DeviceIcon
} from '@mui/icons-material';
import { topologyAPI } from '../api/api';

function Topology() {
  const [topology, setTopology] = useState({ nodes: [], links: [], total_nodes: 0, total_links: 0 });
  const [nodes, setNodes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentTab, setCurrentTab] = useState(0);
  const [openDiscoveryDialog, setOpenDiscoveryDialog] = useState(false);
  const [discoverySession, setDiscoverySession] = useState(null);
  const [discoveryForm, setDiscoveryForm] = useState({
    seed_device_ids: [],
    max_depth: 5
  });
  const canvasRef = useRef(null);

  useEffect(() => {
    loadTopology();
  }, []);

  useEffect(() => {
    if (currentTab === 0 && topology.nodes.length > 0) {
      drawTopology();
    }
  }, [currentTab, topology]);

  const loadTopology = async () => {
    try {
      setLoading(true);
      const [topologyRes, nodesRes] = await Promise.all([
        topologyAPI.getGraph(),
        topologyAPI.listNodes()
      ]);
      setTopology(topologyRes.data);
      setNodes(nodesRes.data);
      setError(null);
    } catch (err) {
      setError('Failed to load topology: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const drawTopology = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width = canvas.offsetWidth;
    const height = canvas.height = canvas.offsetHeight;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    if (topology.nodes.length === 0) {
      // Draw placeholder message
      ctx.fillStyle = '#999';
      ctx.font = '16px Arial';
      ctx.textAlign = 'center';
      ctx.fillText('No topology data available', width / 2, height / 2);
      ctx.fillText('Click "Start Discovery" to begin network discovery', width / 2, height / 2 + 30);
      return;
    }

    // Draw links
    ctx.strokeStyle = '#ccc';
    ctx.lineWidth = 2;
    topology.links.forEach(link => {
      const sourceNode = topology.nodes.find(n => n.id === link.source_id);
      const targetNode = topology.nodes.find(n => n.id === link.target_id);
      if (sourceNode && targetNode) {
        ctx.beginPath();
        ctx.moveTo(sourceNode.x_position * width, sourceNode.y_position * height);
        ctx.lineTo(targetNode.x_position * width, targetNode.y_position * height);
        ctx.stroke();
      }
    });

    // Draw nodes
    topology.nodes.forEach(node => {
      const x = node.x_position * width;
      const y = node.y_position * height;
      const radius = 25;

      // Node circle
      ctx.fillStyle = getNodeColor(node.node_type);
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, 2 * Math.PI);
      ctx.fill();
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 3;
      ctx.stroke();

      // Node icon
      ctx.fillStyle = '#fff';
      ctx.font = 'bold 20px Arial';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(getNodeIcon(node.node_type), x, y);

      // Node label
      ctx.fillStyle = '#333';
      ctx.font = '12px Arial';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillText(node.hostname || node.ip_address, x, y + radius + 5);
    });
  };

  const getNodeColor = (nodeType) => {
    const colors = {
      router: '#1976d2',
      switch: '#2e7d32',
      firewall: '#d32f2f',
      server: '#ed6c02',
      default: '#757575'
    };
    return colors[nodeType] || colors.default;
  };

  const getNodeIcon = (nodeType) => {
    const icons = {
      router: '🔀',
      switch: '⚡',
      firewall: '🛡️',
      server: '🖥️',
      default: '●'
    };
    return icons[nodeType] || icons.default;
  };

  const getNodeTypeIcon = (nodeType) => {
    switch (nodeType) {
      case 'router':
        return <RouterIcon />;
      case 'switch':
        return <SwitchIcon />;
      case 'firewall':
        return <FirewallIcon />;
      default:
        return <DeviceIcon />;
    }
  };

  const handleStartDiscovery = async () => {
    try {
      const response = await topologyAPI.startDiscovery(
        discoveryForm.seed_device_ids,
        discoveryForm.max_depth
      );
      setDiscoverySession(response.data);
      setOpenDiscoveryDialog(false);

      // Poll for discovery status
      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await topologyAPI.getDiscoveryStatus(response.data.session_id);
          setDiscoverySession(statusRes.data);

          if (statusRes.data.status === 'completed' || statusRes.data.status === 'failed') {
            clearInterval(pollInterval);
            loadTopology();
          }
        } catch (err) {
          clearInterval(pollInterval);
          setError('Failed to get discovery status: ' + err.message);
        }
      }, 3000);
    } catch (err) {
      setError('Failed to start discovery: ' + err.message);
    }
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
          Network Topology
        </Typography>
        <Box>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadTopology}
            sx={{ mr: 1 }}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<StartIcon />}
            onClick={() => setOpenDiscoveryDialog(true)}
          >
            Start Discovery
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {discoverySession && discoverySession.status === 'initiated' && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Discovery in progress: {discoverySession.nodes_discovered || 0} nodes, {discoverySession.links_discovered || 0} links discovered
          ({discoverySession.progress_percentage || 0}%)
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
                    Total Nodes
                  </Typography>
                  <Typography variant="h4">{topology.total_nodes}</Typography>
                </Box>
                <DeviceIcon sx={{ fontSize: 40, color: 'primary.main' }} />
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
                    Total Links
                  </Typography>
                  <Typography variant="h4">{topology.total_links}</Typography>
                </Box>
                <SwitchIcon sx={{ fontSize: 40, color: 'success.main' }} />
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
                    Routers
                  </Typography>
                  <Typography variant="h4">
                    {nodes.filter(n => n.node_type === 'router').length}
                  </Typography>
                </Box>
                <RouterIcon sx={{ fontSize: 40, color: 'info.main' }} />
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
                    Switches
                  </Typography>
                  <Typography variant="h4">
                    {nodes.filter(n => n.node_type === 'switch').length}
                  </Typography>
                </Box>
                <SwitchIcon sx={{ fontSize: 40, color: 'warning.main' }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Paper sx={{ mb: 3 }}>
        <Tabs value={currentTab} onChange={(e, v) => setCurrentTab(v)}>
          <Tab label="Topology Graph" icon={<VisibilityIcon />} />
          <Tab label="Node List" />
        </Tabs>

        {currentTab === 0 && (
          <Box p={3}>
            <canvas
              ref={canvasRef}
              style={{
                width: '100%',
                height: '600px',
                border: '1px solid #e0e0e0',
                borderRadius: '4px'
              }}
            />
            <Box mt={2} display="flex" gap={2} justifyContent="center">
              <Box display="flex" alignItems="center">
                <Box width={20} height={20} bgcolor="#1976d2" borderRadius="50%" mr={1} />
                <Typography variant="caption">Router</Typography>
              </Box>
              <Box display="flex" alignItems="center">
                <Box width={20} height={20} bgcolor="#2e7d32" borderRadius="50%" mr={1} />
                <Typography variant="caption">Switch</Typography>
              </Box>
              <Box display="flex" alignItems="center">
                <Box width={20} height={20} bgcolor="#d32f2f" borderRadius="50%" mr={1} />
                <Typography variant="caption">Firewall</Typography>
              </Box>
              <Box display="flex" alignItems="center">
                <Box width={20} height={20} bgcolor="#ed6c02" borderRadius="50%" mr={1} />
                <Typography variant="caption">Server</Typography>
              </Box>
            </Box>
          </Box>
        )}

        {currentTab === 1 && (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Hostname</TableCell>
                  <TableCell>IP Address</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Discovered Via</TableCell>
                  <TableCell>Last Seen</TableCell>
                  <TableCell>Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {nodes.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <Typography variant="body2" color="text.secondary" py={3}>
                        No topology nodes found. Start a discovery to populate the network topology.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  nodes.map((node) => (
                    <TableRow key={node.id}>
                      <TableCell>
                        <Box display="flex" alignItems="center">
                          {getNodeTypeIcon(node.node_type)}
                          <Typography variant="body2" ml={1}>
                            {node.hostname || 'Unknown'}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>{node.ip_address}</TableCell>
                      <TableCell>
                        <Chip
                          label={node.node_type || 'unknown'}
                          size="small"
                          color="primary"
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={node.discovered_via || 'manual'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        {node.last_seen
                          ? new Date(node.last_seen).toLocaleString()
                          : 'Never'}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={node.is_active ? 'Active' : 'Inactive'}
                          size="small"
                          color={node.is_active ? 'success' : 'default'}
                        />
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>

      {/* Discovery Dialog */}
      <Dialog open={openDiscoveryDialog} onClose={() => setOpenDiscoveryDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Start Topology Discovery</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" paragraph sx={{ mt: 2 }}>
            Topology discovery uses LLDP/CDP to automatically map your network infrastructure.
            Select seed devices to start from and specify the maximum discovery depth.
          </Typography>

          <TextField
            fullWidth
            label="Seed Device IDs (comma-separated)"
            value={discoveryForm.seed_device_ids.join(',')}
            onChange={(e) => setDiscoveryForm({
              ...discoveryForm,
              seed_device_ids: e.target.value.split(',').map(id => parseInt(id.trim())).filter(id => !isNaN(id))
            })}
            margin="normal"
            helperText="Enter device IDs to start discovery from (e.g., 1,2,3)"
          />

          <FormControl fullWidth margin="normal">
            <InputLabel>Maximum Depth</InputLabel>
            <Select
              value={discoveryForm.max_depth}
              onChange={(e) => setDiscoveryForm({ ...discoveryForm, max_depth: e.target.value })}
              label="Maximum Depth"
            >
              <MenuItem value={1}>1 hop</MenuItem>
              <MenuItem value={2}>2 hops</MenuItem>
              <MenuItem value={3}>3 hops</MenuItem>
              <MenuItem value={5}>5 hops (recommended)</MenuItem>
              <MenuItem value={10}>10 hops</MenuItem>
            </Select>
          </FormControl>

          <Alert severity="info" sx={{ mt: 2 }}>
            Discovery can take several minutes depending on network size. The process will run in the background.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDiscoveryDialog(false)}>Cancel</Button>
          <Button
            onClick={handleStartDiscovery}
            variant="contained"
            disabled={discoveryForm.seed_device_ids.length === 0}
          >
            Start Discovery
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}

export default Topology;
