import React, { useState } from 'react';
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Box,
  Typography,
  IconButton,
  Collapse,
  Tooltip,
  Badge,
  Avatar,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { motion } from 'framer-motion';
import { 
  Home as HomeIcon,
  Chat as ChatIcon,
  Code as CodeIcon,
  Storage as StorageIcon,
  Settings as SettingsIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  SmartToy as SmartToyIcon,
  Bolt as BoltIcon,
  AddCircle as AddCircleIcon,
} from '@mui/icons-material';

const drawerWidth = 280;

const DrawerHeader = styled('div')(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  padding: theme.spacing(0, 2),
  ...theme.mixins.toolbar,
  justifyContent: 'space-between',
}));

const GlowingBadge = styled(Badge)(({ theme }) => ({
  '& .MuiBadge-badge': {
    backgroundColor: theme.palette.success.main,
    boxShadow: theme.custom.glow.success,
  },
}));

interface SidebarProps {
  servers: string[];
  connectedServers: string[];
  onConnect: (server: string) => void;
  activeView: string;
  onViewChange: (view: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  servers,
  connectedServers,
  onConnect,
  activeView,
  onViewChange,
}) => {
  const [serversOpen, setServersOpen] = useState(true);
  const [showAllServers, setShowAllServers] = useState(false);
  
  // Show only a few servers or all servers based on toggle
  const visibleServers = showAllServers ? servers : servers.slice(0, 5);
  
  const isConnected = (server: string) => {
    return connectedServers.includes(server);
  };

  const countConnectedServers = () => {
    return connectedServers.length;
  };

  return (
    <Drawer
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: drawerWidth,
          boxSizing: 'border-box',
        },
      }}
      variant="permanent"
      anchor="left"
    >
      <DrawerHeader>
        <Box display="flex" alignItems="center">
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.3 }}
          >
            <Avatar
              sx={{
                bgcolor: 'primary.main',
                boxShadow: theme => theme.custom.glow.primary,
                mr: 1,
              }}
            >
              <SmartToyIcon />
            </Avatar>
          </motion.div>
          <Typography variant="h6" fontWeight="bold">
            MCP Client
          </Typography>
        </Box>
        <IconButton>
          <SettingsIcon fontSize="small" />
        </IconButton>
      </DrawerHeader>
      
      <Divider />
      
      <List>
        <ListItem disablePadding>
          <ListItemButton
            selected={activeView === 'home'}
            onClick={() => onViewChange('home')}
            sx={{ 
              borderRadius: '8px', 
              mx: 1, 
              my: 0.5,
              '&.Mui-selected': {
                bgcolor: 'rgba(96, 165, 250, 0.15)',
                boxShadow: theme => theme.custom.glow.primary,
              }
            }}
          >
            <ListItemIcon>
              <HomeIcon color={activeView === 'home' ? 'primary' : undefined} />
            </ListItemIcon>
            <ListItemText primary="Dashboard" />
          </ListItemButton>
        </ListItem>
        
        <ListItem disablePadding>
          <ListItemButton
            selected={activeView === 'chat'}
            onClick={() => onViewChange('chat')}
            sx={{ 
              borderRadius: '8px', 
              mx: 1, 
              my: 0.5,
              '&.Mui-selected': {
                bgcolor: 'rgba(96, 165, 250, 0.15)',
                boxShadow: theme => theme.custom.glow.primary,
              }
            }}
          >
            <ListItemIcon>
              <ChatIcon color={activeView === 'chat' ? 'primary' : undefined} />
            </ListItemIcon>
            <ListItemText primary="Chat" />
          </ListItemButton>
        </ListItem>
        
        <ListItem disablePadding>
          <ListItemButton
            selected={activeView === 'tools'}
            onClick={() => onViewChange('tools')}
            sx={{ 
              borderRadius: '8px', 
              mx: 1, 
              my: 0.5,
              '&.Mui-selected': {
                bgcolor: 'rgba(96, 165, 250, 0.15)',
                boxShadow: theme => theme.custom.glow.primary,
              }
            }}
          >
            <ListItemIcon>
              <CodeIcon color={activeView === 'tools' ? 'primary' : undefined} />
            </ListItemIcon>
            <ListItemText primary="Tools" />
          </ListItemButton>
        </ListItem>
        
        <ListItem disablePadding>
          <ListItemButton
            selected={activeView === 'resources'}
            onClick={() => onViewChange('resources')}
            sx={{ 
              borderRadius: '8px', 
              mx: 1, 
              my: 0.5,
              '&.Mui-selected': {
                bgcolor: 'rgba(96, 165, 250, 0.15)',
                boxShadow: theme => theme.custom.glow.primary,
              }
            }}
          >
            <ListItemIcon>
              <StorageIcon color={activeView === 'resources' ? 'primary' : undefined} />
            </ListItemIcon>
            <ListItemText primary="Resources" />
          </ListItemButton>
        </ListItem>
      </List>
      
      <Divider sx={{ my: 2 }} />
      
      <ListItem>
        <Box display="flex" justifyContent="space-between" width="100%" alignItems="center">
          <Typography variant="subtitle2" color="text.secondary">
            MCP SERVERS
          </Typography>
          <IconButton size="small" onClick={() => setServersOpen(!serversOpen)}>
            {serversOpen ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
        </Box>
      </ListItem>
      
      <Collapse in={serversOpen} timeout="auto" unmountOnExit>
        <List>
          {visibleServers.map((server, index) => (
            <motion.div
              key={server}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2, delay: 0.1 + index * 0.05 }}
            >
              <ListItemButton
                sx={{ pl: 4 }}
                onClick={() => onConnect(server)}
                selected={isConnected(server)}
              >
                <ListItemIcon>
                  {isConnected(server) ? (
                    <GlowingBadge
                      variant="dot"
                      overlap="circular"
                    >
                      <SmartToyIcon />
                    </GlowingBadge>
                  ) : (
                    <SmartToyIcon />
                  )}
                </ListItemIcon>
                <ListItemText 
                  primary={server} 
                  primaryTypographyProps={{
                    fontWeight: isConnected(server) ? 'bold' : 'normal',
                  }}
                />
              </ListItemButton>
            </motion.div>
          ))}
          
          {servers.length > 5 && (
            <ListItemButton 
              sx={{ pl: 4 }}
              onClick={() => setShowAllServers(!showAllServers)}
            >
              <ListItemIcon>
                {showAllServers ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </ListItemIcon>
              <ListItemText 
                primary={showAllServers ? "Show Less" : `Show ${servers.length - 5} More`} 
                primaryTypographyProps={{
                  variant: 'body2',
                  color: 'text.secondary',
                }}
              />
            </ListItemButton>
          )}
          
          {servers.length === 0 && (
            <ListItem sx={{ pl: 4 }}>
              <ListItemText 
                primary="No servers available" 
                primaryTypographyProps={{
                  variant: 'body2',
                  color: 'text.secondary',
                  fontStyle: 'italic',
                }}
              />
            </ListItem>
          )}
        </List>
      </Collapse>
      
      <Box sx={{ flexGrow: 1 }} />
      
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <Typography variant="caption" color="text.secondary">
          Model Context Protocol
        </Typography>
        <Typography variant="caption" display="block" color="text.secondary">
          v1.0.0
        </Typography>
      </Box>
    </Drawer>
  );
};

export default Sidebar; 