from anthropic import Anthropic
from typing import List, Dict, Any, Optional
import os
import json
from dotenv import load_dotenv

class AnthropicClient:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-3-7-sonnet-20250219"

    def _deep_clean_object(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively clean an object to ensure it doesn't have 'type' at custom field level.
        
        The 'type' field is allowed at the root level of a tool and in the parameters object,
        but not directly inside the 'custom' object or its properties.
        """
        if not isinstance(obj, dict):
            return obj
            
        cleaned = {}
        for key, value in obj.items():
            # If this is the custom object, we need to be careful with type
            if key == "custom" and isinstance(value, dict):
                custom_cleaned = {}
                for custom_key, custom_value in value.items():
                    # Remove 'type' if it's directly inside custom (not allowed)
                    if custom_key == "type":
                        print("WARNING: Removing disallowed 'type' field from inside 'custom' object")
                        continue
                        
                    # Special handling for parameters
                    if custom_key == "parameters" and isinstance(custom_value, dict):
                        # Parameters should have a type field at its root level (as per JSON Schema)
                        parameters_cleaned = {}
                        for param_key, param_value in custom_value.items():
                            # Process properties specially
                            if param_key == "properties" and isinstance(param_value, dict):
                                properties_cleaned = {}
                                for prop_name, prop_value in param_value.items():
                                    if isinstance(prop_value, dict):
                                        # Make sure each property is properly cleaned
                                        properties_cleaned[prop_name] = self._deep_clean_object(prop_value)
                                    else:
                                        properties_cleaned[prop_name] = prop_value
                                parameters_cleaned["properties"] = properties_cleaned
                            else:
                                parameters_cleaned[param_key] = param_value
                        custom_cleaned[custom_key] = parameters_cleaned
                    else:
                        # For other custom fields, clean recursively
                        custom_cleaned[custom_key] = self._deep_clean_object(custom_value) if isinstance(custom_value, dict) else custom_value
                cleaned[key] = custom_cleaned
            # Handle regular nested dictionaries recursively
            elif isinstance(value, dict):
                cleaned[key] = self._deep_clean_object(value)
            # Handle lists of objects
            elif isinstance(value, list):
                if all(isinstance(item, dict) for item in value):
                    cleaned[key] = [self._deep_clean_object(item) for item in value]
                else:
                    cleaned[key] = value
            else:
                cleaned[key] = value
                
        return cleaned
    
    def _format_tool(self, tool: Dict[str, Any]) -> Dict[str, Any]:
        """Format a tool definition for Anthropic's API using custom type as required by API error."""
        # Extract basic tool properties
        tool_name = tool.get("name", "unknown_tool")
        tool_description = tool.get("description", "No description available")
        
        # Create properties based on tool name
        properties = {}
        if tool_name.lower() == "list_files" or tool_name.lower() == "list_directory":
            properties = {
                "directory": {
                    "description": "The directory to list files in",
                    "type": "string"
                }
            }
        elif tool_name.lower() == "read_file":
            properties = {
                "file_path": {
                    "description": "Path to the file to read",
                    "type": "string"
                }
            }
        elif tool_name.lower() == "write_file":
            properties = {
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
            properties = {
                "args": {
                    "description": "Arguments for the tool as a JSON string",
                    "type": "string"
                }
            }
        
        # Create parameters object
        parameters = {
            "type": "object",
            "properties": properties,
            "required": []
        }
        
        # Add required fields based on tool type
        if tool_name.lower() == "list_files" or tool_name.lower() == "list_directory":
            parameters["required"] = ["directory"]
        elif tool_name.lower() == "read_file":
            parameters["required"] = ["file_path"]
        elif tool_name.lower() == "write_file":
            parameters["required"] = ["file_path", "content"]
        
        # Create the proper tool structure with parameters
        formatted_tool = {
            "type": "custom",
            "custom": {
                "name": tool_name,
                "description": tool_description,
                "parameters": parameters
            }
        }
        
        print(f"Created custom tool structure for {tool_name} with proper parameters format")
        return formatted_tool

    async def send_prompt(self, prompt: str, tools: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a prompt to Anthropic's API with optional tools.
        
        Args:
            prompt: The user's prompt
            tools: List of tool definitions from MCP servers
            
        Returns:
            Dict containing the response and any tool calls made
        """
        try:
            messages = [{"role": "user", "content": prompt}]
            
            # Only proceed with tools if they're provided
            if not tools:
                print("No tools provided, sending prompt without tools")
                response = await self.client.messages.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=4096
                )
                # Convert response to a serializable dictionary
                content_list = []
                for item in response.content:
                    content_item = {"type": item.type}
                    if hasattr(item, "text"):
                        content_item["text"] = item.text
                    content_list.append(content_item)
                
                return {
                    "content": content_list,
                    "id": response.id,
                    "model": response.model
                }
            
            # Log the number of tools
            print(f"Received {len(tools)} tools")
            
            # Use a minimal valid format for each tool with custom type as required by API error
            minimal_tools = []
            for tool in tools:
                # Create proper tool format with simplified properties
                tool_name = tool.get("name", "unknown")
                tool_desc = tool.get("description", "No description")
                
                # Customize properties based on tool name WITH PROPER TYPE FIELDS
                # Error: "tools.0.custom.type: Extra inputs are not permitted" occurs when structure is incorrect
                simple_properties = {}
                if tool_name.lower() == "list_files" or tool_name.lower() == "list_directory":
                    simple_properties = {
                        "directory": {
                            "description": "The directory to list files in",
                            "type": "string"
                        }
                    }
                elif tool_name.lower() == "read_file":
                    simple_properties = {
                        "file_path": {
                            "description": "Path to the file to read",
                            "type": "string"
                        }
                    }
                elif tool_name.lower() == "write_file":
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
                
                # Create the parameters object in the format Claude expects
                parameters = {
                    "type": "object",
                    "properties": simple_properties,
                    "required": []
                }
                
                # Add required parameters based on tool type
                if tool_name.lower() == "list_files" or tool_name.lower() == "list_directory":
                    parameters["required"] = ["directory"]
                elif tool_name.lower() == "read_file":
                    parameters["required"] = ["file_path"]
                elif tool_name.lower() == "write_file":
                    parameters["required"] = ["file_path", "content"]
                
                # Complete tool format with parameters as required by Claude API
                minimal_tool = {
                    "type": "custom",
                    "custom": {
                        "name": tool_name,
                        "description": tool_desc,
                        "parameters": parameters
                    }
                }
                minimal_tools.append(minimal_tool)
            
            # Print first tool for debugging
            if minimal_tools:
                print(f"First tool: {minimal_tools[0]['custom']['name']}")
            
            # Create the message with minimal tools
            print(f"Sending request with {len(minimal_tools)} minimal tools")
            response = await self.client.messages.create(
                model=self.model,
                messages=messages,
                tools=minimal_tools,
                max_tokens=4096
            )
            
            print("Successfully received response from Anthropic API")
            # Convert response.content to a serializable format
            content_list = []
            for item in response.content:
                content_item = {"type": item.type}
                if hasattr(item, "text"):
                    content_item["text"] = item.text
                if item.type == "tool_use":
                    content_item["id"] = item.id
                    content_item["name"] = item.name
                    content_item["input"] = item.input
                content_list.append(content_item)
                
            # Convert tool_calls to a serializable format if they exist
            tool_calls_list = []
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_calls_list.append({
                        "id": tool_call.id,
                        "name": tool_call.name,
                        "input": tool_call.input
                    })
            
            # Return a fully serializable dictionary
            return {
                "content": content_list,
                "tools": tool_calls_list,
                "id": response.id,
                "model": response.model
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"\n===== ANTHROPIC API ERROR =====\n{error_msg}\n")
            
            # Enhanced error handling
            if "400" in error_msg:
                if "tools.0.custom.type" in error_msg:
                    print("ERROR: There's still an issue with the tool format - 'type' field appears in the wrong place")
                elif "tools" in error_msg:
                    print("ERROR: There's an issue with the tool structure being sent to Anthropic")
            
            return {
                "error": True,
                "message": f"Failed to get response from Anthropic API: {error_msg}",
                "details": error_msg
            }