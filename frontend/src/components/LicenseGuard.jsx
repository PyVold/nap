import React from 'react';
import { Navigate } from 'react-router-dom';
import { Box, CircularProgress, Card, CardContent, Typography, Button, Alert } from '@mui/material';
import { Warning as WarningIcon, Key as KeyIcon } from '@mui/icons-material';
import { useLicense } from '../contexts/LicenseContext';

/**
 * LicenseGuard - Protects routes by checking if license is valid
 * Redirects to /license page if license is expired or invalid
 */
export default function LicenseGuard({ children }) {
  const { license, loading, hasLicense, isLicenseValid } = useLicense();

  // Show loading spinner while checking license
  if (loading) {
    return (
      <Box 
        display="flex" 
        justifyContent="center" 
        alignItems="center" 
        minHeight="80vh"
      >
        <CircularProgress />
      </Box>
    );
  }

  // No license installed - redirect to license page
  if (!hasLicense) {
    return <Navigate to="/license" replace />;
  }

  // License exists but is not valid (expired, etc) - redirect to license page
  if (!isLicenseValid) {
    return <Navigate to="/license" replace />;
  }

  // License is valid - allow access
  return <>{children}</>;
}

/**
 * LicenseWarningBanner - Shows warning on license page when license is invalid
 */
export function LicenseWarningBanner() {
  const { license, hasLicense, isLicenseValid } = useLicense();

  if (!hasLicense) {
    return (
      <Alert severity="error" icon={<KeyIcon />} sx={{ mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          No License Activated
        </Typography>
        <Typography variant="body2">
          Your system does not have an active license. All modules are locked until you activate a valid license.
          Please contact your sales representative or activate a license key below.
        </Typography>
      </Alert>
    );
  }

  if (!isLicenseValid) {
    const daysUntilExpiry = license?.days_until_expiry || 0;
    const isExpired = daysUntilExpiry <= 0;

    return (
      <Alert severity="error" icon={<WarningIcon />} sx={{ mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          License {isExpired ? 'Expired' : 'Invalid'}
        </Typography>
        <Typography variant="body2">
          {isExpired 
            ? `Your license expired ${Math.abs(daysUntilExpiry)} days ago. All modules are now locked.`
            : 'Your license is invalid or corrupted. All modules are locked.'}
          {' '}Please activate a new license key or contact sales to renew your license.
        </Typography>
        {license?.expires_at && (
          <Typography variant="caption" display="block" sx={{ mt: 1 }}>
            Original expiry date: {new Date(license.expires_at).toLocaleDateString()}
          </Typography>
        )}
      </Alert>
    );
  }

  return null;
}
