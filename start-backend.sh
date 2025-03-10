#!/bin/bash

echo "====================================="
echo "MCP Client UI - Starting Backend"
echo "====================================="
echo ""

# Check if both files exist and warn user
if [[ -f mcp-ui.py && -f mcp_ui.py ]]; then
  echo "WARNING: Both mcp-ui.py and mcp_ui.py exist. This may cause confusion."
  echo "This script will use mcp_ui.py as the entry point."
fi

# Check for Python
if ! command -v python &> /dev/null; then
  echo "Error: Python not found. Please install Python 3.8 or higher."
  exit 1
fi

# Check for Anthropic API key
if [[ -z "${ANTHROPIC_API_KEY}" ]]; then
  echo "Warning: ANTHROPIC_API_KEY environment variable is not set."
  echo "LLM functionality will not work correctly."
  echo "Run 'source setup-anthropic.sh' first to set up your API key."
  echo ""
fi

# Start the server with the correct module name
echo "Starting FastAPI server on http://localhost:8000..."
python -m uvicorn mcp_ui:app --host 0.0.0.0 --port 8000 --reload

# This should never be reached unless the server is stopped
echo "Server has stopped."
