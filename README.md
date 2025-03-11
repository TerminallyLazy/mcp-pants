# MCP Client UI

A powerful user interface for interacting with Multiple Cloud Providers (MCP) servers using Claude via the Anthropic API.

## Features

- Connect to multiple MCP servers simultaneously
- Chat with Claude using the Anthropic API
- Utilize tools from all connected servers
- Filter tools by server
- Beautiful, responsive UI

## Prerequisites

- Python 3.8 or higher
- Node.js and npm
- Anthropic API key

## Installation

1. Clone this repository
2. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```
3. Install the required npm packages:
   ```
   cd mcp-client-ui
   npm install
   ```

## Configuration

1. Set up your Anthropic API key in the `.env` file:
   ```
   ANTHROPIC_API_KEY=your_api_key_here
   ```
   
   Or run the setup script:
   ```
   source setup-anthropic.sh
   ```
   
   The script will prompt you to enter your API key if it's not already set.

## Running the application

1. Start the backend server:
   ```
   ./start-backend.sh
   ```

2. Start the frontend server:
   ```
   ./start-frontend.sh
   ```

3. Open your browser and navigate to http://localhost:5173

## Using the MCP Client UI

### Connecting to MCP Servers

1. From the home screen, enter the URL of an MCP server (e.g., http://localhost:8080)
2. Click "Connect"
3. Repeat for additional servers you want to connect to

### Using the Chat Interface

1. Click on "Chat" in the sidebar
2. Type your message in the input box
3. Claude will respond and may use tools from any of your connected servers
4. You can filter which tools Claude can access by selecting specific servers in the Tools Panel

### Managing Connections

- Connected servers are displayed in the sidebar
- Click on a server to view details or disconnect
- Use the sidebar to navigate between different views

## Troubleshooting

- If you see errors related to the Anthropic API key, make sure it's correctly set in your `.env` file
- If tools aren't appearing, check that your MCP servers are running and properly connected
- For server connection issues, verify that the MCP server URLs are correct and the servers are running

## License

[MIT License](LICENSE)
