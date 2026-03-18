import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Alert,
  CircularProgress,
  InputAdornment,
  IconButton,
  Chip,
  Divider,
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Lock as LockIcon,
  Person as PersonIcon,
  Security,
  Speed,
  SmartToy,
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  React.useEffect(() => {
    if (isAuthenticated) {
      navigate('/');
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const result = await login(username, password);

    if (result.success) {
      navigate('/');
    } else {
      setError(result.error);
    }

    setLoading(false);
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        background: 'linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)',
        overflow: 'hidden',
      }}
    >
      {/* Left side - Branding */}
      <Box
        sx={{
          flex: 1,
          display: { xs: 'none', md: 'flex' },
          flexDirection: 'column',
          justifyContent: 'center',
          px: 8,
          color: 'white',
        }}
      >
        <Box sx={{ mb: 6 }}>
          <Box display="flex" alignItems="center" gap={1.5} mb={3}>
            <Box
              sx={{
                width: 48,
                height: 48,
                borderRadius: 2,
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Security sx={{ fontSize: 28, color: 'white' }} />
            </Box>
            <Typography variant="h4" fontWeight="bold">
              NAP
            </Typography>
            <Chip label="v2.0" size="small" sx={{ color: 'rgba(255,255,255,0.7)', borderColor: 'rgba(255,255,255,0.3)' }} variant="outlined" />
          </Box>
          <Typography variant="h3" fontWeight="bold" sx={{ lineHeight: 1.2, mb: 2 }}>
            Network Audit
            <br />
            Platform
          </Typography>
          <Typography variant="h6" sx={{ color: 'rgba(255,255,255,0.6)', fontWeight: 400, maxWidth: 400 }}>
            Enterprise network compliance, powered by AI
          </Typography>
        </Box>

        <Box display="flex" gap={3} flexWrap="wrap">
          {[
            { icon: <Security sx={{ fontSize: 20 }} />, label: 'Compliance Auditing' },
            { icon: <SmartToy sx={{ fontSize: 20 }} />, label: 'AI-Powered Insights' },
            { icon: <Speed sx={{ fontSize: 20 }} />, label: 'Real-time Monitoring' },
          ].map((feature) => (
            <Box key={feature.label} display="flex" alignItems="center" gap={1} sx={{ color: 'rgba(255,255,255,0.7)' }}>
              {feature.icon}
              <Typography variant="body2">{feature.label}</Typography>
            </Box>
          ))}
        </Box>
      </Box>

      {/* Right side - Login form */}
      <Box
        sx={{
          flex: { xs: 1, md: '0 0 480px' },
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          p: 3,
        }}
      >
        <Paper
          elevation={0}
          sx={{
            p: 5,
            borderRadius: 4,
            width: '100%',
            maxWidth: 420,
            bgcolor: 'rgba(255,255,255,0.98)',
          }}
        >
          {/* Mobile header */}
          <Box sx={{ display: { xs: 'block', md: 'none' }, textAlign: 'center', mb: 3 }}>
            <Box
              sx={{
                width: 48,
                height: 48,
                borderRadius: 2,
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                mb: 1,
              }}
            >
              <Security sx={{ fontSize: 28, color: 'white' }} />
            </Box>
            <Typography variant="h5" fontWeight="bold">NAP</Typography>
          </Box>

          <Typography variant="h5" fontWeight="bold" sx={{ mb: 0.5 }}>
            Welcome back
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Sign in to your account to continue
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2, borderRadius: 2 }}>
              {error}
            </Alert>
          )}

          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              margin="normal"
              required
              autoFocus
              disabled={loading}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <PersonIcon sx={{ color: 'text.disabled' }} />
                  </InputAdornment>
                ),
              }}
              sx={{
                '& .MuiOutlinedInput-root': { borderRadius: 2 },
              }}
            />

            <TextField
              fullWidth
              label="Password"
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              margin="normal"
              required
              disabled={loading}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <LockIcon sx={{ color: 'text.disabled' }} />
                  </InputAdornment>
                ),
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      onClick={() => setShowPassword(!showPassword)}
                      edge="end"
                      size="small"
                    >
                      {showPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
              sx={{
                '& .MuiOutlinedInput-root': { borderRadius: 2 },
              }}
            />

            <Button
              type="submit"
              fullWidth
              variant="contained"
              size="large"
              disabled={loading}
              sx={{
                mt: 3,
                mb: 2,
                py: 1.5,
                borderRadius: 2,
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                fontWeight: 700,
                fontSize: 15,
                boxShadow: '0 4px 15px rgba(102, 126, 234, 0.35)',
                '&:hover': {
                  boxShadow: '0 6px 20px rgba(102, 126, 234, 0.5)',
                },
              }}
            >
              {loading ? <CircularProgress size={24} color="inherit" /> : 'Sign In'}
            </Button>
          </form>

          <Divider sx={{ my: 2 }}>
            <Chip label="Demo Accounts" size="small" variant="outlined" sx={{ fontSize: 11 }} />
          </Divider>

          <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center' }}>
            {[
              { user: 'admin', role: 'Admin' },
              { user: 'operator', role: 'Operator' },
              { user: 'viewer', role: 'Viewer' },
            ].map((demo) => (
              <Button
                key={demo.user}
                size="small"
                variant="outlined"
                onClick={() => {
                  setUsername(demo.user);
                  setPassword(demo.user);
                }}
                sx={{
                  borderRadius: 2,
                  fontSize: 11,
                  textTransform: 'none',
                  borderColor: 'divider',
                  color: 'text.secondary',
                  '&:hover': { borderColor: 'primary.main', color: 'primary.main' },
                }}
              >
                {demo.role}
              </Button>
            ))}
          </Box>
          <Typography variant="caption" color="error" display="block" textAlign="center" sx={{ mt: 1.5 }}>
            Change default passwords in production
          </Typography>
        </Paper>
      </Box>
    </Box>
  );
}
