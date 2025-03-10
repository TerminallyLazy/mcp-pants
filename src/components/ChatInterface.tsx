import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  TextField,
  IconButton,
  Paper,
  Typography,
  Avatar,
  Chip,
  Divider,
  Card,
  CardContent,
  CircularProgress,
  Alert,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import SendIcon from '@mui/icons-material/Send';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PersonIcon from '@mui/icons-material/Person';
import CodeIcon from '@mui/icons-material/Code';
import BuildIcon from '@mui/icons-material/Build';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

const MessageContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  marginBottom: theme.spacing(2),
  alignItems: 'flex-start',
}));

const MessageContent = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(2),
  maxWidth: '80%',
  borderRadius: '16px',
  position: 'relative',
}));

const UserMessageContent = styled(MessageContent)(({ theme }) => ({
  marginLeft: 'auto',
  background: theme.palette.primary.dark,
  color: theme.palette.primary.contrastText,
  boxShadow: `0 4px 20px rgba(59, 130, 246, 0.3)`,
  borderRadius: '16px 16px 2px 16px',
}));

const AssistantMessageContent = styled(MessageContent)(({ theme }) => ({
  marginRight: 'auto',
  background: theme.palette.background.paper,
  borderRadius: '16px 16px 16px 2px',
}));

const ToolCard = styled(Card)(({ theme }) => ({
  marginTop: theme.spacing(1),
  background: 'rgba(31, 41, 55, 0.7)',
  boxShadow: `0 8px 32px rgba(0, 0, 0, 0.3)`,
  backdropFilter: 'blur(8px)',
  borderRadius: theme.shape.borderRadius,
  border: '1px solid rgba(255, 255, 255, 0.05)',
}));

const TypingIndicator = () => (
  <Box sx={{ display: 'flex', gap: 1, p: 1 }}>
    {[0, 1, 2].map((i) => (
      <motion.div
        key={i}
        animate={{ y: [0, -5, 0] }}
        transition={{
          duration: 1,
          repeat: Infinity,
          repeatType: 'loop',
          delay: i * 0.2,
        }}
      >
        <Box
          sx={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            bgcolor: 'primary.main',
          }}
        />
      </motion.div>
    ))}
  </Box>
);

interface Tool {
  name: string;
  server: string;
  args: any;
  result: any;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  tools?: Tool[];
}

interface ChatInterfaceProps {
  onSendMessage: (message: string) => Promise<any>;
  connectedServers: string[];
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ onSendMessage, connectedServers }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSend = async () => {
    if (inputValue.trim() === '') return;
    setError(null);
    
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
    };
    
    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    
    try {
      const response = await onSendMessage(inputValue);
      
      // Check if the response contains tool usage
      const hasTools = response.tools && response.tools.length > 0;
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.response || 'No response',
        timestamp: new Date(),
        tools: hasTools ? response.tools : undefined,
      };
      
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      
      setError('Failed to get a response. Please make sure you have set up the Anthropic API key and that you have at least one MCP server connected.');
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, there was an error processing your request.',
        timestamp: new Date(),
      };
      
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const renderCodeBlock = ({ node, inline, className, children, ...props }: any) => {
    const match = /language-(\w+)/.exec(className || '');
    return !inline && match ? (
      <SyntaxHighlighter
        style={atomDark}
        language={match[1]}
        PreTag="div"
        {...props}
      >
        {String(children).replace(/\n$/, '')}
      </SyntaxHighlighter>
    ) : (
      <code className={className} {...props}>
        {children}
      </code>
    );
  };

  const renderToolResult = (tool: Tool) => {
    const resultContent = tool.result?.content || tool.result;
    let displayResult = '';
    
    if (Array.isArray(resultContent)) {
      // Handle array of content objects
      displayResult = resultContent.map((item: any) => {
        if (typeof item === 'object' && item.text) {
          return item.text;
        }
        return String(item);
      }).join('\n');
    } else if (typeof resultContent === 'object') {
      // Handle single object
      if (resultContent.text) {
        displayResult = resultContent.text;
      } else {
        // Stringify the object for display
        displayResult = JSON.stringify(resultContent, null, 2);
      }
    } else {
      // Handle string or other primitive
      displayResult = String(resultContent || 'No result returned');
    }
    
    return (
      <Box>
        <Typography variant="subtitle2" sx={{ mt: 1, fontWeight: 'bold' }}>
          Tool Result:
        </Typography>
        <Box sx={{ 
          mt: 1, 
          p: 1, 
          borderRadius: 1, 
          bgcolor: 'background.paper',
          border: '1px solid rgba(255,255,255,0.1)',
          fontFamily: 'monospace',
          fontSize: '0.85rem',
          whiteSpace: 'pre-wrap',
          maxHeight: '200px',
          overflow: 'auto'
        }}>
          {displayResult}
        </Box>
      </Box>
    );
  };

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
      }}
    >
      {error && (
        <Alert 
          severity="error" 
          sx={{ mb: 2 }}
          onClose={() => setError(null)}
        >
          {error}
        </Alert>
      )}
      
      {connectedServers.length === 0 && (
        <Alert 
          severity="warning" 
          sx={{ mb: 2 }}
        >
          No MCP servers connected. Connect to at least one server to use tools with Claude.
        </Alert>
      )}
      
      <Box
        sx={{
          flexGrow: 1,
          overflowY: 'auto',
          p: 2,
          scrollbarWidth: 'thin',
          '&::-webkit-scrollbar': {
            width: '6px',
          },
          '&::-webkit-scrollbar-thumb': {
            backgroundColor: 'rgba(255, 255, 255, 0.1)',
            borderRadius: '3px',
          },
        }}
      >
        {messages.length === 0 ? (
          <Box
            sx={{
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexDirection: 'column',
              gap: 2,
              opacity: 0.7,
            }}
          >
            <motion.div
              initial={{ scale: 0.5, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.5 }}
            >
              <Avatar
                sx={{
                  width: 80,
                  height: 80,
                  bgcolor: 'primary.dark',
                  boxShadow: theme => theme.custom.glow.primary,
                }}
              >
                <SmartToyIcon sx={{ fontSize: 40 }} />
              </Avatar>
            </motion.div>
            <Typography variant="h6" color="text.secondary">
              Start a conversation with Claude
            </Typography>
            <Typography variant="body2" color="text.secondary" textAlign="center" sx={{ maxWidth: 500 }}>
              Claude can use tools from all connected MCP servers to help you.
              {connectedServers.length > 0 && (
                <Box component="span" sx={{ display: 'block', mt: 1 }}>
                  Connected servers: {connectedServers.join(', ')}
                </Box>
              )}
            </Typography>
          </Box>
        ) : (
          messages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <MessageContainer>
                <Avatar
                  sx={{
                    mr: 1,
                    ...(message.role === 'assistant' && {
                      bgcolor: 'primary.dark',
                      boxShadow: theme => theme.custom.glow.primary,
                    }),
                  }}
                >
                  {message.role === 'assistant' ? (
                    <SmartToyIcon />
                  ) : (
                    <PersonIcon />
                  )}
                </Avatar>
                
                {message.role === 'user' ? (
                  <UserMessageContent>
                    <Typography variant="body1">{message.content}</Typography>
                  </UserMessageContent>
                ) : (
                  <AssistantMessageContent>
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        code: renderCodeBlock,
                      }}
                    >
                      {message.content}
                    </ReactMarkdown>
                    
                    {message.tools && message.tools.length > 0 && (
                      <Box sx={{ mt: 2 }}>
                        {message.tools.map((tool, index) => (
                          <ToolCard key={index}>
                            <CardContent>
                              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                                <BuildIcon sx={{ mr: 1, color: 'primary.main' }} />
                                <Typography variant="subtitle1" fontWeight="bold">
                                  {tool.name}
                                </Typography>
                                <Chip 
                                  label={`Server: ${tool.server}`} 
                                  size="small" 
                                  sx={{ ml: 1 }}
                                />
                              </Box>
                              
                              <Divider sx={{ mb: 2 }} />
                              
                              <Typography variant="subtitle2">
                                Arguments:
                              </Typography>
                              <Box sx={{ 
                                p: 1, 
                                borderRadius: 1, 
                                bgcolor: 'rgba(0,0,0,0.2)',
                                fontFamily: 'monospace',
                                fontSize: '0.85rem',
                                mb: 2
                              }}>
                                <pre>{JSON.stringify(tool.args, null, 2)}</pre>
                              </Box>
                              
                              {renderToolResult(tool)}
                            </CardContent>
                          </ToolCard>
                        ))}
                      </Box>
                    )}
                  </AssistantMessageContent>
                )}
              </MessageContainer>
              
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{
                  display: 'block',
                  textAlign: message.role === 'user' ? 'right' : 'left',
                  mb: 3,
                  opacity: 0.7,
                }}
              >
                {message.timestamp.toLocaleTimeString()}
              </Typography>
            </motion.div>
          ))
        )}
        
        <div ref={messagesEndRef} />
        
        {isLoading && (
          <MessageContainer>
            <Avatar
              sx={{
                mr: 1,
                bgcolor: 'primary.dark',
                boxShadow: theme => theme.custom.glow.primary,
              }}
            >
              <SmartToyIcon />
            </Avatar>
            <AssistantMessageContent sx={{ p: 1 }}>
              <TypingIndicator />
            </AssistantMessageContent>
          </MessageContainer>
        )}
      </Box>
      
      <Box
        sx={{
          p: 2,
          borderTop: '1px solid rgba(255, 255, 255, 0.1)',
          bgcolor: 'background.paper',
        }}
      >
        <Box
          sx={{
            display: 'flex',
            gap: 1,
          }}
        >
          <TextField
            fullWidth
            multiline
            maxRows={4}
            placeholder="Send a message to Claude..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            variant="outlined"
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: '16px',
                bgcolor: 'rgba(0, 0, 0, 0.2)',
              },
            }}
            disabled={isLoading}
          />
          
          <IconButton
            color="primary"
            onClick={handleSend}
            disabled={isLoading || !inputValue.trim()}
            sx={{
              height: 54,
              width: 54,
              bgcolor: 'primary.dark',
              transition: 'all 0.2s ease-in-out',
              '&:hover': {
                bgcolor: 'primary.main',
                boxShadow: theme => theme.custom.glow.primary,
              },
            }}
          >
            {isLoading ? (
              <CircularProgress size={24} />
            ) : (
              <SendIcon />
            )}
          </IconButton>
        </Box>
      </Box>
    </Box>
  );
};

export default ChatInterface; 