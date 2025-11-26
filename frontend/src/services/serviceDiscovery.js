/**
 * Service Discovery Client
 * Fetches available microservices from the API Gateway
 * and provides dynamic module loading for the frontend
 */

import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:3000';

class ServiceDiscovery {
  constructor() {
    this.services = [];
    this.servicesLoaded = false;
  }

  /**
   * Fetch available services from API Gateway
   * @returns {Promise<Array>} List of available services
   */
  async discoverServices() {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/services`);
      this.services = response.data;
      this.servicesLoaded = true;
      console.log('✅ Discovered services:', this.services);
      return this.services;
    } catch (error) {
      console.error('❌ Failed to discover services:', error);
      // Return default services as fallback
      return this.getDefaultServices();
    }
  }

  /**
   * Get default services configuration (fallback)
   * @returns {Array} Default services list
   */
  getDefaultServices() {
    return [
      {
        id: 'device-service',
        name: 'Device Management',
        enabled: true,
        ui_routes: ['devices', 'discovery', 'health'],
        icon: 'Devices',
        description: 'Manage devices, discovery groups, and health monitoring'
      },
      {
        id: 'rule-service',
        name: 'Rules & Audits',
        enabled: true,
        ui_routes: ['rules', 'audits'],
        icon: 'Rule',
        description: 'Manage compliance rules and run audits'
      },
      {
        id: 'backup-service',
        name: 'Config Backups',
        enabled: true,
        ui_routes: ['backups', 'drift'],
        icon: 'Backup',
        description: 'Configuration backup and drift detection'
      },
      {
        id: 'inventory-service',
        name: 'Hardware Inventory',
        enabled: true,
        ui_routes: ['inventory'],
        icon: 'Inventory',
        description: 'Track hardware components and software versions'
      },
      {
        id: 'admin-service',
        name: 'Administration',
        enabled: true,
        ui_routes: ['admin', 'users', 'integrations'],
        icon: 'Admin',
        description: 'User management, integrations, and system monitoring'
      }
    ];
  }

  /**
   * Get all enabled services
   * @returns {Array} List of enabled services
   */
  getEnabledServices() {
    return this.services.filter(service => service.enabled);
  }

  /**
   * Get service by ID
   * @param {string} serviceId - Service identifier
   * @returns {Object|null} Service object or null
   */
  getServiceById(serviceId) {
    return this.services.find(service => service.id === serviceId) || null;
  }

  /**
   * Check if a specific service is available
   * @param {string} serviceId - Service identifier
   * @returns {boolean} True if service is available and enabled
   */
  isServiceAvailable(serviceId) {
    const service = this.getServiceById(serviceId);
    return service && service.enabled;
  }

  /**
   * Get navigation items for enabled services
   * @returns {Array} Navigation items for the UI
   */
  getNavigationItems() {
    const navItems = [];

    this.getEnabledServices().forEach(service => {
      service.ui_routes.forEach(route => {
        navItems.push({
          serviceId: service.id,
          serviceName: service.name,
          route: `/${route}`,
          label: this.formatRouteLabel(route),
          icon: this.getIconForRoute(route)
        });
      });
    });

    return navItems;
  }

  /**
   * Format route label for display
   * @param {string} route - Route name
   * @returns {string} Formatted label
   */
  formatRouteLabel(route) {
    const labels = {
      'devices': 'Devices',
      'discovery': 'Discovery',
      'health': 'Health Monitoring',
      'rules': 'Rules',
      'audits': 'Audits',
      'backups': 'Config Backups',
      'drift': 'Drift Detection',
      'inventory': 'Hardware Inventory',
      'admin': 'Admin Panel',
      'users': 'User Management',
      'integrations': 'Integrations'
    };

    return labels[route] || route.charAt(0).toUpperCase() + route.slice(1);
  }

  /**
   * Get Material-UI icon name for route
   * @param {string} route - Route name
   * @returns {string} Icon name
   */
  getIconForRoute(route) {
    const icons = {
      'devices': 'Router',
      'discovery': 'Search',
      'health': 'HealthAndSafety',
      'rules': 'Rule',
      'audits': 'Assessment',
      'backups': 'Backup',
      'drift': 'Compare',
      'inventory': 'Inventory2',
      'admin': 'AdminPanelSettings',
      'users': 'People',
      'integrations': 'IntegrationInstructions'
    };

    return icons[route] || 'FolderOpen';
  }

  /**
   * Check health of all services
   * @returns {Promise<Object>} Health status of all services
   */
  async checkServicesHealth() {
    try {
      const response = await axios.get(`${API_BASE_URL}/health`);
      return response.data;
    } catch (error) {
      console.error('❌ Failed to check services health:', error);
      return { status: 'error', services: {} };
    }
  }
}

// Create singleton instance
const serviceDiscovery = new ServiceDiscovery();

export default serviceDiscovery;
