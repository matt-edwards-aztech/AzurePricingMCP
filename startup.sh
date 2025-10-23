#!/bin/bash

# Startup script for Azure App Service
echo "Starting Azure Pricing Remote MCP Server..."

# Set Python path
export PYTHONPATH=/home/site/wwwroot:$PYTHONPATH

# Navigate to the app directory
cd /home/site/wwwroot

# Start the application
python -m uvicorn azure_pricing_mcp_remote:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info