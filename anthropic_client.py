from anthropic import Anthropic
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv

class AnthropicClient:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-3-7-sonnet-20250219"

    def _format_tool(self, tool: Dict[str, Any]) -> Dict[str, Any]:
        """Format a tool definition for Anthropic's API."""
        # The error suggests there might be an extra 'type' field in the custom object
        # Let's make sure we're only including the required fields
        
        # Extract and clean the input schema to ensure it doesn't have unexpected fields
        input_schema = tool.get("inputSchema", {})
        
        return {
            "type": "custom",
            "custom": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": input_schema
            }
        }

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
            
            # Format tools for Anthropic API if provided
            formatted_tools = None
            if tools:
                formatted_tools = [self._format_tool(tool) for tool in tools]
                
                # Debug log the formatted tools to see what's being sent
                print(f"DEBUG - Formatted tools: {formatted_tools}")
            
            # Create the message with tools if available
            response = await self.client.messages.create(
                model=self.model,
                messages=messages,
                tools=formatted_tools,
                max_tokens=4096
            )
            
            return {
                "content": response.content,
                "tools": response.tool_calls if hasattr(response, 'tool_calls') else [],
                "id": response.id,
                "model": response.model
            }
            
        except Exception as e:
            print(f"DEBUG - Anthropic API error: {str(e)}")
            return {
                "error": True,
                "message": f"Failed to get response from Anthropic API: {str(e)}",
                "details": str(e)
            } 