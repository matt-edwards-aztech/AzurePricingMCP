# Azure Retail Prices MCP Server - Deployment Guide

## 🚀 Quick Start

### 1. **Setup Environment**
```bash
# Create project directory
mkdir azure-pricing-mcp && cd azure-pricing-mcp

# Copy the server files
# (Copy all provided files to this directory)

# Install dependencies
pip install -r requirements.txt
```

### 2. **Test Basic Functionality**
```bash
# Test server compilation
python -m py_compile azure_pricing_mcp.py

# Test help command
python azure_pricing_mcp.py --help
```

### 3. **Deploy as HTTPS Server**

#### Option A: HTTP Transport
```bash
python azure_pricing_mcp.py --transport http --port 8000
```
Access at: `http://localhost:8000`

#### Option B: SSE Transport (Recommended for HTTPS)
```bash
python azure_pricing_mcp.py --transport sse --port 8000
```

### 4. **Production HTTPS Deployment**

#### Using nginx as HTTPS proxy:
```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Using systemd service:
```ini
[Unit]
Description=Azure Pricing MCP Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/azure-pricing-mcp
ExecStart=/usr/bin/python3 azure_pricing_mcp.py --transport sse --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 🔧 Configuration Options

### Environment Variables
```bash
# Optional: Set custom timeouts
export AZURE_API_TIMEOUT=30

# Optional: Set custom rate limits  
export AZURE_API_RATE_LIMIT=100
```

### MCP Client Configuration

#### Claude Desktop
```json
{
  "mcpServers": {
    "azure-pricing": {
      "command": "python",
      "args": ["/path/to/azure_pricing_mcp.py"]
    }
  }
}
```

#### Remote HTTPS Connection
```json
{
  "mcpServers": {
    "azure-pricing": {
      "url": "https://your-domain.com",
      "transport": "sse"
    }
  }
}
```

## 🛡️ Security Considerations

### 1. **Network Security**
- The Azure Retail Prices API is public and requires no authentication
- No sensitive data is stored or transmitted by the server
- All pricing data comes directly from Microsoft's public API

### 2. **Rate Limiting**
- Implement reverse proxy rate limiting for production
- Monitor API usage to avoid potential service limits
- Consider caching responses for frequently requested data

### 3. **HTTPS Deployment**
- Always use HTTPS in production environments
- Implement proper SSL certificate management
- Consider using Let's Encrypt for free SSL certificates

## 📊 Monitoring & Logging

### Basic Logging
The server includes built-in logging. To enable debug mode:
```python
# Add to the top of azure_pricing_mcp.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Production Monitoring
```bash
# Monitor server health
curl -f http://localhost:8000/health || echo "Server down"

# Monitor API response times
time curl -s "http://localhost:8000/tools" > /dev/null
```

## 🔄 Updates & Maintenance

### Updating Dependencies
```bash
pip install -r requirements.txt --upgrade
```

### Testing After Updates
```bash
python test_server.py
```

## 🐛 Troubleshooting

### Common Issues

#### 1. **403 Forbidden Errors**
- **Cause**: Network restrictions blocking `prices.azure.com`
- **Solution**: Configure firewall/proxy to allow Azure API access
- **Test**: `curl https://prices.azure.com/api/retail/prices?$top=1`

#### 2. **Import Errors**
- **Cause**: Missing dependencies
- **Solution**: `pip install -r requirements.txt`

#### 3. **Port Already in Use**
- **Cause**: Another service using the port
- **Solution**: Use different port or stop conflicting service
- **Check**: `lsof -i :8000`

#### 4. **Large Response Timeouts**
- **Cause**: Requesting too much data at once
- **Solution**: Use smaller `limit` parameters and pagination

### Network Configuration

If deploying in a restricted environment, ensure these domains are allowed:
- `prices.azure.com` (Azure Retail Prices API)

## 📈 Performance Optimization

### 1. **Caching**
Consider implementing Redis caching for frequently requested data:
```python
# Example caching implementation
import redis
cache = redis.Redis(host='localhost', port=6379, db=0)
```

### 2. **Connection Pooling**
The server uses httpx with connection pooling by default:
- Max keepalive connections: 5
- Max total connections: 10
- Request timeout: 30 seconds

### 3. **Response Optimization**
- Use `response_format: "json"` for programmatic access
- Apply specific filters to reduce response size
- Use pagination for large datasets

## 🎯 Best Practices

### 1. **Development**
```bash
# Run in development mode
python azure_pricing_mcp.py --transport stdio

# Use test script for validation
python test_server.py
```

### 2. **Staging**
```bash
# Run with HTTP transport for testing
python azure_pricing_mcp.py --transport http --port 8080
```

### 3. **Production**
```bash
# Run with SSE transport behind HTTPS proxy
python azure_pricing_mcp.py --transport sse --port 8000
```

## 📋 Checklist for Deployment

- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Server compiles without errors (`python -m py_compile azure_pricing_mcp.py`)
- [ ] Network access to `prices.azure.com` verified
- [ ] SSL certificates configured (for HTTPS)
- [ ] Firewall rules configured
- [ ] Monitoring and logging configured
- [ ] Backup and recovery procedures in place
- [ ] Documentation updated for your environment

## 🆘 Support

For issues specific to this MCP server implementation:
1. Check the troubleshooting section above
2. Verify network connectivity to Azure APIs
3. Test with the provided test script
4. Check server logs for detailed error messages

For Azure API-related issues:
- Consult [Azure Retail Prices API documentation](https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices)
- Check Azure status page for service outages