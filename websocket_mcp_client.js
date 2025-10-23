#!/usr/bin/env node

/**
 * WebSocket MCP Client for Claude Desktop
 * Connects to remote MCP server via WebSocket and bridges to stdio
 */

const WebSocket = require('ws');
const readline = require('readline');

// Configuration
const WS_URL = process.argv[2] || 'wss://azure-pricing-mcp-uksouth.azurewebsites.net/mcp';
const RECONNECT_DELAY = 5000;

let ws = null;
let messageId = 1;
let pendingRequests = new Map();

// Setup stdin/stdout for MCP protocol
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

process.stdin.resume();

function log(message) {
  console.error(`[WebSocket MCP Client] ${new Date().toISOString()} ${message}`);
}

function sendToClaudeDesktop(message) {
  process.stdout.write(JSON.stringify(message) + '\\n');
}

function connectWebSocket() {
  log(`Connecting to ${WS_URL}`);
  
  ws = new WebSocket(WS_URL, {
    handshakeTimeout: 10000,
    perMessageDeflate: false
  });

  ws.on('open', () => {
    log('WebSocket connected successfully');
  });

  ws.on('message', (data) => {
    try {
      const message = JSON.parse(data.toString());
      log(`Received from server: ${message.method || 'response'}`);
      
      // Forward message to Claude Desktop
      sendToClaudeDesktop(message);
    } catch (error) {
      log(`Error parsing server message: ${error.message}`);
    }
  });

  ws.on('close', (code, reason) => {
    log(`WebSocket closed: ${code} ${reason}`);
    
    // Attempt to reconnect after delay
    setTimeout(() => {
      log('Attempting to reconnect...');
      connectWebSocket();
    }, RECONNECT_DELAY);
  });

  ws.on('error', (error) => {
    log(`WebSocket error: ${error.message}`);
  });
}

// Handle messages from Claude Desktop
rl.on('line', (line) => {
  if (!line.trim()) return;
  
  try {
    const message = JSON.parse(line);
    log(`Received from Claude Desktop: ${message.method || 'request'}`);
    
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message));
    } else {
      log('WebSocket not connected, buffering message');
      
      // Send error response for requests when not connected
      if (message.id !== undefined) {
        sendToClaudeDesktop({
          jsonrpc: '2.0',
          id: message.id,
          error: {
            code: -32000,
            message: 'WebSocket not connected'
          }
        });
      }
    }
  } catch (error) {
    log(`Error parsing Claude Desktop message: ${error.message}`);
  }
});

rl.on('close', () => {
  log('Input stream closed, exiting');
  if (ws) {
    ws.close();
  }
  process.exit(0);
});

// Handle process signals
process.on('SIGINT', () => {
  log('Received SIGINT, closing...');
  if (ws) {
    ws.close();
  }
  process.exit(0);
});

process.on('SIGTERM', () => {
  log('Received SIGTERM, closing...');
  if (ws) {
    ws.close();
  }
  process.exit(0);
});

// Start connection
log('Starting WebSocket MCP Client');
connectWebSocket();