import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Switch,
  FormControlLabel,
  Chip,
  Alert,
  Grid,
  Card,
  CardContent,
  Checkbox,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
  FormGroup,
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  PersonAdd as PersonAddIcon,
  People as PeopleIcon,
  Group as GroupIcon,
  Security as SecurityIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material';
import api from '../api/api';
import { useAuth } from '../contexts/AuthContext';

function TabPanel({ children, value, index, ...other }) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export default function UserManagement() {
  const { user } = useAuth();
  const [tabValue, setTabValue] = useState(0);
  const [users, setUsers] = useState([]);
  const [groups, setGroups] = useState([]);
  const [availablePermissions, setAvailablePermissions] = useState([]);
  const [availableModules, setAvailableModules] = useState([
    'devices', 'device_groups', 'discovery_groups', 'device_import',
    'audit', 'audit_schedules', 'rules', 'rule_templates',
    'config_backups', 'config_templates', 'drift_detection',
    'notifications', 'health', 'integrations', 'licensing',
    'topology', 'analytics', 'admin'
  ]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // User dialog state
  const [userDialog, setUserDialog] = useState({ open: false, user: null });
  const [userForm, setUserForm] = useState({
    username: '',
    email: '',
    password: '',
    full_name: '',
    is_active: true,
    is_superuser: false,
  });

  // Group dialog state
  const [groupDialog, setGroupDialog] = useState({ open: false, group: null });
  const [groupForm, setGroupForm] = useState({
    name: '',
    description: '',
    is_active: true,
    permissions: [],
    module_access: [],
  });

  // Group member dialog state
  const [memberDialog, setMemberDialog] = useState({ open: false, group: null });
  const [selectedUsers, setSelectedUsers] = useState([]);

  useEffect(() => {
    fetchUsers();
    fetchGroups();
    fetchAvailablePermissions();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await api.get('/user-management/users');
      setUsers(response.data);
    } catch (error) {
      console.error('Error fetching users:', error);
      setError('Failed to fetch users');
    }
  };

  const fetchGroups = async () => {
    try {
      const response = await api.get('/user-management/groups');
      setGroups(response.data);
    } catch (error) {
      console.error('Error fetching groups:', error);
      setError('Failed to fetch groups');
    }
  };

  const fetchAvailablePermissions = async () => {
    try {
      const response = await api.get('/user-management/permissions');
      setAvailablePermissions(response.data);
    } catch (error) {
      console.error('Error fetching permissions:', error);
      // Set default permissions if API fails
      setAvailablePermissions([
        'run_audits', 'view_audits',
        'modify_rules', 'view_rules', 'delete_rules',
        'modify_templates', 'view_templates', 'deploy_templates',
        'apply_fix', 'view_remediation',
        'create_users', 'modify_users', 'delete_users', 'view_users',
        'create_groups', 'modify_groups', 'delete_groups', 'view_groups',
        'create_devices', 'modify_devices', 'delete_devices', 'view_devices',
        'create_backups', 'view_backups', 'restore_backups',
        'manage_system', 'view_logs'
      ]);
    }
  };

  // User management functions
  const handleOpenUserDialog = (user = null) => {
    if (user) {
      setUserForm({
        username: user.username,
        email: user.email,
        password: '',
        full_name: user.full_name || '',
        is_active: user.is_active,
        is_superuser: user.is_superuser,
      });
    } else {
      setUserForm({
        username: '',
        email: '',
        password: '',
        full_name: '',
        is_active: true,
        is_superuser: false,
      });
    }
    setUserDialog({ open: true, user });
  };

  const handleCloseUserDialog = () => {
    setUserDialog({ open: false, user: null });
    setUserForm({
      username: '',
      email: '',
      password: '',
      full_name: '',
      is_active: true,
      is_superuser: false,
    });
  };

  const handleSaveUser = async () => {
    try {
      if (userDialog.user) {
        // Update existing user
        const updateData = { ...userForm };
        if (!updateData.password) {
          delete updateData.password; // Don't update password if not provided
        }
        await api.put(`/user-management/users/${userDialog.user.id}`, updateData);
        setSuccess('User updated successfully');
      } else {
        // Create new user
        await api.post('/user-management/users', userForm);
        setSuccess('User created successfully');
      }
      handleCloseUserDialog();
      fetchUsers();
    } catch (error) {
      console.error('Error saving user:', error);
      setError(error.response?.data?.detail || 'Failed to save user');
    }
  };

  const handleDeleteUser = async (userId) => {
    if (window.confirm('Are you sure you want to delete this user?')) {
      try {
        await api.delete(`/user-management/users/${userId}`);
        setSuccess('User deleted successfully');
        fetchUsers();
      } catch (error) {
        console.error('Error deleting user:', error);
        setError(error.response?.data?.detail || 'Failed to delete user');
      }
    }
  };

  // Group management functions
  const handleOpenGroupDialog = (group = null) => {
    if (group) {
      setGroupForm({
        name: group.name,
        description: group.description || '',
        is_active: group.is_active,
        permissions: group.permissions || [],
        module_access: group.module_access || [],
      });
    } else {
      setGroupForm({
        name: '',
        description: '',
        is_active: true,
        permissions: [],
        module_access: [],
      });
    }
    setGroupDialog({ open: true, group });
  };

  const handleCloseGroupDialog = () => {
    setGroupDialog({ open: false, group: null });
    setGroupForm({
      name: '',
      description: '',
      is_active: true,
      permissions: [],
      module_access: [],
    });
  };

  const handleSaveGroup = async () => {
    try {
      const groupData = {
        name: groupForm.name,
        description: groupForm.description,
        is_active: groupForm.is_active,
        permissions: groupForm.permissions,
        module_access: groupForm.module_access,
      };

      if (groupDialog.group) {
        // Update existing group
        await api.put(`/user-management/groups/${groupDialog.group.id}`, groupData);
        setSuccess('Group updated successfully');
      } else {
        // Create new group
        await api.post('/user-management/groups', groupData);
        setSuccess('Group created successfully');
      }
      handleCloseGroupDialog();
      fetchGroups();
    } catch (error) {
      console.error('Error saving group:', error);
      setError(error.response?.data?.detail || 'Failed to save group');
    }
  };

  const handleDeleteGroup = async (groupId) => {
    if (window.confirm('Are you sure you want to delete this group? Users will be removed from this group.')) {
      try {
        await api.delete(`/user-management/groups/${groupId}`);
        setSuccess('Group deleted successfully');
        fetchGroups();
      } catch (error) {
        console.error('Error deleting group:', error);
        setError(error.response?.data?.detail || 'Failed to delete group');
      }
    }
  };

  const handleTogglePermission = (permission) => {
    setGroupForm(prev => ({
      ...prev,
      permissions: prev.permissions.includes(permission)
        ? prev.permissions.filter(p => p !== permission)
        : [...prev.permissions, permission]
    }));
  };

  const handleToggleModule = (module) => {
    setGroupForm(prev => ({
      ...prev,
      module_access: prev.module_access.includes(module)
        ? prev.module_access.filter(m => m !== module)
        : [...prev.module_access, module]
    }));
  };

  // Member management functions
  const handleOpenMemberDialog = async (group) => {
    try {
      const response = await api.get(`/user-management/groups/${group.id}/members`);
      setSelectedUsers(response.data);
      setMemberDialog({ open: true, group });
    } catch (error) {
      console.error('Error fetching group members:', error);
      setError('Failed to fetch group members');
    }
  };

  const handleCloseMemberDialog = () => {
    setMemberDialog({ open: false, group: null });
    setSelectedUsers([]);
  };

  const handleSaveMembers = async () => {
    try {
      await api.put(`/user-management/groups/${memberDialog.group.id}/members`, {
        user_ids: selectedUsers
      });
      setSuccess('Group members updated successfully');
      handleCloseMemberDialog();
      fetchGroups();
    } catch (error) {
      console.error('Error updating group members:', error);
      setError(error.response?.data?.detail || 'Failed to update group members');
    }
  };

  const handleToggleUserInGroup = (userId) => {
    setSelectedUsers(prev =>
      prev.includes(userId)
        ? prev.filter(id => id !== userId)
        : [...prev, userId]
    );
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        User Management
      </Typography>

      {error && (
        <Alert severity="error" onClose={() => setError('')} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" onClose={() => setSuccess('')} sx={{ mb: 2 }}>
          {success}
        </Alert>
      )}

      <Paper>
        <Tabs
          value={tabValue}
          onChange={(e, newValue) => setTabValue(newValue)}
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab icon={<PeopleIcon />} label="Users" iconPosition="start" />
          <Tab icon={<GroupIcon />} label="Groups" iconPosition="start" />
        </Tabs>

        {/* Users Tab */}
        <TabPanel value={tabValue} index={0}>
          <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="h6">Users</Typography>
            <Button
              variant="contained"
              startIcon={<PersonAddIcon />}
              onClick={() => handleOpenUserDialog()}
            >
              Add User
            </Button>
          </Box>

          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Username</TableCell>
                  <TableCell>Email</TableCell>
                  <TableCell>Full Name</TableCell>
                  <TableCell>Groups</TableCell>
                  <TableCell>Superuser</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>{user.username}</TableCell>
                    <TableCell>{user.email}</TableCell>
                    <TableCell>{user.full_name || '-'}</TableCell>
                    <TableCell>
                      {user.groups?.length > 0 ? (
                        user.groups.map((group, idx) => (
                          <Chip
                            key={idx}
                            label={group}
                            size="small"
                            sx={{ mr: 0.5, mb: 0.5 }}
                          />
                        ))
                      ) : (
                        '-'
                      )}
                    </TableCell>
                    <TableCell>
                      {user.is_superuser ? (
                        <Chip label="Yes" color="secondary" size="small" />
                      ) : (
                        '-'
                      )}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={user.is_active ? 'Active' : 'Inactive'}
                        color={user.is_active ? 'success' : 'default'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <IconButton
                        size="small"
                        onClick={() => handleOpenUserDialog(user)}
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => handleDeleteUser(user.id)}
                        color="error"
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </TabPanel>

        {/* Groups Tab */}
        <TabPanel value={tabValue} index={1}>
          <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="h6">User Groups</Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => handleOpenGroupDialog()}
            >
              Add Group
            </Button>
          </Box>

          <Grid container spacing={2}>
            {groups.map((group) => (
              <Grid item xs={12} md={6} lg={4} key={group.id}>
                <Card>
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="h6">{group.name}</Typography>
                      <Chip
                        label={group.is_active ? 'Active' : 'Inactive'}
                        color={group.is_active ? 'success' : 'default'}
                        size="small"
                      />
                    </Box>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      {group.description || 'No description'}
                    </Typography>
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="caption" color="text.secondary">
                        Members: {group.member_count || 0}
                      </Typography>
                      <br />
                      <Typography variant="caption" color="text.secondary">
                        Permissions: {group.permissions?.length || 0}
                      </Typography>
                      <br />
                      <Typography variant="caption" color="text.secondary">
                        Modules: {group.module_access?.length || 0}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => handleOpenGroupDialog(group)}
                        startIcon={<EditIcon />}
                      >
                        Edit
                      </Button>
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => handleOpenMemberDialog(group)}
                        startIcon={<PeopleIcon />}
                      >
                        Members
                      </Button>
                      <IconButton
                        size="small"
                        onClick={() => handleDeleteGroup(group.id)}
                        color="error"
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </TabPanel>
      </Paper>

      {/* User Dialog */}
      <Dialog open={userDialog.open} onClose={handleCloseUserDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {userDialog.user ? 'Edit User' : 'Add User'}
        </DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Username"
            value={userForm.username}
            onChange={(e) => setUserForm({ ...userForm, username: e.target.value })}
            margin="normal"
            disabled={!!userDialog.user}
          />
          <TextField
            fullWidth
            label="Email"
            type="email"
            value={userForm.email}
            onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
            margin="normal"
          />
          <TextField
            fullWidth
            label="Full Name"
            value={userForm.full_name}
            onChange={(e) => setUserForm({ ...userForm, full_name: e.target.value })}
            margin="normal"
          />
          <TextField
            fullWidth
            label={userDialog.user ? 'Password (leave blank to keep current)' : 'Password'}
            type="password"
            value={userForm.password}
            onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
            margin="normal"
            required={!userDialog.user}
          />
          <FormControlLabel
            control={
              <Switch
                checked={userForm.is_active}
                onChange={(e) => setUserForm({ ...userForm, is_active: e.target.checked })}
              />
            }
            label="Active"
          />
          <FormControlLabel
            control={
              <Switch
                checked={userForm.is_superuser}
                onChange={(e) => setUserForm({ ...userForm, is_superuser: e.target.checked })}
              />
            }
            label="Superuser (has all permissions)"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseUserDialog}>Cancel</Button>
          <Button onClick={handleSaveUser} variant="contained">
            {userDialog.user ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Group Dialog */}
      <Dialog open={groupDialog.open} onClose={handleCloseGroupDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          {groupDialog.group ? 'Edit Group' : 'Add Group'}
        </DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Group Name"
            value={groupForm.name}
            onChange={(e) => setGroupForm({ ...groupForm, name: e.target.value })}
            margin="normal"
          />
          <TextField
            fullWidth
            label="Description"
            value={groupForm.description}
            onChange={(e) => setGroupForm({ ...groupForm, description: e.target.value })}
            margin="normal"
            multiline
            rows={2}
          />
          <FormControlLabel
            control={
              <Switch
                checked={groupForm.is_active}
                onChange={(e) => setGroupForm({ ...groupForm, is_active: e.target.checked })}
              />
            }
            label="Active"
          />

          <Divider sx={{ my: 2 }} />

          <Typography variant="h6" gutterBottom>
            <SecurityIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
            Permissions
          </Typography>
          <FormGroup>
            <Grid container spacing={1}>
              {availablePermissions.map((permission) => (
                <Grid item xs={12} sm={6} key={permission}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={groupForm.permissions.includes(permission)}
                        onChange={() => handleTogglePermission(permission)}
                      />
                    }
                    label={permission.replace(/_/g, ' ')}
                  />
                </Grid>
              ))}
            </Grid>
          </FormGroup>

          <Divider sx={{ my: 2 }} />

          <Typography variant="h6" gutterBottom>
            Module Access
          </Typography>
          <FormGroup>
            <Grid container spacing={1}>
              {availableModules.map((module) => (
                <Grid item xs={12} sm={6} key={module}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={groupForm.module_access.includes(module)}
                        onChange={() => handleToggleModule(module)}
                      />
                    }
                    label={module.replace(/_/g, ' ')}
                  />
                </Grid>
              ))}
            </Grid>
          </FormGroup>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseGroupDialog}>Cancel</Button>
          <Button onClick={handleSaveGroup} variant="contained">
            {groupDialog.group ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Member Management Dialog */}
      <Dialog open={memberDialog.open} onClose={handleCloseMemberDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          Manage Members: {memberDialog.group?.name}
        </DialogTitle>
        <DialogContent>
          <List>
            {users.map((user) => (
              <ListItem key={user.id}>
                <ListItemText
                  primary={user.username}
                  secondary={user.email}
                />
                <ListItemSecondaryAction>
                  <Checkbox
                    checked={selectedUsers.includes(user.id)}
                    onChange={() => handleToggleUserInGroup(user.id)}
                  />
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseMemberDialog}>Cancel</Button>
          <Button onClick={handleSaveMembers} variant="contained">
            Save Members
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
