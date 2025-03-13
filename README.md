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

![Image 1](https://cdn.discordapp.com/attachments/1053882445017124977/1348910293194903574/image.png?ex=67d3d11b&is=67d27f9b&hm=dede5e76ccb94967a5a0657263e2a629e0a72be4da887d78f0796008a2aa2739&)
![Image 2](https://cdn.discordapp.com/attachments/1053882445017124977/1348910293551681587/image.png?ex=67d3d11b&is=67d27f9b&hm=8b0a57ab1b6f2f21a3ed1553ce2c29042fc3631f4be26cdb202da8c52af8b417&)
![Image 3](https://cdn.discordapp.com/attachments/1053882445017124977/1348910376691044414/image.png?ex=67d3d12f&is=67d27faf&hm=91e65134de255970e0c6f3bd0bbe4ba53a5b896fb92aac2dcfa107e07d7e3023&)

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
