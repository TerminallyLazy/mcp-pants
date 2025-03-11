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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import SearchIcon from '@mui/icons-material/Search';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import StorageIcon from '@mui/icons-material/Storage';
import LinkIcon from '@mui/icons-material/Link';
import DescriptionIcon from '@mui/icons-material/Description';
import BookmarkBorderIcon from '@mui/icons-material/BookmarkBorder';
import BookmarkIcon from '@mui/icons-material/Bookmark';
import VisibilityIcon from '@mui/icons-material/Visibility';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import CloseIcon from '@mui/icons-material/Close';
import RefreshIcon from '@mui/icons-material/Refresh';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import remarkGfm from 'remark-gfm';

interface Resource {
  uri: string;
  name?: string;
  description?: string;
  mimeType?: string;
  server?: string;
}

interface ResourceContent {
  uri: string;
  mimeType?: string;
  text: string;
}

interface ResourcesPanelProps {
  resources: Resource[];
  servers: string[];
  onFetchResource: (serverName: string, uri: string) => Promise<ResourceContent>;
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

const ContentPreview = styled(Box)(({ theme }) => ({
  fontFamily: '"Roboto Mono", monospace',
  padding: theme.spacing(2),
  borderRadius: theme.shape.borderRadius,
  backgroundColor: 'rgba(0, 0, 0, 0.3)',
  overflowX: 'auto',
  maxHeight: '500px',
  overflowY: 'auto',
}));

const CodeBlock = ({ language, value }: { language: string, value: string }) => {
  return (
    <SyntaxHighlighter style={atomDark} language={language} wrapLines>
      {value}
    </SyntaxHighlighter>
  );
};

const ResourcesPanel: React.FC<ResourcesPanelProps> = ({
  resources,
  servers,
  onFetchResource,
  onRefresh,
  loading,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedResource, setSelectedResource] = useState<Resource | null>(null);
  const [resourceContent, setResourceContent] = useState<ResourceContent | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [favoriteResources, setFavoriteResources] = useState<string[]>([]);
  const [serverFilter, setServerFilter] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  const filteredResources = resources.filter(resource => {
    const matchesSearch = !searchQuery || 
      resource.uri.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (resource.name && resource.name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (resource.description && resource.description.toLowerCase().includes(searchQuery.toLowerCase()));
    
    const matchesServer = !serverFilter || (resource.server && resource.server === serverFilter);
    
    return matchesSearch && matchesServer;
  });

  const handleSelectResource = (resource: Resource) => {
    setSelectedResource(resource);
    setResourceContent(null);
  };

  const handleFetchResource = async () => {
    if (!selectedResource || !selectedResource.server) return;
    
    setIsLoading(true);
    setResourceContent(null);
    
    try {
      const result = await onFetchResource(selectedResource.server, selectedResource.uri);
      setResourceContent(result);
    } catch (error) {
      console.error('Error fetching resource:', error);
      setResourceContent({
        uri: selectedResource.uri,
        text: 'Failed to fetch resource content',
        mimeType: 'text/plain'
      });
    } finally {
      setIsLoading(false);
    }
  };

  const toggleFavorite = (uri: string) => {
    if (favoriteResources.includes(uri)) {
      setFavoriteResources(favoriteResources.filter((item) => item !== uri));
    } else {
      setFavoriteResources([...favoriteResources, uri]);
    }
  };

  const isFavorite = (uri: string) => favoriteResources.includes(uri);

  const handleCopyUri = (uri: string) => {
    navigator.clipboard.writeText(uri);
  };

  const handleFullViewOpen = () => {
    setDialogOpen(true);
  };

  const handleFullViewClose = () => {
    setDialogOpen(false);
  };

  const getResourceDisplayName = (resource: Resource) => {
    if (resource.name) return resource.name;
    
    // Extract a name from the URI
    const parts = resource.uri.split('/');
    return parts[parts.length - 1] || resource.uri;
  };

  const getContentType = (mimeType?: string) => {
    if (!mimeType) return 'text';
    if (mimeType.includes('json')) return 'json';
    if (mimeType.includes('markdown')) return 'markdown';
    if (mimeType.includes('javascript') || mimeType.includes('typescript')) return 'javascript';
    if (mimeType.includes('html')) return 'html';
    if (mimeType.includes('css')) return 'css';
    if (mimeType.includes('xml')) return 'xml';
    return 'text';
  };

  const renderContent = (content: ResourceContent) => {
    const contentType = getContentType(content.mimeType);
    
    switch (contentType) {
      case 'json':
        try {
          const formattedJson = JSON.stringify(JSON.parse(content.text), null, 2);
          return <CodeBlock language="json" value={formattedJson} />;
        } catch {
          return <pre>{content.text}</pre>;
        }
      case 'markdown':
        return (
          <ReactMarkdown 
            remarkPlugins={[remarkGfm]}
            components={{
              code({className, children, ...props}: any) {
                const match = /language-(\w+)/.exec(className || '');
                return match ? (
                  <SyntaxHighlighter
                    language={match[1]}
                    style={atomDark as any}
                  >
                    {String(children).replace(/\n$/, '')}
                  </SyntaxHighlighter>
                ) : (
                  <code className={className} {...props}>
                    {children}
                  </code>
                );
              }
            }}
          >
            {content.text}
          </ReactMarkdown>
        );
      case 'javascript':
        return <CodeBlock language="javascript" value={content.text} />;
      case 'html':
        return <CodeBlock language="html" value={content.text} />;
      case 'css':
        return <CodeBlock language="css" value={content.text} />;
      case 'xml':
        return <CodeBlock language="xml" value={content.text} />;
      default:
        return <pre>{content.text}</pre>;
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Typography variant="h4" component="h1" fontWeight="bold">
          MCP Resources {filteredResources.length > 0 ? `(${filteredResources.length})` : ''}
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
          placeholder="Search resources..."
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
        {filteredResources.map((resource, index) => (
          <Grid item xs={12} sm={6} md={4} key={`${resource.server || 'unknown'}-${resource.uri}`}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
            >
              <StyledCard 
                sx={{ 
                  cursor: 'pointer',
                  ...(selectedResource?.uri === resource.uri && {
                    borderColor: 'primary.main', 
                    boxShadow: theme => theme.custom.glow.primary,
                  })
                }}
                onClick={() => handleSelectResource(resource)}
              >
                <CardContent sx={{ pb: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <DescriptionIcon sx={{ mr: 1, color: 'primary.main' }} />
                    <Typography variant="h6" fontWeight="medium" noWrap>
                      {getResourceDisplayName(resource)}
                    </Typography>
                  </Box>
                  
                  {resource.server && (
                    <Chip 
                      label={`Server: ${resource.server}`}
                      size="small"
                      sx={{ mb: 1 }}
                    />
                  )}
                  
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {resource.description || 'No description provided'}
                  </Typography>
                  
                  <Box sx={{ mb: 1 }}>
                    <Typography 
                      variant="caption" 
                      color="text.secondary"
                      sx={{
                        display: 'block',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap'
                      }}
                    >
                      URI: {resource.uri}
                    </Typography>
                    
                    {resource.mimeType && (
                      <Typography variant="caption" color="text.secondary">
                        Type: {resource.mimeType}
                      </Typography>
                    )}
                  </Box>
                </CardContent>
                
                <CardActions sx={{ justifyContent: 'space-between', mt: 'auto', p: 1 }}>
                  <Tooltip title={isFavorite(resource.uri) ? "Remove from favorites" : "Add to favorites"}>
                    <IconButton 
                      size="small" 
                      onClick={(e) => { 
                        e.stopPropagation(); 
                        toggleFavorite(resource.uri);
                      }}
                    >
                      {isFavorite(resource.uri) ? 
                        <BookmarkIcon color="primary" /> : 
                        <BookmarkBorderIcon />
                      }
                    </IconButton>
                  </Tooltip>
                  
                  <Box sx={{ display: 'flex' }}>
                    <Tooltip title="Copy URI">
                      <IconButton 
                        size="small" 
                        onClick={(e) => {
                          e.stopPropagation();
                          handleCopyUri(resource.uri);
                        }}
                      >
                        <ContentCopyIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    
                    <Button 
                      size="small" 
                      variant="text" 
                      endIcon={<VisibilityIcon />}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSelectResource(resource);
                      }}
                    >
                      View
                    </Button>
                  </Box>
                </CardActions>
              </StyledCard>
            </motion.div>
          </Grid>
        ))}
      </Grid>

      {selectedResource && (
        <Box component={motion.div} 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          sx={{ mt: 4 }}
        >
          <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
            <LinkIcon sx={{ mr: 1 }} />
            Resource: {getResourceDisplayName(selectedResource)}
            {selectedResource.server && (
              <Chip 
                label={`Server: ${selectedResource.server}`}
                size="small"
                color="primary"
                sx={{ ml: 2 }}
              />
            )}
          </Typography>
          
          <Divider sx={{ my: 2 }} />
          
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
              URI
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Typography 
                variant="body2" 
                component="code"
                sx={{ 
                  bgcolor: 'rgba(0, 0, 0, 0.2)',
                  p: 1,
                  borderRadius: 1,
                  flexGrow: 1,
                  fontFamily: '"Roboto Mono", monospace',
                }}
              >
                {selectedResource.uri}
              </Typography>
              <IconButton 
                size="small" 
                onClick={() => handleCopyUri(selectedResource.uri)}
                sx={{ ml: 1 }}
              >
                <ContentCopyIcon fontSize="small" />
              </IconButton>
            </Box>
          </Box>
          
          {selectedResource.description && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
                Description
              </Typography>
              <Typography variant="body2">
                {selectedResource.description}
              </Typography>
            </Box>
          )}
          
          <Button
            variant="contained"
            color="primary"
            startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : <VisibilityIcon />}
            onClick={handleFetchResource}
            disabled={isLoading || !selectedResource.server}
            fullWidth
            sx={{
              py: 1,
              '&:hover': {
                boxShadow: theme => theme.custom.glow.primary,
              },
            }}
          >
            {isLoading ? 'Loading...' : 'Fetch Resource Content'}
          </Button>
          
          {!selectedResource.server && (
            <Typography variant="caption" color="error" sx={{ display: 'block', mt: 1, textAlign: 'center' }}>
              Server information is missing. Cannot fetch resource.
            </Typography>
          )}
          
          {resourceContent && (
            <Box sx={{ mt: 3 }}>
              <Divider sx={{ my: 2 }} />
              
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                <Typography variant="subtitle2" fontWeight="bold">
                  Resource Content
                  {resourceContent.mimeType && (
                    <Chip 
                      label={resourceContent.mimeType}
                      size="small"
                      sx={{ ml: 1 }}
                    />
                  )}
                </Typography>
                
                <Button
                  size="small"
                  startIcon={<VisibilityIcon />}
                  onClick={handleFullViewOpen}
                >
                  Full View
                </Button>
              </Box>
              
              <ContentPreview>
                {renderContent(resourceContent)}
              </ContentPreview>
            </Box>
          )}
        </Box>
      )}
      
      <Dialog
        open={dialogOpen}
        onClose={handleFullViewClose}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">
              {selectedResource ? getResourceDisplayName(selectedResource) : 'Resource Content'}
            </Typography>
            <IconButton onClick={handleFullViewClose} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent dividers>
          {resourceContent && (
            <Box sx={{ maxHeight: '80vh', overflow: 'auto' }}>
              {renderContent(resourceContent)}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleFullViewClose}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ResourcesPanel;
