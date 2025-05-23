import { useState, useRef, useEffect } from 'react';
import { Box, Container, Paper, TextField, Button, Typography, ThemeProvider, createTheme, Avatar, Grid } from '@mui/material';
import axios from 'axios';
import { API_ENDPOINTS } from './config';

const theme = createTheme({
  palette: {
    primary: {
      main: '#6A5ACD', // SlateBlue - more modern and appealing
    },
    secondary: {
      main: '#FF6B6B', // Coral pink - child-friendly
    },
    background: {
      default: '#F8F9FA',
      paper: '#FFFFFF',
    },
  },
  typography: {
    fontFamily: '"Comic Sans MS", "Comic Sans", cursive',
    h3: {
      fontWeight: 700,
      color: '#6A5ACD',
    },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 16,
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 20,
          textTransform: 'none',
          fontWeight: 600,
        },
      },
    },
  },
});

function App() {
  const [userInput, setUserInput] = useState('');
  const [messages, setMessages] = useState([
    { text: "Hello! I'm your storytelling assistant. What kind of story would you like to hear today?", sender: 'bot' }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [story, setStory] = useState('');
  const messagesEndRef = useRef(null);
  
  // Auto-scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setIsLoading(true);  // Now using setIsLoading instead of setLoading
    setError(null);
    
    try {
      const response = await axios.post('/api/story', {
        prompt: userInput
      });
      
      // Add the user's message
      setMessages(prev => [...prev, { text: userInput, sender: 'user' }]);
      
      // Add the bot's response
      setMessages(prev => [...prev, { 
        text: response.data.status === 'success' 
          ? response.data.story
          : response.data.message, 
        sender: 'bot' 
      }]);
      // Clear the input
      setUserInput('');
    } catch (error) {
      console.error('Error details:', error.response?.data || error.message);
      setError(error.response?.data?.message || 'An error occurred while generating the story');
      
      // Add error message to chat
      setMessages(prev => [...prev, { 
        text: 'Sorry, I encountered an error while generating the story. Please try again.',
        sender: 'bot'
      }]);
    } finally {
      setIsLoading(false);  // Now using setIsLoading instead of setLoading
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <Container maxWidth="md" sx={{ height: '100vh', py: 2 }}>
        <Grid container spacing={2} direction="column" sx={{ height: '100%' }}>
          <Grid item sx={{ flexShrink: 0 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 2, mb: 1 }}>
              <Avatar 
                src="/storytelling-icon.png" 
                alt="Storytelling AI" 
                sx={{ width: 56, height: 56, bgcolor: 'primary.main' }}
              >
                📚
              </Avatar>
              <Typography variant="h3" align="center">
                🌟 Story Time! 🌟
              </Typography>
            </Box>
          </Grid>
          
          <Grid item xs sx={{ flexGrow: 1, minHeight: 0 }}>
            <Paper
              elevation={3}
              sx={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                p: 3,
                backgroundColor: 'background.paper',
                boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
              }}
            >
              <Box
                className="message-container"
                sx={{
                  flexGrow: 1,
                  overflowY: 'auto',
                  mb: 2,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 2,
                  px: 1,
                  minHeight: 0,
                }}
              >
                {messages.map((message, index) => (
                  <Box
                    key={index}
                    sx={{
                      alignSelf: message.sender === 'user' ? 'flex-end' : 'flex-start',
                      maxWidth: '80%',
                      display: 'flex',
                      alignItems: 'flex-end',
                      gap: 1,
                    }}
                  >
                    {message.sender === 'bot' && (
                      <Avatar 
                        sx={{ 
                          bgcolor: 'secondary.main', 
                          width: 40, 
                          height: 40,
                          display: { xs: 'none', sm: 'flex' }
                        }}
                      >
                        📚
                      </Avatar>
                    )}
                    <Paper
                      elevation={2}
                      sx={{
                        p: 2,
                        backgroundColor: message.sender === 'user' ? 'primary.main' : 'secondary.light',
                        color: message.sender === 'user' ? 'white' : 'text.primary',
                        borderRadius: message.sender === 'user' ? '20px 20px 5px 20px' : '20px 20px 20px 5px',
                        boxShadow: message.sender === 'user' 
                          ? '0 4px 12px rgba(106, 90, 205, 0.2)' 
                          : '0 4px 12px rgba(255, 107, 107, 0.2)',
                      }}
                    >
                      <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{message.text}</Typography>
                    </Paper>
                    {message.sender === 'user' && (
                      <Avatar 
                        sx={{ 
                          bgcolor: 'primary.main', 
                          width: 40, 
                          height: 40,
                          display: { xs: 'none', sm: 'flex' }
                        }}
                      >
                        👧
                      </Avatar>
                    )}
                  </Box>
                ))}
                <div ref={messagesEndRef} />
              </Box>
              
              <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', gap: 1 }}>
                <TextField
                  fullWidth
                  variant="outlined"
                  placeholder="Tell me what kind of story you'd like to hear!"
                  value={userInput}
                  onChange={(e) => setUserInput(e.target.value)}
                  disabled={isLoading}
                  sx={{ 
                    backgroundColor: 'background.paper',
                    '& .MuiOutlinedInput-root': {
                      borderRadius: '20px',
                    }
                  }}
                />
                <Button 
                  type="submit" 
                  variant="contained" 
                  color="primary"
                  disabled={isLoading || !userInput.trim()}
                  sx={{ px: 3 }}
                >
                  {isLoading ? 'Thinking...' : 'Send'}
                </Button>
              </Box>
            </Paper>
          </Grid>
        </Grid>
      </Container>
    </ThemeProvider>
  );
}

export default App;