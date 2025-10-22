# Azure Retail Prices MCP Server

A comprehensive Model Context Protocol (MCP) server for accessing Azure retail pricing information through the Azure Retail Prices REST API. This server enables cost analysis, price comparison across regions, and savings plan calculations for Azure services.

## Features

### 🔧 **Available Tools**

1. **`azure_get_service_prices`** - Get Azure retail prices with comprehensive filtering
   - Filter by service name, service family, region, SKU, and price type
   - Support for multiple currencies
   - Includes savings plan pricing when available

2. **`azure_compare_region_prices`** - Compare prices across multiple Azure regions
   - Side-by-side price comparison for cost optimization
   - Identifies cheapest and most expensive regions
   - Calculates potential savings by region

3. **`azure_search_sku_prices`** - Search for SKU pricing using flexible terms
   - Partial SKU name matching
   - Service family filtering
   - Optional savings plan inclusion

4. **`azure_get_service_families`** - List available Azure service families
   - Discover available services and their organization
   - Example SKUs and pricing ranges
   - Service descriptions and use cases

5. **`azure_calculate_savings_plan`** - Calculate savings plan benefits
   - Compare pay-as-you-go vs savings plan pricing
   - ROI analysis for different commitment terms
   - Recommendations for optimal savings plans

### 🌍 **Supported Features**

- **Multiple Currencies**: USD, EUR, GBP, JPY, CAD, AUD, INR, CNY, BRL
- **Output Formats**: Markdown (human-readable) and JSON (machine-readable)
- **Pagination**: Efficient handling of large result sets
- **Error Handling**: Comprehensive error messages with guidance
- **Rate Limiting**: Respectful API usage with proper timeouts

## Installation

### Prerequisites

- Python 3.8+
- pip package manager

### Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Make the server executable:**
   ```bash
   chmod +x azure_pricing_mcp.py
   ```

## Usage

### Running the Server

#### Stdio Transport (Default)
```bash
python azure_pricing_mcp.py
```

#### HTTP Transport
```bash
python azure_pricing_mcp.py --transport http --port 8000
```

#### SSE Transport
```bash
python azure_pricing_mcp.py --transport sse --port 8000
```

### Transport Options

| Transport | Use Case | Communication |
|-----------|----------|---------------|
| **Stdio** | Local/CLI integration | Bidirectional via stdin/stdout |
| **HTTP** | Web services, multiple clients | Request-response over HTTP |
| **SSE** | Real-time updates | Server-sent events over HTTP |

## Tool Examples

### 1. Get Virtual Machine Prices

**Input:**
```json
{
  "service_name": "Virtual Machines",
  "service_family": "Compute",
  "region": "eastus",
  "currency": "USD",
  "limit": 10
}
```

**Usage:**
- Compare VM pricing across different SKUs
- Find the most cost-effective compute options
- Analyze pricing trends for capacity planning

### 2. Compare Regions for Storage

**Input:**
```json
{
  "service_name": "Storage",
  "regions": ["eastus", "westeurope", "uksouth", "australiaeast"],
  "currency": "USD"
}
```

**Usage:**
- Identify the most cost-effective storage regions
- Calculate data transfer cost implications
- Optimize multi-region deployment costs

### 3. Search for Database SKUs

**Input:**
```json
{
  "search_term": "SQL",
  "service_family": "Databases",
  "include_savings_plans": true,
  "currency": "EUR"
}
```

**Usage:**
- Discover available SQL database options
- Compare managed vs self-hosted costs
- Evaluate savings plan benefits for databases

### 4. Calculate Savings Plan Benefits

**Input:**
```json
{
  "service_name": "Virtual Machines",
  "sku_name": "Standard_D4s_v3",
  "region": "westus2",
  "currency": "USD"
}
```

**Usage:**
- Determine ROI for 1-year vs 3-year commitments
- Calculate break-even points for different usage patterns
- Optimize reservation purchasing decisions

## Integration Examples

### Claude Desktop Integration

Add to your Claude Desktop configuration:

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

### Programmatic Usage

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def get_vm_prices():
    server_params = StdioServerParameters(
        command="python",
        args=["azure_pricing_mcp.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            result = await session.call_tool(
                "azure_get_service_prices",
                {
                    "service_name": "Virtual Machines",
                    "region": "eastus",
                    "limit": 5
                }
            )
            print(result.content[0].text)

asyncio.run(get_vm_prices())
```

## Best Practices

### 1. **Efficient Filtering**
- Use specific service names and regions to reduce result sets
- Apply service family filters for targeted searches
- Combine multiple filters for precise results

### 2. **Pagination Management**
- Start with smaller limits (50-100) for initial exploration
- Use pagination for large datasets
- Monitor response sizes to avoid timeouts

### 3. **Currency Considerations**
- Use local currency for budget planning
- USD provides the most comprehensive data
- Consider exchange rate fluctuations for long-term planning

### 4. **Error Handling**
- Check for network connectivity issues
- Validate input parameters before API calls
- Implement retry logic for transient failures

## API Limitations

- **Rate Limiting**: No explicit limits documented, but respectful usage recommended
- **Data Freshness**: Pricing updated regularly by Microsoft
- **Region Coverage**: Covers all public Azure regions
- **Service Coverage**: All first-party Azure services included

## Troubleshooting

### Common Issues

1. **Network Timeouts**
   - Reduce the `limit` parameter
   - Check internet connectivity
   - Try simpler filters

2. **No Results Found**
   - Verify service names and regions are correct
   - Try broader search terms
   - Check if the service is available in the specified region

3. **Large Response Sizes**
   - Use more specific filters
   - Reduce the limit parameter
   - Use pagination for large datasets

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Follow PEP 8 style guidelines
2. Add comprehensive docstrings
3. Include error handling
4. Test with multiple Azure services
5. Update documentation

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool provides pricing information from Azure's public API. Prices are for reference only and may not reflect current contractual pricing. Always verify pricing through official Azure channels for billing purposes.
