import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Card,
  CardContent,
  CardActions,
  Grid,
  Divider,
  Chip,
  InputAdornment,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  CircularProgress,
  IconButton,
  Tooltip,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import SearchIcon from '@mui/icons-material/Search';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CodeIcon from '@mui/icons-material/Code';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import InfoIcon from '@mui/icons-material/Info';
import BookmarkBorderIcon from '@mui/icons-material/BookmarkBorder';
import BookmarkIcon from '@mui/icons-material/Bookmark';
import { motion } from 'framer-motion';
import RefreshIcon from '@mui/icons-material/Refresh';
import StorageIcon from '@mui/icons-material/Storage';
import CloseIcon from '@mui/icons-material/Close';

interface Tool {
  name: string;
  description?: string;
  inputSchema?: any;
  server?: string;
}

interface ToolsPanelProps {
  tools: Tool[];
  servers: string[];
  onCallTool: (serverName: string, toolName: string, args: any) => Promise<any>;
  onRefresh: () => Promise<void>;
  loading: boolean;
}

const StyledCard = styled(Card)(({ theme }) => ({
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  backdropFilter: 'blur(8px)',
  background: 'rgba(31, 41, 55, 0.7)',
  border: '1px solid rgba(255, 255, 255, 0.08)',
  transition: 'all 0.2s ease-in-out',
  '&:hover': {
    transform: 'translateY(-4px)',
    boxShadow: '0 12px 28px rgba(0, 0, 0, 0.3)',
  },
}));

const JsonEditor = styled(TextField)(({ theme }) => ({
  fontFamily: '"Roboto Mono", monospace',
  '& .MuiInputBase-input': {
    fontFamily: '"Roboto Mono", monospace',
  },
}));

const ToolsPanel: React.FC<ToolsPanelProps> = ({
  tools,
  servers,
  onCallTool,
  onRefresh,
  loading,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null);
  const [args, setArgs] = useState<any>({});
  const [response, setResponse] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [favoriteTools, setFavoriteTools] = useState<string[]>([]);
  const [selectedServer, setSelectedServer] = useState<string | null>(null);
  const [serverFilter, setServerFilter] = useState<string | null>(null);

  const filteredTools = tools.filter(tool => {
    const matchesSearch = !searchQuery || 
      tool.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (tool.description && tool.description.toLowerCase().includes(searchQuery.toLowerCase()));
    
    const matchesServer = !serverFilter || (tool.server && tool.server === serverFilter);
    
    return matchesSearch && matchesServer;
  });

  const handleSelectTool = (tool: Tool) => {
    setSelectedTool(tool);
    setArgs({});
    setResponse(null);
    if (tool.server) {
      setSelectedServer(tool.server);
    }
  };

  const handleArgsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setArgs(e.target.value);
    try {
      JSON.parse(e.target.value);
    } catch (err) {
    }
  };

  const handleCallTool = async () => {
    if (!selectedTool || !selectedServer) return;
    
    setIsLoading(true);
    setResponse(null);
    
    try {
      const result = await onCallTool(selectedServer, selectedTool.name, args);
      setResponse(result);
    } catch (error) {
      console.error('Error calling tool:', error);
      setResponse({ error: 'Failed to call tool' });
    } finally {
      setIsLoading(false);
    }
  };

  const toggleFavorite = (toolName: string) => {
    if (favoriteTools.includes(toolName)) {
      setFavoriteTools(favoriteTools.filter((name) => name !== toolName));
    } else {
      setFavoriteTools([...favoriteTools, toolName]);
    }
  };

  const isFavorite = (toolName: string) => favoriteTools.includes(toolName);

  const formatResponse = (res: any) => {
    if (typeof res === 'string') {
      try {
        const parsed = JSON.parse(res);
        return JSON.stringify(parsed, null, 2);
      } catch (e) {
        return res;
      }
    }
    
    return JSON.stringify(res, null, 2);
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Typography variant="h4" component="h1" fontWeight="bold">
          MCP Tools {filteredTools.length > 0 ? `(${filteredTools.length})` : ''}
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            color="primary"
            startIcon={loading ? <CircularProgress size={20} /> : <RefreshIcon />}
            onClick={onRefresh}
            disabled={loading}
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </Button>
        </Box>
      </Box>
      
      <Box sx={{ display: 'flex', mb: 4, gap: 2 }}>
        <TextField
          fullWidth
          placeholder="Search tools..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
          sx={{ mb: 0 }}
        />
        
        <Button
          variant="outlined"
          color={serverFilter ? "primary" : "inherit"}
          onClick={() => setServerFilter(serverFilter ? null : (servers[0] || null))}
          startIcon={<StorageIcon />}
        >
          {serverFilter || "All Servers"}
        </Button>
        
        {serverFilter && (
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <IconButton onClick={() => setServerFilter(null)} size="small">
              <CloseIcon fontSize="small" />
            </IconButton>
          </Box>
        )}
      </Box>
      
      {serverFilter && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle1" gutterBottom>
            Filtering by server: <Chip label={serverFilter} color="primary" />
          </Typography>
        </Box>
      )}
      
      {!serverFilter && servers.length > 0 && (
        <Box sx={{ mb: 3, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Typography variant="subtitle1" sx={{ mr: 1 }}>
            Filter by server:
          </Typography>
          {servers.map(server => (
            <Chip 
              key={server}
              label={server}
              onClick={() => setServerFilter(server)}
              clickable
              color="primary"
              variant="outlined"
            />
          ))}
        </Box>
      )}
      
      <Grid container spacing={3}>
        {filteredTools.map((tool, index) => (
          <Grid item xs={12} sm={6} md={4} key={`${tool.server || 'unknown'}-${tool.name}`}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
            >
              <StyledCard 
                sx={{ 
                  cursor: 'pointer',
                  ...(selectedTool?.name === tool.name && {
                    borderColor: 'primary.main', 
                    boxShadow: theme => theme.custom.glow.primary,
                  })
                }}
                onClick={() => handleSelectTool(tool)}
              >
                <CardContent sx={{ pb: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <CodeIcon sx={{ mr: 1, color: 'primary.main' }} />
                    <Typography variant="h6" fontWeight="bold">
                      {tool.name}
                    </Typography>
                  </Box>
                  
                  {tool.server && (
                    <Chip 
                      label={`Server: ${tool.server}`}
                      size="small"
                      sx={{ mb: 1 }}
                    />
                  )}
                  
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {tool.description || 'No description provided'}
                  </Typography>
                  
                  {tool.inputSchema && (
                    <Box sx={{ mb: 1 }}>
                      <Typography variant="caption" color="text.secondary">
                        Requires {Object.keys(tool.inputSchema.properties || {}).length} parameter(s)
                      </Typography>
                    </Box>
                  )}
                </CardContent>
                
                <CardActions sx={{ justifyContent: 'space-between', mt: 'auto', p: 1 }}>
                  <Tooltip title={isFavorite(tool.name) ? "Remove from favorites" : "Add to favorites"}>
                    <IconButton 
                      size="small" 
                      onClick={(e) => { 
                        e.stopPropagation(); 
                        toggleFavorite(tool.name);
                      }}
                    >
                      {isFavorite(tool.name) ? 
                        <BookmarkIcon color="primary" /> : 
                        <BookmarkBorderIcon />
                      }
                    </IconButton>
                  </Tooltip>
                  
                  <Button 
                    size="small" 
                    variant="text" 
                    endIcon={<PlayArrowIcon />}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSelectTool(tool);
                    }}
                  >
                    Use Tool
                  </Button>
                </CardActions>
              </StyledCard>
            </motion.div>
          </Grid>
        ))}
      </Grid>

      {selectedTool && (
        <Box component={motion.div} 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          sx={{ mt: 4 }}
        >
          <Typography variant="h5" gutterBottom>
            Execute Tool: {selectedTool.name}
            {selectedServer && (
              <Chip 
                label={`Server: ${selectedServer}`}
                size="small"
                color="primary"
                sx={{ ml: 2 }}
              />
            )}
          </Typography>
          
          <Divider sx={{ my: 2 }} />
          
          <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
            Arguments (JSON format)
          </Typography>
          
          <JsonEditor
            fullWidth
            multiline
            minRows={4}
            maxRows={12}
            value={JSON.stringify(args, null, 2)}
            onChange={handleArgsChange}
            error={false}
            helperText=""
            sx={{ 
              mb: 2,
              fontFamily: '"Roboto Mono", monospace',
            }}
          />
          
          {selectedTool.inputSchema && (
            <Accordion
              sx={{
                bgcolor: 'rgba(31, 41, 55, 0.6)',
                boxShadow: 'none',
                '&:before': {
                  display: 'none',
                },
                mb: 2,
              }}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography fontSize="0.875rem" fontWeight="bold">
                  Schema Definition
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Box
                  component="pre"
                  sx={{
                    p: 2,
                    borderRadius: 1,
                    bgcolor: 'rgba(0, 0, 0, 0.3)',
                    overflowX: 'auto',
                    fontSize: '0.75rem',
                  }}
                >
                  {JSON.stringify(selectedTool.inputSchema, null, 2)}
                </Box>
              </AccordionDetails>
            </Accordion>
          )}
          
          <Button
            variant="contained"
            color="primary"
            startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : <PlayArrowIcon />}
            onClick={handleCallTool}
            disabled={isLoading}
            fullWidth
            sx={{
              py: 1,
              '&:hover': {
                boxShadow: theme => theme.custom.glow.primary,
              },
            }}
          >
            {isLoading ? 'Running...' : 'Run Tool'}
          </Button>
          
          {response && (
            <Box sx={{ mt: 3 }}>
              <Divider sx={{ my: 2 }} />
              
              <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
                Response
              </Typography>
              
              <Box
                component="pre"
                sx={{
                  p: 2,
                  borderRadius: 1,
                  bgcolor: 'rgba(0, 0, 0, 0.3)',
                  overflowX: 'auto',
                  fontSize: '0.75rem',
                  maxHeight: '300px',
                  overflowY: 'auto',
                }}
              >
                {formatResponse(response)}
              </Box>
            </Box>
          )}
        </Box>
      )}
    </Box>
  );
};

export default ToolsPanel; 