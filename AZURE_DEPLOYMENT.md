# Azure App Service Deployment Guide

Deploy your Azure Pricing MCP Server as a web application on Azure App Service.

## 🚀 Quick Deployment

### Option 1: Automated Script (Recommended)

```bash
# Make the script executable
chmod +x deploy/scripts/deploy.sh

# Deploy with default settings
./deploy/scripts/deploy.sh

# Or customize the deployment
./deploy/scripts/deploy.sh "my-resource-group" "my-app-name" "westus2"
```

### Option 2: Manual Azure CLI Deployment

```bash
# 1. Create resource group
az group create --name azure-pricing-mcp-rg --location eastus

# 2. Deploy infrastructure
az deployment group create \
  --resource-group azure-pricing-mcp-rg \
  --template-file deploy/bicep/main.bicep \
  --parameters appName=azure-pricing-mcp

# 3. Deploy application code
zip -r app.zip . -x "*.git*" "*__pycache__*" "*.pyc" "*venv*"
az webapp deployment source config-zip \
  --resource-group azure-pricing-mcp-rg \
  --name azure-pricing-mcp \
  --src app.zip
```

### Option 3: GitHub Actions CI/CD

1. **Set up GitHub Secrets:**
   - Go to your repository → Settings → Secrets and variables → Actions
   - Add `AZURE_WEBAPP_PUBLISH_PROFILE` (download from Azure Portal)

2. **Trigger Deployment:**
   - Push to `main` branch or manually trigger the workflow
   - Monitor progress in Actions tab

## 🏗️ Architecture

```
Internet → Azure App Service → Flask App (port 8000)
                             └─→ MCP Server (port 8001)
                                 └─→ Azure Pricing API
```

## 📋 Prerequisites

- **Azure CLI** installed and logged in
- **Azure subscription** with appropriate permissions
- **jq** installed (for deployment script)

```bash
# Install Azure CLI (Ubuntu/Debian)
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Install jq
sudo apt-get install jq

# Login to Azure
az login
```

## ⚙️ Configuration Options

### App Service Settings

| Setting | Value | Description |
|---------|-------|-------------|
| `WEBSITES_PORT` | `8000` | Port for Flask app |
| `PYTHON_ENABLE_GUNICORN_MULTIWORKERS` | `true` | Enable multiple workers |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` | Build during deployment |
| `AZURE_API_TIMEOUT` | `30` | API timeout in seconds |

### Resource Sizing

| Tier | SKU | vCPU | RAM | Use Case |
|------|-----|------|-----|----------|
| Free | F1 | Shared | 1GB | Development/Testing |
| Basic | B1 | 1 | 1.75GB | Light production |
| Basic | B2 | 2 | 3.5GB | Standard production |
| Standard | S1 | 1 | 1.75GB | Production with scaling |

## 🔒 Security Configuration

### HTTPS Only
```bash
az webapp update --resource-group azure-pricing-mcp-rg \
  --name azure-pricing-mcp --https-only true
```

### Custom Domain (Optional)
```bash
# Add custom domain
az webapp config hostname add \
  --resource-group azure-pricing-mcp-rg \
  --webapp-name azure-pricing-mcp \
  --hostname yourdomain.com

# Configure SSL
az webapp config ssl create \
  --resource-group azure-pricing-mcp-rg \
  --name azure-pricing-mcp \
  --hostname yourdomain.com
```

## 🧪 Testing Your Deployment

### Health Check
```bash
curl https://your-app-name.azurewebsites.net/health
```

Expected response:
```json
{
  "status": "healthy",
  "mcp_server": "running"
}
```

### API Documentation
```bash
curl https://your-app-name.azurewebsites.net/docs
```

### MCP Tool Test
```bash
# Test pricing tool via the Flask proxy
curl -X POST https://your-app-name.azurewebsites.net/api/tools \
  -H "Content-Type: application/json" \
  -d '{
    "name": "azure_get_service_prices",
    "arguments": {
      "service_name": "Virtual Machines",
      "limit": 5
    }
  }'
```

## 📊 Monitoring and Logs

### View Live Logs
```bash
az webapp log tail --name azure-pricing-mcp \
  --resource-group azure-pricing-mcp-rg
```

### Enable Application Insights
```bash
az monitor app-insights component create \
  --app azure-pricing-mcp-insights \
  --location eastus \
  --resource-group azure-pricing-mcp-rg

# Link to web app
az webapp config appsettings set \
  --resource-group azure-pricing-mcp-rg \
  --name azure-pricing-mcp \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY="your-key"
```

### Set up Alerts
```bash
az monitor metrics alert create \
  --name "High Response Time" \
  --resource-group azure-pricing-mcp-rg \
  --scopes "/subscriptions/{subscription}/resourceGroups/azure-pricing-mcp-rg/providers/Microsoft.Web/sites/azure-pricing-mcp" \
  --condition "avg http_response_time > 5" \
  --description "Alert when response time > 5 seconds"
```

## 🔄 Updates and Maintenance

### Update Application Code
```bash
# Using deployment script
./deploy/scripts/deploy.sh

# Or manually
zip -r app.zip . -x "*.git*" "*__pycache__*"
az webapp deployment source config-zip \
  --resource-group azure-pricing-mcp-rg \
  --name azure-pricing-mcp \
  --src app.zip
```

### Scale the Application
```bash
# Scale up (more CPU/memory)
az appservice plan update \
  --name azure-pricing-mcp-plan \
  --resource-group azure-pricing-mcp-rg \
  --sku B2

# Scale out (more instances)
az webapp scale \
  --resource-group azure-pricing-mcp-rg \
  --name azure-pricing-mcp \
  --instance-count 2
```

## 🌐 Client Configuration

### MCP Client Setup
Configure your MCP client to use the deployed server:

```json
{
  "mcpServers": {
    "azure-pricing": {
      "url": "https://your-app-name.azurewebsites.net",
      "transport": "http"
    }
  }
}
```

### Claude Desktop Configuration
```json
{
  "mcpServers": {
    "azure-pricing": {
      "command": "curl",
      "args": [
        "-X", "POST",
        "https://your-app-name.azurewebsites.net/api/tools",
        "-H", "Content-Type: application/json",
        "-d", "@-"
      ]
    }
  }
}
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Deployment Fails
```bash
# Check deployment logs
az webapp log deployment list --name azure-pricing-mcp --resource-group azure-pricing-mcp-rg

# Check build logs
az webapp log download --name azure-pricing-mcp --resource-group azure-pricing-mcp-rg
```

#### 2. App Won't Start
```bash
# Check application logs
az webapp log tail --name azure-pricing-mcp --resource-group azure-pricing-mcp-rg

# Check startup command
az webapp config show --name azure-pricing-mcp --resource-group azure-pricing-mcp-rg \
  --query "siteConfig.appCommandLine"
```

#### 3. Health Check Fails
- Verify port configuration (8000)
- Check if MCP server is starting on port 8001
- Review application logs for errors

#### 4. Slow Performance
- Upgrade to higher tier (B2, S1, etc.)
- Enable Application Insights for detailed metrics
- Consider caching for frequently requested data

### Debug Commands
```bash
# SSH into the container (if debugging needed)
az webapp ssh --name azure-pricing-mcp --resource-group azure-pricing-mcp-rg

# Download logs for offline analysis
az webapp log download --name azure-pricing-mcp --resource-group azure-pricing-mcp-rg

# Restart the application
az webapp restart --name azure-pricing-mcp --resource-group azure-pricing-mcp-rg
```

## 💰 Cost Optimization

### Estimated Monthly Costs
- **Free Tier (F1)**: $0 (limited hours)
- **Basic B1**: ~$13-15/month
- **Basic B2**: ~$26-30/month  
- **Standard S1**: ~$56-60/month

### Cost Saving Tips
1. **Use Free Tier** for development/testing
2. **Auto-scale** based on demand
3. **Stop during non-business hours** if appropriate
4. **Monitor usage** with cost alerts

## 📞 Support and Resources

- **Azure Documentation**: [App Service Python apps](https://docs.microsoft.com/en-us/azure/app-service/quickstart-python)
- **Azure CLI Reference**: [az webapp commands](https://docs.microsoft.com/en-us/cli/azure/webapp)
- **Application Logs**: Use `az webapp log tail` for real-time debugging
- **GitHub Repository**: [Azure Pricing MCP](https://github.com/matt-edwards-aztech/AzurePricingMCP)

For issues specific to this deployment, check the troubleshooting section above or review the application logs for detailed error information.