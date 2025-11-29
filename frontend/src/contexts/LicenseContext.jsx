import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../api/api';

const LicenseContext = createContext();

export const useLicense = () => {
  const context = useContext(LicenseContext);
  if (!context) {
    throw new Error('useLicense must be used within a LicenseProvider');
  }
  return context;
};

export const LicenseProvider = ({ children }) => {
  const [license, setLicense] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchLicense();
  }, []);

  const fetchLicense = async () => {
    setLoading(true);
    try {
      const response = await api.get('/license/status');
      console.log('[LicenseContext] License fetched successfully:', response.data);
      setLicense(response.data);
      setError(null);
    } catch (err) {
      console.log('[LicenseContext] Error fetching license:', err.response?.status, err.message);
      if (err.response?.status === 404 || err.response?.status === 402) {
        // No license activated or license invalid - this is ok, just set to null
        setLicense(null);
        setError(null);
      } else {
        // Network or other error - log but don't block
        console.error('[LicenseContext] Failed to fetch license:', err);
        setError('Failed to fetch license status');
        // Still set license to null so app doesn't hang
        setLicense(null);
      }
    } finally {
      setLoading(false);
      console.log('[LicenseContext] Loading complete');
    }
  };

  /**
   * Check if a specific module is enabled in the license
   * @param {string} module - Module key (e.g., 'scheduled_audits', 'api_access')
   * @returns {boolean}
   */
  const hasModule = (module) => {
    if (!license || !license.is_valid) return false;
    
    const modules = license.features?.modules || [];
    
    // Enterprise has all modules
    if (modules.includes('all')) return true;
    
    return modules.includes(module);
  };

  /**
   * Check if current usage is within quota
   * @param {string} quotaType - 'devices', 'users', or 'storage'
   * @returns {boolean}
   */
  const isWithinQuota = (quotaType) => {
    if (!license) return false;
    
    const quotas = license.quotas || {};
    const usage = license.current_usage || {};
    
    const max = quotas[`max_${quotaType}`] || 0;
    const current = usage[quotaType] || 0;
    
    // Unlimited check
    if (max >= 999999) return true;
    
    return current < max;
  };

  /**
   * Get usage percentage for a quota type
   * @param {string} quotaType - 'devices', 'users', or 'storage'
   * @returns {number} - Percentage (0-100)
   */
  const getUsagePercentage = (quotaType) => {
    if (!license) return 0;
    
    const quotas = license.quotas || {};
    const usage = license.current_usage || {};
    
    const max = quotas[`max_${quotaType}`] || 0;
    const current = usage[quotaType] || 0;
    
    // Unlimited check
    if (max >= 999999) return 0;
    
    if (max === 0) return 0;
    
    return Math.min((current / max) * 100, 100);
  };

  /**
   * Check if license is expiring soon (within 30 days)
   * @returns {boolean}
   */
  const isExpiringSoon = () => {
    if (!license) return false;
    return license.expiring_soon || false;
  };

  /**
   * Get days until expiry
   * @returns {number}
   */
  const getDaysUntilExpiry = () => {
    if (!license) return 0;
    return license.days_until_expiry || 0;
  };

  /**
   * Get tier display name
   * @returns {string}
   */
  const getTierDisplayName = () => {
    if (!license) return 'No License';
    
    const tierNames = {
      starter: 'Starter',
      professional: 'Professional',
      enterprise: 'Enterprise',
      enterprise_plus: 'Enterprise Plus'
    };
    
    return tierNames[license.tier] || license.tier;
  };

  /**
   * Check if user has unlimited quota
   * @returns {boolean}
   */
  const isUnlimited = () => {
    if (!license) return false;
    return license.features?.unlimited || false;
  };

  /**
   * Get list of all enabled modules
   * @returns {string[]}
   */
  const getEnabledModules = () => {
    if (!license) return [];
    return license.features?.modules || [];
  };

  const value = {
    // State
    license,
    loading,
    error,
    
    // Actions
    refetch: fetchLicense,
    
    // Helper functions
    hasModule,
    isWithinQuota,
    getUsagePercentage,
    isExpiringSoon,
    getDaysUntilExpiry,
    getTierDisplayName,
    isUnlimited,
    getEnabledModules,
    
    // Computed values
    isLicenseActive: license?.is_active || false,
    isLicenseValid: license?.valid || license?.is_valid || false,
    hasLicense: !!license,
    tier: license?.tier || null,
  };

  return (
    <LicenseContext.Provider value={value}>
      {children}
    </LicenseContext.Provider>
  );
};
