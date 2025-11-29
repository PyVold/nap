import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  Alert
} from '@mui/material';
import LockIcon from '@mui/icons-material/Lock';
import UpgradeIcon from '@mui/icons-material/Upgrade';
import { useLicense } from '../contexts/LicenseContext';

/**
 * Component to show when a feature requires upgrade
 * 
 * @param {string} module - Module key that's required
 * @param {string} featureName - Display name of the feature
 * @param {string} description - Description of what the feature does
 * @param {string} requiredTier - Minimum tier required (starter, professional, enterprise)
 */
export default function UpgradePrompt({ 
  module, 
  featureName, 
  description,
  requiredTier = 'professional'
}) {
  const { getTierDisplayName, tier } = useLicense();

  const tierInfo = {
    starter: {
      color: 'info',
      features: 'Basic device management and manual audits'
    },
    professional: {
      color: 'success',
      features: 'Scheduled audits, API access, backups, and webhooks'
    },
    enterprise: {
      color: 'secondary',
      features: 'All features including AI, workflows, and unlimited devices'
    }
  };

  const required = tierInfo[requiredTier] || tierInfo.professional;

  return (
    <Box
      display="flex"
      justifyContent="center"
      alignItems="center"
      minHeight="60vh"
      p={3}
    >
      <Card sx={{ maxWidth: 700, width: '100%' }}>
        <CardContent sx={{ p: 4, textAlign: 'center' }}>
          {/* Lock Icon */}
          <Box
            sx={{
              width: 80,
              height: 80,
              borderRadius: '50%',
              bgcolor: 'grey.100',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 24px'
            }}
          >
            <LockIcon sx={{ fontSize: 48, color: 'text.secondary' }} />
          </Box>

          {/* Title */}
          <Typography variant="h4" gutterBottom fontWeight="bold">
            {featureName}
          </Typography>

          {/* Current Tier */}
          <Box mb={2}>
            <Typography variant="body2" color="text.secondary" component="span">
              Your current plan:{' '}
            </Typography>
            <Chip
              label={getTierDisplayName()}
              size="small"
              color="primary"
              sx={{ fontWeight: 'bold' }}
            />
          </Box>

          {/* Description */}
          <Typography variant="body1" color="text.secondary" paragraph sx={{ mb: 3 }}>
            {description}
          </Typography>

          {/* Upgrade Info */}
          <Alert severity="info" sx={{ mb: 3, textAlign: 'left' }}>
            <Typography variant="subtitle2" gutterBottom>
              <strong>Available in {tierInfo[requiredTier]?.color || 'Professional'} Plan</strong>
            </Typography>
            <Typography variant="body2">
              {required.features}
            </Typography>
          </Alert>

          {/* CTA Buttons */}
          <Box display="flex" gap={2} justifyContent="center">
            <Button
              variant="contained"
              color="primary"
              size="large"
              startIcon={<UpgradeIcon />}
              href="mailto:sales@ipdevops.com?subject=Upgrade License Request"
              sx={{ minWidth: 180 }}
            >
              Upgrade License
            </Button>
            <Button
              variant="outlined"
              size="large"
              href="mailto:sales@ipdevops.com?subject=License Information Request"
            >
              Contact Sales
            </Button>
          </Box>

          {/* Pricing Hint */}
          <Box mt={3} p={2} bgcolor="grey.50" borderRadius={1}>
            <Typography variant="caption" color="text.secondary">
              💡 <strong>Tip:</strong> Upgrading preserves all your existing data, devices, and configurations.
            </Typography>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}

/**
 * Higher-order component to wrap features with license check
 * Usage: export default withLicenseCheck(YourComponent, 'module_name', 'Feature Name')
 */
export function withLicenseCheck(Component, module, featureName, description) {
  return function LicenseCheckedComponent(props) {
    const { hasModule, loading } = useLicense();

    if (loading) {
      return (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
          Loading...
        </Box>
      );
    }

    if (!hasModule(module)) {
      return (
        <UpgradePrompt
          module={module}
          featureName={featureName}
          description={description}
        />
      );
    }

    return <Component {...props} />;
  };
}
