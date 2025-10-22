#!/usr/bin/env python3
"""
Azure App Service entry point for Azure Pricing MCP Server

This module provides a Flask wrapper for the MCP server to work with Azure App Service.
It runs the MCP server in HTTP mode and provides health check endpoints.
"""

from flask import Flask, request, jsonify
import subprocess
import sys
import os
import threading
import time
import requests
from azure_pricing_mcp import main as mcp_main

# Create Flask app
app = Flask(__name__)

# Global variable to track MCP server process
mcp_process = None
mcp_thread = None

def start_mcp_server():
    """Start the MCP server in a separate thread."""
    global mcp_thread
    
    def run_mcp():
        # Override sys.argv to set HTTP transport
        original_argv = sys.argv
        try:
            sys.argv = ['azure_pricing_mcp.py', '--transport', 'http', '--port', '8001']
            mcp_main()
        except Exception as e:
            print(f"Error starting MCP server: {e}")
        finally:
            sys.argv = original_argv
    
    mcp_thread = threading.Thread(target=run_mcp, daemon=True)
    mcp_thread.start()
    
    # Wait a moment for the server to start
    time.sleep(2)

@app.route('/')
def index():
    """Root endpoint with basic information."""
    return jsonify({
        "name": "Azure Pricing MCP Server",
        "version": "1.0.0",
        "description": "Model Context Protocol server for Azure retail pricing information",
        "endpoints": {
            "health": "/health",
            "mcp": "http://localhost:8001",
            "docs": "/docs"
        }
    })

@app.route('/health')
def health():
    """Health check endpoint for Azure App Service."""
    try:
        # Check if MCP server is responding
        response = requests.get('http://localhost:8001', timeout=5)
        if response.status_code == 200:
            return jsonify({"status": "healthy", "mcp_server": "running"}), 200
        else:
            return jsonify({"status": "unhealthy", "mcp_server": "not responding"}), 503
    except requests.exceptions.RequestException:
        return jsonify({"status": "unhealthy", "mcp_server": "not accessible"}), 503

@app.route('/docs')
def docs():
    """Documentation endpoint."""
    return jsonify({
        "title": "Azure Pricing MCP Server API",
        "description": "This server provides Model Context Protocol tools for Azure pricing analysis",
        "tools": [
            {
                "name": "azure_get_service_prices",
                "description": "Get Azure retail prices with comprehensive filtering"
            },
            {
                "name": "azure_compare_region_prices", 
                "description": "Compare prices across multiple Azure regions"
            },
            {
                "name": "azure_search_sku_prices",
                "description": "Search for SKU pricing using flexible terms"
            },
            {
                "name": "azure_get_service_families",
                "description": "List available Azure service families"
            },
            {
                "name": "azure_calculate_savings_plan",
                "description": "Calculate savings plan benefits"
            }
        ],
        "mcp_endpoint": "http://localhost:8001",
        "transport": "HTTP",
        "documentation": "https://github.com/matt-edwards-aztech/AzurePricingMCP"
    })

@app.route('/api/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy_to_mcp(path):
    """Proxy API requests to the MCP server."""
    try:
        mcp_url = f'http://localhost:8001/{path}'
        
        if request.method == 'GET':
            response = requests.get(mcp_url, params=request.args, timeout=30)
        elif request.method == 'POST':
            response = requests.post(mcp_url, json=request.json, timeout=30)
        elif request.method == 'PUT':
            response = requests.put(mcp_url, json=request.json, timeout=30)
        elif request.method == 'DELETE':
            response = requests.delete(mcp_url, timeout=30)
        
        return response.content, response.status_code, response.headers.items()
    
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"MCP server error: {str(e)}"}), 503

if __name__ == "__main__":
    # Start the MCP server
    start_mcp_server()
    
    # Get port from environment variable (Azure App Service default)
    port = int(os.environ.get('PORT', 8000))
    
    # Run Flask app
    app.run(host='0.0.0.0', port=port, debug=False)