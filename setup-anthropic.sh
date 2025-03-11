#!/bin/bash

# Get the directory containing this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source the .env file to get the API key
if [ -f "$SCRIPT_DIR/.env" ]; then
    # Export all variables from .env file
    export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs -d '\n')
    
    # Check if ANTHROPIC_API_KEY was successfully exported
    if [ -n "$ANTHROPIC_API_KEY" ]; then
        echo "Anthropic API key successfully loaded from .env file"
        echo "ANTHROPIC_API_KEY is now set in your environment"
    else
        echo "Failed to load ANTHROPIC_API_KEY from .env file"
        exit 1
    fi
else
    echo "Error: .env file not found in $SCRIPT_DIR"
    echo "Please create an .env file with your ANTHROPIC_API_KEY"
    exit 1
fi
