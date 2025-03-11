import argparse
import asyncio
import json
import logging
import os
import pathlib
import re
import sys
import time
import aiohttp
import importlib.util
from typing import Optional, Dict, List, Any, Callable, Awaitable
from contextlib import AsyncExitStack
from dotenv import load_dotenv, find_dotenv
from datetime import datetime
import anthropic
from anthropic_client import AnthropicClient

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

# Load environment variables from .env file
load_dotenv(find_dotenv(), override=True)  # Add override=True to make sure .env takes precedence

# Get Anthropic API key from .env file
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if ANTHROPIC_API_KEY:
    print(f"Loaded API key from .env: {ANTHROPIC_API_KEY[:10]}...")
else:
    print("Warning: No ANTHROPIC_API_KEY found in .env file")

async def handle_sampling_message(message: types.CreateMessageRequestParams) -> types.CreateMessageResult:
    """Handle a message for sampling purposes (LLM sampling/calling).
    
    This follows the MCP SDK pattern for sampling callbacks.
    """
    
    # Get Anthropic API key from environment variables
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        return types.CreateMessageResult(
            id="",
            createdAt="",
            assistantId="",
            threadId="",
            messageId="",
            status="completed",
            content=types.MessageContent(
                type="text",
                text="Error: ANTHROPIC_API_KEY environment variable not set.",
            ),
            model="claude-3-7-sonnet-20250219",
            stopReason="error",
        )

    # Extract user message text from the incoming message.
    # This callback expects that the message has a 'content.text' field.
    if hasattr(message, "content") and hasattr(message.content, "text"):
        user_message = message.content.text
    elif hasattr(message, "text"):
        user_message = message.text
    else:
        user_message = str(message)
    
    try:
        # This is using the blocking anthropic client inside an executor
        def call_anthropic():
            # Initialize the Anthropic client
            client = anthropic.Anthropic(api_key=anthropic_api_key)
            
            # Create messages as shown in the example
            response = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": user_message}
                ],
            )
            return response
        
        # Run the blocking API call in a thread pool
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, call_anthropic)
        
        print(f"Received response from Anthropic API: {str(response)[:200]}...")
        
        # Extract the response text from the assistant's message
        if not response.content:
            raise Exception("No content in response from Anthropic API")
        
        assistant_message = response.content[0].text if response.content and response.content[0].type == "text" else ""
        
        # Return results in the format expected by MCP SDK
        return types.CreateMessageResult(
            id=response.id,
            createdAt=datetime.now().isoformat(),
            assistantId="anthropic",
            threadId="sample_thread_id",
            messageId=response.id,
            status="completed",
            content=types.MessageContent(
                type="text",
                text=assistant_message,
            ),
            model=response.model,
            stopReason="end_turn",
        )
    except Exception as e:
        error_message = f"Error using Anthropic API: {str(e)}"
        print(error_message)
        return types.CreateMessageResult(
            id="",
            createdAt="",
            assistantId="",
            threadId="",
            messageId="",
            status="completed",
            content=types.MessageContent(
                type="text",
                text=error_message,
            ),
            model="claude-3-7-sonnet-20250219",
            stopReason="error",
        )

class MCPConfigClient:
    def __init__(self, config_file="mcp_config.json"):
        self.config_file = config_file
        self.server_params = {}
        self.sessions = {}  # Change single session to a dictionary of sessions
        self.exit_stack = AsyncExitStack()
        self.stdio_transports = {}  # Store transports for each server
        self.active_servers = set()  # Track active servers

        # Save config file path in user's home directory for caching
        self.config_cache_file = os.path.expanduser("~/.mcp_client_config")
        self.save_config_path(config_file)

    def save_config_path(self, config_path):
        """Save the config file path in a cache file."""
        try:
            with open(self.config_cache_file, 'w') as f:
                f.write(config_path)
            return True
        except Exception as e:
            print(f"Warning: Could not save config path: {e}")
            return False

    def get_saved_config_path(self):
        """Get the previously saved config file path."""
        try:
            if os.path.exists(self.config_cache_file):
                with open(self.config_cache_file, 'r') as f:
                    return f.read().strip()
        except Exception:
            pass
        return "mcp_config.json"

    def load_config(self):
        """Load MCP server configurations from the provided JSON file."""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)

            for server_name, server_config in config.get("mcpServers", {}).items():
                if server_config.get("enabled", True):
                    env_dict = server_config.get("env")
                    self.server_params[server_name] = StdioServerParameters(
                        command=server_config["command"],
                        args=server_config["args"],
                        env=env_dict
                    )

            print(f"Loaded {len(self.server_params)} MCP servers from config")
            return True
        except Exception as e:
            print(f"Error loading MCP config: {e}")
            return False

    async def connect_to_server(self, server_name):
        """Connect to a specific MCP server.
        
        Args:
            server_name: Name of the server to connect to
            
        Returns:
            bool: True if the connection was successful, False otherwise
        """
        if server_name not in self.server_params:
            print(f"Unknown server: {server_name}")
            return False

        # If already connected, just return success
        if server_name in self.sessions:
            print(f"Already connected to {server_name}")
            return True

        try:
            print(f"Connecting to MCP server: {server_name}")
            server_params = self.server_params[server_name]
            
            # Create stdio transport using MCP SDK
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            self.stdio_transports[server_name] = stdio_transport
            stdio, write = stdio_transport

            # Create a client session with the sampling callback
            print(f"Establishing MCP client session for {server_name}")
            session = await self.exit_stack.enter_async_context(
                ClientSession(stdio, write, sampling_callback=handle_sampling_message)
            )
            
            # Initialize the connection
            print(f"Initializing connection to {server_name}")
            initialization_result = await session.initialize()
            
            # Store the session
            self.sessions[server_name] = session
            self.active_servers.add(server_name)
            
            # Print server capabilities from initialization result
            if hasattr(initialization_result, "capabilities"):
                capabilities = initialization_result.capabilities
                print(f"Server capabilities: {capabilities}")
            
            # List tools if supported
            try:
                response = await session.list_tools()
                if hasattr(response, "tools"):
                    tools = response.tools
                    tool_names = [getattr(tool, "name", "unknown") for tool in tools]
                    print(f"\nConnected to {server_name} with {len(tool_names)} tools: {', '.join(tool_names)}")
                else:
                    print(f"Connected to {server_name} but it returned an empty tools list")
            except Exception as e:
                print(f"Note: Server {server_name} doesn't support tools API or returned an error: {e}")
                print(f"Connected to {server_name} but couldn't list tools")
            
            return True
        except Exception as e:
            print(f"Error connecting to server {server_name}: {e}")
            # Add detailed error info
            if hasattr(e, "__dict__"):
                error_details = {k: str(v) for k, v in e.__dict__.items() if k != "args"}
                print(f"Error details: {error_details}")
            return False

    async def disconnect(self, server_name=None):
        """Disconnect from a specific server or all servers if none specified."""
        if server_name is None:
            # Disconnect from all servers
            servers_to_disconnect = list(self.sessions.keys())
            for server in servers_to_disconnect:
                await self.disconnect(server)
            return True

        if server_name not in self.sessions:
            print(f"No connection to {server_name}")
            return False

        try:
            # Clean up will be handled by the exit stack when it's closed
            del self.sessions[server_name]
            del self.stdio_transports[server_name]
            self.active_servers.remove(server_name)
            print(f"Disconnected from '{server_name}' server")
            return True
        except Exception as e:
            print(f"Error disconnecting from server: {e}")
            return False

    async def list_servers(self):
        """List all available MCP servers."""
        servers = list(self.server_params.keys())
        print("Available MCP servers:")
        for i, server in enumerate(servers, 1):
            status = "connected" if server in self.sessions else "disconnected"
            print(f"{i}. {server} ({status})")
        return servers

    async def get_connected_servers(self):
        """Return a list of currently connected servers."""
        return list(self.active_servers)

    async def list_tools(self, server_name=None):
        """List all available tools for the specified server or across all connected servers."""
        if not self.sessions:
            print("No servers connected")
            return []

        all_tools = []
        
        if server_name:
            # Get tools for specific server
            if server_name not in self.sessions:
                print(f"Not connected to {server_name}")
                return []
                
            try:
                response = await self.sessions[server_name].list_tools()
                tools = response.tools if hasattr(response, "tools") else []
                print(f"Available tools on '{server_name}':")
                for i, tool in enumerate(tools, 1):
                    print(f"{i}. {tool.name}: {tool.description}")
                    input_schema = getattr(tool, "inputSchema", None)
                    if input_schema:
                        print("   Input schema:")
                        for prop_name, prop in input_schema.get("properties", {}).items():
                            required = "Required" if prop_name in input_schema.get("required", []) else "Optional"
                            print(f"    - {prop_name} ({required}): {prop.get('description', '')}")
                all_tools.extend(tools)
            except Exception as e:
                print(f"Error listing tools for {server_name}: {e}")
        else:
            # Get tools from all connected servers
            for srv_name in self.sessions:
                try:
                    response = await self.sessions[srv_name].list_tools()
                    tools = response.tools if hasattr(response, "tools") else []
                    print(f"Available tools on '{srv_name}':")
                    for i, tool in enumerate(tools, 1):
                        print(f"{i}. {tool.name}: {tool.description}")
                        input_schema = getattr(tool, "inputSchema", None)
                        if input_schema:
                            print("   Input schema:")
                            for prop_name, prop in input_schema.get("properties", {}).items():
                                required = "Required" if prop_name in input_schema.get("required", []) else "Optional"
                                print(f"    - {prop_name} ({required}): {prop.get('description', '')}")
                    all_tools.extend(tools)
                except Exception as e:
                    print(f"Error listing tools for {srv_name}: {e}")

        return all_tools

    async def call_tool(self, server_name, tool_name, arguments=None):
        """Call a tool on a specific server with optional arguments.
        
        Args:
            server_name: The name of the server to call the tool on
            tool_name: The name of the tool to call
            arguments: Optional arguments to pass to the tool
            
        Returns:
            The result of the tool call, or None if an error occurred
        """
        if not self.sessions:
            print("No servers connected")
            return None

        if server_name not in self.sessions:
            print(f"Not connected to server: {server_name}")
            return None

        # Normalize arguments to a dictionary if None
        if arguments is None:
            arguments = {}
            
        print(f"Calling tool '{tool_name}' on server '{server_name}' with arguments: {json.dumps(arguments, indent=2)[:200]}...")

        try:
            # Use the MCP SDK to list tools and find the one we need
            response = await self.sessions[server_name].list_tools()
            tools = response.tools if hasattr(response, "tools") else []
            
            # Case-insensitive search for the tool
            tool_name_lower = tool_name.lower()
            selected_tool = next(
                (tool for tool in tools if getattr(tool, "name", "").lower() == tool_name_lower), 
                None
            )

            if not selected_tool:
                available_tools = [getattr(tool, "name", "") for tool in tools]
                print(f"Tool '{tool_name}' not found on server '{server_name}'")
                print(f"Available tools: {available_tools}")
                return None

            # Validate arguments against the tool's input schema if possible
            input_schema = getattr(selected_tool, "inputSchema", None)
            if input_schema and "required" in input_schema:
                missing_args = [arg for arg in input_schema["required"] if arg not in arguments]
                if missing_args:
                    print(f"Missing required arguments for tool '{tool_name}': {missing_args}")
                    return None
                    
            # Call the tool using the MCP SDK
            print(f"Executing tool '{selected_tool.name}' on server '{server_name}'...")
            start_time = time.time()
            result = await self.sessions[server_name].call_tool(selected_tool.name, arguments=arguments)
            elapsed_time = time.time() - start_time
            
            print(f"Tool execution completed in {elapsed_time:.2f} seconds")
            return result
        except Exception as e:
            print(f"Error calling tool: {e}")
            # Include more detailed error information if available
            if hasattr(e, "__dict__"):
                error_details = {k: str(v) for k, v in e.__dict__.items() if k != "args"}
                print(f"Error details: {error_details}")
            return None

    async def send_prompt(self, message, server_contexts=None):
        """Send a prompt to the Claude API with contexts from MCP servers."""
        if not ANTHROPIC_API_KEY:
            print("Error: ANTHROPIC_API_KEY not found in .env file")
            return None
        
        # Debug information - print first few chars of API key
        masked_key = ANTHROPIC_API_KEY[:5] + "..." + ANTHROPIC_API_KEY[-4:]
        print(f"Using Anthropic API key: {masked_key}")

        # If server_contexts is None, use all connected servers
        if server_contexts is None and self.sessions:
            server_contexts = list(self.sessions.keys())
        elif not server_contexts:
            server_contexts = []

        # Collect tools from specified servers using the MCP SDK
        available_tools = []
        server_tool_map = {}  # Map to track which tool belongs to which server
        
        print(f"Collecting tools from servers: {server_contexts}")
        
        for server_name in server_contexts:
            if server_name in self.sessions:
                try:
                    # This uses the MCP SDK to list tools from the server
                    response = await self.sessions[server_name].list_tools()
                    tools = response.tools if hasattr(response, "tools") else []
                    print(f"Found {len(tools)} tools on server '{server_name}'")
                    
                    for tool in tools:
                        # Get tool attributes using SDK patterns
                        tool_name = getattr(tool, 'name', '')
                        tool_description = getattr(tool, 'description', '')
                        parameters = getattr(tool, 'inputSchema', {})
                        
                        # Format parameters according to Anthropic's API requirements
                        schema_params = {}
                        
                        if 'properties' in parameters:
                            schema_params['properties'] = parameters.get('properties', {})
                            
                        if 'required' in parameters:
                            schema_params['required'] = parameters['required']
                            
                        # Always add type:object to the schema
                        schema_params['type'] = 'object'
                        
                        # Simplify properties based on tool name - REMOVING ALL TYPE FIELDS
                        # Error: "tools.0.custom.type: Extra inputs are not permitted"
                        simple_properties = {}
                        if tool_name.lower() == "list_files" or tool_name.lower() == "list_directory":
                            simple_properties = {
                                "directory": {
                                    "description": "The directory to list files in"
                                }
                            }
                        elif tool_name.lower() == "read_file":
                            simple_properties = {
                                "file_path": {
                                    "description": "Path to the file to read"
                                }
                            }
                        elif tool_name.lower() == "write_file":
                            simple_properties = {
                                "file_path": {
                                    "description": "Path to the file to write"
                                },
                                "content": {
                                    "description": "Content to write to the file"
                                }
                            }
                        else:
                            # Generic format for other tools
                            simple_properties = {
                                "args": {
                                    "description": "Arguments for the tool as a JSON string"
                                }
                            }
                        
                        # ULTRA-MINIMAL implementation - absolute bare minimum required fields
                        tool_dict = {
                            "type": "custom",
                            "custom": {
                                "name": tool_name,
                                "description": tool_description
                            }
                        }
                        
                        print(f"Created custom-based tool for {tool_name} (using 'custom' type as required by API)")
                        
                        available_tools.append(tool_dict)
                        server_tool_map[tool_name] = server_name
                        print(f"Added tool: {tool_name} from server: {server_name}")
                except Exception as e:
                    print(f"Error getting tools from {server_name}: {e}")

        # Build system prompt with tool information
        system_prompt = "You are Claude, a helpful AI assistant with access to tools from connected MCP servers."
        
        if available_tools:
            system_prompt += "\n\nYou have access to the following tools from MCP servers:"
            for i, tool in enumerate(available_tools, 1):
                tool_name = tool['custom']['name']  # Updated to use custom format
                tool_desc = tool['custom']['description']  # Updated to use custom format
                server = server_tool_map.get(tool_name, "unknown")
                system_prompt += f"\n{i}. {tool_name} (from {server}): {tool_desc}"
        
        try:
            # Use the Anthropic Python library's best practices
            def call_anthropic():
                try:
                    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                    
                    # Prepare the request parameters
                    kwargs = {
                        "model": "claude-3-7-sonnet-20250219",
                        "max_tokens": 4000,
                        "system": system_prompt,
                        "messages": [
                            {"role": "user", "content": message}
                        ]
                    }
                    
                    # If there are server contexts and tools available, add them to the request
                    if server_contexts and available_tools:
                        print(f"Using {len(available_tools)} tools with minimal schema")
                        
                        # Just use the tools without any manipulation
                        kwargs["tools"] = available_tools
                        
                        # Print first tool for debugging
                        if available_tools:
                            print(f"First tool: {available_tools[0]['function']['name']}")
                            print(json.dumps(available_tools[0], indent=2))
                    
                    # Print debugging information
                    print(f"Sending request to Anthropic API using Python client")
                    print(f"Number of tools: {len(available_tools)}")
                    if available_tools:
                        print(f"First tool: {available_tools[0]['custom']['name']}")
                    
                    # Make the API call
                    response = client.messages.create(**kwargs)
                    
                    # Convert the response object to a dictionary to avoid "object Message can't be used in 'await' expression"
                    response_dict = {
                        "id": response.id,
                        "model": response.model,
                        "content": []
                    }
                    
                    # Convert content items
                    for item in response.content:
                        content_item = {"type": item.type}
                        if hasattr(item, "text"):
                            content_item["text"] = item.text
                        if item.type == "tool_use":
                            content_item["id"] = item.id
                            content_item["name"] = item.name
                            content_item["input"] = item.input
                        response_dict["content"].append(content_item)
                        
                    # Return the dictionary instead of the Message object
                    return response_dict
                except anthropic.APIStatusError as e:
                    # Handle API errors more specifically
                    if e.status_code == 401:
                        print("Authentication error: The API key appears to be invalid or expired")
                    elif e.status_code == 400:
                        print("Bad request: Check the format of your request and tools")
                        error_message = str(e)
                        if "tools.0" in error_message and "Extra inputs are not permitted" in error_message:
                            print("CRITICAL ERROR: Tool structure error detected!")
                            print(f"Full error message: {error_message}")
                            print("This means there's a problem with the tool structure")
                            # Print a simplified version of the tools for debugging
                            if "tools" in kwargs:
                                for i, tool in enumerate(kwargs["tools"]):
                                    print(f"\nTOOL {i} STRUCTURE:")
                                    if "custom" in tool:
                                        custom_obj = tool["custom"]
                                        print(f"- name: {custom_obj.get('name')}")
                                        print(f"- CUSTOM KEYS: {list(custom_obj.keys())}")
                                        if "type" in custom_obj:
                                            print(f"  FOUND ILLEGAL 'type' KEY: {custom_obj['type']}")
                        if "tools" in kwargs:
                            print(f"Number of tools in request: {len(kwargs['tools'])}")
                    elif e.status_code == 429:
                        print("Rate limit exceeded: Too many requests")
                    
                    # Re-raise to be caught by outer exception handler
                    raise
            
            # Run the API call directly using async methods if possible
            try:
                # First try running directly with async client to avoid thread pool issues
                client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                
                # Prepare the request parameters
                kwargs = {
                    "model": "claude-3-7-sonnet-20250219",
                    "max_tokens": 4000,
                    "system": system_prompt,
                    "messages": [
                        {"role": "user", "content": message}
                    ]
                }
                
                # Add tools if available
                if server_contexts and available_tools:
                    kwargs["tools"] = available_tools
                
                print("Sending request directly using async Anthropic API")
                response = await client.messages.create(**kwargs)
                
                # Convert response to dictionary immediately
                result = {
                    "id": response.id,
                    "model": response.model,
                    "content": []
                }
                
                # Convert content items to dictionaries
                for item in response.content:
                    content_item = {"type": item.type}
                    if hasattr(item, "text"):
                        content_item["text"] = item.text
                    if item.type == "tool_use":
                        content_item["id"] = item.id
                        content_item["name"] = item.name
                        content_item["input"] = item.input
                    result["content"].append(content_item)
                
                print("Successfully got response using async Anthropic API")
            except Exception as direct_error:
                print(f"Error using async approach: {direct_error}, falling back to thread pool")
                # Fall back to thread pool approach
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(None, call_anthropic)
            
            # Convert result to a dict to avoid "object Message can't be used in 'await' expression"
            if isinstance(result, dict):
                result_dict = result  # Already a dict, no conversion needed
            else:
                # Convert Message object to dict
                result_dict = {
                    "id": result.id,
                    "model": result.model,
                    "content": [{"type": item.type, "text": item.text if hasattr(item, "text") else ""} 
                               for item in result.content]
                }
                
                # Add tool_calls if they exist
                if hasattr(result, "tool_calls"):
                    result_dict["tool_calls"] = result.tool_calls
            
            # Handle tool calls in the response, using dict format
            tool_calls_detected = False
            for content_item in result_dict.get("content", []):
                if content_item.get("type") == "tool_use":
                    tool_calls_detected = True
                    break
                
            if tool_calls_detected:
                print("Tool use detected in response")
                
                tool_calls = []
                for content_item in result_dict.get("content", []):
                    if content_item.get("type") == "tool_use":
                        tool_use_id = content_item.get("id", "")
                        tool_name = content_item.get("name", "")
                        tool_input = content_item.get("input", {})
                        server_name = server_tool_map.get(tool_name)
                        
                        tool_calls.append({
                            "id": tool_use_id,
                            "name": tool_name,
                            "server": server_name,
                            "input": tool_input
                        })
                
                # Process all tool calls
                tool_results = []
                for tool_call in tool_calls:
                    server_name = tool_call["server"]
                    tool_name = tool_call["name"]
                    tool_input = tool_call["input"]
                    
                    if server_name and server_name in self.sessions:
                        print(f"Executing tool '{tool_name}' on server '{server_name}'")
                        try:
                            # Call the tool using the MCP SDK pattern
                            tool_result = await self.call_tool(server_name, tool_name, tool_input)
                            print(f"Tool result: {str(tool_result)[:200]}...")
                            
                            tool_results.append({
                                "id": tool_call["id"],
                                "name": tool_name,
                                "server": server_name,
                                "input": tool_input,  # Include the input for use in UI
                                "result": tool_result
                            })
                        except Exception as e:
                            print(f"Error executing tool: {e}")
                            tool_results.append({
                                "id": tool_call["id"],
                                "name": tool_name,
                                "server": server_name,
                                "input": tool_input,  # Include the input for use in UI
                                "error": str(e)
                            })
                
                # Update the result_dict with tool results
                result_dict["tools"] = tool_results  # Add tool results to the response
            else:
                # Make sure there's a content list
                if "content" not in result_dict:
                    result_dict["content"] = []
            
            return result_dict
        except Exception as e:
            error_details = str(e)
            if hasattr(e, "__dict__"):
                error_attrs = {k: str(v) for k, v in e.__dict__.items() if k != "args"}
                error_details += f"\nError details: {json.dumps(error_attrs, indent=2)}"
            
            print(f"Error sending prompt: {error_details}")
            return {
                "error": True,
                "message": f"Failed to get response from Anthropic API: {str(e)}",
                "details": error_details
            }

    async def list_prompts(self):
        """List available prompts on the current server."""
        if not self.sessions:
            print("No server connected")
            return []

        try:
            prompts = await self.sessions[self.current_server_name].list_prompts()
            print(f"\nAvailable prompts on '{self.current_server_name}':")
            if not prompts:
                print("  No prompts available")
            else:
                for i, prompt in enumerate(prompts):
                    print(f"{i+1}. {prompt.name}: {prompt.description}")
                    if hasattr(prompt, 'arguments') and prompt.arguments:
                        print("   Arguments:")
                        for arg in prompt.arguments:
                            print(f"    - {arg.name}: {arg.description} (Required: {arg.required})")
            return prompts
        except Exception as e:
            print(f"Error listing prompts: {e}")
            print("This server may not support the prompts API")
            return []

    async def execute_prompt(self):
        """Execute a preset prompt on the current server."""
        if not self.sessions:
            print("No server connected")
            return None

        prompts = await self.list_prompts()
        if not prompts:
            print("No prompts available or not supported by this server")
            return None

        selection = int(input("\nSelect a prompt (number): ")) - 1
        if selection < 0 or selection >= len(prompts):
            print("Invalid selection.")
            return None

        selected_prompt = prompts[selection]
        print(f"Selected: {selected_prompt.name}")

        prompt_args = {}
        if hasattr(selected_prompt, 'arguments') and selected_prompt.arguments:
            for arg in selected_prompt.arguments:
                prompt_args[arg.name] = input(f"Enter {arg.name} ({arg.description}): ")

        try:
            prompt = await self.sessions[self.current_server_name].get_prompt(selected_prompt.name, arguments=prompt_args)
            if prompt and hasattr(prompt, 'messages'):
                print("\nPrompt template:")
                for msg in prompt.messages:
                    text = msg.content.text if hasattr(msg.content, 'text') else msg.content
                    print(f"{msg.role}: {text}")
                return prompt
            else:
                print("Prompt retrieved but has no messages")
                return None
        except Exception as e:
            print(f"Error executing prompt: {e}")
            return None

    async def list_resources(self):
        """List all resources available through the current server."""
        if not self.sessions:
            print("No server connected")
            return []

        try:
            resources = await self.sessions[self.current_server_name].list_resources()
            print(f"\nAvailable resources on '{self.current_server_name}':")
            if not resources:
                print("  No resources available")
            else:
                for i, resource in enumerate(resources):
                    print(f"{i+1}. {resource.uri}")
            return resources
        except Exception as e:
            print(f"Error listing resources: {e}")
            print("This server may not support the resources API")
            return []

    async def read_resource(self):
        """Read a resource from the current server."""
        if not self.sessions:
            print("No server connected")
            return None

        resources = await self.list_resources()
        if not resources:
            return None

        selection = int(input("\nSelect a resource (number): ")) - 1
        if selection < 0 or selection >= len(resources):
            print("Invalid selection.")
            return None

        selected_resource = resources[selection]
        print(f"Selected: {selected_resource.uri}")

        try:
            content, mime_type = await self.sessions[self.current_server_name].read_resource(selected_resource.uri)
            print(f"\nResource content (MIME type: {mime_type}):")
            if mime_type.startswith("text/"):
                print(content)
            else:
                print(f"Binary content, {len(content)} bytes")
            return content
        except Exception as e:
            print(f"Error reading resource: {e}")
            return None

    async def run(self):
        """Run the interactive MCP client."""
        if not self.load_config():
            print("Failed to load configuration. Exiting.")
            return

        print("\nWelcome to the MCP Config Client!")
        print("Type 'help' to see available commands.")

        while True:
            try:
                command = input("\nCommand: ").strip().lower()

                if command in ["exit", "quit"]:
                    if self.sessions:
                        await self.disconnect()
                    print("Goodbye!")
                    break

                elif command == "help":
                    print("\nAvailable commands:")
                    print("  servers      - List available MCP servers")
                    print("  connect      - Connect to a server")
                    print("  disconnect   - Disconnect from current server")
                    print("  tools        - List available tools on the current server")
                    print("  call         - Call a tool on the current server")
                    print("  prompts      - List available prompts on the current server")
                    print("  execute      - Execute a prompt on the current server")
                    print("  resources    - List available resources on the current server")
                    print("  read         - Read a resource from the current server")
                    print("  prompt       - Send a direct prompt to the current server")
                    print("  help         - Show this help message")
                    print("  exit         - Exit the client")

                elif command == "servers":
                    await self.list_servers()

                elif command == "connect":
                    servers = await self.list_servers()
                    if servers:
                        try:
                            selection = int(input("\nSelect a server (number): ")) - 1
                            if 0 <= selection < len(servers):
                                server_name = servers[selection]
                                await self.connect_to_server(server_name)
                            else:
                                print("Invalid selection.")
                        except ValueError:
                            print("Please enter a valid number.")

                elif command == "disconnect":
                    if self.sessions:
                        await self.disconnect()
                    else:
                        print("No server currently connected.")

                elif command == "tools":
                    if self.sessions:
                        await self.list_tools()
                    else:
                        print("Please connect to a server first.")

                elif command == "call":
                    if self.sessions:
                        await self.call_tool()
                    else:
                        print("Please connect to a server first.")

                elif command == "prompts":
                    if self.sessions:
                        await self.list_prompts()
                    else:
                        print("Please connect to a server first.")

                elif command == "execute":
                    if self.sessions:
                        await self.execute_prompt()
                    else:
                        print("Please connect to a server first.")

                elif command == "resources":
                    if self.sessions:
                        await self.list_resources()
                    else:
                        print("Please connect to a server first.")

                elif command == "read":
                    if self.sessions:
                        await self.read_resource()
                    else:
                        print("Please connect to a server first.")

                elif command == "prompt":
                    if self.sessions:
                        await self.send_prompt()
                    else:
                        print("Please connect to a server first.")

                else:
                    print(f"Unknown command: {command}. Type 'help' for available commands.")

            except Exception as e:
                print(f"Error: {e}")

async def main():
    client = MCPConfigClient()
    saved_config = client.get_saved_config_path()
    config_file = input(f"Enter path to config file (default: {saved_config}): ") or saved_config
    client.config_file = config_file
    client.save_config_path(config_file)
    await client.run()

if __name__ == "__main__":
    asyncio.run(main())
