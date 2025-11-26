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
  MonetizationOn as LicenseIcon,
  DeviceHub as TopologyIcon,
  Description as TemplateIcon,
  Timeline as AnalyticsIcon,
  AdminPanelSettings as AdminIcon,
  ManageAccounts as ManageAccountsIcon,
  Logout as LogoutIcon,
  AccountTree as WorkflowIcon,
  Memory as HardwareIcon,
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
import Licensing from './components/Licensing';
import Topology from './components/Topology';
import ConfigTemplates from './components/ConfigTemplates';
import Analytics from './components/Analytics';
import AdminPanel from './components/AdminPanel';
import UserManagement from './components/UserManagement';
import Workflows from './components/Workflows';
import HardwareInventory from './components/HardwareInventory';
import Login from './components/Login';
import ApiActivityIndicator from './components/ApiActivityIndicator';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import api from './api/api';

const drawerWidth = 240;

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#667eea',
    },
    secondary: {
      main: '#764ba2',
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
          boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
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
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
        },
      },
    },
  },
});

function AppContent() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, isAuthenticated, loading, logout, userModules } = useAuth();

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

  // Show loading while checking authentication
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  // Don't render if not authenticated (will redirect)
  if (!isAuthenticated) {
    return null;
  }

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  // Module name mapping to menu items
  const allMenuItems = [
    { text: 'Dashboard', icon: <DashboardIcon />, path: '/', module: null }, // Always visible
    { text: 'Devices', icon: <DevicesIcon />, path: '/devices', module: 'devices' },
    { text: 'Device Groups', icon: <GroupIcon />, path: '/device-groups', module: 'device_groups' },
    { text: 'Discovery Groups', icon: <ScheduleIcon />, path: '/discovery-groups', module: 'discovery_groups' },
    { text: 'Device Import', icon: <CloudUpload />, path: '/device-import', module: 'device_import' },
    { text: 'Audit Results', icon: <Assessment />, path: '/audits', module: 'audit' },
    { text: 'Audit Schedules', icon: <CalendarMonth />, path: '/audit-schedules', module: 'audit_schedules' },
    { text: 'Rule Management', icon: <Security />, path: '/rules', module: 'rules' },
    { text: 'Rule Templates', icon: <LibraryBooks />, path: '/rule-templates', module: 'rule_templates' },
    { text: 'Config Backups', icon: <Backup />, path: '/config-backups', module: 'config_backups' },
    { text: 'Drift Detection', icon: <CompareArrows />, path: '/drift-detection', module: 'drift_detection' },
    { text: 'Notifications', icon: <NotificationsIcon />, path: '/notifications', module: 'notifications' },
    { text: 'Device Health', icon: <RouterIcon />, path: '/health', module: 'health' },
    { text: 'Hardware Inventory', icon: <HardwareIcon />, path: '/hardware-inventory', module: 'hardware_inventory' },
    { text: 'divider', isDivider: true },
    { text: 'Integration Hub', icon: <IntegrationIcon />, path: '/integrations', module: 'integrations' },
    { text: 'Licensing', icon: <LicenseIcon />, path: '/licensing', module: 'licensing' },
    { text: 'Topology', icon: <TopologyIcon />, path: '/topology', module: 'topology' },
    { text: 'Config Templates', icon: <TemplateIcon />, path: '/config-templates', module: 'config_templates' },
    { text: 'Workflows', icon: <WorkflowIcon />, path: '/workflows', module: 'workflows' },
    { text: 'Analytics', icon: <AnalyticsIcon />, path: '/analytics', module: 'analytics' },
    { text: 'divider', isDivider: true },
    { text: 'User Management', icon: <ManageAccountsIcon />, path: '/user-management', module: null, adminOnly: true }, // Admin only
    { text: 'Admin Panel', icon: <AdminIcon />, path: '/admin', module: null, adminOnly: true }, // Admin only
  ];

  // Filter menu items based on user role and module access
  const menuItems = allMenuItems.filter(item => {
    // Always show dividers
    if (item.isDivider) return true;

    // Hide admin panel for non-admins
    if (item.adminOnly && user?.role !== 'admin') return false;

    // If item doesn't require a specific module (like Dashboard), show it
    if (!item.module) return true;

    // If userModules is empty, show all (could be superuser or still loading)
    // This prevents hiding all menus during initial load
    if (!userModules || userModules.length === 0) return true;

    // Check if user has access to this module
    return userModules.includes(item.module);
  });

  const drawer = (
    <Box>
      <Toolbar sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
        <Typography variant="h6" noWrap component="div" color="white" fontWeight="bold">
          Network Audit
        </Typography>
      </Toolbar>
      <Divider />
      <List>
        {menuItems.map((item) => {
          if (item.isDivider) {
            return <Divider key={item.text} sx={{ my: 1 }} />;
          }
          return (
            <ListItem key={item.text} disablePadding>
              <ListItemButton
                selected={location.pathname === item.path}
                onClick={() => {
                  navigate(item.path);
                  setMobileOpen(false);
                }}
                sx={{
                  '&.Mui-selected': {
                    backgroundColor: darkMode ? 'rgba(102, 126, 234, 0.3)' : 'rgba(102, 126, 234, 0.1)',
                    borderLeft: '4px solid #667eea',
                  },
                }}
              >
                <ListItemIcon
                  sx={{
                    color: location.pathname === item.path ? '#667eea' : 'inherit',
                  }}
                >
                  {item.icon}
                </ListItemIcon>
                <ListItemText
                  primary={item.text}
                  sx={{
                    '& .MuiListItemText-primary': {
                      fontWeight: location.pathname === item.path ? 600 : 400,
                    },
                  }}
                />
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>
    </Box>
  );

  return (
    <ThemeProvider theme={darkMode ? darkTheme : theme}>
      <CssBaseline />
      <ApiActivityIndicator />
      <Box sx={{ display: 'flex' }}>
        <AppBar
          position="fixed"
          sx={{
            width: { sm: `calc(100% - ${drawerWidth}px)` },
            ml: { sm: `${drawerWidth}px` },
            background: darkMode
              ? 'linear-gradient(135deg, #434343 0%, #000000 100%)'
              : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          }}
        >
          <Toolbar>
            <IconButton
              color="inherit"
              edge="start"
              onClick={handleDrawerToggle}
              sx={{ mr: 2, display: { sm: 'none' } }}
            >
              <MenuIcon />
            </IconButton>
            <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
              {menuItems.find((item) => item.path === location.pathname)?.text || 'Dashboard'}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Chip
                label={`${user?.username || 'Unknown'} (${user?.role || 'viewer'})`}
                color="primary"
                variant="outlined"
                size="small"
                sx={{ color: 'white', borderColor: 'rgba(255,255,255,0.5)' }}
              />
              <IconButton onClick={() => setDarkMode(!darkMode)} color="inherit">
                {darkMode ? <Brightness7 /> : <Brightness4 />}
              </IconButton>
              <Button
                color="inherit"
                startIcon={<LogoutIcon />}
                onClick={handleLogout}
                size="small"
              >
                Logout
              </Button>
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
              '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
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
            backgroundColor: darkMode ? '#121212' : '#f5f5f5',
          }}
        >
          <Toolbar />
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/devices" element={<DeviceManagement />} />
            <Route path="/device-groups" element={<DeviceGroups />} />
            <Route path="/discovery-groups" element={<DiscoveryGroups />} />
            <Route path="/device-import" element={<DeviceImport />} />
            <Route path="/audits" element={<AuditResults />} />
            <Route path="/audit-schedules" element={<AuditSchedules />} />
            <Route path="/rules" element={<RuleManagement />} />
            <Route path="/rule-templates" element={<RuleTemplates />} />
            <Route path="/config-backups" element={<ConfigBackups />} />
            <Route path="/drift-detection" element={<DriftDetection />} />
            <Route path="/notifications" element={<Notifications />} />
            <Route path="/health" element={<DeviceHealth />} />
            <Route path="/hardware-inventory" element={<HardwareInventory />} />
            <Route path="/integrations" element={<Integrations />} />
            <Route path="/licensing" element={<Licensing />} />
            <Route path="/topology" element={<Topology />} />
            <Route path="/config-templates" element={<ConfigTemplates />} />
            <Route path="/workflows" element={<Workflows />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/admin" element={<AdminPanel />} />
            <Route path="/user-management" element={<UserManagement />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Box>
      </Box>
    </ThemeProvider>
  );
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/*" element={<AppContent />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
