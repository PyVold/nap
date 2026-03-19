/**
 * Vendor configuration for all supported network device vendors.
 * Central source of truth for vendor display names, colors, and identifiers.
 */

export const VENDOR_CONFIG = {
  cisco_xr: { label: 'Cisco IOS-XR', color: '#049fd9', short: 'XR' },
  cisco_xe: { label: 'Cisco IOS-XE', color: '#00bceb', short: 'XE' },
  nokia_sros: { label: 'Nokia SR OS', color: '#124191', short: 'Nokia' },
  juniper_junos: { label: 'Juniper JunOS', color: '#84b135', short: 'JunOS' },
  arista_eos: { label: 'Arista EOS', color: '#4c8bf5', short: 'Arista' },
};

/**
 * Get the display label for a vendor key.
 * Falls back to the raw vendor string if not found in config.
 */
export const getVendorLabel = (vendorKey) => {
  return VENDOR_CONFIG[vendorKey]?.label || vendorKey;
};

/**
 * Get the color for a vendor key.
 * Falls back to a default gray if not found.
 */
export const getVendorColor = (vendorKey) => {
  return VENDOR_CONFIG[vendorKey]?.color || '#757575';
};

/**
 * Get the short name for a vendor key.
 * Falls back to the raw vendor string if not found.
 */
export const getVendorShort = (vendorKey) => {
  return VENDOR_CONFIG[vendorKey]?.short || vendorKey;
};

/**
 * List of all vendor keys.
 */
export const VENDOR_KEYS = Object.keys(VENDOR_CONFIG);

/**
 * Uppercase vendor keys (used by rule templates).
 */
export const VENDOR_KEYS_UPPER = VENDOR_KEYS.map((k) => k.toUpperCase());
