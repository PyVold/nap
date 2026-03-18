import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import {
  ThemeProvider,
  createTheme,
  CssBaseline,
  Box,
  AppBar,
  Toolbar,
  Typography,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  IconButton,
  Divider,
  CircularProgress,
  Chip,
  Button,
  Collapse,
  Tooltip,
  Breadcrumbs,
  Link,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Security,
  Router as RouterIcon,
  Assessment,
  Devices as DevicesIcon,
  Menu as MenuIcon,
  Brightness4,
  Brightness7,
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
  Logout as LogoutIcon,
  AccountTree as WorkflowIcon,
  Memory as HardwareIcon,
  Key as KeyIcon,
  SmartToy as AIIcon,
  AutoFixHigh as RuleBuilderIcon,
  Healing as RemediationIcon,
  Assessment as ReportsIcon,
  Shield as AnomalyIcon,
  Hub as MCPHubIcon,
  Bolt as ImpactIcon,
  TrendingUp as PredictionIcon,
  Tune as OptimizerIcon,
  PrecisionManufacturing as MultiAgentIcon,
  History as HistoryIcon,
  MenuBook as MenuBookIcon,
  ExpandLess,
  ExpandMore,
  Search as SearchIcon,
  Settings as SettingsIcon,
  NavigateNext,
  Home,
} from '@mui/icons-material';
import Dashboard from './components/Dashboard';
import RuleManagement from './components/RuleManagement';
import DeviceHealth from './components/DeviceHealth';
import AuditResults from './components/AuditResults';
import DeviceManagement from './components/DeviceManagement';
import DiscoveryGroups from './components/DiscoveryGroups';
import DeviceGroups from './components/DeviceGroups';
import AuditSchedules from './components/AuditSchedules';
import ConfigBackups from './components/ConfigBackups';
import Notifications from './components/Notifications';
import DeviceImport from './components/DeviceImport';
import DriftDetection from './components/DriftDetection';
import RuleTemplates from './components/RuleTemplates';
import Integrations from './components/Integrations';
import Analytics from './components/Analytics';
import UserManagement from './components/UserManagement';
import Workflows from './components/Workflows';
import HardwareInventory from './components/HardwareInventory';
import LicenseManagement from './components/LicenseManagement';
import AdminDashboard from './components/AdminDashboard';
import AIChat from './components/AIChat';
import AIRuleBuilder from './components/AIRuleBuilder';
import AIRemediation from './components/AIRemediation';
import AIReports from './components/AIReports';
import AnomalyDetection from './components/AnomalyDetection';
import MCPHub from './components/MCPHub';
import ImpactAnalysis from './components/ImpactAnalysis';
import CompliancePrediction from './components/CompliancePrediction';
import ConfigOptimizer from './components/ConfigOptimizer';
import MultiAgentOps from './components/MultiAgentOps';
import AIHistory from './components/AIHistory';
import KnowledgeBase from './components/KnowledgeBase';
import Login from './components/Login';
import Settings from './components/Settings';
import ApiActivityIndicator from './components/ApiActivityIndicator';
import LicenseGuard from './components/LicenseGuard';
import ModuleGuard from './components/ModuleGuard';
import ErrorBoundary from './components/ErrorBoundary';
import CommandPalette from './components/CommandPalette';
import NotificationCenter from './components/NotificationCenter';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { LicenseProvider } from './contexts/LicenseContext';
import { fetchModuleMappings, mapRouteToModule } from './utils/moduleMappings';

const drawerWidth = 260;

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#667eea',
    },
    secondary: {
      main: '#764ba2',
    },
    background: {
      default: '#f8f9fa',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          fontWeight: 600,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
          border: '1px solid rgba(0,0,0,0.06)',
        },
      },
    },
  },
});

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#667eea',
    },
    secondary: {
      main: '#764ba2',
    },
    background: {
      default: '#0f1117',
      paper: '#1a1d28',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          fontWeight: 600,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
          border: '1px solid rgba(255,255,255,0.06)',
        },
      },
    },
  },
});

// Sidebar section definitions
const sidebarSections = [
  {
    id: 'main',
    label: null, // No header for main section
    items: [
      { text: 'Dashboard', icon: <DashboardIcon />, path: '/', module: null },
    ],
  },
  {
    id: 'network',
    label: 'Network',
    items: [
      { text: 'Devices', icon: <DevicesIcon />, path: '/devices', module: 'devices' },
      { text: 'Device Groups', icon: <GroupIcon />, path: '/device-groups', module: 'device_groups' },
      { text: 'Discovery', icon: <ScheduleIcon />, path: '/discovery-groups', module: 'discovery_groups' },
      { text: 'Import', icon: <CloudUpload />, path: '/device-import', module: 'device_import' },
      { text: 'Health', icon: <RouterIcon />, path: '/health', module: 'health' },
      { text: 'Hardware', icon: <HardwareIcon />, path: '/hardware-inventory', module: 'hardware_inventory' },
    ],
  },
  {
    id: 'compliance',
    label: 'Compliance',
    items: [
      { text: 'Audit Results', icon: <Assessment />, path: '/audits', module: 'audit' },
      { text: 'Schedules', icon: <CalendarMonth />, path: '/audit-schedules', module: 'audit_schedules' },
      { text: 'Rules', icon: <Security />, path: '/rules', module: 'rules' },
      { text: 'Templates', icon: <LibraryBooks />, path: '/rule-templates', module: 'rule_templates' },
    ],
  },
  {
    id: 'config',
    label: 'Configuration',
    items: [
      { text: 'Backups', icon: <Backup />, path: '/config-backups', module: 'config_backups' },
      { text: 'Drift Detection', icon: <CompareArrows />, path: '/drift-detection', module: 'drift_detection' },
    ],
  },
  {
    id: 'operations',
    label: 'Operations',
    items: [
      { text: 'Notifications', icon: <NotificationsIcon />, path: '/notifications', module: 'notifications' },
      { text: 'Integrations', icon: <IntegrationIcon />, path: '/integrations', module: 'integrations' },
      { text: 'Workflows', icon: <WorkflowIcon />, path: '/workflows', module: 'workflows' },
      { text: 'Analytics', icon: <AnalyticsIcon />, path: '/analytics', module: 'analytics' },
    ],
  },
  {
    id: 'ai',
    label: 'AI & Intelligence',
    items: [
      { text: 'AI Chat', icon: <AIIcon />, path: '/ai-chat', module: 'analytics' },
      { text: 'Rule Builder', icon: <RuleBuilderIcon />, path: '/ai-rule-builder', module: 'analytics' },
      { text: 'Remediation', icon: <RemediationIcon />, path: '/ai-remediation', module: 'analytics' },
      { text: 'Reports', icon: <ReportsIcon />, path: '/ai-reports', module: 'analytics' },
      { text: 'Anomaly Detection', icon: <AnomalyIcon />, path: '/anomaly-detection', module: 'analytics' },
      { text: 'Impact Analysis', icon: <ImpactIcon />, path: '/impact-analysis', module: 'analytics' },
      { text: 'Forecast', icon: <PredictionIcon />, path: '/compliance-prediction', module: 'analytics' },
      { text: 'Config Intelligence', icon: <OptimizerIcon />, path: '/config-optimizer', module: 'analytics' },
      { text: 'Multi-Agent', icon: <MultiAgentIcon />, path: '/multi-agent-ops', module: 'analytics' },
      { text: 'MCP Hub', icon: <MCPHubIcon />, path: '/mcp-hub', module: 'analytics' },
      { text: 'Knowledge Base', icon: <MenuBookIcon />, path: '/knowledge-base', module: 'analytics' },
      { text: 'AI History', icon: <HistoryIcon />, path: '/ai-history', module: 'analytics' },
    ],
  },
  {
    id: 'admin',
    label: 'Admin',
    items: [
      { text: 'License', icon: <KeyIcon />, path: '/license', module: null },
      { text: 'Settings', icon: <SettingsIcon />, path: '/settings', module: null },
      { text: 'Users', icon: <ManageAccountsIcon />, path: '/user-management', module: null, adminOnly: true },
      { text: 'Admin Panel', icon: <AdminIcon />, path: '/admin', module: null, adminOnly: true },
    ],
  },
];

// Build flat list of all items for route lookups
const allFlatItems = sidebarSections.flatMap((s) => s.items);

// Breadcrumb path map
const breadcrumbMap = {};
sidebarSections.forEach((section) => {
  section.items.forEach((item) => {
    breadcrumbMap[item.path] = {
      label: item.text,
      section: section.label,
    };
  });
});

function AppContent() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('nap_dark_mode') === 'true');
  const [moduleMappings, setModuleMappings] = useState(null);
  const [collapsedSections, setCollapsedSections] = useState(() => {
    try { return JSON.parse(localStorage.getItem('nap_collapsed_sections')) || {}; } catch { return {}; }
  });
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, isAuthenticated, loading, logout, userModules, isAdmin } = useAuth();

  // Persist dark mode
  useEffect(() => {
    localStorage.setItem('nap_dark_mode', darkMode);
  }, [darkMode]);

  // Persist collapsed sections
  useEffect(() => {
    localStorage.setItem('nap_collapsed_sections', JSON.stringify(collapsedSections));
  }, [collapsedSections]);

  // Global keyboard shortcut for command palette
  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // Fetch module mappings on mount
  useEffect(() => {
    const loadModuleMappings = async () => {
      try {
        const mappings = await fetchModuleMappings();
        setModuleMappings(mappings);
      } catch (error) {
        console.error('Failed to load module mappings:', error);
      }
    };
    loadModuleMappings();
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!loading && !isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, loading, navigate]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  const handleDrawerToggle = () => setMobileOpen(!mobileOpen);

  const toggleSection = (sectionId) => {
    setCollapsedSections((prev) => ({ ...prev, [sectionId]: !prev[sectionId] }));
  };

  // Check if user has access to a menu item
  const hasAccess = (item) => {
    if (item.adminOnly && !isAdmin) return false;
    if (!item.module) return true;
    if (!userModules || userModules.length === 0) return false;
    const licenseModule = mapRouteToModule(item.module, moduleMappings);
    return userModules.includes(licenseModule);
  };

  // Check if current path is in a section
  const isSectionActive = (section) => section.items.some((item) => location.pathname === item.path);

  const drawer = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Sidebar Header */}
      <Toolbar sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', minHeight: '56px !important' }}>
        <Box display="flex" alignItems="center" gap={1} width="100%">
          <Typography variant="h6" noWrap color="white" fontWeight="bold" sx={{ fontSize: 16 }}>
            NAP
          </Typography>
          <Chip
            label="v2.0"
            size="small"
            sx={{ height: 18, fontSize: 10, color: 'rgba(255,255,255,0.8)', borderColor: 'rgba(255,255,255,0.3)', bgcolor: 'transparent' }}
            variant="outlined"
          />
        </Box>
      </Toolbar>

      {/* Search button */}
      <Box sx={{ px: 1.5, py: 1 }}>
        <Button
          fullWidth
          variant="outlined"
          startIcon={<SearchIcon />}
          onClick={() => setCommandPaletteOpen(true)}
          sx={{
            justifyContent: 'flex-start',
            color: 'text.secondary',
            borderColor: 'divider',
            textTransform: 'none',
            fontWeight: 400,
            fontSize: 13,
            py: 0.5,
          }}
        >
          Search...
          <Chip label="Ctrl+K" size="small" variant="outlined" sx={{ ml: 'auto', fontSize: 10, height: 18, borderColor: 'divider' }} />
        </Button>
      </Box>

      {/* Sections */}
      <Box sx={{ flex: 1, overflow: 'auto', px: 0.5 }}>
        {sidebarSections.map((section) => {
          const visibleItems = section.items.filter(hasAccess);
          if (visibleItems.length === 0) return null;

          const isCollapsed = collapsedSections[section.id] && !isSectionActive(section);

          return (
            <Box key={section.id} sx={{ mb: 0.5 }}>
              {section.label && (
                <ListItemButton
                  onClick={() => toggleSection(section.id)}
                  dense
                  sx={{
                    py: 0.25,
                    px: 1.5,
                    borderRadius: 1,
                    minHeight: 28,
                  }}
                >
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, fontSize: 10, flexGrow: 1 }}
                  >
                    {section.label}
                  </Typography>
                  {isCollapsed ? <ExpandMore sx={{ fontSize: 16, color: 'text.disabled' }} /> : <ExpandLess sx={{ fontSize: 16, color: 'text.disabled' }} />}
                </ListItemButton>
              )}
              <Collapse in={!isCollapsed} timeout="auto">
                <List dense disablePadding>
                  {visibleItems.map((item) => (
                    <ListItem key={item.path} disablePadding sx={{ px: 0.5 }}>
                      <ListItemButton
                        selected={location.pathname === item.path}
                        onClick={() => {
                          navigate(item.path);
                          setMobileOpen(false);
                        }}
                        sx={{
                          py: 0.5,
                          px: 1.5,
                          borderRadius: 1.5,
                          mb: 0.25,
                          '&.Mui-selected': {
                            backgroundColor: darkMode ? 'rgba(102, 126, 234, 0.25)' : 'rgba(102, 126, 234, 0.12)',
                            '&:hover': {
                              backgroundColor: darkMode ? 'rgba(102, 126, 234, 0.35)' : 'rgba(102, 126, 234, 0.18)',
                            },
                          },
                        }}
                      >
                        <ListItemIcon
                          sx={{
                            minWidth: 32,
                            color: location.pathname === item.path ? '#667eea' : 'text.secondary',
                            '& .MuiSvgIcon-root': { fontSize: 18 },
                          }}
                        >
                          {item.icon}
                        </ListItemIcon>
                        <ListItemText
                          primary={item.text}
                          sx={{
                            '& .MuiListItemText-primary': {
                              fontSize: 13,
                              fontWeight: location.pathname === item.path ? 600 : 400,
                              color: location.pathname === item.path ? '#667eea' : 'text.primary',
                            },
                          }}
                        />
                      </ListItemButton>
                    </ListItem>
                  ))}
                </List>
              </Collapse>
            </Box>
          );
        })}
      </Box>
    </Box>
  );

  // Build breadcrumbs
  const currentPage = breadcrumbMap[location.pathname];

  return (
    <ThemeProvider theme={darkMode ? darkTheme : theme}>
      <CssBaseline />
      <ApiActivityIndicator />
      <CommandPalette open={commandPaletteOpen} onClose={() => setCommandPaletteOpen(false)} />
      <Box sx={{ display: 'flex' }}>
        <AppBar
          position="fixed"
          elevation={0}
          sx={{
            width: { sm: `calc(100% - ${drawerWidth}px)` },
            ml: { sm: `${drawerWidth}px` },
            background: darkMode
              ? 'rgba(26, 29, 40, 0.95)'
              : 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(20px)',
            borderBottom: 1,
            borderColor: 'divider',
          }}
        >
          <Toolbar variant="dense">
            <IconButton
              edge="start"
              onClick={handleDrawerToggle}
              sx={{ mr: 2, display: { sm: 'none' }, color: 'text.primary' }}
            >
              <MenuIcon />
            </IconButton>

            {/* Breadcrumbs */}
            <Box sx={{ flexGrow: 1 }}>
              <Breadcrumbs separator={<NavigateNext sx={{ fontSize: 14 }} />} sx={{ fontSize: 13 }}>
                <Link
                  underline="hover"
                  color="text.secondary"
                  onClick={() => navigate('/')}
                  sx={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 0.5, fontSize: 13 }}
                >
                  <Home sx={{ fontSize: 16 }} />
                </Link>
                {currentPage?.section && (
                  <Typography color="text.secondary" sx={{ fontSize: 13 }}>
                    {currentPage.section}
                  </Typography>
                )}
                <Typography color="text.primary" fontWeight={600} sx={{ fontSize: 13 }}>
                  {currentPage?.label || 'Dashboard'}
                </Typography>
              </Breadcrumbs>
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              {/* Search shortcut */}
              <Tooltip title="Search (Ctrl+K)">
                <IconButton onClick={() => setCommandPaletteOpen(true)} sx={{ color: 'text.secondary' }} size="small">
                  <SearchIcon fontSize="small" />
                </IconButton>
              </Tooltip>

              {/* Notification Center */}
              <NotificationCenter />

              {/* Dark mode toggle */}
              <Tooltip title={darkMode ? 'Light mode' : 'Dark mode'}>
                <IconButton onClick={() => setDarkMode(!darkMode)} sx={{ color: 'text.secondary' }} size="small">
                  {darkMode ? <Brightness7 fontSize="small" /> : <Brightness4 fontSize="small" />}
                </IconButton>
              </Tooltip>

              {/* User info */}
              <Chip
                label={user?.username || 'Unknown'}
                size="small"
                variant="outlined"
                sx={{ fontSize: 12, height: 26 }}
              />

              {/* Settings */}
              <Tooltip title="Settings">
                <IconButton onClick={() => navigate('/settings')} sx={{ color: 'text.secondary' }} size="small">
                  <SettingsIcon fontSize="small" />
                </IconButton>
              </Tooltip>

              {/* Logout */}
              <Tooltip title="Logout">
                <IconButton onClick={handleLogout} sx={{ color: 'text.secondary' }} size="small">
                  <LogoutIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
          </Toolbar>
        </AppBar>

        <Box
          component="nav"
          sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
        >
          <Drawer
            variant="temporary"
            open={mobileOpen}
            onClose={handleDrawerToggle}
            ModalProps={{ keepMounted: true }}
            sx={{
              display: { xs: 'block', sm: 'none' },
              '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
            }}
          >
            {drawer}
          </Drawer>
          <Drawer
            variant="permanent"
            sx={{
              display: { xs: 'none', sm: 'block' },
              '& .MuiDrawer-paper': {
                boxSizing: 'border-box',
                width: drawerWidth,
                borderRight: 1,
                borderColor: 'divider',
              },
            }}
            open
          >
            {drawer}
          </Drawer>
        </Box>

        <Box
          component="main"
          sx={{
            flexGrow: 1,
            p: 0,
            width: { sm: `calc(100% - ${drawerWidth}px)` },
            minHeight: '100vh',
            backgroundColor: darkMode ? '#0f1117' : '#f8f9fa',
          }}
        >
          <Toolbar variant="dense" />
          <Routes>
            <Route path="/" element={<LicenseGuard><Dashboard /></LicenseGuard>} />
            <Route path="/devices" element={<LicenseGuard><ModuleGuard module="devices"><DeviceManagement /></ModuleGuard></LicenseGuard>} />
            <Route path="/device-groups" element={<LicenseGuard><ModuleGuard module="device_groups"><DeviceGroups /></ModuleGuard></LicenseGuard>} />
            <Route path="/discovery-groups" element={<LicenseGuard><ModuleGuard module="discovery_groups"><DiscoveryGroups /></ModuleGuard></LicenseGuard>} />
            <Route path="/device-import" element={<LicenseGuard><ModuleGuard module="device_import"><DeviceImport /></ModuleGuard></LicenseGuard>} />
            <Route path="/audits" element={<LicenseGuard><ModuleGuard module="audit"><AuditResults /></ModuleGuard></LicenseGuard>} />
            <Route path="/audit-schedules" element={<LicenseGuard><ModuleGuard module="audit_schedules"><AuditSchedules /></ModuleGuard></LicenseGuard>} />
            <Route path="/rules" element={<LicenseGuard><ModuleGuard module="rules"><RuleManagement /></ModuleGuard></LicenseGuard>} />
            <Route path="/rule-templates" element={<LicenseGuard><ModuleGuard module="rule_templates"><RuleTemplates /></ModuleGuard></LicenseGuard>} />
            <Route path="/config-backups" element={<LicenseGuard><ModuleGuard module="config_backups"><ConfigBackups /></ModuleGuard></LicenseGuard>} />
            <Route path="/drift-detection" element={<LicenseGuard><ModuleGuard module="drift_detection"><DriftDetection /></ModuleGuard></LicenseGuard>} />
            <Route path="/notifications" element={<LicenseGuard><ModuleGuard module="notifications"><Notifications /></ModuleGuard></LicenseGuard>} />
            <Route path="/health" element={<LicenseGuard><ModuleGuard module="health"><DeviceHealth /></ModuleGuard></LicenseGuard>} />
            <Route path="/hardware-inventory" element={<LicenseGuard><ModuleGuard module="hardware_inventory"><HardwareInventory /></ModuleGuard></LicenseGuard>} />
            <Route path="/integrations" element={<LicenseGuard><ModuleGuard module="integrations"><Integrations /></ModuleGuard></LicenseGuard>} />
            <Route path="/workflows" element={<LicenseGuard><ModuleGuard module="workflows"><Workflows /></ModuleGuard></LicenseGuard>} />
            <Route path="/analytics" element={<LicenseGuard><ModuleGuard module="analytics"><Analytics /></ModuleGuard></LicenseGuard>} />
            <Route path="/ai-chat" element={<LicenseGuard><ModuleGuard module="analytics"><AIChat /></ModuleGuard></LicenseGuard>} />
            <Route path="/ai-rule-builder" element={<LicenseGuard><ModuleGuard module="analytics"><AIRuleBuilder /></ModuleGuard></LicenseGuard>} />
            <Route path="/ai-remediation" element={<LicenseGuard><ModuleGuard module="analytics"><AIRemediation /></ModuleGuard></LicenseGuard>} />
            <Route path="/ai-reports" element={<LicenseGuard><ModuleGuard module="analytics"><AIReports /></ModuleGuard></LicenseGuard>} />
            <Route path="/anomaly-detection" element={<LicenseGuard><ModuleGuard module="analytics"><AnomalyDetection /></ModuleGuard></LicenseGuard>} />
            <Route path="/mcp-hub" element={<LicenseGuard><ModuleGuard module="analytics"><MCPHub /></ModuleGuard></LicenseGuard>} />
            <Route path="/impact-analysis" element={<LicenseGuard><ModuleGuard module="analytics"><ImpactAnalysis /></ModuleGuard></LicenseGuard>} />
            <Route path="/compliance-prediction" element={<LicenseGuard><ModuleGuard module="analytics"><CompliancePrediction /></ModuleGuard></LicenseGuard>} />
            <Route path="/config-optimizer" element={<LicenseGuard><ModuleGuard module="analytics"><ConfigOptimizer /></ModuleGuard></LicenseGuard>} />
            <Route path="/multi-agent-ops" element={<LicenseGuard><ModuleGuard module="analytics"><MultiAgentOps /></ModuleGuard></LicenseGuard>} />
            <Route path="/ai-history" element={<LicenseGuard><ModuleGuard module="analytics"><AIHistory /></ModuleGuard></LicenseGuard>} />
            <Route path="/knowledge-base" element={<LicenseGuard><ModuleGuard module="analytics"><KnowledgeBase /></ModuleGuard></LicenseGuard>} />
            <Route path="/settings" element={<LicenseGuard><Settings /></LicenseGuard>} />
            <Route path="/admin" element={<LicenseGuard><AdminDashboard /></LicenseGuard>} />
            <Route path="/user-management" element={<LicenseGuard><UserManagement /></LicenseGuard>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Box>
      </Box>
    </ThemeProvider>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <Router>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/license" element={<LicensePageWrapper />} />
            <Route path="/*" element={
              <LicenseProvider>
                <AppContent />
              </LicenseProvider>
            } />
          </Routes>
        </Router>
      </AuthProvider>
    </ErrorBoundary>
  );
}

function LicensePageWrapper() {
  const { isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, loading, navigate]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <ErrorBoundary>
      <LicenseProvider>
        <LicenseManagement />
      </LicenseProvider>
    </ErrorBoundary>
  );
}

export default App;
