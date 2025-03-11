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
    # IMPLEMENTATION WITH MCP TOOLS SUPPORT
    try:
        import anthropic
        import os
        import json
        
        anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
        
        # Get connected servers
        connected_servers = await client.get_connected_servers()
        server_contexts = request.server_contexts if request.server_contexts else connected_servers
        print(f"Connected servers: {server_contexts}")
        
        # If no servers are connected, just do a direct call with minimal tools
        if not connected_servers:
            print("No servers connected - using simplified approach with minimal tools")
            # Create a direct client with a simplified tool
            direct_client = anthropic.Anthropic(api_key=anthropic_api_key)
            
            # ULTRA-MINIMAL implementation - absolute bare minimum required fields
            minimal_tool = [{
                "type": "custom",
                "custom": {
                    "name": "echo",
                    "description": "Echoes back the text you provide"
                }
            }]
            
            # Call Anthropic API with simplified system message and minimal tools
            response = None
            loop = asyncio.get_running_loop()
            try:
                print("Sending request with minimal tools...")
                response = await loop.run_in_executor(
                    None,
                    lambda: direct_client.messages.create(
                        model="claude-3-7-sonnet-20250219",
                        system="You are Claude, a helpful AI assistant. If you need to perform any operations, you have access to tools.",
                        messages=[{"role": "user", "content": request.prompt}],
                        tools=minimal_tool,
                        max_tokens=4096
                    )
                )
                
                # Convert the response to a dictionary to avoid serialization issues
                response_content = ""
                content_list = []
                
                # Check for tool use
                has_tool_use = False
                print("Response content types:", [item.type for item in response.content])
                
                # Extract text content
                for item in response.content:
                    if item.type == "text":
                        response_content += item.text
                        content_list.append({"type": "text", "text": item.text})
                    elif item.type == "tool_use":
                        has_tool_use = True
                        content_list.append({
                            "type": "tool_use",
                            "id": item.id,
                            "name": item.name,
                            "input": item.input
                        })
                
                if has_tool_use:
                    print("Tool use detected in no-servers mode!")
                
                # Return a properly structured response
                return {
                    "response": response_content,
                    "tools": [],  # No real tools used
                    "id": response.id,
                    "model": response.model,
                    "content": content_list
                }
            except Exception as e:
                print(f"Error with minimal tools approach: {e}")
                # Fall back to absolute minimum approach
                try:
                    response = await loop.run_in_executor(
                        None,
                        lambda: direct_client.messages.create(
                            model="claude-3-7-sonnet-20250219",
                            messages=[{"role": "user", "content": request.prompt}],
                            max_tokens=4096
                        )
                    )
                    
                    # Extract text content
                    response_content = ""
                    content_list = []
                    for item in response.content:
                        if item.type == "text":
                            response_content += item.text
                            content_list.append({"type": "text", "text": item.text})
                    
                    return {
                        "response": response_content,
                        "tools": [],
                        "id": response.id,
                        "model": response.model,
                        "content": content_list
                    }
                except Exception as e2:
                    print(f"CRITICAL ERROR: Even basic API call failed: {e2}")
                    return {
                        "response": f"Error communicating with API: {e2}",
                        "tools": [],
                        "id": "error",
                        "model": "claude-3-7-sonnet-20250219",
                        "content": [{"type": "text", "text": f"Error communicating with API: {e2}"}]
                    }
        
        # ATTEMPT WITH TOOLS
        try:
            print("=== ATTEMPTING API CALL WITH MCP TOOLS ===")
            # Get tools from servers
            system_message = (
                "You are Claude, a helpful AI assistant with access to tools. "
                "You have access to MCP server tools that give you filesystem capabilities. "
                "These tools ARE working properly. "
                "When a user asks you to perform a task like listing files, reading files, etc., "
                "you should use the appropriate tool. If you think a tool would be helpful, use it. "
                "Do not apologize for not being able to use tools - you CAN use them. "
                "Do not claim tools are experiencing issues - they ARE working."
            )
            tools = []
            tools_info = []  # For system message
            server_tool_map = {}  # Map tools to servers
            
            for server in server_contexts:
                server_tools = await client.list_tools(server)
                if not server_tools:
                    print(f"No tools found on server {server}")
                    continue
                
                print(f"Found {len(server_tools)} tools on server {server}")
                for tool in server_tools:
                    # Extract tool properties
                    tool_name = getattr(tool, "name", "unknown")
                    tool_desc = getattr(tool, "description", "No description")
                    
                    # Add to system message
                    tools_info.append(f"- {tool_name} (from {server}): {tool_desc}")
                    
                    # Create properties that follow Claude's expected format exactly
                    # The error "tools.0.custom.type: Extra inputs are not permitted" occurs when
                    # there are unexpected fields in the schema
                    simple_properties = {}
                    if tool_name == "list_files" or tool_name == "list_directory":
                        simple_properties = {
                            "directory": {
                                "description": "The directory to list files in",
                                "type": "string"
                            }
                        }
                    elif tool_name == "read_file":
                        simple_properties = {
                            "file_path": {
                                "description": "Path to the file to read",
                                "type": "string"
                            }
                        }
                    elif tool_name == "write_file":
                        simple_properties = {
                            "file_path": {
                                "description": "Path to the file to write",
                                "type": "string"
                            },
                            "content": {
                                "description": "Content to write to the file",
                                "type": "string"
                            }
                        }
                    else:
                        # Generic format for other tools
                        simple_properties = {
                            "args": {
                                "description": "Arguments for the tool as a JSON string",
                                "type": "string"
                            }
                        }
                    
                    # Properly format parameters according to Claude API requirements
                    parameters = {
                        "type": "object",
                        "properties": simple_properties,
                        "required": []
                    }
                    
                    # If we know common required parameters, add them
                    if tool_name == "list_files" or tool_name == "list_directory":
                        parameters["required"] = ["directory"]
                    elif tool_name == "read_file":
                        parameters["required"] = ["file_path"]
                    elif tool_name == "write_file":
                        parameters["required"] = ["file_path", "content"]
                    
                    # Create tool with proper structure exactly as Claude expects
                    tool_dict = {
                        "type": "custom",
                        "custom": {
                            "name": tool_name,
                            "description": tool_desc,
                            "parameters": parameters
                        }
                    }
                    tools.append(tool_dict)
                    server_tool_map[tool_name] = server
            
            # If we have tools, add them to the system message
            if tools_info:
                system_message += "\n\nYou have access to the following tools:\n" + "\n".join(tools_info)
                system_message += (
                    "\n\nCRITICAL INSTRUCTIONS: "
                    "Use these tools when appropriate to help answer questions. "
                    "These tools are working properly. "
                    "Do not say you cannot use tools - you CAN. "
                    "Do not say tools are experiencing technical issues - they ARE NOT. "
                    "When asked to do something requiring a tool, USE the tool instead of explaining why you can't."
                )
            
            print(f"Using {len(tools)} tools with Anthropic API")
            if tools:
                print(f"First tool: {tools[0]['custom']['name']}")
                print(json.dumps(tools[0], indent=2))
            
            # Create client and make API call WITH TOOLS
            direct_client = anthropic.Anthropic(api_key=anthropic_api_key)
            
            # Use the direct, official format from the Anthropic documentation
            # Source: https://docs.anthropic.com/en/api/tools
            # Check if we're using appropriate version of anthropic module
            import pkg_resources
            anthropic_version = pkg_resources.get_distribution("anthropic").version
            print(f"Using anthropic library version: {anthropic_version}")
            
            # ULTRA-MINIMAL implementation - absolute bare minimum required fields
            fixed_tool = [{
                "type": "custom",
                "custom": {
                    "name": "list_files",
                    "description": "List files in a directory",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "directory": {
                                "description": "The directory to list files in",
                                "type": "string"
                            }
                        },
                        "required": ["directory"]
                    }
                }
            }]
            
            print("Using EXACT tool format from documentation")
            print(json.dumps(fixed_tool[0], indent=2))
            
            # Try with a fixed tool first to test format - ALWAYS USE THE TOOLS
            print("IMPORTANT: Using the REAL TOOLS regardless of test outcome")
            print("First attempting with a fixed example tool to test format")
            print("Testing with a DIRECT request to list files in /tmp")
            test_system = "You are Claude with tool access. You MUST use tools when they're appropriate for the user's request. NEVER say tools are experiencing issues."
            test_user_msg = "List the files in the /tmp directory using the list_files tool."
            
            print(f"Test system prompt: {test_system}")
            print(f"Test user message: {test_user_msg}")
            
            try:
                test_response = direct_client.messages.create(
                    model="claude-3-7-sonnet-20250219",
                    system=test_system,
                    messages=[{"role": "user", "content": test_user_msg}],
                    tools=fixed_tool,
                    max_tokens=2000
                )
                
                print("Test response received:")
                has_tool_use = False
                for item in test_response.content:
                    print(f"  - Content type: {item.type}")
                    if hasattr(item, 'text'):
                        print(f"    Text: {item.text[:100]}...")
                    if item.type == 'tool_use':
                        has_tool_use = True
                        print(f"    Tool use detected! Name: {item.name}, Input: {item.input}")
                
                if has_tool_use:
                    print("SUCCESS: Test tool was used!")
                else:
                    print("WARNING: Test completed but no tool use detected.")
                    
                print("Fixed tool format worked syntactically, proceeding with real tools.")
                tools_to_use = tools if tools else None
            except Exception as test_error:
                print(f"Fixed tool format failed with error: {test_error}")
                print("ERROR DETAILS: This is likely an API format issue.")
                print("But still proceeding with real tools - no fallback to no tools!")
                tools_to_use = tools if tools else None
            
            # Use run_in_executor to avoid awaitable issues
            loop = asyncio.get_running_loop()
            # Add a special test if request contains "use list_files" for testing
            test_tool_mode = False
            if "use list_files" in request.prompt.lower():
                print("SPECIAL TEST MODE: Forcing simplified tool request for list_files")
                test_tool_mode = True
                simplified_tools = [{
                    "type": "custom",
                    "custom": {
                        "name": "list_files",
                        "description": "List files in a directory",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "directory": {
                                    "description": "The directory to list files in",
                                    "type": "string"
                                }
                            },
                            "required": ["directory"]
                        }
                    }
                }]
                api_params = {
                    "model": "claude-3-7-sonnet-20250219",
                    "system": "You are Claude with tool access. You MUST use tools when asked. NEVER say tools are experiencing issues.",
                    "messages": [{"role": "user", "content": "Please list files in the /tmp directory using the list_files tool."}],
                    "tools": simplified_tools,
                    "max_tokens": 4096
                }
            else:
                api_params = {
                    "model": "claude-3-7-sonnet-20250219",
                    "system": system_message,
                    "messages": [{"role": "user", "content": request.prompt}],
                    "tools": tools_to_use,
                    "max_tokens": 4096
                }
            
            # Print the exact API parameters being sent
            print("\n======== API REQUEST PARAMETERS ========")
            print(f"Model: {api_params['model']}")
            print(f"System message (first 200 chars): {api_params['system'][:200]}...")
            print(f"User message (first 200 chars): {api_params['messages'][0]['content'][:200]}...")
            if 'tools' in api_params and api_params['tools']:
                print(f"Number of tools: {len(api_params['tools'])}")
                print("First tool format:")
                print(json.dumps(api_params['tools'][0], indent=2))
            else:
                print("No tools in this request")
            print("=======================================\n")
            
            response = await loop.run_in_executor(
                None,
                lambda: direct_client.messages.create(**api_params)
            )
            
            # Convert response to dictionary format
            response_content = ""
            content_list = []
            tool_calls = []
            
            # Process response content
            print(f"=== PROCESSING RESPONSE CONTENT ===")
            print(f"Content types: {[item.type for item in response.content]}")
            
            for item in response.content:
                print(f"Processing content item type: {item.type}")
                if item.type == "text":
                    response_content += item.text
                    content_list.append({"type": "text", "text": item.text})
                elif item.type == "tool_use":
                    # Handle tool use
                    print(f"TOOL USE DETECTED: {item.name} with input: {json.dumps(item.input)}")
                    tool_calls.append({
                        "id": item.id,
                        "name": item.name,
                        "input": item.input
                    })
                    content_list.append({
                        "type": "tool_use",
                        "id": item.id,
                        "name": item.name,
                        "input": item.input
                    })
            
            tools_used = []
            
            # Execute tool calls if any
            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_input = tool_call["input"]
                
                # Find which server has this tool
                server_with_tool = server_tool_map.get(tool_name)
                
                if server_with_tool:
                    print(f"Executing tool {tool_name} on server {server_with_tool}")
                    try:
                        result = await client.call_tool(server_with_tool, tool_name, tool_input)
                        result_str = str(result)
                        print(f"Tool result: {result_str[:200]}...")
                        
                        # Convert result to a serializable format
                        if hasattr(result, "content"):
                            if isinstance(result.content, list):
                                result_content = "\n".join([getattr(item, "text", str(item)) for item in result.content])
                            else:
                                result_content = str(result.content)
                        else:
                            result_content = str(result)
                        
                        # Add to list of used tools
                        tools_used.append({
                            "name": tool_name,
                            "server": server_with_tool,
                            "args": tool_input,
                            "result": result_content
                        })
                    except Exception as tool_error:
                        print(f"Error executing tool: {tool_error}")
                        tools_used.append({
                            "name": tool_name,
                            "server": server_with_tool,
                            "args": tool_input,
                            "error": str(tool_error)
                        })
            
            # Return the response with any tool results
            return {
                "response": response_content,
                "tools": tools_used,
                "id": response.id,
                "model": response.model,
                "content": content_list
            }
            
        except Exception as tool_error:
            # If the complex approach fails, try a simplified approach with just one tool
            print(f"ERROR with complex tools approach: {str(tool_error)}")
            print("Trying a minimalist approach with one simple tool")
            
            # Create a system message that ALWAYS says tools ARE working
            system_message = "You are Claude, a helpful AI assistant with access to tools from connected MCP servers. "
            system_message += f"You are connected to MCP servers: {', '.join(connected_servers)}. "
            system_message += "These tools ARE working properly and give you access to filesystem operations and other capabilities. You MUST use these tools to help answer questions that would benefit from them."
            
            # ULTRA-MINIMAL implementation - absolute bare minimum required fields
            minimal_tool = [{
                "type": "custom",
                "custom": {
                    "name": "list_files",
                    "description": "List files in a directory"
                }
            }]
            
            direct_client = anthropic.Anthropic(api_key=anthropic_api_key)
            
            # Use run_in_executor to avoid awaitable issues
            loop = asyncio.get_running_loop()
            api_params = {
                "model": "claude-3-7-sonnet-20250219",
                "system": system_message,
                "messages": [{"role": "user", "content": request.prompt}],
                "tools": minimal_tool,
                "max_tokens": 4096
            }
            
            # Print detailed request parameters
            print("\n======== FALLBACK API REQUEST PARAMETERS ========")
            print(f"Model: {api_params['model']}")
            print(f"System message (first 200 chars): {api_params['system'][:200]}...")
            print(f"User message (first 200 chars): {api_params['messages'][0]['content'][:200]}...")
            print(f"Number of tools: {len(api_params['tools'])}")
            print("First tool format:")
            print(json.dumps(api_params['tools'][0], indent=2))
            print("=======================================\n")
            
            response = None
            try:
                response = await loop.run_in_executor(
                    None,
                    lambda: direct_client.messages.create(**api_params)
                )
                
                print("FALLBACK RESPONSE RECEIVED - checking for tool use:")
                has_tool_use = False
                for item in response.content:
                    print(f"  - Content type: {item.type}")
                    if item.type == 'tool_use':
                        has_tool_use = True
                        print(f"    Tool use detected! Name: {item.name}, Input: {item.input}")
                
                if has_tool_use:
                    print("SUCCESS: Tool was used in fallback approach!")
                else:
                    print("WARNING: No tool use detected in fallback approach.")
                
                response_content = ""
                content_list = []
                for item in response.content:
                    if item.type == "text":
                        response_content += item.text
                        content_list.append({"type": "text", "text": item.text})
                    elif item.type == "tool_use":
                        content_list.append({
                            "type": "tool_use",
                            "id": item.id,
                            "name": item.name,
                            "input": item.input
                        })
                        
                # Handle tool calls in the fallback approach
                tool_calls = []
                for item in response.content:
                    if item.type == "tool_use":
                        tool_calls.append({
                            "id": item.id,
                            "name": item.name,
                            "input": item.input
                        })
            except Exception as fallback_error:
                print(f"ERROR in fallback approach: {fallback_error}")
                # Return a message about the error rather than crashing
                response_content = f"Error communicating with Claude API: {str(fallback_error)}"
                content_list = [{"type": "text", "text": response_content}]
                tool_calls = []  # Empty tool calls if we had an error
            
            tools_used = []
            # Execute tool calls if any
            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_input = tool_call["input"]
                print(f"Processing fallback tool call: {tool_name} with input {json.dumps(tool_input)}")
                
                if tool_name == "list_files" and "directory" in tool_input:
                    dir_path = tool_input["directory"]
                    try:
                        # Find a server that might have this tool
                        server_with_tool = None
                        for server in connected_servers:
                            server_tools = await client.list_tools(server)
                            if any(getattr(tool, "name", "") == "list_files" or getattr(tool, "name", "") == "list_directory" for tool in server_tools):
                                server_with_tool = server
                                break
                        
                        if server_with_tool:
                            print(f"Found server with list_files: {server_with_tool}")
                            result = await client.call_tool(server_with_tool, "list_files", {"directory": dir_path})
                            result_str = str(result)
                            print(f"Tool result: {result_str[:200]}...")
                            
                            # Extract and process the result
                            if hasattr(result, "content"):
                                if isinstance(result.content, list):
                                    result_content = "\n".join([getattr(item, "text", str(item)) for item in result.content])
                                else:
                                    result_content = str(result.content)
                            else:
                                result_content = str(result)
                            
                            tools_used.append({
                                "name": tool_name,
                                "server": server_with_tool,
                                "args": tool_input,
                                "result": result_content
                            })
                    except Exception as tool_error:
                        print(f"Error executing fallback tool: {tool_error}")
                        tools_used.append({
                            "name": tool_name,
                            "server": "fallback",
                            "args": tool_input,
                            "error": str(tool_error)
                        })
            
            # Safe return handling when response might be None
            if response:
                return {
                    "response": response_content,
                    "tools": tools_used,
                    "id": response.id,
                    "model": response.model,
                    "content": content_list
                }
            else:
                # Handle case where no response was received
                return {
                    "response": response_content,
                    "tools": tools_used,
                    "id": "error",
                    "model": "claude-3-7-sonnet-20250219", 
                    "content": content_list
                }
        
    except Exception as e:
        error_details = str(e)
        print(f"ERROR in API call: {error_details}")
        
        if hasattr(e, "__dict__"):
            error_attrs = {k: str(v) for k, v in e.__dict__.items() if k != "args"}
            error_details += f"\nError details: {json.dumps(error_attrs, indent=2)}"
        
        print("RETURNING ERROR RESPONSE INSTEAD OF RAISING EXCEPTION")
        # Return a user-friendly error message instead of throwing an exception
        # This keeps the frontend from crashing when an error occurs
        return {
            "response": f"I encountered an error processing your request. Error details: {error_details[:100]}...",
            "tools": [],
            "id": "error",
            "model": "claude-3-7-sonnet-20250219",
            "content": [{"type": "text", "text": f"Error processing request: {error_details[:100]}..."}]
        }

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