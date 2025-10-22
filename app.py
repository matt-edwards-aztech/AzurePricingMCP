#!/usr/bin/env python3
"""
Azure App Service entry point for Azure Pricing MCP Server

This module provides a Flask wrapper that directly integrates MCP tools
for Azure App Service deployment.
"""

from flask import Flask, request, jsonify
import sys
import os
import asyncio
import json
from typing import Dict, Any

# Import the MCP tools directly
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

# Create Flask app
app = Flask(__name__)

# MCP tool registry
MCP_TOOLS = {
    "azure_get_service_prices": {
        "func": azure_get_service_prices,
        "input_model": ServicePricesInput,
        "description": "Get Azure retail prices with comprehensive filtering"
    },
    "azure_compare_region_prices": {
        "func": azure_compare_region_prices,
        "input_model": RegionComparisonInput,
        "description": "Compare prices across multiple Azure regions"
    },
    "azure_search_sku_prices": {
        "func": azure_search_sku_prices,
        "input_model": SKUSearchInput,
        "description": "Search for SKU pricing using flexible terms"
    },
    "azure_get_service_families": {
        "func": azure_get_service_families,
        "input_model": ServiceFamiliesInput,
        "description": "List available Azure service families"
    },
    "azure_calculate_savings_plan": {
        "func": azure_calculate_savings_plan,
        "input_model": SavingsPlanInput,
        "description": "Calculate savings plan benefits"
    }
}

async def execute_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Execute an MCP tool with the given arguments."""
    if tool_name not in MCP_TOOLS:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    tool_info = MCP_TOOLS[tool_name]
    input_model = tool_info["input_model"]
    tool_func = tool_info["func"]
    
    # Validate and create input model
    try:
        validated_input = input_model(**arguments)
    except Exception as e:
        raise ValueError(f"Invalid arguments for {tool_name}: {str(e)}")
    
    # Execute the tool
    result = await tool_func(validated_input)
    return result

@app.route('/')
def index():
    """Root endpoint with basic information."""
    return jsonify({
        "name": "Azure Pricing MCP Server",
        "version": "1.0.0",
        "description": "Model Context Protocol server for Azure retail pricing information",
        "endpoints": {
            "health": "/health",
            "tools": "/tools",
            "docs": "/docs"
        },
        "available_tools": list(MCP_TOOLS.keys())
    })

@app.route('/health')
def health():
    """Health check endpoint for Azure App Service."""
    try:
        # Test a simple tool execution to ensure everything is working
        asyncio.run(execute_mcp_tool("azure_get_service_families", {"limit": 1}))
        return jsonify({"status": "healthy", "mcp_tools": "operational"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 503

@app.route('/docs')
def docs():
    """Documentation endpoint."""
    tools_info = []
    for tool_name, tool_data in MCP_TOOLS.items():
        tools_info.append({
            "name": tool_name,
            "description": tool_data["description"]
        })
    
    return jsonify({
        "title": "Azure Pricing MCP Server API",
        "description": "This server provides Model Context Protocol tools for Azure pricing analysis",
        "tools": tools_info,
        "usage": {
            "endpoint": "/tools",
            "method": "POST",
            "format": {
                "tool_name": "string",
                "arguments": "object"
            }
        },
        "documentation": "https://github.com/matt-edwards-aztech/AzurePricingMCP"
    })

@app.route('/tools', methods=['POST'])
def execute_tool():
    """Execute an MCP tool with the provided arguments."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        tool_name = data.get('tool_name') or data.get('name')
        arguments = data.get('arguments', {})
        
        if not tool_name:
            return jsonify({"error": "tool_name is required"}), 400
        
        # Execute the tool
        result = asyncio.run(execute_mcp_tool(tool_name, arguments))
        
        return jsonify({
            "tool_name": tool_name,
            "result": result,
            "status": "success"
        })
        
    except ValueError as e:
        return jsonify({"error": str(e), "status": "validation_error"}), 400
    except Exception as e:
        return jsonify({"error": str(e), "status": "execution_error"}), 500

@app.route('/tools/<tool_name>', methods=['POST'])
def execute_specific_tool(tool_name):
    """Execute a specific MCP tool by name."""
    try:
        arguments = request.get_json() or {}
        
        # Execute the tool
        result = asyncio.run(execute_mcp_tool(tool_name, arguments))
        
        return jsonify({
            "tool_name": tool_name,
            "result": result,
            "status": "success"
        })
        
    except ValueError as e:
        return jsonify({"error": str(e), "status": "validation_error"}), 400
    except Exception as e:
        return jsonify({"error": str(e), "status": "execution_error"}), 500

if __name__ == "__main__":
    # Get port from environment variable (Azure App Service default)
    port = int(os.environ.get('PORT', 8000))
    
    # Run Flask app
    app.run(host='0.0.0.0', port=port, debug=False)