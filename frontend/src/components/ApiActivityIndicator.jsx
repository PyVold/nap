import React, { useState, useEffect } from 'react';
import { Box, Chip, Tooltip, Fade } from '@mui/material';
import { CloudSync, CloudDone } from '@mui/icons-material';
import { subscribeToApiActivity } from '../api/api';

const ApiActivityIndicator = () => {
  const [isActive, setIsActive] = useState(false);
  const [requestCount, setRequestCount] = useState(0);

  useEffect(() => {
    const unsubscribe = subscribeToApiActivity((active, count) => {
      setIsActive(active);
      setRequestCount(count);
    });

    return () => {
      unsubscribe();
    };
  }, []);

  return (
    <Fade in={isActive} timeout={300}>
      <Box
        sx={{
          position: 'fixed',
          top: 16,
          right: 16,
          zIndex: 9999,
        }}
      >
        <Tooltip title={`${requestCount} active API ${requestCount === 1 ? 'request' : 'requests'}`} arrow>
          <Chip
            icon={isActive ? <CloudSync className="rotating-icon" /> : <CloudDone />}
            label={`API ${requestCount}`}
            color={isActive ? 'primary' : 'success'}
            size="small"
            sx={{
              fontWeight: 'bold',
              boxShadow: 3,
              backdropFilter: 'blur(10px)',
              backgroundColor: isActive ? 'rgba(25, 118, 210, 0.9)' : 'rgba(46, 125, 50, 0.9)',
              color: 'white',
              '& .rotating-icon': {
                animation: 'spin 1s linear infinite',
              },
              '@keyframes spin': {
                '0%': {
                  transform: 'rotate(0deg)',
                },
                '100%': {
                  transform: 'rotate(360deg)',
                },
              },
            }}
          />
        </Tooltip>
      </Box>
    </Fade>
  );
};

export default ApiActivityIndicator;
