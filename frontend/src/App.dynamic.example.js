/**
 * Example: Dynamic App.js with Service Discovery
 *
 * This shows how to integrate the service discovery into your React app.
 * Replace your current App.js with this pattern.
 */

import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Box, CircularProgress, Typography } from '@mui/material';

// Service Discovery
import serviceDiscovery from './services/serviceDiscovery';

// Layout Components
import Sidebar from './components/Sidebar';
import Header from './components/Header';

// Import your existing page components
import Dashboard from './pages/Dashboard';
import Devices from './pages/Devices';
import DiscoveryGroups from './pages/DiscoveryGroups';
import Health from './pages/Health';
import Rules from './pages/Rules';
import Audits from './pages/Audits';
import ConfigBackups from './pages/ConfigBackups';
import DriftDetection from './pages/DriftDetection';
import HardwareInventory from './pages/HardwareInventory';
import Admin from './pages/Admin';
import UserManagement from './pages/UserManagement';
import Integrations from './pages/Integrations';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

// Route mapping - maps service UI routes to React components
const ROUTE_COMPONENTS = {
  '/devices': Devices,
  '/discovery': DiscoveryGroups,
  '/health': Health,
  '/rules': Rules,
  '/audits': Audits,
  '/backups': ConfigBackups,
  '/drift': DriftDetection,
  '/inventory': HardwareInventory,
  '/admin': Admin,
  '/users': UserManagement,
  '/integrations': Integrations,
};

function App() {
  const [servicesLoaded, setServicesLoaded] = useState(false);
  const [services, setServices] = useState([]);
  const [navItems, setNavItems] = useState([]);
  const [error, setError] = useState(null);

  // Discover services on app startup
  useEffect(() => {
    async function loadServices() {
      try {
        console.log('🔍 Discovering services...');
        const discoveredServices = await serviceDiscovery.discoverServices();
        setServices(discoveredServices);

        // Build navigation items from discovered services
        const navigation = serviceDiscovery.getNavigationItems();
        setNavItems(navigation);

        setServicesLoaded(true);
        console.log('✅ Services loaded successfully');
      } catch (err) {
        console.error('❌ Failed to load services:', err);
        setError('Failed to connect to services. Please try again later.');
        setServicesLoaded(true); // Still show UI with error
      }
    }

    loadServices();
  }, []);

  // Show loading spinner while discovering services
  if (!servicesLoaded) {
    return (
      <Box
        display="flex"
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        minHeight="100vh"
        gap={2}
      >
        <CircularProgress size={60} />
        <Typography variant="h6">Discovering services...</Typography>
      </Box>
    );
  }

  // Show error if service discovery failed
  if (error) {
    return (
      <Box
        display="flex"
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        minHeight="100vh"
        gap={2}
      >
        <Typography variant="h5" color="error">
          {error}
        </Typography>
        <Typography variant="body2">
          The API Gateway may be offline. Please check your connection.
        </Typography>
      </Box>
    );
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Box sx={{ display: 'flex', minHeight: '100vh' }}>
          {/* Sidebar with dynamic navigation */}
          <Sidebar navItems={navItems} services={services} />

          {/* Main content area */}
          <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
            <Header />

            {/* Dynamic Routes based on discovered services */}
            <Routes>
              {/* Dashboard (always available) */}
              <Route path="/" element={<Dashboard />} />

              {/* Dynamically create routes for each service */}
              {navItems.map(item => {
                const Component = ROUTE_COMPONENTS[item.route];
                if (Component) {
                  return (
                    <Route
                      key={item.route}
                      path={item.route}
                      element={<Component />}
                    />
                  );
                }
                return null;
              })}

              {/* 404 page */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Box>
        </Box>
      </Router>
    </ThemeProvider>
  );
}

export default App;


/**
 * Example Sidebar Component
 */
/*
function Sidebar({ navItems, services }) {
  return (
    <Box
      sx={{
        width: 240,
        bgcolor: 'background.paper',
        borderRight: 1,
        borderColor: 'divider',
      }}
    >
      <List>
        {navItems.map(item => {
          // Check if service is available
          const isAvailable = serviceDiscovery.isServiceAvailable(item.serviceId);

          return (
            <ListItem
              button
              key={item.route}
              component={Link}
              to={item.route}
              disabled={!isAvailable}
            >
              <ListItemIcon>
                <Icon>{item.icon}</Icon>
              </ListItemIcon>
              <ListItemText
                primary={item.label}
                secondary={isAvailable ? null : 'Offline'}
              />
            </ListItem>
          );
        })}
      </List>

      {/* Service Status Indicator *\/}
      <Divider />
      <Box sx={{ p: 2 }}>
        <Typography variant="caption" color="text.secondary">
          Services Status
        </Typography>
        {services.map(service => (
          <Box key={service.id} sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                bgcolor: service.enabled ? 'success.main' : 'error.main',
                mr: 1,
              }}
            />
            <Typography variant="caption">{service.name}</Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
}
*/
