import React from 'react';
import { Box, Card, CardContent, Typography, Button, Alert } from '@mui/material';
import { ErrorOutline as ErrorIcon } from '@mui/icons-material';

/**
 * Error Boundary Component
 * Catches JavaScript errors anywhere in the child component tree and displays a fallback UI
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Log the error to console
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({
      error,
      errorInfo
    });
  }

  render() {
    if (this.state.hasError) {
      return (
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            minHeight: '100vh',
            bgcolor: '#f5f5f5',
            p: 3
          }}
        >
          <Card sx={{ maxWidth: 600, width: '100%' }}>
            <CardContent sx={{ p: 4 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <ErrorIcon sx={{ fontSize: 48, color: 'error.main', mr: 2 }} />
                <Typography variant="h4" component="h1">
                  Something went wrong
                </Typography>
              </Box>

              <Alert severity="error" sx={{ mb: 3 }}>
                <Typography variant="body1" gutterBottom>
                  {this.state.error && this.state.error.toString()}
                </Typography>
              </Alert>

              <Typography variant="body2" color="text.secondary" paragraph>
                The application encountered an unexpected error. This has been logged for investigation.
              </Typography>

              {process.env.NODE_ENV === 'development' && this.state.errorInfo && (
                <Box
                  sx={{
                    mt: 2,
                    p: 2,
                    bgcolor: '#f5f5f5',
                    borderRadius: 1,
                    maxHeight: 300,
                    overflow: 'auto'
                  }}
                >
                  <Typography variant="caption" component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
                    {this.state.errorInfo.componentStack}
                  </Typography>
                </Box>
              )}

              <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
                <Button
                  variant="contained"
                  onClick={() => {
                    this.setState({ hasError: false, error: null, errorInfo: null });
                    window.location.reload();
                  }}
                >
                  Reload Page
                </Button>
                <Button
                  variant="outlined"
                  onClick={() => {
                    this.setState({ hasError: false, error: null, errorInfo: null });
                    window.location.href = '/';
                  }}
                >
                  Go to Home
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Box>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
