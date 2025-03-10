#!/bin/bash

echo "====================================="
echo "MCP Client UI - Starting Frontend"
echo "====================================="
echo ""

# Check if backend is running
if ! curl -s http://localhost:8000/servers > /dev/null; then
  echo "Warning: Backend does not appear to be running or is not responding."
  echo "Please make sure to start the backend first using ./start-backend.sh"
  echo ""
  
  read -p "Do you want to continue anyway? (y/n) " -n 1 -r
  echo ""
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Exiting. Start the backend first with ./start-backend.sh"
    exit 1
  fi
fi

# Check for required tools
if ! command -v bun &> /dev/null; then
  echo "Warning: Bun not found. Falling back to npm."
  if ! command -v npm &> /dev/null; then
    echo "Error: Neither Bun nor npm found. Please install Node.js and npm or Bun."
    exit 1
  fi
  
  echo "Starting React frontend with npm..."
  npm run dev
else
  echo "Starting React frontend with Bun..."
  bun run dev
fi
