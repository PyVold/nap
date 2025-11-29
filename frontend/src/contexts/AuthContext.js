import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../api/api';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [userModules, setUserModules] = useState([]);
  const [userPermissions, setUserPermissions] = useState([]);
  const [accessInfoLoaded, setAccessInfoLoaded] = useState(false);

  // Fetch user's modules and permissions
  const fetchUserAccessInfo = async (userId) => {
    if (!userId) {
      console.warn('No user ID provided to fetchUserAccessInfo');
      setAccessInfoLoaded(true);
      return;
    }

    try {
      const [modulesResponse, permissionsResponse] = await Promise.all([
        api.get(`/user-management/users/${userId}/modules`).catch(err => {
          console.error('Error fetching modules:', err);
          return { data: [] };
        }),
        api.get(`/user-management/users/${userId}/permissions`).catch(err => {
          console.error('Error fetching permissions:', err);
          return { data: [] };
        })
      ]);
      
      // Ensure we have valid arrays
      const modules = Array.isArray(modulesResponse.data) ? modulesResponse.data : [];
      const permissions = Array.isArray(permissionsResponse.data) ? permissionsResponse.data : [];
      
      setUserModules(modules);
      setUserPermissions(permissions);
      setAccessInfoLoaded(true);
    } catch (error) {
      console.error('Error fetching user access info:', error);
      // If it fails, don't block the user - they might be superuser
      setUserModules([]);
      setUserPermissions([]);
      setAccessInfoLoaded(true);
    }
  };

  useEffect(() => {
    // Check for existing token on mount
    const storedToken = localStorage.getItem('auth_token');
    const storedUser = localStorage.getItem('auth_user');

    if (storedToken && storedUser) {
      setToken(storedToken);
      const userData = JSON.parse(storedUser);
      setUser(userData);
      // Add token to axios default headers
      api.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;

      // Fetch user modules and permissions if user_id is available
      if (userData.user_id) {
        fetchUserAccessInfo(userData.user_id);
      } else {
        setAccessInfoLoaded(true);
      }
    }
    setLoading(false);
  }, []);

  const login = async (username, password) => {
    try {
      const response = await api.post('/login', { username, password });
      const { access_token, username: authUsername, role } = response.data;

      // Add token to axios default headers first
      api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

      // Get user info to get user_id
      const userInfoResponse = await api.get('/me');
      const userData = {
        username: authUsername,
        role,
        user_id: userInfoResponse.data.id
      };

      setToken(access_token);
      setUser(userData);

      // Store in localStorage
      localStorage.setItem('auth_token', access_token);
      localStorage.setItem('auth_user', JSON.stringify(userData));

      // Fetch user modules and permissions
      await fetchUserAccessInfo(userData.user_id);

      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Login failed'
      };
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    setUserModules([]);
    setUserPermissions([]);
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    delete api.defaults.headers.common['Authorization'];
  };

  // Check if user is admin/superuser
  const isAdmin = user?.role === 'admin' || user?.is_superuser === true;

  const value = {
    user,
    token,
    login,
    logout,
    loading,
    isAuthenticated: !!token,
    userModules,
    userPermissions,
    isAdmin,
    accessInfoLoaded,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
