import React, { useState, useEffect } from 'react';
import {
  Box, Paper, Typography, TextField, Button, Grid,
  Chip, Alert, CircularProgress, IconButton, FormControl, InputLabel,
  Select, MenuItem, Dialog, DialogTitle, DialogContent, DialogActions,
  Accordion, AccordionSummary, AccordionDetails,
} from '@mui/material';
import MenuBookIcon from '@mui/icons-material/MenuBook';
import SearchIcon from '@mui/icons-material/Search';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import DescriptionIcon from '@mui/icons-material/Description';
import { aiAPI } from '../api/api';
import { VENDOR_CONFIG, getVendorLabel } from '../utils/vendorConfig';
import { useCanModify } from './RoleBasedAccess';

const KnowledgeBase = () => {
  const canModify = useCanModify();
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Query state
  const [query, setQuery] = useState('');
  const [queryResult, setQueryResult] = useState(null);
  const [querying, setQuerying] = useState(false);

  // Filter state
  const [categoryFilter, setCategoryFilter] = useState('');
  const [vendorFilter, setVendorFilter] = useState('');

  // Add entry dialog
  const [addOpen, setAddOpen] = useState(false);
  const [newEntry, setNewEntry] = useState({
    title: '', content: '', category: 'general', vendor: '', tags: '',
  });
  const [adding, setAdding] = useState(false);

  // Upload dialog
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadCategory, setUploadCategory] = useState('general');
  const [uploadVendor, setUploadVendor] = useState('');
  const [uploadTags, setUploadTags] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);

  useEffect(() => {
    fetchEntries();
  }, [categoryFilter, vendorFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  const fetchEntries = async () => {
    setLoading(true);
    try {
      const params = {};
      if (categoryFilter) params.category = categoryFilter;
      if (vendorFilter) params.vendor = vendorFilter;
      const response = await aiAPI.getKnowledgeBase(params);
      setEntries(response.data.entries);
    } catch (err) {
      setError('Failed to load knowledge base');
    } finally {
      setLoading(false);
    }
  };

  const handleQuery = async () => {
    if (!query.trim()) return;
    setQuerying(true);
    setQueryResult(null);
    setError(null);
    try {
      const response = await aiAPI.queryKnowledgeBase({
        query: query.trim(),
        category: categoryFilter || undefined,
        vendor: vendorFilter || undefined,
      });
      setQueryResult(response.data);
    } catch (err) {
      setError('Failed to query knowledge base');
    } finally {
      setQuerying(false);
    }
  };

  const handleAdd = async () => {
    if (!newEntry.title.trim() || !newEntry.content.trim()) return;
    setAdding(true);
    try {
      await aiAPI.addKnowledgeEntry({
        title: newEntry.title,
        content: newEntry.content,
        category: newEntry.category,
        vendor: newEntry.vendor || undefined,
        tags: newEntry.tags || undefined,
      });
      setSuccess('Knowledge base entry added successfully');
      setAddOpen(false);
      setNewEntry({ title: '', content: '', category: 'general', vendor: '', tags: '' });
      fetchEntries();
    } catch (err) {
      setError('Failed to add entry');
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (entryId) => {
    try {
      await aiAPI.deleteKnowledgeEntry(entryId);
      setSuccess('Entry deleted');
      fetchEntries();
    } catch (err) {
      setError('Failed to delete entry');
    }
  };

  const handleUpload = async () => {
    if (!uploadFile) return;
    setUploading(true);
    setUploadResult(null);
    try {
      const response = await aiAPI.uploadKnowledgeDocument(
        uploadFile,
        uploadCategory,
        uploadVendor || undefined,
        uploadTags || undefined,
      );
      const data = response.data;
      setUploadResult(data);
      setSuccess(`Uploaded "${uploadFile.name}" — ${data.chunks_created} knowledge base entries created`);
      fetchEntries();
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to upload document';
      setError(msg);
    } finally {
      setUploading(false);
    }
  };

  const handleUploadClose = () => {
    setUploadOpen(false);
    setUploadFile(null);
    setUploadCategory('general');
    setUploadVendor('');
    setUploadTags('');
    setUploadResult(null);
  };

  const getCategoryColor = (cat) => {
    const colors = {
      best_practices: 'success',
      troubleshooting: 'warning',
      vendor_docs: 'info',
      config_examples: 'secondary',
      general: 'default',
    };
    return colors[cat] || 'default';
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, gap: 1 }}>
        <MenuBookIcon sx={{ fontSize: 32, color: 'primary.main' }} />
        <Typography variant="h5" fontWeight="bold">Knowledge Base</Typography>
        <Chip label="RAG-Powered" color="primary" size="small" />
      </Box>

      {error && <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>{error}</Alert>}
      {success && <Alert severity="success" onClose={() => setSuccess(null)} sx={{ mb: 2 }}>{success}</Alert>}

      {/* Query Section */}
      <Paper elevation={2} sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Typography variant="h6" gutterBottom>Ask the Knowledge Base</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Ask questions about network best practices, vendor configurations, or troubleshooting. AI will search the knowledge base and provide contextual answers.
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <TextField
            fullWidth
            placeholder='e.g., "How do I configure BGP authentication on Cisco IOS-XR?" or "What are NTP best practices?"'
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleQuery()}
            size="small"
          />
          <Button
            variant="contained"
            startIcon={querying ? <CircularProgress size={20} color="inherit" /> : <SearchIcon />}
            onClick={handleQuery}
            disabled={!query.trim() || querying}
          >
            {querying ? 'Searching...' : 'Search'}
          </Button>
        </Box>
      </Paper>

      {/* Query Result */}
      {queryResult && (
        <Paper elevation={3} sx={{ p: 3, mb: 3, borderRadius: 2, border: '2px solid', borderColor: 'primary.main' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">Answer</Typography>
            <Chip
              label={`Confidence: ${Math.round((queryResult.confidence || 0) * 100)}%`}
              color={queryResult.confidence >= 0.7 ? 'success' : 'warning'}
              size="small"
            />
          </Box>
          <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', mb: 2 }}>
            {queryResult.answer}
          </Typography>
          {queryResult.sources_used?.length > 0 && (
            <Box sx={{ mt: 1 }}>
              <Typography variant="caption" color="text.secondary">Sources:</Typography>
              <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.5 }}>
                {queryResult.sources_used.map((source, idx) => (
                  <Chip key={idx} label={source} size="small" variant="outlined" color="info" />
                ))}
              </Box>
            </Box>
          )}
          {queryResult.additional_recommendations?.length > 0 && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2">Additional Recommendations:</Typography>
              <ul style={{ margin: '4px 0', paddingLeft: 20 }}>
                {queryResult.additional_recommendations.map((rec, idx) => (
                  <li key={idx}><Typography variant="body2">{rec}</Typography></li>
                ))}
              </ul>
            </Box>
          )}
          <Typography variant="caption" color="text.secondary">
            Searched {queryResult.total_entries_searched} entries
          </Typography>
        </Paper>
      )}

      {/* Filters + Add Button */}
      <Box sx={{ display: 'flex', gap: 2, mb: 2, alignItems: 'center' }}>
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel>Category</InputLabel>
          <Select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} label="Category">
            <MenuItem value="">All Categories</MenuItem>
            <MenuItem value="best_practices">Best Practices</MenuItem>
            <MenuItem value="troubleshooting">Troubleshooting</MenuItem>
            <MenuItem value="vendor_docs">Vendor Docs</MenuItem>
            <MenuItem value="config_examples">Config Examples</MenuItem>
            <MenuItem value="general">General</MenuItem>
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel>Vendor</InputLabel>
          <Select value={vendorFilter} onChange={(e) => setVendorFilter(e.target.value)} label="Vendor">
            <MenuItem value="">All Vendors</MenuItem>
            {Object.entries(VENDOR_CONFIG).map(([key, cfg]) => (
              <MenuItem key={key} value={key}>{cfg.label}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <Box sx={{ flex: 1 }} />
        {canModify && (
          <>
            <Button variant="outlined" startIcon={<UploadFileIcon />} onClick={() => setUploadOpen(true)}>
              Upload Document
            </Button>
            <Button variant="outlined" startIcon={<AddIcon />} onClick={() => setAddOpen(true)}>
              Add Entry
            </Button>
          </>
        )}
      </Box>

      {/* Entries List */}
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      ) : entries.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography color="text.secondary">No knowledge base entries found. Add some to get started!</Typography>
        </Paper>
      ) : (
        entries.map((entry) => (
          <Accordion key={entry.id} variant="outlined" sx={{ mb: 1 }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flex: 1 }}>
                <Typography variant="body1" fontWeight="bold">{entry.title}</Typography>
                <Chip label={entry.category} size="small" color={getCategoryColor(entry.category)} />
                {entry.vendor && <Chip label={getVendorLabel(entry.vendor)} size="small" variant="outlined" />}
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', mb: 1 }}>
                {entry.content}
              </Typography>
              {entry.tags?.length > 0 && (
                <Box sx={{ display: 'flex', gap: 0.5, mb: 1 }}>
                  {entry.tags.map((tag, idx) => (
                    <Chip key={idx} label={tag} size="small" variant="outlined" />
                  ))}
                </Box>
              )}
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="caption" color="text.secondary">
                  Added by {entry.created_by || 'system'} {entry.created_at ? `on ${new Date(entry.created_at).toLocaleDateString()}` : ''}
                </Typography>
                {canModify && (
                  <IconButton size="small" color="error" onClick={() => handleDelete(entry.id)}>
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                )}
              </Box>
            </AccordionDetails>
          </Accordion>
        ))
      )}

      {/* Add Entry Dialog */}
      <Dialog open={addOpen} onClose={() => setAddOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Add Knowledge Base Entry</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth label="Title" value={newEntry.title}
            onChange={(e) => setNewEntry({ ...newEntry, title: e.target.value })}
            sx={{ mt: 1, mb: 2 }}
          />
          <TextField
            fullWidth label="Content" value={newEntry.content}
            onChange={(e) => setNewEntry({ ...newEntry, content: e.target.value })}
            multiline rows={8} sx={{ mb: 2 }}
          />
          <Grid container spacing={2}>
            <Grid item xs={4}>
              <FormControl fullWidth size="small">
                <InputLabel>Category</InputLabel>
                <Select value={newEntry.category} onChange={(e) => setNewEntry({ ...newEntry, category: e.target.value })} label="Category">
                  <MenuItem value="general">General</MenuItem>
                  <MenuItem value="best_practices">Best Practices</MenuItem>
                  <MenuItem value="troubleshooting">Troubleshooting</MenuItem>
                  <MenuItem value="vendor_docs">Vendor Docs</MenuItem>
                  <MenuItem value="config_examples">Config Examples</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={4}>
              <FormControl fullWidth size="small">
                <InputLabel>Vendor</InputLabel>
                <Select value={newEntry.vendor} onChange={(e) => setNewEntry({ ...newEntry, vendor: e.target.value })} label="Vendor">
                  <MenuItem value="">Generic (all vendors)</MenuItem>
                  {Object.entries(VENDOR_CONFIG).map(([key, cfg]) => (
                    <MenuItem key={key} value={key}>{cfg.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={4}>
              <TextField
                fullWidth size="small" label="Tags (comma-separated)"
                value={newEntry.tags}
                onChange={(e) => setNewEntry({ ...newEntry, tags: e.target.value })}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddOpen(false)}>Cancel</Button>
          <Button
            variant="contained" onClick={handleAdd}
            disabled={!newEntry.title.trim() || !newEntry.content.trim() || adding}
          >
            {adding ? 'Adding...' : 'Add Entry'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Upload Document Dialog */}
      <Dialog open={uploadOpen} onClose={handleUploadClose} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <CloudUploadIcon color="primary" />
          Upload Document to Knowledge Base
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Upload PDF, DOCX, TXT, MD, CSV, JSON, YAML, or XML files. The document will be parsed and split into searchable knowledge base entries.
          </Typography>

          {/* File picker */}
          <Box
            sx={{
              border: '2px dashed', borderColor: uploadFile ? 'primary.main' : 'divider',
              borderRadius: 2, p: 3, textAlign: 'center', mb: 2,
              bgcolor: uploadFile ? 'primary.50' : 'transparent',
              cursor: 'pointer', '&:hover': { borderColor: 'primary.main', bgcolor: 'action.hover' },
            }}
            onClick={() => document.getElementById('kb-upload-input').click()}
          >
            <input
              id="kb-upload-input"
              type="file"
              hidden
              accept=".pdf,.docx,.doc,.txt,.md,.csv,.json,.yaml,.yml,.conf,.cfg,.log,.xml"
              onChange={(e) => {
                if (e.target.files?.[0]) setUploadFile(e.target.files[0]);
              }}
            />
            {uploadFile ? (
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}>
                <DescriptionIcon color="primary" />
                <Typography variant="body1" fontWeight="bold">{uploadFile.name}</Typography>
                <Typography variant="body2" color="text.secondary">
                  ({(uploadFile.size / 1024).toFixed(1)} KB)
                </Typography>
              </Box>
            ) : (
              <>
                <CloudUploadIcon sx={{ fontSize: 40, color: 'text.secondary', mb: 1 }} />
                <Typography variant="body1" color="text.secondary">
                  Click to select a file
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  PDF, DOCX, TXT, MD, CSV, JSON, YAML, XML (max 20MB)
                </Typography>
              </>
            )}
          </Box>

          <Grid container spacing={2}>
            <Grid item xs={4}>
              <FormControl fullWidth size="small">
                <InputLabel>Category</InputLabel>
                <Select value={uploadCategory} onChange={(e) => setUploadCategory(e.target.value)} label="Category">
                  <MenuItem value="general">General</MenuItem>
                  <MenuItem value="best_practices">Best Practices</MenuItem>
                  <MenuItem value="troubleshooting">Troubleshooting</MenuItem>
                  <MenuItem value="vendor_docs">Vendor Docs</MenuItem>
                  <MenuItem value="config_examples">Config Examples</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={4}>
              <FormControl fullWidth size="small">
                <InputLabel>Vendor</InputLabel>
                <Select value={uploadVendor} onChange={(e) => setUploadVendor(e.target.value)} label="Vendor">
                  <MenuItem value="">Generic (all vendors)</MenuItem>
                  {Object.entries(VENDOR_CONFIG).map(([key, cfg]) => (
                    <MenuItem key={key} value={key}>{cfg.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={4}>
              <TextField
                fullWidth size="small" label="Tags (comma-separated)"
                value={uploadTags}
                onChange={(e) => setUploadTags(e.target.value)}
              />
            </Grid>
          </Grid>

          {/* Upload result */}
          {uploadResult && (
            <Alert severity="success" sx={{ mt: 2 }}>
              <Typography variant="body2" fontWeight="bold">
                Document processed successfully
              </Typography>
              <Typography variant="body2">
                {uploadResult.chunks_created} entries created from "{uploadResult.filename}"
                {uploadResult.metadata?.pages && ` (${uploadResult.metadata.pages} pages)`}
                {uploadResult.metadata?.text_length && ` — ${uploadResult.metadata.text_length.toLocaleString()} characters extracted`}
              </Typography>
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleUploadClose}>
            {uploadResult ? 'Done' : 'Cancel'}
          </Button>
          {!uploadResult && (
            <Button
              variant="contained"
              startIcon={uploading ? <CircularProgress size={20} color="inherit" /> : <CloudUploadIcon />}
              onClick={handleUpload}
              disabled={!uploadFile || uploading}
            >
              {uploading ? 'Uploading...' : 'Upload & Process'}
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default KnowledgeBase;
