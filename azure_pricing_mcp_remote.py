#!/usr/bin/env python3
"""
Azure Retail Prices Remote MCP Server

This is a true remote MCP server that runs on Azure App Service with WebSocket transport.
Claude Desktop can connect directly to this without needing a bridge.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# Import our existing MCP tools
from azure_pricing_mcp import (
    azure_get_service_prices,
    azure_compare_region_prices,
    azure_search_sku_prices,
    azure_get_service_families,
    azure_calculate_savings_plan,
    ServicePricesInput,
    RegionComparisonInput,
    SKUSearchInput,
    ServiceFamiliesInput,
    SavingsPlanInput
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Azure Pricing Remote MCP Server",
    description="Remote MCP server for Azure retail pricing information",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MCP tool registry
MCP_TOOLS = {
    "azure_get_service_prices": {
        "func": azure_get_service_prices,
        "input_model": ServicePricesInput,
        "description": "Get Azure retail prices with comprehensive filtering",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service_name": {
                    "type": "string",
                    "description": "Azure service name to filter by"
                },
                "service_family": {
                    "type": "string",
                    "description": "Service family to filter by"
                },
                "region": {
                    "type": "string",
                    "description": "Azure region name"
                },
                "sku_name": {
                    "type": "string",
                    "description": "SKU name to filter by"
                },
                "currency": {
                    "type": "string",
                    "enum": ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "INR", "CNY", "BRL"],
                    "description": "Currency code"
                },
                "limit": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Maximum number of results"
                },
                "response_format": {
                    "type": "string",
                    "enum": ["markdown", "json"],
                    "description": "Output format"
                }
            }
        }
    },
    "azure_compare_region_prices": {
        "func": azure_compare_region_prices,
        "input_model": RegionComparisonInput,
        "description": "Compare prices across multiple Azure regions",
        "inputSchema": {
            "type": "object",
            "required": ["service_name", "regions"],
            "properties": {
                "service_name": {
                    "type": "string",
                    "description": "Azure service name to compare"
                },
                "regions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 2,
                    "maxItems": 10,
                    "description": "List of Azure region names to compare"
                },
                "sku_name": {
                    "type": "string",
                    "description": "Specific SKU to compare"
                },
                "currency": {
                    "type": "string",
                    "enum": ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "INR", "CNY", "BRL"],
                    "description": "Currency code"
                }
            }
        }
    },
    "azure_search_sku_prices": {
        "func": azure_search_sku_prices,
        "input_model": SKUSearchInput,
        "description": "Search for SKU pricing using flexible terms",
        "inputSchema": {
            "type": "object",
            "required": ["search_term"],
            "properties": {
                "search_term": {
                    "type": "string",
                    "description": "Search term for SKU names"
                },
                "service_family": {
                    "type": "string",
                    "description": "Filter by service family"
                },
                "region": {
                    "type": "string",
                    "description": "Filter by specific region"
                },
                "currency": {
                    "type": "string",
                    "enum": ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "INR", "CNY", "BRL"],
                    "description": "Currency code"
                },
                "limit": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Maximum number of results"
                }
            }
        }
    },
    "azure_get_service_families": {
        "func": azure_get_service_families,
        "input_model": ServiceFamiliesInput,
        "description": "List available Azure service families",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Maximum number of service families to return"
                },
                "response_format": {
                    "type": "string",
                    "enum": ["markdown", "json"],
                    "description": "Output format"
                }
            }
        }
    },
    "azure_calculate_savings_plan": {
        "func": azure_calculate_savings_plan,
        "input_model": SavingsPlanInput,
        "description": "Calculate savings plan benefits",
        "inputSchema": {
            "type": "object",
            "required": ["service_name"],
            "properties": {
                "service_name": {
                    "type": "string",
                    "description": "Azure service name to analyze"
                },
                "sku_name": {
                    "type": "string",
                    "description": "Specific SKU to analyze"
                },
                "region": {
                    "type": "string",
                    "description": "Azure region to analyze"
                },
                "currency": {
                    "type": "string",
                    "enum": ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "INR", "CNY", "BRL"],
                    "description": "Currency code"
                }
            }
        }
    }
}

class MCPConnection:
    """Manages an MCP WebSocket connection."""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.initialized = False
    
    async def send_response(self, response: Dict[str, Any]):
        """Send a JSON-RPC response."""
        await self.websocket.send_text(json.dumps(response))
    
    async def send_error(self, request_id: Any, code: int, message: str, data: Any = None):
        """Send a JSON-RPC error response."""
        error_response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }
        if data:
            error_response["error"]["data"] = data
        
        await self.send_response(error_response)
    
    async def handle_initialize(self, request_id: Any, params: Dict[str, Any]):
        """Handle MCP initialize request."""
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "azure-pricing-remote-mcp",
                    "version": "1.0.0"
                }
            }
        }
        await self.send_response(response)
        self.initialized = True
        logger.info("MCP client initialized")
    
    async def handle_tools_list(self, request_id: Any):
        """Handle tools/list request."""
        tools = []
        for tool_name, tool_info in MCP_TOOLS.items():
            tools.append({
                "name": tool_name,
                "description": tool_info["description"],
                "inputSchema": tool_info["inputSchema"]
            })
        
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": tools
            }
        }
        await self.send_response(response)
    
    async def handle_tools_call(self, request_id: Any, params: Dict[str, Any]):
        """Handle tools/call request."""
        try:
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name not in MCP_TOOLS:
                await self.send_error(request_id, -32602, f"Unknown tool: {tool_name}")
                return
            
            tool_info = MCP_TOOLS[tool_name]
            input_model = tool_info["input_model"]
            tool_func = tool_info["func"]
            
            # Validate and execute the tool
            try:
                validated_input = input_model(**arguments)
                result = await tool_func(validated_input)
                
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": result
                            }
                        ]
                    }
                }
                await self.send_response(response)
                
            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                await self.send_error(request_id, -32000, f"Tool execution failed: {str(e)}")
                
        except Exception as e:
            logger.error(f"Tools call handler error: {e}")
            await self.send_error(request_id, -32000, f"Internal error: {str(e)}")
    
    async def handle_message(self, message: str):
        """Handle incoming MCP message."""
        try:
            data = json.loads(message)
            method = data.get("method")
            request_id = data.get("id")
            params = data.get("params", {})
            
            logger.info(f"Received MCP message: {method}")
            
            if method == "initialize":
                await self.handle_initialize(request_id, params)
            elif method == "notifications/initialized":
                # No response needed
                pass
            elif method == "tools/list":
                await self.handle_tools_list(request_id)
            elif method == "tools/call":
                await self.handle_tools_call(request_id, params)
            else:
                await self.send_error(request_id, -32601, f"Method not found: {method}")
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            await self.send_error(None, -32700, "Parse error")
        except Exception as e:
            logger.error(f"Message handling error: {e}")
            await self.send_error(None, -32000, f"Internal error: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint with server information."""
    return {
        "name": "Azure Pricing Remote MCP Server",
        "version": "1.0.0",
        "description": "Remote MCP server for Azure retail pricing information",
        "protocol": "WebSocket MCP",
        "websocket_endpoint": "/mcp",
        "tools": list(MCP_TOOLS.keys())
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "protocol": "WebSocket MCP"}

@app.websocket("/mcp")
async def mcp_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for MCP communication."""
    await websocket.accept()
    connection = MCPConnection(websocket)
    logger.info("MCP WebSocket connection established")
    
    try:
        while True:
            message = await websocket.receive_text()
            await connection.handle_message(message)
    except WebSocketDisconnect:
        logger.info("MCP WebSocket connection closed")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

@app.get("/mcp-info")
async def mcp_info():
    """Information about connecting to this MCP server."""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Azure Pricing Remote MCP Server</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            code { background: #f5f5f5; padding: 2px 6px; border-radius: 3px; }
            pre { background: #f5f5f5; padding: 20px; border-radius: 5px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <h1>Azure Pricing Remote MCP Server</h1>
        <p>This is a remote MCP server providing Azure pricing tools via WebSocket.</p>
        
        <h2>Claude Desktop Configuration</h2>
        <p>Add this to your <code>claude_desktop_config.json</code>:</p>
        <pre>{
  "mcpServers": {
    "azure-pricing": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/client-websocket", "ws://your-domain/mcp"]
    }
  }
}</pre>
        
        <h2>Available Tools</h2>
        <ul>
            <li><strong>azure_get_service_prices</strong> - Get Azure retail prices with filtering</li>
            <li><strong>azure_compare_region_prices</strong> - Compare prices across regions</li>
            <li><strong>azure_search_sku_prices</strong> - Search for SKU pricing</li>
            <li><strong>azure_get_service_families</strong> - List Azure service families</li>
            <li><strong>azure_calculate_savings_plan</strong> - Calculate savings plan benefits</li>
        </ul>
    </body>
    </html>
    """)

if __name__ == "__main__":
    # Get port from environment variable (Azure App Service default)
    port = int(os.environ.get('PORT', 8000))
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info(f"Starting Azure Pricing Remote MCP Server on port {port}")
    
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )