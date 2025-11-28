import React from 'react';
import { useLicense } from '../contexts/LicenseContext';
import UpgradePrompt from './UpgradePrompt';
import AuditSchedules from './AuditSchedules'; // Your existing component

/**
 * Wrapper for AuditSchedules with license check
 * This ensures only Professional+ users can access scheduled audits
 */
export default function AuditSchedulesWrapper() {
  const { hasModule, loading } = useLicense();

  if (loading) {
    return <div>Loading...</div>;
  }

  // Check if user has access to scheduled audits
  if (!hasModule('scheduled_audits')) {
    return (
      <UpgradePrompt
        module="scheduled_audits"
        featureName="Scheduled Audits"
        description="Automate your compliance checks with cron-based scheduling. Run audits daily, weekly, or on any custom schedule without manual intervention."
        requiredTier="professional"
      />
    );
  }

  // User has access, show the actual component
  return <AuditSchedules />;
}
