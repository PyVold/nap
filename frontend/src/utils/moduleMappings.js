/**
 * Module Mappings Utility
 *
 * Handles the mapping between frontend route/menu names and backend license module names.
 * This ensures consistency between what the frontend displays and what the backend enforces.
 */

import api from '../api/api';

// Cache for module mappings
let cachedMappings = null;

/**
 * Fetch module mappings from backend
 *
 * @returns {Promise<Object>} Module mappings, display names, and tier information
 */
export const fetchModuleMappings = async () => {
  try {
    const response = await api.get('/license/module-mappings');
    cachedMappings = response.data;
    return cachedMappings;
  } catch (error) {
    console.error('Error fetching module mappings:', error);
    // Return default mappings if fetch fails
    return getDefaultMappings();
  }
};

/**
 * Get cached module mappings or fetch if not cached
 *
 * @returns {Promise<Object>} Module mappings
 */
export const getModuleMappings = async () => {
  if (cachedMappings) {
    return cachedMappings;
  }
  return await fetchModuleMappings();
};

/**
 * Map a frontend route/menu name to its corresponding license module
 *
 * @param {string} routeName - Frontend route or menu name (e.g., 'audit', 'audit_schedules')
 * @param {Object} mappings - Module mappings object (optional, will fetch if not provided)
 * @returns {string} License module name (e.g., 'manual_audits', 'scheduled_audits')
 */
export const mapRouteToModule = (routeName, mappings = null) => {
  // Remove leading slash if present
  const cleanRoute = routeName.replace(/^\//, '');

  // If no mappings provided, use cached or default
  const moduleMap = mappings?.mappings || cachedMappings?.mappings || getDefaultMappings().mappings;

  // Return mapped module or the route name itself if no mapping exists
  return moduleMap[cleanRoute] || cleanRoute;
};

/**
 * Check if user has access to a specific route/menu item
 *
 * @param {string} routeName - Frontend route or menu name
 * @param {Array<string>} userModules - List of modules user has access to (from backend)
 * @param {Object} mappings - Module mappings object (optional)
 * @returns {boolean} True if user has access, false otherwise
 */
export const hasRouteAccess = (routeName, userModules, mappings = null) => {
  if (!routeName || !userModules) {
    return false;
  }

  // Map the route to its license module
  const licenseModule = mapRouteToModule(routeName, mappings);

  // Check if user has access to this module
  return userModules.includes(licenseModule);
};

/**
 * Default mappings (fallback if API call fails)
 * Should match the backend ROUTE_MODULE_MAP
 */
function getDefaultMappings() {
  return {
    mappings: {
      // Device Management
      'devices': 'devices',
      'device_groups': 'device_groups',
      'discovery_groups': 'discovery',
      'device_import': 'devices',

      // Auditing
      'audit': 'manual_audits',
      'audits': 'manual_audits',
      'audit_schedules': 'scheduled_audits',

      // Rules
      'rules': 'basic_rules',
      'rule_templates': 'rule_templates',

      // Configuration Management
      'config_backups': 'config_backups',
      'drift_detection': 'drift_detection',

      // Monitoring & Notifications
      'notifications': 'webhooks',
      'health': 'health_checks',
      'hardware_inventory': 'devices',

      // Advanced Features
      'integrations': 'integrations',
      'workflows': 'workflow_automation',
      'analytics': 'ai_features',

      // API Access
      'api': 'api_access',
    },
    modules: {},
    tiers: {}
  };
}

/**
 * Clear cached mappings (useful for testing or when license changes)
 */
export const clearMappingsCache = () => {
  cachedMappings = null;
};
