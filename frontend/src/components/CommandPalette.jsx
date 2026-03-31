import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Dialog,
  DialogContent,
  TextField,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  Box,
  Chip,
  InputAdornment,
  Divider,
} from '@mui/material';
import {
  Search as SearchIcon,
  Dashboard as DashboardIcon,
  Security,
  Router as RouterIcon,
  Assessment,
  Devices as DevicesIcon,
  Schedule as ScheduleIcon,
  Group as GroupIcon,
  CalendarMonth,
  Backup,
  Notifications as NotificationsIcon,
  CloudUpload,
  CompareArrows,
  LibraryBooks,
  Hub as IntegrationIcon,
  Timeline as AnalyticsIcon,
  AdminPanelSettings as AdminIcon,
  ManageAccounts as ManageAccountsIcon,
  AccountTree as WorkflowIcon,
  Memory as HardwareIcon,
  Key as KeyIcon,
  SmartToy as AIIcon,
  AutoFixHigh as RuleBuilderIcon,
  Healing as RemediationIcon,
  Shield as AnomalyIcon,
  Hub as MCPHubIcon,
  Bolt as ImpactIcon,
  TrendingUp as PredictionIcon,
  Tune as OptimizerIcon,
  PrecisionManufacturing as MultiAgentIcon,
  History as HistoryIcon,
  MenuBook as MenuBookIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

const allCommands = [
  { label: 'Dashboard', path: '/', icon: <DashboardIcon />, category: 'Navigation', keywords: ['home', 'overview'] },
  { label: 'Devices', path: '/devices', icon: <DevicesIcon />, category: 'Network', keywords: ['router', 'switch', 'network'] },
  { label: 'Device Groups', path: '/device-groups', icon: <GroupIcon />, category: 'Network', keywords: ['group', 'cluster'] },
  { label: 'Discovery Groups', path: '/discovery-groups', icon: <ScheduleIcon />, category: 'Network', keywords: ['scan', 'discover', 'subnet'] },
  { label: 'Device Import', path: '/device-import', icon: <CloudUpload />, category: 'Network', keywords: ['csv', 'upload', 'bulk'] },
  { label: 'Device Health', path: '/health', icon: <RouterIcon />, category: 'Network', keywords: ['ping', 'status', 'reachability'] },
  { label: 'Hardware Inventory', path: '/hardware-inventory', icon: <HardwareIcon />, category: 'Network', keywords: ['chassis', 'optics', 'modules'] },
  { label: 'Audit Results', path: '/audits', icon: <Assessment />, category: 'Compliance', keywords: ['compliance', 'findings', 'results'] },
  { label: 'Audit Schedules', path: '/audit-schedules', icon: <CalendarMonth />, category: 'Compliance', keywords: ['cron', 'schedule', 'automated'] },
  { label: 'Rule Management', path: '/rules', icon: <Security />, category: 'Compliance', keywords: ['xpath', 'policy', 'check'] },
  { label: 'Rule Templates', path: '/rule-templates', icon: <LibraryBooks />, category: 'Compliance', keywords: ['cis', 'pci', 'nist', 'template'] },
  { label: 'Config Backups', path: '/config-backups', icon: <Backup />, category: 'Configuration', keywords: ['backup', 'snapshot', 'version'] },
  { label: 'Drift Detection', path: '/drift-detection', icon: <CompareArrows />, category: 'Configuration', keywords: ['change', 'drift', 'diff'] },
  { label: 'Notifications', path: '/notifications', icon: <NotificationsIcon />, category: 'Operations', keywords: ['webhook', 'slack', 'teams', 'alert'] },
  { label: 'Integration Hub', path: '/integrations', icon: <IntegrationIcon />, category: 'Operations', keywords: ['netbox', 'servicenow', 'ansible'] },
  { label: 'Workflows', path: '/workflows', icon: <WorkflowIcon />, category: 'Operations', keywords: ['dag', 'automation', 'pipeline'] },
  { label: 'Analytics', path: '/analytics', icon: <AnalyticsIcon />, category: 'Operations', keywords: ['trends', 'charts', 'reports'] },
  { label: 'AI Chat', path: '/ai-chat', icon: <AIIcon />, category: 'AI Features', keywords: ['ask', 'query', 'natural language', 'assistant'] },
  { label: 'AI Rule Builder', path: '/ai-rule-builder', icon: <RuleBuilderIcon />, category: 'AI Features', keywords: ['generate', 'create rule', 'nlp'] },
  { label: 'AI Remediation', path: '/ai-remediation', icon: <RemediationIcon />, category: 'AI Features', keywords: ['fix', 'heal', 'resolve'] },
  { label: 'AI Reports', path: '/ai-reports', icon: <Assessment />, category: 'AI Features', keywords: ['report', 'executive', 'summary'] },
  { label: 'Anomaly Detection', path: '/anomaly-detection', icon: <AnomalyIcon />, category: 'AI Features', keywords: ['anomaly', 'unusual', 'ml'] },
  { label: 'Impact Analysis', path: '/impact-analysis', icon: <ImpactIcon />, category: 'AI Features', keywords: ['blast radius', 'risk', 'change'] },
  { label: 'Compliance Forecast', path: '/compliance-prediction', icon: <PredictionIcon />, category: 'AI Features', keywords: ['predict', 'forecast', 'trend'] },
  { label: 'Config Intelligence', path: '/config-optimizer', icon: <OptimizerIcon />, category: 'AI Features', keywords: ['optimize', 'cleanup', 'unused'] },
  { label: 'Multi-Agent Ops', path: '/multi-agent-ops', icon: <MultiAgentIcon />, category: 'AI Features', keywords: ['orchestrate', 'agent', 'multi'] },
  { label: 'MCP Hub', path: '/mcp-hub', icon: <MCPHubIcon />, category: 'AI Features', keywords: ['mcp', 'protocol', 'integration'] },
  { label: 'AI History', path: '/ai-history', icon: <HistoryIcon />, category: 'AI Features', keywords: ['history', 'interactions', 'log'] },
  { label: 'Knowledge Base', path: '/knowledge-base', icon: <MenuBookIcon />, category: 'AI Features', keywords: ['rag', 'docs', 'knowledge'] },
  { label: 'License', path: '/license', icon: <KeyIcon />, category: 'Admin', keywords: ['license', 'key', 'tier'] },
  { label: 'User Management', path: '/user-management', icon: <ManageAccountsIcon />, category: 'Admin', keywords: ['users', 'roles', 'permissions'] },
  { label: 'Admin Dashboard', path: '/admin', icon: <AdminIcon />, category: 'Admin', keywords: ['admin', 'system', 'settings'] },
  { label: 'Settings', path: '/settings', icon: <SettingsIcon />, category: 'Admin', keywords: ['preferences', 'theme', 'config'] },
];

const CommandPalette = ({ open, onClose }) => {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const navigate = useNavigate();
  const inputRef = useRef(null);
  const listRef = useRef(null);

  const filtered = query.trim()
    ? allCommands.filter((cmd) => {
        const q = query.toLowerCase();
        return (
          cmd.label.toLowerCase().includes(q) ||
          cmd.category.toLowerCase().includes(q) ||
          cmd.keywords.some((k) => k.includes(q))
        );
      })
    : allCommands;

  // Group by category
  const grouped = filtered.reduce((acc, cmd) => {
    if (!acc[cmd.category]) acc[cmd.category] = [];
    acc[cmd.category].push(cmd);
    return acc;
  }, {});

  const flatList = Object.entries(grouped).flatMap(([, cmds]) => cmds);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  useEffect(() => {
    if (open) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [open]);

  const handleSelect = useCallback(
    (cmd) => {
      navigate(cmd.path);
      onClose();
    },
    [navigate, onClose]
  );

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => Math.min(prev + 1, flatList.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter' && flatList[selectedIndex]) {
      handleSelect(flatList[selectedIndex]);
    }
  };

  // Scroll selected item into view
  useEffect(() => {
    if (listRef.current) {
      const items = listRef.current.querySelectorAll('[data-cmd-item]');
      if (items[selectedIndex]) {
        items[selectedIndex].scrollIntoView({ block: 'nearest' });
      }
    }
  }, [selectedIndex]);

  let itemIndex = -1;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          position: 'fixed',
          top: '15%',
          m: 0,
          borderRadius: 3,
          maxHeight: '60vh',
        },
      }}
    >
      <DialogContent sx={{ p: 0 }}>
        <TextField
          inputRef={inputRef}
          fullWidth
          placeholder="Search pages, features, or type a command..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          variant="outlined"
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon color="action" />
              </InputAdornment>
            ),
            endAdornment: (
              <InputAdornment position="end">
                <Chip label="ESC" size="small" variant="outlined" sx={{ fontSize: 10 }} />
              </InputAdornment>
            ),
            sx: { fontSize: 16 },
          }}
          sx={{
            '& .MuiOutlinedInput-notchedOutline': { border: 'none' },
            borderBottom: 1,
            borderColor: 'divider',
          }}
        />
        <List ref={listRef} dense sx={{ maxHeight: '45vh', overflow: 'auto', py: 1 }}>
          {Object.entries(grouped).map(([category, cmds], catIdx) => (
            <React.Fragment key={category}>
              {catIdx > 0 && <Divider sx={{ my: 0.5 }} />}
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ px: 2, py: 0.5, display: 'block', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1 }}
              >
                {category}
              </Typography>
              {cmds.map((cmd) => {
                itemIndex++;
                const idx = itemIndex;
                return (
                  <ListItem key={cmd.path} disablePadding data-cmd-item>
                    <ListItemButton
                      selected={selectedIndex === idx}
                      onClick={() => handleSelect(cmd)}
                      sx={{
                        mx: 1,
                        borderRadius: 1,
                        '&.Mui-selected': {
                          backgroundColor: 'primary.main',
                          color: 'primary.contrastText',
                          '& .MuiListItemIcon-root': { color: 'primary.contrastText' },
                          '& .MuiTypography-root': { color: 'primary.contrastText' },
                          '&:hover': { backgroundColor: 'primary.dark' },
                        },
                      }}
                    >
                      <ListItemIcon sx={{ minWidth: 36 }}>{cmd.icon}</ListItemIcon>
                      <ListItemText primary={cmd.label} />
                      <Typography variant="caption" color="text.secondary" sx={{ opacity: 0.6 }}>
                        {cmd.category}
                      </Typography>
                    </ListItemButton>
                  </ListItem>
                );
              })}
            </React.Fragment>
          ))}
          {flatList.length === 0 && (
            <Box sx={{ p: 3, textAlign: 'center' }}>
              <Typography color="text.secondary">No results for "{query}"</Typography>
            </Box>
          )}
        </List>
        <Box sx={{ px: 2, py: 1, borderTop: 1, borderColor: 'divider', display: 'flex', gap: 2 }}>
          <Typography variant="caption" color="text.secondary">
            <Chip label="↑↓" size="small" variant="outlined" sx={{ fontSize: 10, mr: 0.5 }} /> Navigate
          </Typography>
          <Typography variant="caption" color="text.secondary">
            <Chip label="↵" size="small" variant="outlined" sx={{ fontSize: 10, mr: 0.5 }} /> Open
          </Typography>
          <Typography variant="caption" color="text.secondary">
            <Chip label="Ctrl+K" size="small" variant="outlined" sx={{ fontSize: 10, mr: 0.5 }} /> Toggle
          </Typography>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default CommandPalette;
