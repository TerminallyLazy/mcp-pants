import React, { useState } from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  Divider,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  LinearProgress,
  Tooltip,
  Alert,
  CircularProgress,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { motion } from 'framer-motion';
import { 
  PowerSettingsNew as PowerIcon,
  Refresh as RefreshIcon,
  Add as AddIcon,
  Info as InfoIcon,
  Storage as StorageIcon,
  Check as CheckIcon,
  Close as CloseIcon,
} from '@mui/icons-material';

const StyledCard = styled(Card)(({ theme }) => ({
  position: 'relative',
  backdropFilter: 'blur(8px)',
  background: 'rgba(31, 41, 55, 0.7)',
  border: '1px solid rgba(255, 255, 255, 0.08)',
  overflow: 'visible',
  transition: 'all 0.2s ease-in-out',
  '&:hover': {
    transform: 'translateY(-4px)',
    boxShadow: '0 12px 28px rgba(0, 0, 0, 0.3)',
  },
}));

const StatusIndicator = styled('div', {
  shouldForwardProp: (prop) => prop !== 'status',
})<{ status: 'connected' | 'disconnected' | 'error' }>(({ theme, status }) => ({
  position: 'absolute',
  top: -8,
  right: -8,
  width: 20,
  height: 20,
  borderRadius: '50%',
  zIndex: 1,
  ...(status === 'connected' && {
    backgroundColor: theme.palette.success.main,
    boxShadow: theme.custom.glow.success,
  }),
  ...(status === 'disconnected' && {
    backgroundColor: theme.palette.text.secondary,
  }),
  ...(status === 'error' && {
    backgroundColor: theme.palette.error.main,
    boxShadow: theme.custom.glow.error,
  }),
}));

const ConnectButton = styled(Button)(({ theme }) => ({
  borderRadius: '20px',
  padding: '4px 16px',
  fontWeight: 'bold',
  textTransform: 'none',
  boxShadow: 'none',
  '&.MuiButton-containedSuccess': {
    '&:hover': {
      boxShadow: theme.custom.glow.success,
    },
  },
  '&.MuiButton-outlined': {
    borderWidth: 2,
    '&:hover': {
      borderWidth: 2,
    },
  },
}));

interface ServerManagementProps {
  servers: string[];
  connectedServers: string[];
  onConnect: (server: string) => Promise<void>;
  onDisconnect: (server?: string) => Promise<void>;
  onRefresh: () => Promise<void>;
  loading: boolean;
  error: string | null;
}

const ServerManagement: React.FC<ServerManagementProps> = ({
  servers,
  connectedServers,
  onConnect,
  onDisconnect,
  onRefresh,
  loading,
  error,
}) => {
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [newServerName, setNewServerName] = useState('');
  const [loadingServer, setLoadingServer] = useState<string | null>(null);

  const handleConnect = async (server: string) => {
    if (connectedServers.includes(server)) {
      await onDisconnect(server);
    } else {
      setLoadingServer(server);
      await onConnect(server);
      setLoadingServer(null);
    }
  };

  const getServerStatus = (server: string) => {
    if (connectedServers.includes(server)) return 'connected';
    return 'disconnected';
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Typography variant="h4" component="h1" fontWeight="bold">
          MCP Servers {servers.length > 0 ? `(${servers.length})` : ''}
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
          
          <Button
            variant="contained"
            color="secondary"
            startIcon={<AddIcon />}
            onClick={() => setShowAddDialog(true)}
          >
            Add Server
          </Button>
        </Box>
      </Box>
      
      {error && (
        <Alert 
          severity="error" 
          sx={{ mb: 3 }}
          action={
            <IconButton color="inherit" size="small" onClick={() => {}}>
              <CloseIcon fontSize="inherit" />
            </IconButton>
          }
        >
          {error}
        </Alert>
      )}
      
      {loading && <LinearProgress sx={{ mb: 3 }} />}
      
      {servers.length === 0 && !loading && (
        <Alert 
          severity="info" 
          sx={{ mb: 3 }}
        >
          No servers found. Check that the backend is running and click "Refresh" to try again.
        </Alert>
      )}
      
      <Grid container spacing={3}>
        {servers.map((server, index) => (
          <Grid item xs={12} sm={6} md={4} key={server}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
            >
              <StyledCard>
                <StatusIndicator status={getServerStatus(server)} />
                
                <CardContent sx={{ pb: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <StorageIcon sx={{ mr: 1, color: 'primary.main' }} />
                    <Typography variant="h6" fontWeight="bold" noWrap>
                      {server}
                    </Typography>
                  </Box>
                  
                  <Divider sx={{ my: 1 }} />
                  
                  <Chip
                    label={connectedServers.includes(server) ? "Connected" : "Disconnected"}
                    size="small"
                    color={connectedServers.includes(server) ? "success" : "default"}
                    sx={{ 
                      borderRadius: '4px',
                      ...(connectedServers.includes(server) && { boxShadow: theme => theme.custom.glow.success }),
                    }}
                  />
                </CardContent>
                
                <CardActions sx={{ justifyContent: 'space-between', px: 2, pb: 2 }}>
                  <Tooltip title="Server Info">
                    <IconButton size="small">
                      <InfoIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  
                  {loadingServer === server ? (
                    <CircularProgress size={24} />
                  ) : (
                    <ConnectButton
                      variant={connectedServers.includes(server) ? "contained" : "outlined"}
                      color={connectedServers.includes(server) ? "success" : "primary"}
                      size="small"
                      startIcon={connectedServers.includes(server) ? <CheckIcon /> : <PowerIcon />}
                      onClick={() => handleConnect(server)}
                    >
                      {connectedServers.includes(server) ? "Connected" : "Connect"}
                    </ConnectButton>
                  )}
                </CardActions>
              </StyledCard>
            </motion.div>
          </Grid>
        ))}
      </Grid>
      
      <Dialog
        open={showAddDialog}
        onClose={() => setShowAddDialog(false)}
        PaperProps={{
          sx: {
            bgcolor: 'background.paper',
            backdropFilter: 'blur(8px)',
            boxShadow: '0 12px 28px rgba(0, 0, 0, 0.3)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: 2,
          }
        }}
      >
        <DialogTitle>Add MCP Server</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Server Name"
            fullWidth
            variant="outlined"
            value={newServerName}
            onChange={(e) => setNewServerName(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowAddDialog(false)}>Cancel</Button>
          <Button 
            onClick={() => {
              // Save new server logic would go here
              setShowAddDialog(false);
              setNewServerName('');
            }}
            variant="contained"
            color="primary"
            disabled={!newServerName.trim()}
          >
            Add
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ServerManagement; 