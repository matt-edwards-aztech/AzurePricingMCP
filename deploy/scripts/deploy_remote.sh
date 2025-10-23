#!/bin/bash

# Azure App Service Deployment Script for Remote Azure Pricing MCP Server
# Usage: ./deploy_remote.sh [resource-group-name] [app-name] [location]

set -e

# Default values
RESOURCE_GROUP=${1:-"azure-pricing-mcp-remote-rg"}
APP_NAME=${2:-"azure-pricing-mcp-remote"}
LOCATION=${3:-"eastus"}
SUBSCRIPTION_ID=${4:-""}

echo "🚀 Deploying Remote Azure Pricing MCP Server to Azure App Service"
echo "Resource Group: $RESOURCE_GROUP"
echo "App Name: $APP_NAME"
echo "Location: $LOCATION"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed. Please install it first."
    exit 1
fi

# Check if logged in
if ! az account show &> /dev/null; then
    echo "🔐 Please log in to Azure..."
    az login
fi

# Set subscription if provided
if [ ! -z "$SUBSCRIPTION_ID" ]; then
    echo "🔄 Setting subscription to: $SUBSCRIPTION_ID"
    az account set --subscription "$SUBSCRIPTION_ID"
fi

# Create resource group if it doesn't exist
echo "📦 Creating resource group if it doesn't exist..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output table

# Deploy Bicep template for remote MCP
echo "🏗️  Deploying Azure resources using Bicep..."
BICEP_PATH="$(dirname "$0")/../bicep/main.bicep"

if [ ! -f "$BICEP_PATH" ]; then
    echo "❌ Bicep template not found at: $BICEP_PATH"
    exit 1
fi

DEPLOYMENT_OUTPUT=$(az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file "$BICEP_PATH" \
    --parameters appName="$APP_NAME" location="$LOCATION" \
    --output tsv \
    --query 'properties.outputs.webAppUrl.value')

WEB_APP_URL="$DEPLOYMENT_OUTPUT"
WEB_APP_NAME="$APP_NAME"

echo "✅ Azure resources deployed successfully!"
echo "   Web App Name: $WEB_APP_NAME"
echo "   Web App URL: $WEB_APP_URL"

# Deploy application code for remote MCP
echo "📤 Deploying remote MCP application code..."
APP_ROOT="$(dirname "$0")/../.."

# Create deployment package for remote MCP
TEMP_ZIP="/tmp/azure-pricing-mcp-remote.zip"
cd "$APP_ROOT"

echo "📦 Creating remote MCP deployment package..."
python3 -c "
import zipfile
import os

# Create a zip file with remote MCP files
with zipfile.ZipFile('$TEMP_ZIP', 'w') as zipf:
    # Add Python files for remote MCP
    for file in ['azure_pricing_mcp.py', 'azure_pricing_mcp_remote.py', 'app_remote.py', 'setup.py']:
        if os.path.exists(file):
            zipf.write(file)
    
    # Use remote requirements
    if os.path.exists('requirements_remote.txt'):
        zipf.write('requirements_remote.txt', 'requirements.txt')
    
    # Add other important files
    for file in ['.dockerignore']:
        if os.path.exists(file):
            zipf.write(file)

print('Remote MCP deployment package created')
"

echo "🚀 Deploying to Azure App Service..."
az webapp deploy \
    --resource-group "$RESOURCE_GROUP" \
    --name "$WEB_APP_NAME" \
    --src-path "$TEMP_ZIP" \
    --type zip

# Clean up
rm -f "$TEMP_ZIP"

# Configure startup command for remote MCP
echo "⚙️  Configuring startup command for remote MCP..."
az webapp config set \
    --resource-group "$RESOURCE_GROUP" \
    --name "$WEB_APP_NAME" \
    --startup-file "python app_remote.py"

# Configure app settings for WebSocket support
echo "🔧 Configuring WebSocket settings..."
az webapp config appsettings set \
    --resource-group "$RESOURCE_GROUP" \
    --name "$WEB_APP_NAME" \
    --settings \
        SCM_DO_BUILD_DURING_DEPLOYMENT=true \
        WEBSITES_PORT=8000 \
        WEBSITES_ENABLE_APP_SERVICE_STORAGE=false

# Wait for deployment to complete
echo "⏳ Waiting for deployment to complete..."
sleep 30

# Test the deployment
echo "🧪 Testing remote MCP deployment..."
HEALTH_URL="$WEB_APP_URL/health"
MCP_INFO_URL="$WEB_APP_URL/mcp-info"

if curl -f -s "$HEALTH_URL" > /dev/null; then
    echo "✅ Deployment successful! Health check passed."
    echo ""
    echo "🌐 Your Remote Azure Pricing MCP Server is now available at:"
    echo "   $WEB_APP_URL"
    echo ""
    echo "📋 Available endpoints:"
    echo "   • Health Check: $WEB_APP_URL/health"
    echo "   • MCP WebSocket: $WEB_APP_URL/mcp"
    echo "   • Setup Guide: $WEB_APP_URL/mcp-info"
    echo ""
    echo "🔧 Claude Desktop Configuration:"
    echo '   {
     "mcpServers": {
       "azure-pricing": {
         "command": "npx",
         "args": ["-y", "@modelcontextprotocol/client-websocket", "wss://'$(echo "$WEB_APP_URL" | sed 's|https://||')/mcp"]
       }
     }
   }'
    echo ""
    echo "📝 Next steps:"
    echo "   1. Add the configuration above to your Claude Desktop"
    echo "   2. Restart Claude Desktop"
    echo "   3. Test: 'Show me Azure service families'"
else
    echo "❌ Deployment health check failed. Please check the logs:"
    echo "   az webapp log tail --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP"
    exit 1
fi