import React, { useState, useEffect } from 'react';
import {
  Box, Paper, Typography, Button, Card, CardContent, CardActions,
  Chip, Alert, CircularProgress, Grid, TextField, Dialog, DialogTitle,
  DialogContent, DialogActions, FormControl, InputLabel, Select, MenuItem,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  IconButton, Tooltip, Divider, List, ListItem, ListItemText, ListItemIcon,
} from '@mui/material';
import HubIcon from '@mui/icons-material/Hub';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import BuildIcon from '@mui/icons-material/Build';
import StorageIcon from '@mui/icons-material/Storage';
import { mcpAPI } from '../api/api';
import { useCanModify } from './RoleBasedAccess';

const MCPHub = () => {
  const canModify = useCanModify();
  const [connections, setConnections] = useState([]);
  const [napTools, setNapTools] = useState([]);
  const [napResources, setNapResources] = useState([]);
  const [napPrompts, setNapPrompts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    name: '', server_url: '', transport: 'sse', auth_config: null,
  });
  const [tab, setTab] = useState('server'); // 'server' or 'hub'

  useEffect(() => {
    fetchAll();
  }, []);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [toolsRes, resourcesRes, promptsRes, connRes] = await Promise.all([
        mcpAPI.getTools().catch(() => ({ data: { tools: [] } })),
        mcpAPI.getResources().catch(() => ({ data: { resources: [] } })),
        mcpAPI.getPrompts().catch(() => ({ data: { prompts: [] } })),
        mcpAPI.getConnections().catch(() => ({ data: [] })),
      ]);
      setNapTools(toolsRes.data.tools || []);
      setNapResources(resourcesRes.data.resources || []);
      setNapPrompts(promptsRes.data.prompts || []);
      setConnections(connRes.data || []);
    } catch (err) {
      console.error('Failed to fetch MCP data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddConnection = async () => {
    try {
      await mcpAPI.createConnection(formData);
      setSuccess('Connection added successfully');
      setDialogOpen(false);
      setFormData({ name: '', server_url: '', transport: 'sse', auth_config: null });
      fetchAll();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add connection.');
    }
  };

  const handleTestConnection = async (id) => {
    try {
      const result = await mcpAPI.testConnection(id);
      if (result.data.status === 'connected') {
        setSuccess('Connection test successful');
      } else {
        setError('Connection test failed: ' + (result.data.status || 'unreachable'));
      }
      fetchAll();
    } catch (err) {
      setError('Connection test failed.');
    }
  };

  const handleDeleteConnection = async (id) => {
    try {
      await mcpAPI.deleteConnection(id);
      setSuccess('Connection removed');
      fetchAll();
    } catch (err) {
      setError('Failed to remove connection.');
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, gap: 1 }}>
        <HubIcon sx={{ fontSize: 32, color: 'primary.main' }} />
        <Typography variant="h5" fontWeight="bold">MCP Integration Hub</Typography>
        <Chip label="MCP" color="secondary" size="small" />
      </Box>

      {error && <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>{error}</Alert>}
      {success && <Alert severity="success" onClose={() => setSuccess(null)} sx={{ mb: 2 }}>{success}</Alert>}

      {/* Tab Selector */}
      <Box sx={{ display: 'flex', gap: 1, mb: 3 }}>
        <Button
          variant={tab === 'server' ? 'contained' : 'outlined'}
          onClick={() => setTab('server')}
          startIcon={<StorageIcon />}
        >
          NAP MCP Server
        </Button>
        <Button
          variant={tab === 'hub' ? 'contained' : 'outlined'}
          onClick={() => setTab('hub')}
          startIcon={<HubIcon />}
        >
          External Connections
        </Button>
      </Box>

      {tab === 'server' ? (
        <>
          {/* NAP as MCP Server */}
          <Typography variant="h6" gutterBottom>NAP exposes these MCP capabilities</Typography>

          {/* Tools */}
          <Paper elevation={2} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
            <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
              <BuildIcon fontSize="small" sx={{ mr: 0.5, verticalAlign: 'middle' }} />
              Tools ({napTools.length})
            </Typography>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Tool Name</TableCell>
                    <TableCell>Description</TableCell>
                    <TableCell>Parameters</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {napTools.map((tool, idx) => (
                    <TableRow key={idx}>
                      <TableCell>
                        <Chip label={tool.name} size="small" color="primary" variant="outlined" />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{tool.description}</Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>
                          {Object.keys(tool.inputSchema?.properties || {}).join(', ') || 'none'}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>

          {/* Resources */}
          <Paper elevation={2} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
            <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
              <StorageIcon fontSize="small" sx={{ mr: 0.5, verticalAlign: 'middle' }} />
              Resources ({napResources.length})
            </Typography>
            <Grid container spacing={2}>
              {napResources.map((resource, idx) => (
                <Grid item xs={12} sm={6} md={4} key={idx}>
                  <Card variant="outlined">
                    <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                      <Typography variant="body2" fontWeight="bold">{resource.name}</Typography>
                      <Typography variant="caption" color="primary" sx={{ fontFamily: 'monospace' }}>
                        {resource.uri}
                      </Typography>
                      <Typography variant="caption" display="block" color="text.secondary">
                        {resource.description}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Paper>

          {/* Prompts */}
          <Paper elevation={2} sx={{ p: 3, borderRadius: 2 }}>
            <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
              Prompts ({napPrompts.length})
            </Typography>
            {napPrompts.map((prompt, idx) => (
              <Card key={idx} variant="outlined" sx={{ mb: 1 }}>
                <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Typography variant="body2" fontWeight="bold">{prompt.name}</Typography>
                  <Typography variant="body2" color="text.secondary">{prompt.description}</Typography>
                  {prompt.arguments && (
                    <Box sx={{ mt: 0.5 }}>
                      {prompt.arguments.map((arg, aIdx) => (
                        <Chip key={aIdx} label={`${arg.name}${arg.required ? '*' : ''}`} size="small" variant="outlined" sx={{ mr: 0.5 }} />
                      ))}
                    </Box>
                  )}
                </CardContent>
              </Card>
            ))}
          </Paper>
        </>
      ) : (
        <>
          {/* External MCP Connections */}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="h6">External MCP Server Connections</Typography>
            {canModify && (
              <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialogOpen(true)}>
                Add Connection
              </Button>
            )}
          </Box>

          {loading ? (
            <CircularProgress />
          ) : connections.length === 0 ? (
            <Paper sx={{ p: 4, textAlign: 'center', borderRadius: 2 }}>
              <HubIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
              <Typography variant="body1" gutterBottom>No external MCP connections configured</Typography>
              <Typography variant="body2" color="text.secondary">
                Connect NAP to external MCP servers to extend its capabilities.
              </Typography>
            </Paper>
          ) : (
            <Grid container spacing={2}>
              {connections.map((conn) => (
                <Grid item xs={12} sm={6} md={4} key={conn.id}>
                  <Card variant="outlined">
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                        <Typography variant="subtitle2" fontWeight="bold">{conn.name}</Typography>
                        <Chip
                          label={conn.status}
                          size="small"
                          color={conn.status === 'connected' ? 'success' : 'error'}
                          icon={conn.status === 'connected' ? <CheckCircleIcon /> : <ErrorIcon />}
                        />
                      </Box>
                      <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>{conn.server_url}</Typography>
                      <Typography variant="caption" display="block" color="text.secondary">
                        Transport: {conn.transport}
                      </Typography>
                    </CardContent>
                    {canModify && (
                      <CardActions>
                        <Button size="small" startIcon={<PlayArrowIcon />} onClick={() => handleTestConnection(conn.id)}>
                          Test
                        </Button>
                        <IconButton size="small" color="error" onClick={() => handleDeleteConnection(conn.id)}>
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </CardActions>
                    )}
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}
        </>
      )}

      {/* Add Connection Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add MCP Server Connection</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth label="Connection Name" sx={{ mt: 1, mb: 2 }}
            value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          />
          <TextField
            fullWidth label="Server URL" sx={{ mb: 2 }}
            placeholder="http://server:port"
            value={formData.server_url} onChange={(e) => setFormData({ ...formData, server_url: e.target.value })}
          />
          <FormControl fullWidth>
            <InputLabel>Transport</InputLabel>
            <Select value={formData.transport} onChange={(e) => setFormData({ ...formData, transport: e.target.value })} label="Transport">
              <MenuItem value="sse">SSE (Server-Sent Events)</MenuItem>
              <MenuItem value="stdio">stdio</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleAddConnection} disabled={!formData.name || !formData.server_url}>
            Add Connection
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default MCPHub;
