#!/usr/bin/env node
/**
 * Azure Pricing MCP Bridge
 * Converts MCP JSON-RPC protocol to HTTP API calls
 */

const https = require('https');
const readline = require('readline');

const BASE_URL = 'https://azure-pricing-mcp.azurewebsites.net';

// Setup stdin/stdout for MCP protocol
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

// Keep the process alive
process.stdin.resume();

function log(message) {
  console.error(`[Azure Pricing Bridge] ${new Date().toISOString()} ${message}`);
}

function sendResponse(response) {
  process.stdout.write(JSON.stringify(response) + '\n');
}

function makeHttpRequest(endpoint, data = null) {
  return new Promise((resolve, reject) => {
    const url = new URL(endpoint, BASE_URL);
    const options = {
      hostname: url.hostname,
      port: url.port || 443,
      path: url.pathname,
      method: data ? 'POST' : 'GET',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'Azure-Pricing-MCP-Bridge/1.0'
      },
      timeout: 30000
    };

    const req = https.request(options, (res) => {
      let responseData = '';
      
      res.on('data', (chunk) => {
        responseData += chunk;
      });
      
      res.on('end', () => {
        try {
          const jsonResponse = JSON.parse(responseData);
          resolve(jsonResponse);
        } catch (e) {
          resolve({ error: `Invalid JSON response: ${e.message}`, raw: responseData });
        }
      });
    });

    req.on('error', (e) => {
      reject(new Error(`Request failed: ${e.message}`));
    });

    req.on('timeout', () => {
      req.destroy();
      reject(new Error('Request timeout'));
    });

    if (data) {
      req.write(JSON.stringify(data));
    }
    
    req.end();
  });
}

async function handleMessage(message) {
  const { method, params = {}, id } = message;
  
  try {
    switch (method) {
      case 'initialize':
        sendResponse({
          jsonrpc: '2.0',
          id: id,
          result: {
            protocolVersion: '2024-11-05',
            capabilities: {
              tools: {}
            },
            serverInfo: {
              name: 'azure-pricing-bridge',
              version: '1.0.0'
            }
          }
        });
        break;
        
      case 'notifications/initialized':
        // No response needed for notifications
        log('MCP client initialized');
        break;
        
      case 'tools/list':
        try {
          const docsResponse = await makeHttpRequest('/docs');
          
          if (docsResponse.error) {
            throw new Error(docsResponse.error);
          }
          
          const tools = (docsResponse.tools || []).map(tool => ({
            name: tool.name,
            description: tool.description,
            inputSchema: {
              type: 'object',
              properties: {
                service_name: {
                  type: 'string',
                  description: 'Azure service name to filter by'
                },
                region: {
                  type: 'string',
                  description: 'Azure region name'
                },
                limit: {
                  type: 'number',
                  description: 'Maximum number of results (1-1000)',
                  minimum: 1,
                  maximum: 1000
                },
                currency: {
                  type: 'string',
                  description: 'Currency code (USD, EUR, GBP, etc.)',
                  enum: ['USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'INR', 'CNY', 'BRL']
                },
                response_format: {
                  type: 'string',
                  description: 'Output format',
                  enum: ['markdown', 'json']
                }
              }
            }
          }));
          
          sendResponse({
            jsonrpc: '2.0',
            id: id,
            result: { tools }
          });
        } catch (error) {
          sendResponse({
            jsonrpc: '2.0',
            id: id,
            error: {
              code: -32000,
              message: 'Failed to get tools list',
              data: error.message
            }
          });
        }
        break;
        
      case 'tools/call':
        try {
          const { name: toolName, arguments: toolArgs } = params;
          
          if (!toolName) {
            throw new Error('Tool name is required');
          }
          
          const apiData = {
            tool_name: toolName,
            arguments: toolArgs || {}
          };
          
          const apiResponse = await makeHttpRequest('/tools', apiData);
          
          if (apiResponse.error) {
            throw new Error(apiResponse.error);
          }
          
          const resultText = apiResponse.result || JSON.stringify(apiResponse, null, 2);
          
          sendResponse({
            jsonrpc: '2.0',
            id: id,
            result: {
              content: [
                {
                  type: 'text',
                  text: resultText
                }
              ]
            }
          });
        } catch (error) {
          sendResponse({
            jsonrpc: '2.0',
            id: id,
            error: {
              code: -32000,
              message: 'Tool execution failed',
              data: error.message
            }
          });
        }
        break;
        
      default:
        sendResponse({
          jsonrpc: '2.0',
          id: id,
          error: {
            code: -32601,
            message: `Method not found: ${method}`
          }
        });
    }
  } catch (error) {
    log(`Error handling message: ${error.message}`);
    sendResponse({
      jsonrpc: '2.0',
      id: id,
      error: {
        code: -32000,
        message: 'Internal error',
        data: error.message
      }
    });
  }
}

// Main message processing loop
rl.on('line', async (line) => {
  if (!line.trim()) return;
  
  try {
    const message = JSON.parse(line);
    log(`Received message: ${message.method}`);
    await handleMessage(message);
  } catch (error) {
    log(`JSON parse error: ${error.message}`);
    sendResponse({
      jsonrpc: '2.0',
      id: null,
      error: {
        code: -32700,
        message: 'Parse error'
      }
    });
  }
});

rl.on('close', () => {
  log('Input stream closed');
});

rl.on('error', (error) => {
  log(`Readline error: ${error.message}`);
});

// Handle process signals
process.on('SIGINT', () => {
  log('Received SIGINT, exiting');
  process.exit(0);
});

process.on('SIGTERM', () => {
  log('Received SIGTERM, exiting');
  process.exit(0);
});

log('Azure Pricing MCP Bridge started');