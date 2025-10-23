#!/usr/bin/env python3
"""
Entry point for Azure App Service deployment of Remote MCP Server
"""

from azure_pricing_mcp_remote import app

if __name__ == "__main__":
    import uvicorn
    import os
    
    port = int(os.environ.get('PORT', 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)