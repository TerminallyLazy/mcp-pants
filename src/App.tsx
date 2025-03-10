import React, { useState, useEffect } from 'react';
import { Box, CssBaseline, ThemeProvider } from '@mui/material';
import { styled } from '@mui/material/styles';
import darkTheme from './theme';

// Import custom components
import Sidebar from './components/Sidebar';
import ServerManagement from './components/ServerManagement';
import ChatInterface from './components/ChatInterface';
import ToolsPanel from './components/ToolsPanel';

// Define interfaces for the entities
interface Tool {
  name: string;
  description?: string;
  inputSchema?: any;
}

interface Prompt {
  name: string;
  description?: string;
}

interface Resource {
  uri: string;
}

const MainContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  minHeight: '100vh',
  background: theme.palette.background.default,
}));

const ContentContainer = styled(Box)(({ theme }) => ({
  flexGrow: 1,
  padding: theme.spacing(3),
  marginLeft: 280, // Sidebar width
  overflowX: 'hidden',
}));

const App: React.FC = () => {
  // State variables
  const [activeView, setActiveView] = useState<string>('home');
  const [servers, setServers] = useState<string[]>([]);
  const [connectedServers, setConnectedServers] = useState<string[]>([]);
  const [connectStatus, setConnectStatus] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [tools, setTools] = useState<Tool[]>([]);
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [resources, setResources] = useState<Resource[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  const backendUrl = 'http://localhost:8000'; // FastAPI backend

  // Fetch servers when the component mounts
  useEffect(() => {
    console.log("App component mounted - fetching servers...");
    fetchServers();
    
    // Set up a refresh interval (optional - every 30 seconds)
    const intervalId = setInterval(() => {
      console.log("Auto-refreshing servers list");
      fetchServers();
    }, 30000);
    
    // Clean up the interval on component unmount
    return () => clearInterval(intervalId);
  }, []);

  // Also fetch connected servers when component mounts
  useEffect(() => {
    // Initially fetch connected servers
    fetchConnectedServers();
    
    // Set up interval to refresh connected servers list
    const intervalId = setInterval(() => {
      fetchConnectedServers();
    }, 10000);
    
    return () => clearInterval(intervalId);
  }, []);

  // Fetch servers list
  const fetchServers = async () => {
    console.log("Fetching servers from backend...");
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${backendUrl}/servers`);
      console.log("Server response status:", res.status);
      
      if (!res.ok) throw new Error(`Failed to fetch servers: ${res.status} ${res.statusText}`);
      
      const data = await res.json();
      console.log("Received servers data:", data);
      
      setServers(data.servers || []);
      console.log("Servers state updated:", data.servers || []);
    } catch (error) {
      console.error("Error fetching servers", error);
      setError("Failed to fetch servers. Make sure the backend server is running.");
    } finally {
      setLoading(false);
    }
  };

  // Fetch connected servers
  const fetchConnectedServers = async () => {
    try {
      const res = await fetch(`${backendUrl}/connected_servers`);
      if (!res.ok) return;
      
      const data = await res.json();
      setConnectedServers(data.servers || []);
    } catch (error) {
      console.error("Error fetching connected servers", error);
    }
  };

  // Fetch tools from a specific server
  const fetchTools = async (serverName?: string) => {
    setLoading(true);
    setError(null);
    try {
      const url = serverName 
        ? `${backendUrl}/tools?server_name=${serverName}` 
        : `${backendUrl}/tools`;
        
      const res = await fetch(url);
      if (!res.ok) throw new Error('Failed to fetch tools');
      
      const data = await res.json();
      setTools(data.tools || []);
    } catch (error) {
      console.error("Error fetching tools", error);
      setError("Failed to fetch tools. Make sure you're connected to a server.");
    } finally {
      setLoading(false);
    }
  };

  // Fetch prompts from a specific server
  const fetchPrompts = async (serverName?: string) => {
    setLoading(true);
    setError(null);
    try {
      const url = serverName 
        ? `${backendUrl}/prompts?server_name=${serverName}` 
        : `${backendUrl}/prompts`;
        
      const res = await fetch(url);
      if (!res.ok) throw new Error('Failed to fetch prompts');
      
      const data = await res.json();
      setPrompts(data.prompts || []);
    } catch (error) {
      console.error("Error fetching prompts", error);
      setError("Failed to fetch prompts. Make sure you're connected to a server.");
    } finally {
      setLoading(false);
    }
  };

  // Fetch resources from a specific server
  const fetchResources = async (serverName?: string) => {
    setLoading(true);
    setError(null);
    try {
      const url = serverName 
        ? `${backendUrl}/resources?server_name=${serverName}` 
        : `${backendUrl}/resources`;
        
      const res = await fetch(url);
      if (!res.ok) throw new Error('Failed to fetch resources');
      
      const data = await res.json();
      setResources(data.resources || []);
    } catch (error) {
      console.error("Error fetching resources", error);
      setError("Failed to fetch resources. Make sure you're connected to a server.");
    } finally {
      setLoading(false);
    }
  };

  // Connect to a server
  const handleConnect = async (serverName: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${backendUrl}/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ server_name: serverName })
      });
      
      if (!res.ok) throw new Error('Failed to connect to server');
      
      const data = await res.json();
      setConnectStatus(`Connected to ${data.server}`);
      
      // Update connected servers list
      await fetchConnectedServers();
      
      // Fetch tools after connecting
      await fetchTools(serverName);
    } catch (error) {
      console.error("Error connecting to server", error);
      setError(`Failed to connect to "${serverName}". The server might be unavailable.`);
    } finally {
      setLoading(false);
    }
  };

  // Disconnect from a specific server
  const handleDisconnect = async (serverName?: string) => {
    setLoading(true);
    setError(null);
    try {
      const body = serverName ? JSON.stringify({ server_name: serverName }) : null;
      const res = await fetch(`${backendUrl}/disconnect`, {
        method: 'POST',
        headers: body ? { 'Content-Type': 'application/json' } : undefined,
        body
      });
      
      if (!res.ok) throw new Error('Failed to disconnect from server');
      
      setConnectStatus('');
      
      // Update connected servers list
      await fetchConnectedServers();
      
      // Clear tools if no servers connected or fetch from remaining server
      if (connectedServers.length <= 1) {
        setTools([]);
      } else {
        await fetchTools();
      }
    } catch (error) {
      console.error("Error disconnecting from server", error);
      setError("Failed to disconnect. Try again later.");
    } finally {
      setLoading(false);
    }
  };

  // Call a tool on a specific server
  const handleCallTool = async (serverName: string, toolName: string, args: any) => {
    setError(null);
    try {
      const res = await fetch(`${backendUrl}/tools/${serverName}/${toolName}/call`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool_name: toolName, arguments: args })
      });
      
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Failed to call tool');
      }
      
      const data = await res.json();
      return data;
    } catch (error) {
      console.error(`Error calling tool "${toolName}"`, error);
      throw error;
    }
  };

  // Send a message to the LLM
  const handleSendMessage = async (message: string) => {
    setError(null);
    try {
      const res = await fetch(`${backendUrl}/prompt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          prompt: message,
          server_contexts: connectedServers  // Pass all connected servers for context
        })
      });
      
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Failed to send message');
      }
      
      const data = await res.json();
      return data;
    } catch (error) {
      console.error("Error sending message", error);
      throw error;
    }
  };

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <MainContainer>
        <Sidebar
          servers={servers}
          connectedServers={connectedServers}
          onConnect={handleConnect}
          activeView={activeView}
          onViewChange={setActiveView}
        />
        
        <ContentContainer>
          {activeView === 'home' && (
            <ServerManagement
              servers={servers}
              connectedServers={connectedServers}
              onConnect={handleConnect}
              onDisconnect={handleDisconnect}
              onRefresh={fetchServers}
              loading={loading}
              error={error}
            />
          )}
          
          {activeView === 'chat' && (
            <ChatInterface 
              onSendMessage={handleSendMessage} 
              connectedServers={connectedServers}
            />
          )}
          
          {activeView === 'tools' && (
            <ToolsPanel
              tools={tools}
              servers={connectedServers}
              onCallTool={handleCallTool}
              onRefresh={fetchTools}
              loading={loading}
            />
          )}
          
          {activeView === 'resources' && (
            <Box>
              {/* Resources Panel Component would go here */}
            </Box>
          )}
        </ContentContainer>
      </MainContainer>
    </ThemeProvider>
  );
};

export default App;
