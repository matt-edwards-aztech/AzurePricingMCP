#!/bin/bash

# Azure App Service Deployment Script for Azure Pricing MCP Server
# Usage: ./deploy.sh [resource-group-name] [app-name] [location]

set -e

# Default values
RESOURCE_GROUP=${1:-"azure-pricing-mcp-rg"}
APP_NAME=${2:-"azure-pricing-mcp"}
LOCATION=${3:-"eastus"}
SUBSCRIPTION_ID=${4:-""}

echo "🚀 Deploying Azure Pricing MCP Server to Azure App Service"
echo "Resource Group: $RESOURCE_GROUP"
echo "App Name: $APP_NAME"
echo "Location: $LOCATION"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed. Please install it first."
    echo "   Visit: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
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

# Deploy Bicep template
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
    --query 'properties.outputs' \
    --output json)

WEB_APP_URL=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.webAppUrl.value')
WEB_APP_NAME=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.webAppName.value')

echo "✅ Azure resources deployed successfully!"
echo "   Web App Name: $WEB_APP_NAME"
echo "   Web App URL: $WEB_APP_URL"

# Deploy application code
echo "📤 Deploying application code..."
APP_ROOT="$(dirname "$0")/../.."

# Zip the application files
TEMP_ZIP="/tmp/azure-pricing-mcp.zip"
cd "$APP_ROOT"

echo "📦 Creating deployment package..."
zip -r "$TEMP_ZIP" . \
    -x "*.git*" \
    -x "*__pycache__*" \
    -x "*.pyc" \
    -x "*venv*" \
    -x "*.md" \
    -x "docs/*" \
    -x ".vscode/*" \
    -x ".idea/*"

echo "🚀 Deploying to Azure App Service..."
az webapp deployment source config-zip \
    --resource-group "$RESOURCE_GROUP" \
    --name "$WEB_APP_NAME" \
    --src "$TEMP_ZIP"

# Clean up
rm -f "$TEMP_ZIP"

# Configure startup command
echo "⚙️  Configuring startup command..."
az webapp config set \
    --resource-group "$RESOURCE_GROUP" \
    --name "$WEB_APP_NAME" \
    --startup-file "gunicorn --bind=0.0.0.0:8000 --timeout 600 app:app"

# Wait for deployment to complete
echo "⏳ Waiting for deployment to complete..."
sleep 30

# Test the deployment
echo "🧪 Testing deployment..."
HEALTH_URL="$WEB_APP_URL/health"

if curl -f -s "$HEALTH_URL" > /dev/null; then
    echo "✅ Deployment successful! Health check passed."
    echo ""
    echo "🌐 Your Azure Pricing MCP Server is now available at:"
    echo "   $WEB_APP_URL"
    echo ""
    echo "📋 Available endpoints:"
    echo "   • Health Check: $WEB_APP_URL/health"
    echo "   • API Documentation: $WEB_APP_URL/docs"
    echo "   • MCP Server: $WEB_APP_URL (port 8001 internally)"
    echo ""
    echo "🔧 Next steps:"
    echo "   1. Test the API endpoints"
    echo "   2. Configure your MCP client to use: $WEB_APP_URL"
    echo "   3. Monitor logs: az webapp log tail --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP"
else
    echo "❌ Deployment health check failed. Please check the logs:"
    echo "   az webapp log tail --name $WEB_APP_NAME --resource-group $RESOURCE_GROUP"
    exit 1
fi