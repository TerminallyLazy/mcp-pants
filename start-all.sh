#!/bin/bash

echo "====================================="
echo "MCP Client UI - Starting All Services"
echo "====================================="
echo ""

# Function to check if a command exists
command_exists() {
  command -v "$1" &> /dev/null
}

# Check for needed terminal emulators
TERMINAL=""
if command_exists gnome-terminal; then
  TERMINAL="gnome-terminal"
elif command_exists xterm; then
  TERMINAL="xterm"
elif command_exists konsole; then
  TERMINAL="konsole"
elif command_exists terminator; then
  TERMINAL="terminator"
fi

# Check for Anthropic API key
if [[ -z "${ANTHROPIC_API_KEY}" ]]; then
  echo "Warning: ANTHROPIC_API_KEY environment variable is not set."
  echo "LLM functionality will not work correctly."
  echo "Run 'source setup-anthropic.sh' first to set up your API key."
  echo ""
  
  read -p "Do you want to continue anyway? (y/n) " -n 1 -r
  echo ""
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Exiting. Set up the Anthropic API key first with 'source setup-anthropic.sh'."
    exit 1
  fi
fi

# Get the current directory path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -n "$TERMINAL" ]]; then
  # Start backend in a new terminal window
  echo "Starting backend in a new terminal window..."
  case "$TERMINAL" in
    "gnome-terminal") 
      gnome-terminal -- bash -c "cd \"$SCRIPT_DIR\" && ./start-backend.sh; read -p 'Press Enter to close this terminal...'"
      ;;
    "xterm") 
      xterm -e "cd \"$SCRIPT_DIR\" && ./start-backend.sh; read -p 'Press Enter to close this terminal...'"
      ;;
    "konsole") 
      konsole --workdir "$SCRIPT_DIR" -e "./start-backend.sh; read -p 'Press Enter to close this terminal...'"
      ;;
    "terminator") 
      terminator --working-directory="$SCRIPT_DIR" -e "./start-backend.sh; read -p 'Press Enter to close this terminal...'"
      ;;
  esac
  
  # Wait for backend to start
  echo "Waiting for backend to initialize (5 seconds)..."
  sleep 5
  
  # Start frontend in the current terminal
  echo "Starting frontend in this terminal..."
  cd "$SCRIPT_DIR" && ./start-frontend.sh
else
  # No terminal emulator found, run in background with nohup
  echo "No terminal emulator found. Starting backend in the background..."
  cd "$SCRIPT_DIR"
  nohup ./start-backend.sh > backend.log 2>&1 &
  BACKEND_PID=$!
  echo "Backend started with PID $BACKEND_PID (logs in backend.log)"
  
  # Wait for backend to start
  echo "Waiting for backend to initialize (5 seconds)..."
  sleep 5
  
  # Start frontend
  echo "Starting frontend..."
  ./start-frontend.sh
fi
