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
    return {
        "name": getattr(tool, "name", None),
        "description": getattr(tool, "description", None),
        "inputSchema": getattr(tool, "inputSchema", None),
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
    connected_servers = await client.get_connected_servers()
    if not connected_servers:
        # Still allow the prompt to be sent even if no servers are connected
        print("Warning: No servers connected for context")
    
    try:
        # Use the specified server contexts or default to all connected servers
        server_contexts = request.server_contexts if request.server_contexts else connected_servers
        
        # Get tools from connected servers
        tools = []
        for server in server_contexts:
            server_tools = await client.list_tools(server)
            if server_tools:
                tools.extend([tool_to_dict(tool) for tool in server_tools])
        
        # Send prompt to Anthropic API with tools
        result = await anthropic_client.send_prompt(request.prompt, tools)
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to get response from Anthropic API")
            
        # Check if there was an error
        if result.get("error", False):
            error_message = result.get("message", "Unknown error")
            error_details = result.get("details", "")
            print(f"Error details from Anthropic API: {error_details}")
            raise HTTPException(status_code=500, detail=error_message)
        
        # Process the result
        response_content = ""
        tools_used = []
        
        # Extract the content from Claude's response
        if "content" in result:
            for content_item in result["content"]:
                if content_item["type"] == "text":
                    response_content += content_item["text"]
        
        # Add any tool calls that were made
        if "tools" in result and result["tools"]:
            for tool in result["tools"]:
                tools_used.append({
                    "name": tool["name"],
                    "server": tool.get("server", "unknown"),
                    "args": tool.get("arguments", {}),
                    "result": tool.get("output", "")
                })
        
        return {
            "response": response_content,
            "tools": tools_used,
            "id": result.get("id", ""),
            "model": result.get("model", "claude-3-sonnet-20240229")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending prompt: {str(e)}")

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
