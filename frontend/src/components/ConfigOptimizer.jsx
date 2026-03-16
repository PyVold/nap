import React, { useState } from 'react';
import {
  Box, Paper, Typography, TextField, Button, Chip, Alert, CircularProgress,
  Grid, Card, CardContent, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Tabs, Tab,
} from '@mui/material';
import TuneIcon from '@mui/icons-material/Tune';
import CleaningServicesIcon from '@mui/icons-material/CleaningServices';
import CompareArrowsIcon from '@mui/icons-material/CompareArrows';
import SearchIcon from '@mui/icons-material/Search';
import { aiAPI } from '../api/api';

const categoryColors = {
  unused: '#9e9e9e', redundant: '#ff9800', stale: '#795548',
  security: '#f44336', best_practice: '#2196f3', simplification: '#4caf50',
};

const ConfigOptimizer = () => {
  const [tab, setTab] = useState(0);
  const [deviceId, setDeviceId] = useState('');
  const [groupId, setGroupId] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [similarDeviceId, setSimilarDeviceId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [optimizeResult, setOptimizeResult] = useState(null);
  const [compareResult, setCompareResult] = useState(null);
  const [searchResult, setSearchResult] = useState(null);
  const [similarResult, setSimilarResult] = useState(null);

  const handleOptimize = async () => {
    if (!deviceId) return;
    setLoading(true); setError(null); setOptimizeResult(null);
    try {
      const response = await aiAPI.optimizeConfig(parseInt(deviceId));
      setOptimizeResult(response.data);
    } catch (err) { setError(err.response?.data?.detail || 'Optimization failed.'); }
    finally { setLoading(false); }
  };

  const handleCompareGroup = async () => {
    if (!groupId) return;
    setLoading(true); setError(null); setCompareResult(null);
    try {
      const response = await aiAPI.compareGroupConfigs(parseInt(groupId));
      setCompareResult(response.data);
    } catch (err) { setError(err.response?.data?.detail || 'Comparison failed.'); }
    finally { setLoading(false); }
  };

  const handleSearch = async () => {
    if (!searchQuery) return;
    setLoading(true); setError(null); setSearchResult(null);
    try {
      const response = await aiAPI.searchConfigs(searchQuery, 10);
      setSearchResult(response.data);
    } catch (err) { setError(err.response?.data?.detail || 'Search failed.'); }
    finally { setLoading(false); }
  };

  const handleFindSimilar = async () => {
    if (!similarDeviceId) return;
    setLoading(true); setError(null); setSimilarResult(null);
    try {
      const response = await aiAPI.findSimilarConfigs(parseInt(similarDeviceId));
      setSimilarResult(response.data);
    } catch (err) { setError(err.response?.data?.detail || 'Similarity search failed.'); }
    finally { setLoading(false); }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, gap: 1 }}>
        <TuneIcon sx={{ fontSize: 32, color: 'primary.main' }} />
        <Typography variant="h5" fontWeight="bold">Config Intelligence</Typography>
        <Chip label="Phase 3" color="secondary" size="small" />
      </Box>

      {error && <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>{error}</Alert>}

      <Tabs value={tab} onChange={(e, v) => setTab(v)} sx={{ mb: 3 }}>
        <Tab icon={<CleaningServicesIcon />} label="Optimize" />
        <Tab icon={<CompareArrowsIcon />} label="Compare Group" />
        <Tab icon={<SearchIcon />} label="Semantic Search" />
        <Tab icon={<TuneIcon />} label="Find Similar" />
      </Tabs>

      {/* Tab 0: Optimize */}
      {tab === 0 && (
        <Paper elevation={2} sx={{ p: 3, borderRadius: 2 }}>
          <Typography variant="h6" gutterBottom>Config Optimization</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            AI analyzes device config for unused, redundant, stale, and insecure configurations.
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
            <TextField size="small" label="Device ID" type="number" value={deviceId}
              onChange={(e) => setDeviceId(e.target.value)} />
            <Button variant="contained" onClick={handleOptimize} disabled={!deviceId || loading}
              startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <CleaningServicesIcon />}>
              {loading ? 'Analyzing...' : 'Analyze Config'}
            </Button>
          </Box>

          {optimizeResult && (
            <>
              <Grid container spacing={2} sx={{ mb: 2 }}>
                <Grid item xs={6} sm={3}>
                  <Card><CardContent sx={{ textAlign: 'center' }}>
                    <Typography variant="caption">Findings</Typography>
                    <Typography variant="h4" fontWeight="bold">{optimizeResult.summary?.total_findings || 0}</Typography>
                  </CardContent></Card>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Card><CardContent sx={{ textAlign: 'center' }}>
                    <Typography variant="caption">Safe Removals</Typography>
                    <Typography variant="h4" fontWeight="bold" color="success.main">{optimizeResult.summary?.safe_removals || 0}</Typography>
                  </CardContent></Card>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Card><CardContent sx={{ textAlign: 'center' }}>
                    <Typography variant="caption">Lines Saveable</Typography>
                    <Typography variant="h4" fontWeight="bold">{optimizeResult.summary?.estimated_lines_saveable || 0}</Typography>
                  </CardContent></Card>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Card><CardContent sx={{ textAlign: 'center' }}>
                    <Typography variant="caption">Reduction</Typography>
                    <Typography variant="h4" fontWeight="bold">{optimizeResult.summary?.config_reduction_percent || 0}%</Typography>
                  </CardContent></Card>
                </Grid>
              </Grid>

              <TableContainer>
                <Table size="small">
                  <TableHead><TableRow>
                    <TableCell>Category</TableCell><TableCell>Severity</TableCell>
                    <TableCell>Description</TableCell><TableCell>Safe</TableCell>
                  </TableRow></TableHead>
                  <TableBody>
                    {(optimizeResult.findings || []).map((f, idx) => (
                      <TableRow key={idx}>
                        <TableCell><Chip label={f.category} size="small"
                          sx={{ bgcolor: (categoryColors[f.category] || '#999') + '20', color: categoryColors[f.category] || '#999' }} /></TableCell>
                        <TableCell><Chip label={f.severity} size="small" color={f.severity === 'high' ? 'error' : 'default'} /></TableCell>
                        <TableCell>
                          <Typography variant="body2">{f.description}</Typography>
                          <Typography variant="caption" color="text.secondary">{f.recommendation}</Typography>
                        </TableCell>
                        <TableCell>{f.safe_to_remove ? 'Yes' : 'No'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </>
          )}
        </Paper>
      )}

      {/* Tab 1: Compare Group */}
      {tab === 1 && (
        <Paper elevation={2} sx={{ p: 3, borderRadius: 2 }}>
          <Typography variant="h6" gutterBottom>Group Config Comparison</Typography>
          <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
            <TextField size="small" label="Device Group ID" type="number" value={groupId}
              onChange={(e) => setGroupId(e.target.value)} />
            <Button variant="contained" onClick={handleCompareGroup} disabled={!groupId || loading}
              startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <CompareArrowsIcon />}>
              Compare
            </Button>
          </Box>
          {compareResult && (
            <Paper sx={{ p: 2, bgcolor: 'grey.50', whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.85rem', maxHeight: 500, overflow: 'auto' }}>
              {JSON.stringify(compareResult, null, 2)}
            </Paper>
          )}
        </Paper>
      )}

      {/* Tab 2: Semantic Search */}
      {tab === 2 && (
        <Paper elevation={2} sx={{ p: 3, borderRadius: 2 }}>
          <Typography variant="h6" gutterBottom>Semantic Config Search</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Search across all device configurations using natural language.
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
            <TextField fullWidth size="small" label="Search Query"
              placeholder='e.g., "devices with BGP MD5 authentication" or "rate limiting ACLs"'
              value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
            <Button variant="contained" onClick={handleSearch} disabled={!searchQuery || loading}
              startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <SearchIcon />}>
              Search
            </Button>
          </Box>
          {searchResult?.results?.length > 0 && (
            <TableContainer>
              <Table size="small">
                <TableHead><TableRow>
                  <TableCell>Device</TableCell><TableCell>Relevance</TableCell>
                  <TableCell>Match</TableCell><TableCell>Explanation</TableCell>
                </TableRow></TableHead>
                <TableBody>
                  {searchResult.results.map((r, idx) => (
                    <TableRow key={idx}>
                      <TableCell><strong>{r.hostname}</strong></TableCell>
                      <TableCell><Chip label={`${Math.round((r.relevance_score || 0) * 100)}%`} size="small"
                        color={r.relevance_score > 0.7 ? 'success' : 'default'} /></TableCell>
                      <TableCell><Typography variant="caption" sx={{ fontFamily: 'monospace' }}>{r.matched_section?.substring(0, 100)}</Typography></TableCell>
                      <TableCell><Typography variant="caption">{r.explanation}</Typography></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Paper>
      )}

      {/* Tab 3: Find Similar */}
      {tab === 3 && (
        <Paper elevation={2} sx={{ p: 3, borderRadius: 2 }}>
          <Typography variant="h6" gutterBottom>Find Similar Configurations</Typography>
          <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
            <TextField size="small" label="Reference Device ID" type="number" value={similarDeviceId}
              onChange={(e) => setSimilarDeviceId(e.target.value)} />
            <Button variant="contained" onClick={handleFindSimilar} disabled={!similarDeviceId || loading}
              startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <TuneIcon />}>
              Find Similar
            </Button>
          </Box>
          {similarResult && (
            <Paper sx={{ p: 2, bgcolor: 'grey.50', whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.85rem', maxHeight: 500, overflow: 'auto' }}>
              {JSON.stringify(similarResult, null, 2)}
            </Paper>
          )}
        </Paper>
      )}
    </Box>
  );
};

export default ConfigOptimizer;
