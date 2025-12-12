import React from 'react';
import { useAuth } from '../contexts/AuthContext';

/**
 * Component to conditionally render children based on user role
 *
 * Usage:
 * <RoleBasedAccess allowedRoles={['admin', 'operator']}>
 *   <Button>Create Device</Button>
 * </RoleBasedAccess>
 */
export function RoleBasedAccess({ allowedRoles, children }) {
  const { user } = useAuth();

  if (!user || !allowedRoles.includes(user.role)) {
    return null;
  }

  return <>{children}</>;
}

/**
 * Component to conditionally render children based on user permission
 *
 * Usage:
 * <PermissionGuard permission="create_devices">
 *   <Button>Add Device</Button>
 * </PermissionGuard>
 */
export function PermissionGuard({ permission, children, fallback = null }) {
  const hasPermission = useHasPermission(permission);

  if (!hasPermission) {
    return fallback;
  }

  return <>{children}</>;
}

/**
 * Component to conditionally render children for viewers (read-only message)
 *
 * Usage:
 * <ViewerMessage>
 *   You don't have permission to modify this resource.
 * </ViewerMessage>
 */
export function ViewerMessage({ children }) {
  const { user } = useAuth();

  if (user?.role !== 'viewer') {
    return null;
  }

  return <>{children}</>;
}

/**
 * Hook to check if user has a specific permission
 *
 * Usage:
 * const canCreateDevice = useHasPermission('create_devices');
 * {canCreateDevice && <Button>Add Device</Button>}
 */
export function useHasPermission(permission) {
  const { user, userPermissions, isAdmin } = useAuth();

  // Superusers and admins have all permissions
  if (user?.is_superuser || isAdmin) {
    return true;
  }

  // Check if user has the specific permission
  return userPermissions?.includes(permission) || false;
}

/**
 * Hook to check multiple permissions (returns true if user has ANY of them)
 *
 * Usage:
 * const canManageRules = useHasAnyPermission(['create_rules', 'modify_rules']);
 */
export function useHasAnyPermission(permissions) {
  const { user, userPermissions, isAdmin } = useAuth();

  if (user?.is_superuser || isAdmin) {
    return true;
  }

  return permissions.some(p => userPermissions?.includes(p));
}

/**
 * Hook to check multiple permissions (returns true if user has ALL of them)
 *
 * Usage:
 * const canFullyManage = useHasAllPermissions(['create_rules', 'delete_rules']);
 */
export function useHasAllPermissions(permissions) {
  const { user, userPermissions, isAdmin } = useAuth();

  if (user?.is_superuser || isAdmin) {
    return true;
  }

  return permissions.every(p => userPermissions?.includes(p));
}

/**
 * Hook to check if user can modify resources
 *
 * Usage:
 * const canModify = useCanModify();
 * {canModify && <Button>Delete</Button>}
 */
export function useCanModify() {
  const { user } = useAuth();
  return user?.role === 'admin' || user?.role === 'operator';
}

/**
 * Hook to check if user is admin
 *
 * Usage:
 * const isAdmin = useIsAdmin();
 * {isAdmin && <Button>Admin Settings</Button>}
 */
export function useIsAdmin() {
  const { user } = useAuth();
  return user?.role === 'admin' || user?.is_superuser;
}

/**
 * Hook to check if user is viewer
 *
 * Usage:
 * const isViewer = useIsViewer();
 * {isViewer && <Alert>Read-only mode</Alert>}
 */
export function useIsViewer() {
  const { user } = useAuth();
  return user?.role === 'viewer';
}

export default RoleBasedAccess;
