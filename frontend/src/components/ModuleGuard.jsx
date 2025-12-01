/**
 * ModuleGuard Component
 *
 * Protects routes by checking if the user has access to the required license module.
 * If the user doesn't have access, redirects to the license page with an error message.
 */

import React from 'react';
import { Navigate } from 'react-router-dom';
import { Box, Alert, CircularProgress } from '@mui/material';
import { useAuth } from '../contexts/AuthContext';
import { mapRouteToModule } from '../utils/moduleMappings';

/**
 * Module Guard Component
 *
 * @param {Object} props
 * @param {React.ReactNode} props.children - Child components to render if access is granted
 * @param {string} props.module - Required module name (frontend route name, will be mapped to license module)
 * @param {React.ReactNode} props.fallback - Optional fallback component if access is denied
 */
const ModuleGuard = ({ children, module, fallback = null }) => {
  const { userModules, accessInfoLoaded, loading } = useAuth();

  // Show loading spinner while checking access
  if (loading || !accessInfoLoaded) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '400px',
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  // If no module is required, allow access
  if (!module) {
    return children;
  }

  // Map the frontend module name to the backend license module name
  const licenseModule = mapRouteToModule(module);

  // Check if user has access to this module
  const hasAccess = userModules && userModules.includes(licenseModule);

  if (!hasAccess) {
    // If a custom fallback is provided, render it
    if (fallback) {
      return fallback;
    }

    // Otherwise, show an error message and redirect option
    return (
      <Box sx={{ p: 3, maxWidth: 800, margin: '0 auto' }}>
        <Alert severity="warning" sx={{ mb: 2 }}>
          <strong>Access Denied</strong>
          <br />
          Your current license tier does not include access to this feature.
          <br />
          <br />
          Required module: <strong>{licenseModule}</strong>
          <br />
          <br />
          Please upgrade your license to access this feature.
        </Alert>
        <Navigate to="/license" replace state={{ from: window.location.pathname }} />
      </Box>
    );
  }

  // User has access, render the children
  return children;
};

export default ModuleGuard;
