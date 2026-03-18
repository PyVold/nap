import React, { useState, useEffect, useCallback } from 'react';
import {
  IconButton,
  Badge,
  Popover,
  Box,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Button,
  Divider,
  Chip,
  Tabs,
  Tab,
} from '@mui/material';
import {
  Notifications as NotificationsIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  CheckCircle as CheckIcon,
  CompareArrows as DriftIcon,
  Security as AuditIcon,
  Router as DeviceIcon,
  Circle as DotIcon,
} from '@mui/icons-material';

const NOTIFICATION_TYPES = {
  audit_failure: { icon: <AuditIcon color="error" fontSize="small" />, color: 'error' },
  drift_detected: { icon: <DriftIcon color="warning" fontSize="small" />, color: 'warning' },
  device_unreachable: { icon: <DeviceIcon color="error" fontSize="small" />, color: 'error' },
  compliance_drop: { icon: <WarningIcon color="warning" fontSize="small" />, color: 'warning' },
  audit_complete: { icon: <CheckIcon color="success" fontSize="small" />, color: 'success' },
  backup_complete: { icon: <CheckIcon color="success" fontSize="small" />, color: 'success' },
  info: { icon: <InfoIcon color="info" fontSize="small" />, color: 'info' },
};

const NotificationCenter = () => {
  const [anchorEl, setAnchorEl] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [tab, setTab] = useState(0);

  const loadNotifications = useCallback(() => {
    // Load from localStorage (persisted notifications)
    const stored = localStorage.getItem('nap_notifications');
    if (stored) {
      try {
        setNotifications(JSON.parse(stored));
      } catch { /* ignore parse errors */ }
    }
  }, []);

  useEffect(() => {
    loadNotifications();
    // Poll for new notifications every 30s
    const interval = setInterval(loadNotifications, 30000);
    return () => clearInterval(interval);
  }, [loadNotifications]);

  // Helper to add notifications (can be called from other components via window event)
  useEffect(() => {
    const handleNewNotification = (event) => {
      const newNotif = {
        id: Date.now(),
        ...event.detail,
        timestamp: new Date().toISOString(),
        read: false,
      };
      setNotifications((prev) => {
        const updated = [newNotif, ...prev].slice(0, 100); // Keep last 100
        localStorage.setItem('nap_notifications', JSON.stringify(updated));
        return updated;
      });
    };
    window.addEventListener('nap-notification', handleNewNotification);
    return () => window.removeEventListener('nap-notification', handleNewNotification);
  }, []);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const handleOpen = (e) => setAnchorEl(e.currentTarget);
  const handleClose = () => setAnchorEl(null);

  const markAllRead = () => {
    const updated = notifications.map((n) => ({ ...n, read: true }));
    setNotifications(updated);
    localStorage.setItem('nap_notifications', JSON.stringify(updated));
  };

  const clearAll = () => {
    setNotifications([]);
    localStorage.removeItem('nap_notifications');
  };

  const filteredNotifications =
    tab === 0 ? notifications : notifications.filter((n) => !n.read);

  const formatTime = (ts) => {
    if (!ts) return '';
    const d = new Date(ts);
    const now = new Date();
    const diffMs = now - d;
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return 'just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    const diffDays = Math.floor(diffHr / 24);
    return `${diffDays}d ago`;
  };

  return (
    <>
      <IconButton color="inherit" onClick={handleOpen}>
        <Badge badgeContent={unreadCount} color="error" max={99}>
          <NotificationsIcon />
        </Badge>
      </IconButton>

      <Popover
        open={Boolean(anchorEl)}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
        PaperProps={{ sx: { width: 380, maxHeight: 500, borderRadius: 2 } }}
      >
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6" fontWeight="bold">
            Notifications
          </Typography>
          <Box>
            <Button size="small" onClick={markAllRead} disabled={unreadCount === 0}>
              Mark all read
            </Button>
            <Button size="small" color="error" onClick={clearAll} disabled={notifications.length === 0}>
              Clear
            </Button>
          </Box>
        </Box>

        <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ px: 2 }}>
          <Tab label={`All (${notifications.length})`} />
          <Tab
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                Unread
                {unreadCount > 0 && <Chip label={unreadCount} size="small" color="error" sx={{ height: 18, fontSize: 11 }} />}
              </Box>
            }
          />
        </Tabs>

        <Divider />

        <List dense sx={{ maxHeight: 350, overflow: 'auto', p: 0 }}>
          {filteredNotifications.length === 0 ? (
            <Box sx={{ p: 4, textAlign: 'center' }}>
              <NotificationsIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
              <Typography color="text.secondary" variant="body2">
                {tab === 1 ? 'No unread notifications' : 'No notifications yet'}
              </Typography>
            </Box>
          ) : (
            filteredNotifications.map((notif) => {
              const typeConfig = NOTIFICATION_TYPES[notif.type] || NOTIFICATION_TYPES.info;
              return (
                <ListItem
                  key={notif.id}
                  sx={{
                    backgroundColor: notif.read ? 'transparent' : 'action.hover',
                    cursor: 'pointer',
                    '&:hover': { backgroundColor: 'action.selected' },
                  }}
                  onClick={() => {
                    const updated = notifications.map((n) =>
                      n.id === notif.id ? { ...n, read: true } : n
                    );
                    setNotifications(updated);
                    localStorage.setItem('nap_notifications', JSON.stringify(updated));
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 36 }}>
                    {!notif.read && (
                      <DotIcon sx={{ fontSize: 8, color: 'primary.main', position: 'absolute', left: 6, top: '50%', transform: 'translateY(-50%)' }} />
                    )}
                    {typeConfig.icon}
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Typography variant="body2" fontWeight={notif.read ? 400 : 600} noWrap>
                        {notif.title}
                      </Typography>
                    }
                    secondary={
                      <Box>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }} noWrap>
                          {notif.message}
                        </Typography>
                        <Typography variant="caption" color="text.disabled">
                          {formatTime(notif.timestamp)}
                        </Typography>
                      </Box>
                    }
                  />
                  <Chip
                    label={notif.type?.replace(/_/g, ' ')}
                    size="small"
                    color={typeConfig.color}
                    variant="outlined"
                    sx={{ fontSize: 10, height: 20, ml: 1 }}
                  />
                </ListItem>
              );
            })
          )}
        </List>
      </Popover>
    </>
  );
};

// Helper function to dispatch notifications from anywhere in the app
export const pushNotification = (title, message, type = 'info') => {
  window.dispatchEvent(
    new CustomEvent('nap-notification', {
      detail: { title, message, type },
    })
  );
};

export default NotificationCenter;
