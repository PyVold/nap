import React, { useState } from 'react';
import {
  Box, IconButton, TextField, Tooltip, Snackbar,
} from '@mui/material';
import ThumbUpIcon from '@mui/icons-material/ThumbUp';
import ThumbDownIcon from '@mui/icons-material/ThumbDown';
import SendIcon from '@mui/icons-material/Send';
import { aiAPI } from '../api/api';

const AIFeedbackWidget = ({ featureType, responseData }) => {
  const [rating, setRating] = useState(null); // 'positive' or 'negative'
  const [comment, setComment] = useState('');
  const [showComment, setShowComment] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [snackbarOpen, setSnackbarOpen] = useState(false);

  const handleRating = (value) => {
    setRating(value);
    setShowComment(true);
  };

  const handleSubmit = async () => {
    try {
      await aiAPI.submitDirectFeedback({
        feature_type: featureType,
        rating,
        comment: comment || '',
        response_summary: typeof responseData === 'string'
          ? responseData.substring(0, 500)
          : String(responseData || '').substring(0, 500),
      });
    } catch (err) {
      console.error('Failed to submit feedback:', err);
    }
    setSubmitted(true);
    setShowComment(false);
    setSnackbarOpen(true);
  };

  const handleThumbClick = (value) => {
    if (submitted) return;
    if (rating === value) {
      handleSubmit();
    } else {
      handleRating(value);
    }
  };

  if (submitted) {
    return (
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={3000}
        onClose={() => setSnackbarOpen(false)}
        message="Thanks for your feedback!"
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      />
    );
  }

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 1, flexWrap: 'wrap' }}>
      <Tooltip title="Helpful">
        <IconButton
          size="small"
          onClick={() => handleThumbClick('positive')}
          color={rating === 'positive' ? 'success' : 'default'}
          sx={{ opacity: rating === 'negative' ? 0.4 : 0.7, '&:hover': { opacity: 1 } }}
        >
          <ThumbUpIcon fontSize="small" />
        </IconButton>
      </Tooltip>
      <Tooltip title="Not helpful">
        <IconButton
          size="small"
          onClick={() => handleThumbClick('negative')}
          color={rating === 'negative' ? 'error' : 'default'}
          sx={{ opacity: rating === 'positive' ? 0.4 : 0.7, '&:hover': { opacity: 1 } }}
        >
          <ThumbDownIcon fontSize="small" />
        </IconButton>
      </Tooltip>
      {showComment && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flex: 1, minWidth: 200 }}>
          <TextField
            size="small"
            variant="outlined"
            placeholder="Optional comment..."
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleSubmit(); }}
            sx={{ flex: 1, '& .MuiOutlinedInput-root': { fontSize: '0.8rem' } }}
          />
          <Tooltip title="Submit feedback">
            <IconButton size="small" onClick={handleSubmit} color="primary">
              <SendIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      )}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={3000}
        onClose={() => setSnackbarOpen(false)}
        message="Thanks for your feedback!"
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      />
    </Box>
  );
};

export default AIFeedbackWidget;
