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
  return user?.role === 'admin';
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
