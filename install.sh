#!/bin/bash

# Update dependencies
echo "Installing dependencies..."

# Install main packages
bun install

# Install additional packages
bun add @mui/icons-material framer-motion react-markdown remark-gfm react-syntax-highlighter
bun add -D @types/react-syntax-highlighter

echo "Installation complete!" 