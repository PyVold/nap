import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Box, Paper, Typography, TextField, IconButton, CircularProgress,
  Card, CardContent, Chip, Divider, Alert, List, ListItem, ListItemText,
  ListItemButton, ListItemSecondaryAction, Tooltip, Button,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PersonIcon from '@mui/icons-material/Person';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import ChatIcon from '@mui/icons-material/Chat';
import { aiAPI } from '../api/api';
import AIFeedbackWidget from './AIFeedbackWidget';

const WELCOME_MESSAGE = {
  role: 'assistant',
  content: 'Hello! I\'m your NAP AI assistant. Ask me anything about your network \u2014 device status, compliance scores, audit results, config changes, and more.\n\nTry asking:\n- "Which devices have compliance below 80%?"\n- "Show me recent config changes"\n- "What\'s our overall compliance score?"',
};

const AIChat = () => {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      setSessionsLoading(true);
      const resp = await aiAPI.getChatSessions();
      setSessions(resp.data || []);
    } catch (err) {
      console.error('Failed to load chat sessions:', err);
    } finally {
      setSessionsLoading(false);
    }
  };

  const selectSession = async (sessionId) => {
    if (sessionId === activeSessionId) return;
    try {
      const resp = await aiAPI.getChatSession(sessionId);
      const sessionData = resp.data;
      setActiveSessionId(sessionId);

      // Convert stored messages to display format
      const displayMessages = (sessionData.messages || []).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      if (displayMessages.length === 0) {
        setMessages([WELCOME_MESSAGE]);
      } else {
        setMessages(displayMessages);
      }
      setError(null);
    } catch (err) {
      setError('Failed to load session');
    }
  };

  const startNewChat = () => {
    setActiveSessionId(null);
    setMessages([WELCOME_MESSAGE]);
    setError(null);
  };

  const deleteSession = async (e, sessionId) => {
    e.stopPropagation();
    try {
      await aiAPI.deleteChatSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        startNewChat();
      }
    } catch (err) {
      setError('Failed to delete session');
    }
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setError(null);

    // Add user message to display
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const response = await aiAPI.chat({
        message: userMessage,
        session_id: activeSessionId,
      });

      const data = response.data;

      // If this was a new session, capture the returned session_id
      if (!activeSessionId && data.session_id) {
        setActiveSessionId(data.session_id);
        // Refresh session list to show the new session
        loadSessions();
      }

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.message,
          queryExecuted: data.query_executed,
          confidence: data.confidence,
        },
      ]);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to get response. Please try again.');
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I encountered an error processing your request. Please try again.',
          isError: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Box sx={{ p: 3, height: 'calc(100vh - 120px)', display: 'flex', gap: 2 }}>
      {/* Session Sidebar */}
      <Paper
        elevation={2}
        sx={{
          width: 260,
          minWidth: 260,
          display: 'flex',
          flexDirection: 'column',
          borderRadius: 2,
          overflow: 'hidden',
        }}
      >
        <Box sx={{ p: 1.5, borderBottom: 1, borderColor: 'divider' }}>
          <Button
            fullWidth
            variant="outlined"
            startIcon={<AddIcon />}
            onClick={startNewChat}
            size="small"
          >
            New Chat
          </Button>
        </Box>
        <Box sx={{ flex: 1, overflow: 'auto' }}>
          {sessionsLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
              <CircularProgress size={20} />
            </Box>
          ) : sessions.length === 0 ? (
            <Typography variant="body2" color="text.secondary" sx={{ p: 2, textAlign: 'center' }}>
              No previous chats
            </Typography>
          ) : (
            <List dense disablePadding>
              {sessions.map((session) => (
                <ListItemButton
                  key={session.id}
                  selected={session.id === activeSessionId}
                  onClick={() => selectSession(session.id)}
                  sx={{ pr: 5 }}
                >
                  <ChatIcon sx={{ fontSize: 16, mr: 1, color: 'text.secondary' }} />
                  <ListItemText
                    primary={session.title}
                    secondary={`${session.message_count} messages`}
                    primaryTypographyProps={{
                      variant: 'body2',
                      noWrap: true,
                      sx: { fontWeight: session.id === activeSessionId ? 600 : 400 },
                    }}
                    secondaryTypographyProps={{ variant: 'caption' }}
                  />
                  <ListItemSecondaryAction>
                    <Tooltip title="Delete">
                      <IconButton
                        edge="end"
                        size="small"
                        onClick={(e) => deleteSession(e, session.id)}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </ListItemSecondaryAction>
                </ListItemButton>
              ))}
            </List>
          )}
        </Box>
      </Paper>

      {/* Main Chat Area */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
          <SmartToyIcon sx={{ fontSize: 32, color: 'primary.main' }} />
          <Typography variant="h5" fontWeight="bold">AI Network Assistant</Typography>
          <Chip label="AI-Powered" color="primary" size="small" sx={{ ml: 1 }} />
          {activeSessionId && (
            <Chip
              label="Session saved"
              color="success"
              size="small"
              variant="outlined"
              sx={{ ml: 'auto' }}
            />
          )}
        </Box>

        {error && (
          <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Messages Area */}
        <Paper
          elevation={2}
          sx={{
            flex: 1,
            overflow: 'auto',
            p: 2,
            mb: 2,
            bgcolor: 'background.default',
            borderRadius: 2,
          }}
        >
          {messages.map((msg, index) => (
            <Box
              key={index}
              sx={{
                display: 'flex',
                mb: 2,
                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
              }}
            >
              <Card
                sx={{
                  maxWidth: '80%',
                  bgcolor: msg.role === 'user' ? 'primary.main' : msg.isError ? 'error.light' : 'background.paper',
                  color: msg.role === 'user' ? 'primary.contrastText' : 'text.primary',
                  borderRadius: 2,
                }}
              >
                <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                    {msg.role === 'user' ? (
                      <PersonIcon fontSize="small" />
                    ) : (
                      <SmartToyIcon fontSize="small" />
                    )}
                    <Typography variant="caption" fontWeight="bold">
                      {msg.role === 'user' ? 'You' : 'NAP AI'}
                    </Typography>
                  </Box>
                  <Typography
                    variant="body2"
                    sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}
                  >
                    {msg.content}
                  </Typography>
                  {msg.queryExecuted && (
                    <Box sx={{ mt: 1 }}>
                      <Divider sx={{ my: 0.5 }} />
                      <Typography variant="caption" color="text.secondary">
                        Queries: {msg.queryExecuted}
                      </Typography>
                    </Box>
                  )}
                  {msg.role === 'assistant' && !msg.isError && (
                    <AIFeedbackWidget featureType="chat" responseData={msg.content} />
                  )}
                </CardContent>
              </Card>
            </Box>
          ))}
          {loading && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, ml: 1 }}>
              <CircularProgress size={20} />
              <Typography variant="body2" color="text.secondary">
                Analyzing your question...
              </Typography>
            </Box>
          )}
          <div ref={messagesEndRef} />
        </Paper>

        {/* Input Area */}
        <Paper elevation={3} sx={{ p: 1.5, borderRadius: 2 }}>
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
            <TextField
              fullWidth
              multiline
              maxRows={4}
              placeholder="Ask about your network... (e.g., 'Which devices failed their last audit?')"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={loading}
              variant="outlined"
              size="small"
              sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
            />
            <IconButton
              color="primary"
              onClick={handleSend}
              disabled={!input.trim() || loading}
              sx={{
                bgcolor: 'primary.main',
                color: 'white',
                '&:hover': { bgcolor: 'primary.dark' },
                '&.Mui-disabled': { bgcolor: 'action.disabledBackground' },
                borderRadius: 2,
                p: 1,
              }}
            >
              <SendIcon />
            </IconButton>
          </Box>
        </Paper>
      </Box>
    </Box>
  );
};

export default AIChat;
