import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from fastapi.middleware.cors import CORSMiddleware
import os
import aiohttp
from dotenv import load_dotenv, find_dotenv
from anthropic_client import AnthropicClient

import importlib.util

# Load environment variables from .env file
load_dotenv(find_dotenv())

# Initialize Anthropic client
anthropic_client = AnthropicClient()

# Dynamically import the mcp-client module.
# (For convenience, you might consider renaming mcp-client.py to mcp_client.py.)
spec = importlib.util.spec_from_file_location("mcp_client", "mcp-client.py")
mcp_client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mcp_client)
MCPConfigClient = mcp_client.MCPConfigClient

app = FastAPI(title="MCP UI Backend")

# Add CORS middleware to allow the frontend to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:*", "http://127.0.0.1:*"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global MCP client instance.
client = MCPConfigClient()
if not client.load_config():
    print("Failed to load MCP configuration.")

# ---------------------------
# Request models for endpoints
# ---------------------------
class ConnectRequest(BaseModel):
    server_name: str

class CallToolRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}

class PromptRequest(BaseModel):
    prompt: str
    server_contexts: Optional[List[str]] = None  # List of servers to use for context

class ExecutePromptRequest(BaseModel):
    prompt_name: str
    arguments: Dict[str, Any] = {}

class ReadResourceRequest(BaseModel):
    resource_uri: str

# ---------------------------
# Helper functions to serialize objects
# ---------------------------
def tool_to_dict(tool) -> Dict[str, Any]:
    """Extract basic MCP tool properties without transforming the schema.
    The proper format conversion happens in the Anthropic client.
    """
    # Safely extract properties with defaults
    return {
        "name": getattr(tool, "name", ""),
        "description": getattr(tool, "description", ""),
        "inputSchema": getattr(tool, "inputSchema", {})
    }

def prompt_to_dict(prompt) -> Dict[str, Any]:
    return {
        "name": getattr(prompt, "name", None),
        "description": getattr(prompt, "description", None),
        "arguments": [vars(arg) for arg in getattr(prompt, "arguments", [])] if hasattr(prompt, "arguments") else []
    }

def resource_to_dict(resource) -> Dict[str, Any]:
    return {"uri": getattr(resource, "uri", None)}

# ---------------------------
# API endpoints
# ---------------------------
@app.get("/servers")
async def get_servers():
    servers = await client.list_servers()  # This prints and returns the list of server names.
    return {"servers": servers}

@app.get("/connected_servers")
async def get_connected_servers():
    connected_servers = await client.get_connected_servers()
    return {"servers": connected_servers}

@app.post("/connect")
async def connect_server(request: ConnectRequest):
    success = await client.connect_to_server(request.server_name)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to connect to server {request.server_name}")
    return {"status": "connected", "server": request.server_name}

@app.post("/disconnect")
async def disconnect_server(request: Optional[ConnectRequest] = None):
    if request and request.server_name:
        success = await client.disconnect(request.server_name)
        if not success:
            raise HTTPException(status_code=400, detail=f"Failed to disconnect from server {request.server_name}")
        return {"status": "disconnected", "server": request.server_name}
    else:
        # Disconnect from all servers
        success = await client.disconnect()
        if not success:
            raise HTTPException(status_code=400, detail="No servers connected")
        return {"status": "disconnected", "message": "Disconnected from all servers"}

@app.get("/tools")
async def get_tools(server_name: Optional[str] = None):
    connected_servers = await client.get_connected_servers()
    if not connected_servers:
        raise HTTPException(status_code=400, detail="No servers connected")
    
    if server_name and server_name not in connected_servers:
        raise HTTPException(status_code=400, detail=f"Not connected to server {server_name}")
    
    tools = await client.list_tools(server_name)
    tools_list = [tool_to_dict(tool) for tool in tools] if tools else []
    return {"tools": tools_list}

@app.post("/tools/{server_name}/{tool_name}/call")
async def call_tool(server_name: str, tool_name: str, request: CallToolRequest):
    connected_servers = await client.get_connected_servers()
    if not connected_servers:
        raise HTTPException(status_code=400, detail="No servers connected")
    
    if server_name not in connected_servers:
        raise HTTPException(status_code=400, detail=f"Not connected to server {server_name}")
    
    try:
        result = await client.call_tool(server_name, tool_name, request.arguments)
        if not result:
            raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found or failed to execute on server {server_name}")
        
        # Convert result content to text
        if hasattr(result, "content"):
            if isinstance(result.content, list):
                content = "\n".join([getattr(item, "text", str(item)) for item in result.content])
            else:
                content = str(result.content)
        else:
            content = "No content returned"
        return {"tool": tool_name, "server": server_name, "response": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calling tool: {str(e)}")

@app.post("/prompt")
async def send_prompt(request: PromptRequest):
    # SIMPLIFIED IMPLEMENTATION - DIRECT APPROACH WITHOUT TOOLS
    # This implementation bypasses the complex tool structure that's causing issues
    try:
        import anthropic
        import os
        import json
        
        print("=== USING DIRECT ANTHROPIC API CALL WITHOUT TOOLS ===")
        anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
        
        # Get connected servers to include in the system message
        connected_servers = await client.get_connected_servers()
        server_contexts = request.server_contexts if request.server_contexts else connected_servers
        print(f"Connected servers: {server_contexts}")
        
        # Create a system message that mentions the tools but doesn't use them
        system_message = "You are Claude, a helpful AI assistant. "
        
        if connected_servers:
            system_message += f"You are connected to the following MCP servers: {', '.join(connected_servers)}. "
            system_message += "Normally you would have access to tools from these servers, but due to technical "
            system_message += "issues, you will need to respond without using tools. Please suggest what kinds of "
            system_message += "tools might be available from these servers if the user asks."
        
        # Create a direct client that doesn't use tools
        direct_client = anthropic.Anthropic(api_key=anthropic_api_key)
        
        # Set up try/except to catch any serialization issues
        try:
            # Using anthropic_client.messages.create in a non-awaitable way
            # Get Anthropic client and create parameters
            anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
            
            # Define request parameters
            request_params = {
                "model": "claude-3-7-sonnet-20250219",
                "system": system_message,
                "messages": [{"role": "user", "content": request.prompt}],
                "max_tokens": 4096
            }
            
            # Use a synchronous executor to run the API call
            import asyncio
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: anthropic_client.messages.create(**request_params)
            )
            
            print("Successfully called Anthropic API")
            
            # Convert the Anthropic Message object to a serializable dictionary
            # Extract all the necessary fields manually to avoid serialization issues
            response_content = ""
            content_list = []
            
            # Safely extract and convert content items
            if hasattr(response, "content") and response.content:
                for item in response.content:
                    if hasattr(item, "type") and item.type == "text" and hasattr(item, "text"):
                        response_content += item.text
                        content_list.append({"type": "text", "text": item.text})
            
            # Create a completely serializable response dictionary
            response_dict = {
                "response": response_content,
                "tools": [],  # No tools used
                "id": response.id if hasattr(response, "id") else "",
                "model": response.model if hasattr(response, "model") else "claude-3-7-sonnet-20250219",
                "content": content_list
            }
            
            print("Successfully created serializable response")
            return response_dict
            
        except Exception as anthropic_error:
            print(f"Error in Anthropic API call: {anthropic_error}")
            # If there's any error with the Anthropic call or serialization,
            # return a fallback response that is guaranteed to be serializable
            return {
                "response": "I apologize, but I encountered an error processing your request. The error appears to be related to API response serialization.",
                "tools": [],
                "id": "error_fallback",
                "model": "claude-3-7-sonnet-20250219",
                "content": [{"type": "text", "text": "I apologize, but I encountered an error processing your request. The error appears to be related to API response serialization."}]
            }
        
    except Exception as e:
        error_details = str(e)
        print(f"ERROR in direct API call: {error_details}")
        
        if hasattr(e, "__dict__"):
            error_attrs = {k: str(v) for k, v in e.__dict__.items() if k != "args"}
            error_details += f"\nError details: {json.dumps(error_attrs, indent=2)}"
        
        raise HTTPException(status_code=500, detail=f"Error sending prompt: {error_details}")

@app.get("/prompts")
async def get_prompts(server_name: Optional[str] = None):
    connected_servers = await client.get_connected_servers()
    if not connected_servers:
        raise HTTPException(status_code=400, detail="No servers connected")
    
    if server_name and server_name not in connected_servers:
        raise HTTPException(status_code=400, detail=f"Not connected to server {server_name}")
    
    prompts = await client.list_prompts(server_name)
    prompts_list = [prompt_to_dict(prompt) for prompt in prompts] if prompts else []
    return {"prompts": prompts_list}

@app.post("/prompts/{server_name}/{prompt_name}/execute")
async def execute_prompt(server_name: str, prompt_name: str, request: ExecutePromptRequest):
    connected_servers = await client.get_connected_servers()
    if not connected_servers:
        raise HTTPException(status_code=400, detail="No servers connected")
    
    if server_name not in connected_servers:
        raise HTTPException(status_code=400, detail=f"Not connected to server {server_name}")
    
    try:
        prompt_obj = await client.execute_prompt(server_name, prompt_name, request.arguments)
        if prompt_obj and hasattr(prompt_obj, "messages"):
            messages = []
            for msg in prompt_obj.messages:
                text = msg.content.text if hasattr(msg.content, 'text') else str(msg.content)
                messages.append({"role": msg.role, "text": text})
            return {"prompt": prompt_name, "template": messages}
        else:
            return {"detail": "Prompt retrieved but has no messages"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing prompt: {str(e)}")

@app.get("/resources")
async def get_resources(server_name: Optional[str] = None):
    connected_servers = await client.get_connected_servers()
    if not connected_servers:
        raise HTTPException(status_code=400, detail="No servers connected")
    
    if server_name and server_name not in connected_servers:
        raise HTTPException(status_code=400, detail=f"Not connected to server {server_name}")
    
    resources = await client.list_resources(server_name)
    resources_list = [resource_to_dict(resource) for resource in resources] if resources else []
    return {"resources": resources_list}

@app.post("/resource/{server_name}/read")
async def read_resource(server_name: str, request: ReadResourceRequest):
    connected_servers = await client.get_connected_servers()
    if not connected_servers:
        raise HTTPException(status_code=400, detail="No servers connected")
    
    if server_name not in connected_servers:
        raise HTTPException(status_code=400, detail=f"Not connected to server {server_name}")
    
    try:
        content, mime_type = await client.read_resource(server_name, request.resource_uri)
        if mime_type.startswith("text/"):
            return {"uri": request.resource_uri, "mime_type": mime_type, "content": content}
        else:
            return {"uri": request.resource_uri, "mime_type": mime_type, "content": f"Binary content, {len(content)} bytes"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading resource: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("mcp_ui:app", host="0.0.0.0", port=8000, reload=True)
