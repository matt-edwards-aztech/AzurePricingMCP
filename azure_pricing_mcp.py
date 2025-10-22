#!/usr/bin/env python3
"""
Azure Retail Prices MCP Server

This MCP server provides comprehensive tools for accessing Azure retail pricing information
through the Azure Retail Prices REST API. It enables cost analysis, price comparison across
regions, and savings plan calculations.

Key Features:
- Service price lookup with extensive filtering
- Multi-region price comparison 
- SKU-based pricing search
- Service family discovery
- Savings plan analysis
- Support for multiple currencies
- Comprehensive error handling and pagination
"""

import asyncio
import json
import logging
import urllib.parse
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, field_validator, ConfigDict

# Constants
CHARACTER_LIMIT = 25000
API_BASE_URL = "https://prices.azure.com/api/retail/prices"
API_VERSION = "2023-01-01-preview"
DEFAULT_LIMIT = 100
MAX_LIMIT = 1000

# Initialize the MCP server
mcp = FastMCP("azure_pricing_mcp")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResponseFormat(str, Enum):
    """Output format for tool responses."""
    MARKDOWN = "markdown"
    JSON = "json"


class CurrencyCode(str, Enum):
    """Supported currency codes for Azure pricing."""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CAD = "CAD"
    AUD = "AUD"
    INR = "INR"
    CNY = "CNY"
    BRL = "BRL"


class PriceType(str, Enum):
    """Azure pricing types."""
    CONSUMPTION = "Consumption"
    RESERVATION = "Reservation"
    DEV_TEST_CONSUMPTION = "DevTestConsumption"


class ServiceFamily(str, Enum):
    """Common Azure service families."""
    COMPUTE = "Compute"
    NETWORKING = "Networking"
    STORAGE = "Storage"
    DATABASES = "Databases"
    ANALYTICS = "Analytics"
    AI_ML = "AI + Machine Learning"
    CONTAINERS = "Containers"
    SECURITY = "Security"
    MANAGEMENT = "Management and Governance"
    DEVELOPER_TOOLS = "Developer Tools"


# Shared API Client
class AzurePricingClient:
    """Shared HTTP client for Azure Retail Prices API."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def make_request(
        self,
        params: Dict[str, Any],
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Make a request to the Azure Retail Prices API."""
        
        # Build query parameters
        query_params = {
            "api-version": API_VERSION,
            **params
        }
        
        # Add pagination if specified
        if limit:
            query_params["$top"] = min(limit, MAX_LIMIT)
        
        try:
            response = await self.client.get(API_BASE_URL, params=query_params)
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            error_msg = f"Azure API returned {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            raise ValueError(f"Failed to fetch pricing data: {error_msg}")
        except httpx.RequestError as e:
            error_msg = f"Network error connecting to Azure API: {str(e)}"
            logger.error(error_msg)
            raise ValueError(f"Network error: {error_msg}")
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON response from Azure API: {str(e)}"
            logger.error(error_msg)
            raise ValueError(f"Invalid response format: {error_msg}")


# Utility Functions
def format_currency(amount: float, currency: str) -> str:
    """Format currency amount with appropriate symbol."""
    symbols = {
        "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥",
        "CAD": "C$", "AUD": "A$", "INR": "₹", "CNY": "¥", "BRL": "R$"
    }
    symbol = symbols.get(currency, currency)
    
    if currency == "JPY":
        return f"{symbol}{amount:,.0f}"
    else:
        return f"{symbol}{amount:,.4f}"


def build_filter_string(filters: Dict[str, Any]) -> str:
    """Build OData filter string from filter dictionary."""
    filter_parts = []
    
    for key, value in filters.items():
        if value is not None:
            if isinstance(value, str):
                filter_parts.append(f"{key} eq '{value}'")
            elif isinstance(value, list):
                # Handle multiple values with 'or' operator
                or_parts = [f"{key} eq '{v}'" for v in value]
                filter_parts.append(f"({' or '.join(or_parts)})")
            else:
                filter_parts.append(f"{key} eq {value}")
    
    return " and ".join(filter_parts)


def format_pricing_response(
    data: Dict[str, Any],
    format_type: ResponseFormat,
    title: str = "Azure Pricing Information"
) -> str:
    """Format pricing data response based on requested format."""
    
    if format_type == ResponseFormat.JSON:
        return json.dumps(data, indent=2)
    
    # Markdown formatting
    items = data.get("Items", [])
    count = len(items)
    total = data.get("Count", count)
    
    response = [f"# {title}\n"]
    
    if "truncated" in data and data["truncated"]:
        response.append(f"⚠️ **{data['truncation_message']}**\n")
    
    response.append(f"**Results**: {count} items")
    if total > count:
        response.append(f" (showing {count} of {total} total)")
    response.append("\n")
    
    if not items:
        response.append("No pricing data found for the specified criteria.\n")
        return "".join(response)
    
    # Group by service name for better organization
    services = {}
    for item in items:
        service = item.get("serviceName", "Unknown Service")
        if service not in services:
            services[service] = []
        services[service].append(item)
    
    for service_name, service_items in services.items():
        response.append(f"## {service_name}\n")
        
        for item in service_items:
            response.append(f"### {item.get('skuName', 'Unknown SKU')}\n")
            response.append(f"- **Product**: {item.get('productName', 'N/A')}\n")
            response.append(f"- **Region**: {item.get('location', 'N/A')} ({item.get('armRegionName', 'N/A')})\n")
            response.append(f"- **Price**: {format_currency(item.get('retailPrice', 0), item.get('currencyCode', 'USD'))}")
            response.append(f" per {item.get('unitOfMeasure', 'unit')}\n")
            response.append(f"- **Type**: {item.get('type', 'N/A')}\n")
            
            if item.get("savingsPlan"):
                response.append(f"- **Savings Plans Available**:\n")
                for plan in item["savingsPlan"]:
                    savings_price = format_currency(plan.get('retailPrice', 0), item.get('currencyCode', 'USD'))
                    response.append(f"  - {plan.get('term', 'N/A')}: {savings_price} per {item.get('unitOfMeasure', 'unit')}\n")
            
            response.append(f"- **Meter ID**: `{item.get('meterId', 'N/A')}`\n")
            response.append(f"- **Effective Date**: {item.get('effectiveStartDate', 'N/A')}\n\n")
    
    return "".join(response)


def truncate_response(data: Dict[str, Any], char_limit: int) -> Dict[str, Any]:
    """Truncate response data if it exceeds character limit."""
    test_response = format_pricing_response(data, ResponseFormat.MARKDOWN)
    
    if len(test_response) <= char_limit:
        return data
    
    # Truncate items and add metadata
    items = data.get("Items", [])
    original_count = len(items)
    
    # Binary search to find optimal truncation point
    left, right = 1, original_count
    best_count = 1
    
    while left <= right:
        mid = (left + right) // 2
        test_data = {**data, "Items": items[:mid]}
        test_length = len(format_pricing_response(test_data, ResponseFormat.MARKDOWN))
        
        if test_length <= char_limit:
            best_count = mid
            left = mid + 1
        else:
            right = mid - 1
    
    truncated_data = {**data, "Items": items[:best_count]}
    truncated_data["truncated"] = True
    truncated_data["original_count"] = original_count
    truncated_data["truncated_count"] = best_count
    truncated_data["truncation_message"] = (
        f"Response truncated from {original_count} to {best_count} items. "
        f"Use pagination parameters or add more specific filters to see additional results."
    )
    
    return truncated_data


# Input Models
class ServicePricesInput(BaseModel):
    """Input model for getting Azure service prices."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')
    
    service_name: Optional[str] = Field(
        default=None,
        description="Azure service name to filter by (e.g., 'Virtual Machines', 'Storage', 'Azure SQL Database')",
        max_length=100
    )
    service_family: Optional[ServiceFamily] = Field(
        default=None,
        description="Service family to filter by (e.g., 'Compute', 'Storage', 'Networking')"
    )
    region: Optional[str] = Field(
        default=None,
        description="Azure region name to filter by (e.g., 'eastus', 'westeurope', 'uksouth')",
        max_length=50
    )
    sku_name: Optional[str] = Field(
        default=None,
        description="SKU name to filter by (e.g., 'Standard_D2s_v3', 'E4ds v5')",
        max_length=100
    )
    price_type: Optional[PriceType] = Field(
        default=None,
        description="Price type to filter by ('Consumption', 'Reservation', 'DevTestConsumption')"
    )
    currency: CurrencyCode = Field(
        default=CurrencyCode.USD,
        description="Currency code for pricing (default: USD)"
    )
    limit: int = Field(
        default=DEFAULT_LIMIT,
        description="Maximum number of results to return (1-1000)",
        ge=1,
        le=MAX_LIMIT
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
    )


class RegionComparisonInput(BaseModel):
    """Input model for comparing prices across Azure regions."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')
    
    service_name: str = Field(
        ...,
        description="Azure service name to compare (e.g., 'Virtual Machines', 'Storage')",
        min_length=1,
        max_length=100
    )
    sku_name: Optional[str] = Field(
        default=None,
        description="Specific SKU to compare (e.g., 'Standard_D2s_v3'). If not specified, compares all SKUs",
        max_length=100
    )
    regions: List[str] = Field(
        ...,
        description="List of Azure region names to compare (e.g., ['eastus', 'westeurope', 'uksouth'])",
        min_items=2,
        max_items=10
    )
    price_type: Optional[PriceType] = Field(
        default=PriceType.CONSUMPTION,
        description="Price type to compare ('Consumption', 'Reservation', 'DevTestConsumption')"
    )
    currency: CurrencyCode = Field(
        default=CurrencyCode.USD,
        description="Currency code for pricing (default: USD)"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
    )
    
    @field_validator('regions')
    @classmethod
    def validate_regions(cls, v: List[str]) -> List[str]:
        """Validate and normalize region names."""
        if not v:
            raise ValueError("At least 2 regions must be specified")
        return [region.lower().strip() for region in v]


class SKUSearchInput(BaseModel):
    """Input model for searching SKU pricing information."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')
    
    search_term: str = Field(
        ...,
        description="Search term for SKU names (e.g., 'D2s', 'Standard_', 'v3')",
        min_length=1,
        max_length=100
    )
    service_family: Optional[ServiceFamily] = Field(
        default=None,
        description="Filter by service family to narrow search"
    )
    region: Optional[str] = Field(
        default=None,
        description="Filter by specific region",
        max_length=50
    )
    include_savings_plans: bool = Field(
        default=True,
        description="Include savings plan pricing information in results"
    )
    currency: CurrencyCode = Field(
        default=CurrencyCode.USD,
        description="Currency code for pricing (default: USD)"
    )
    limit: int = Field(
        default=DEFAULT_LIMIT,
        description="Maximum number of results to return (1-1000)",
        ge=1,
        le=MAX_LIMIT
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
    )


class ServiceFamiliesInput(BaseModel):
    """Input model for listing Azure service families."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')
    
    limit: int = Field(
        default=DEFAULT_LIMIT,
        description="Maximum number of unique service families to return",
        ge=1,
        le=500
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
    )


class SavingsPlanInput(BaseModel):
    """Input model for calculating savings plan benefits."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra='forbid')
    
    service_name: str = Field(
        ...,
        description="Azure service name to analyze (e.g., 'Virtual Machines')",
        min_length=1,
        max_length=100
    )
    sku_name: Optional[str] = Field(
        default=None,
        description="Specific SKU to analyze (e.g., 'Standard_D2s_v3')",
        max_length=100
    )
    region: Optional[str] = Field(
        default=None,
        description="Azure region to analyze",
        max_length=50
    )
    currency: CurrencyCode = Field(
        default=CurrencyCode.USD,
        description="Currency code for pricing (default: USD)"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
    )


# Tool Implementations

@mcp.tool(
    name="azure_get_service_prices",
    annotations={
        "title": "Get Azure Service Prices",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def azure_get_service_prices(params: ServicePricesInput) -> str:
    """Get Azure retail prices for services with comprehensive filtering options.
    
    This tool retrieves current Azure retail pricing information with extensive filtering
    capabilities. It supports filtering by service name, service family, region, SKU,
    price type, and currency. Results include regular pricing and savings plan options
    when available.
    
    Args:
        params (ServicePricesInput): Filtering parameters including:
            - service_name (Optional[str]): Service to filter by
            - service_family (Optional[ServiceFamily]): Service family to filter by  
            - region (Optional[str]): Azure region to filter by
            - sku_name (Optional[str]): Specific SKU to filter by
            - price_type (Optional[PriceType]): Pricing type to filter by
            - currency (CurrencyCode): Currency for pricing display
            - limit (int): Maximum results to return
            - response_format (ResponseFormat): Output format preference
    
    Returns:
        str: JSON or Markdown formatted pricing information with:
            - Service details and SKU information
            - Regional pricing data
            - Savings plan options when available
            - Pagination metadata
    """
    
    async with AzurePricingClient() as client:
        # Build filter parameters
        filters = {}
        
        if params.service_name:
            filters["serviceName"] = params.service_name
        if params.service_family:
            filters["serviceFamily"] = params.service_family.value
        if params.region:
            filters["armRegionName"] = params.region
        if params.sku_name:
            filters["skuName"] = params.sku_name
        if params.price_type:
            filters["priceType"] = params.price_type.value
        
        # Build API parameters
        api_params = {}
        if params.currency != CurrencyCode.USD:
            api_params["currencyCode"] = f"'{params.currency.value}'"
        
        if filters:
            api_params["$filter"] = build_filter_string(filters)
        
        # Make API request
        data = await client.make_request(api_params, params.limit)
        
        # Check for truncation and format response
        if len(str(data)) > CHARACTER_LIMIT:
            data = truncate_response(data, CHARACTER_LIMIT)
        
        return format_pricing_response(
            data,
            params.response_format,
            title=f"Azure Service Prices ({params.currency.value})"
        )


@mcp.tool(
    name="azure_compare_region_prices",
    annotations={
        "title": "Compare Azure Prices Across Regions",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def azure_compare_region_prices(params: RegionComparisonInput) -> str:
    """Compare Azure service prices across multiple regions for cost optimization.
    
    This tool performs side-by-side price comparison of Azure services across different
    regions, helping identify the most cost-effective deployment locations. It shows
    price variations and potential savings by region.
    
    Args:
        params (RegionComparisonInput): Comparison parameters including:
            - service_name (str): Azure service to compare
            - sku_name (Optional[str]): Specific SKU to compare
            - regions (List[str]): List of regions to compare
            - price_type (Optional[PriceType]): Type of pricing to compare
            - currency (CurrencyCode): Currency for pricing display
            - response_format (ResponseFormat): Output format preference
    
    Returns:
        str: JSON or Markdown formatted comparison showing:
            - Per-region pricing breakdown
            - Price differences and percentage variations
            - Cheapest and most expensive regions
            - Cost optimization recommendations
    """
    
    async with AzurePricingClient() as client:
        region_data = {}
        
        # Fetch pricing data for each region
        for region in params.regions:
            filters = {
                "serviceName": params.service_name,
                "armRegionName": region
            }
            
            if params.sku_name:
                filters["skuName"] = params.sku_name
            if params.price_type:
                filters["priceType"] = params.price_type.value
            
            api_params = {
                "$filter": build_filter_string(filters)
            }
            
            if params.currency != CurrencyCode.USD:
                api_params["currencyCode"] = f"'{params.currency.value}'"
            
            try:
                data = await client.make_request(api_params, limit=100)
                region_data[region] = data.get("Items", [])
            except Exception as e:
                logger.warning(f"Failed to fetch data for region {region}: {e}")
                region_data[region] = []
        
        if params.response_format == ResponseFormat.JSON:
            return json.dumps(region_data, indent=2)
        
        # Markdown formatting with comparison analysis
        response = [f"# Azure Price Comparison: {params.service_name}\n"]
        response.append(f"**Currency**: {params.currency.value}\n")
        response.append(f"**Price Type**: {params.price_type.value if params.price_type else 'All'}\n")
        if params.sku_name:
            response.append(f"**SKU**: {params.sku_name}\n")
        response.append("\n")
        
        # Organize data by SKU for comparison
        sku_comparison = {}
        for region, items in region_data.items():
            for item in items:
                sku_name = item.get("skuName", "Unknown SKU")
                if sku_name not in sku_comparison:
                    sku_comparison[sku_name] = {}
                
                sku_comparison[sku_name][region] = {
                    "price": item.get("retailPrice", 0),
                    "location": item.get("location", region),
                    "unit": item.get("unitOfMeasure", "unit"),
                    "product": item.get("productName", "Unknown Product")
                }
        
        if not sku_comparison:
            response.append("❌ No pricing data found for the specified criteria.\n")
            return "".join(response)
        
        # Generate comparison for each SKU
        for sku_name, region_prices in sku_comparison.items():
            response.append(f"## {sku_name}\n")
            
            if region_prices:
                prices = [(region, data["price"]) for region, data in region_prices.items()]
                prices.sort(key=lambda x: x[1])
                
                cheapest_region, cheapest_price = prices[0]
                most_expensive_region, most_expensive_price = prices[-1]
                
                response.append("| Region | Location | Price | Difference from Cheapest |\n")
                response.append("|--------|----------|-------|-------------------------|\n")
                
                for region, price in prices:
                    data = region_prices[region]
                    location = data["location"]
                    unit = data["unit"]
                    price_str = format_currency(price, params.currency.value)
                    
                    if price == cheapest_price:
                        diff = "**CHEAPEST** 🏆"
                    else:
                        diff_amount = price - cheapest_price
                        diff_percent = ((price - cheapest_price) / cheapest_price) * 100
                        diff = f"+{format_currency(diff_amount, params.currency.value)} (+{diff_percent:.1f}%)"
                    
                    response.append(f"| {region} | {location} | {price_str}/{unit} | {diff} |\n")
                
                # Add savings summary
                if len(prices) > 1:
                    max_savings = most_expensive_price - cheapest_price
                    max_savings_percent = ((most_expensive_price - cheapest_price) / most_expensive_price) * 100
                    response.append(f"\n💰 **Maximum Savings**: {format_currency(max_savings, params.currency.value)} ")
                    response.append(f"({max_savings_percent:.1f}%) by choosing {cheapest_region} over {most_expensive_region}\n\n")
        
        return "".join(response)


@mcp.tool(
    name="azure_search_sku_prices",
    annotations={
        "title": "Search Azure SKU Pricing",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def azure_search_sku_prices(params: SKUSearchInput) -> str:
    """Search for Azure SKU pricing information using flexible search terms.
    
    This tool allows searching for Azure SKUs using partial matches and flexible search
    terms. It's useful for discovering available SKUs and their pricing when you don't
    know the exact SKU name.
    
    Args:
        params (SKUSearchInput): Search parameters including:
            - search_term (str): Partial SKU name or search term
            - service_family (Optional[ServiceFamily]): Filter by service family
            - region (Optional[str]): Filter by specific region
            - include_savings_plans (bool): Include savings plan pricing
            - currency (CurrencyCode): Currency for pricing display
            - limit (int): Maximum results to return
            - response_format (ResponseFormat): Output format preference
    
    Returns:
        str: JSON or Markdown formatted search results with:
            - Matching SKU details and pricing
            - Service and product information
            - Regional availability
            - Savings plan options when available
    """
    
    async with AzurePricingClient() as client:
        # Build filter for SKU search
        filters = {}
        
        if params.service_family:
            filters["serviceFamily"] = params.service_family.value
        if params.region:
            filters["armRegionName"] = params.region
        
        # Use 'contains' for flexible SKU search
        api_params = {}
        
        if filters:
            filter_str = build_filter_string(filters)
            sku_filter = f"contains(skuName, '{params.search_term}')"
            api_params["$filter"] = f"{filter_str} and {sku_filter}" if filter_str else sku_filter
        else:
            api_params["$filter"] = f"contains(skuName, '{params.search_term}')"
        
        if params.currency != CurrencyCode.USD:
            api_params["currencyCode"] = f"'{params.currency.value}'"
        
        # Make API request
        data = await client.make_request(api_params, params.limit)
        
        # Filter out results that don't have savings plans if requested
        if not params.include_savings_plans:
            items = data.get("Items", [])
            filtered_items = [item for item in items if not item.get("savingsPlan")]
            data["Items"] = filtered_items
        
        # Check for truncation and format response
        if len(str(data)) > CHARACTER_LIMIT:
            data = truncate_response(data, CHARACTER_LIMIT)
        
        return format_pricing_response(
            data,
            params.response_format,
            title=f"Azure SKU Search Results: '{params.search_term}'"
        )


@mcp.tool(
    name="azure_get_service_families",
    annotations={
        "title": "List Azure Service Families",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def azure_get_service_families(params: ServiceFamiliesInput) -> str:
    """List available Azure service families and their associated services.
    
    This tool provides an overview of Azure service families and the services within
    each family. It's useful for discovering available services and understanding
    Azure's service organization.
    
    Args:
        params (ServiceFamiliesInput): Parameters including:
            - limit (int): Maximum number of service families to return
            - response_format (ResponseFormat): Output format preference
    
    Returns:
        str: JSON or Markdown formatted list of:
            - Service family names
            - Services within each family
            - Example SKUs and pricing ranges
            - Service descriptions and use cases
    """
    
    async with AzurePricingClient() as client:
        # Fetch a sample of data to discover service families
        api_params = {"$top": params.limit * 10}  # Get more data to find families
        
        data = await client.make_request(api_params)
        items = data.get("Items", [])
        
        # Group by service family
        families = {}
        for item in items:
            family = item.get("serviceFamily", "Other")
            service = item.get("serviceName", "Unknown Service")
            
            if family not in families:
                families[family] = {
                    "services": set(),
                    "example_skus": [],
                    "price_range": {"min": float("inf"), "max": 0}
                }
            
            families[family]["services"].add(service)
            
            # Track example SKUs and price ranges
            price = item.get("retailPrice", 0)
            if price > 0:
                families[family]["price_range"]["min"] = min(families[family]["price_range"]["min"], price)
                families[family]["price_range"]["max"] = max(families[family]["price_range"]["max"], price)
                
                if len(families[family]["example_skus"]) < 3:
                    families[family]["example_skus"].append({
                        "sku": item.get("skuName", "Unknown"),
                        "service": service,
                        "price": price,
                        "currency": item.get("currencyCode", "USD"),
                        "unit": item.get("unitOfMeasure", "unit")
                    })
        
        if params.response_format == ResponseFormat.JSON:
            # Convert sets to lists for JSON serialization
            json_families = {}
            for family, data in families.items():
                json_families[family] = {
                    "services": list(data["services"]),
                    "example_skus": data["example_skus"],
                    "price_range": data["price_range"] if data["price_range"]["min"] != float("inf") else None
                }
            return json.dumps(json_families, indent=2)
        
        # Markdown formatting
        response = [f"# Azure Service Families\n"]
        response.append(f"**Total Families Found**: {len(families)}\n\n")
        
        # Sort families by name
        sorted_families = sorted(families.items())
        
        for family_name, family_data in sorted_families:
            response.append(f"## {family_name}\n")
            
            services = sorted(family_data["services"])
            response.append(f"**Services** ({len(services)}):\n")
            for service in services:
                response.append(f"- {service}\n")
            response.append("\n")
            
            if family_data["example_skus"]:
                response.append("**Example SKUs**:\n")
                for sku_info in family_data["example_skus"]:
                    price_str = format_currency(sku_info["price"], sku_info["currency"])
                    response.append(f"- **{sku_info['sku']}** ({sku_info['service']}): ")
                    response.append(f"{price_str}/{sku_info['unit']}\n")
                response.append("\n")
            
            if family_data["price_range"]["min"] != float("inf"):
                min_price = format_currency(family_data["price_range"]["min"], "USD")
                max_price = format_currency(family_data["price_range"]["max"], "USD")
                response.append(f"**Price Range**: {min_price} - {max_price}\n\n")
        
        return "".join(response)


@mcp.tool(
    name="azure_calculate_savings_plan",
    annotations={
        "title": "Calculate Azure Savings Plan Benefits",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def azure_calculate_savings_plan(params: SavingsPlanInput) -> str:
    """Calculate potential savings from Azure savings plans compared to pay-as-you-go pricing.
    
    This tool analyzes Azure savings plan benefits by comparing regular consumption
    pricing with available savings plan options. It calculates potential cost savings
    and ROI for different commitment terms.
    
    Args:
        params (SavingsPlanInput): Analysis parameters including:
            - service_name (str): Azure service to analyze
            - sku_name (Optional[str]): Specific SKU to analyze
            - region (Optional[str]): Azure region to analyze
            - currency (CurrencyCode): Currency for pricing display
            - response_format (ResponseFormat): Output format preference
    
    Returns:
        str: JSON or Markdown formatted savings analysis with:
            - Pay-as-you-go vs savings plan pricing
            - Potential savings amounts and percentages
            - Break-even analysis for different terms
            - Recommendations for optimal savings plans
    """
    
    async with AzurePricingClient() as client:
        # Build filter for savings plan eligible services
        filters = {"serviceName": params.service_name}
        
        if params.sku_name:
            filters["skuName"] = params.sku_name
        if params.region:
            filters["armRegionName"] = params.region
        
        api_params = {"$filter": build_filter_string(filters)}
        
        if params.currency != CurrencyCode.USD:
            api_params["currencyCode"] = f"'{params.currency.value}'"
        
        # Make API request
        data = await client.make_request(api_params, limit=200)
        items = data.get("Items", [])
        
        # Filter items that have savings plans
        savings_items = [item for item in items if item.get("savingsPlan")]
        
        if not savings_items:
            if params.response_format == ResponseFormat.JSON:
                return json.dumps({"error": "No savings plan eligible items found for the specified criteria"})
            else:
                return "❌ **No savings plan eligible items found** for the specified criteria.\n\nTry searching for different services or regions, or remove specific SKU filters."
        
        if params.response_format == ResponseFormat.JSON:
            return json.dumps({"items_with_savings_plans": savings_items}, indent=2)
        
        # Markdown formatting with savings analysis
        response = [f"# Azure Savings Plan Analysis: {params.service_name}\n"]
        response.append(f"**Currency**: {params.currency.value}\n")
        if params.sku_name:
            response.append(f"**SKU**: {params.sku_name}\n")
        if params.region:
            response.append(f"**Region**: {params.region}\n")
        response.append(f"**Items with Savings Plans**: {len(savings_items)}\n\n")
        
        total_savings = {"1_year": 0, "3_year": 0}
        total_regular_cost = 0
        
        for item in savings_items:
            regular_price = item.get("retailPrice", 0)
            sku_name = item.get("skuName", "Unknown SKU")
            unit = item.get("unitOfMeasure", "unit")
            region = item.get("location", "Unknown Region")
            
            response.append(f"## {sku_name}\n")
            response.append(f"**Region**: {region}\n")
            response.append(f"**Product**: {item.get('productName', 'N/A')}\n\n")
            
            # Regular pricing
            regular_price_str = format_currency(regular_price, params.currency.value)
            response.append(f"**Pay-as-you-go**: {regular_price_str}/{unit}\n\n")
            
            savings_plans = item.get("savingsPlan", [])
            if savings_plans:
                response.append("**Savings Plan Options**:\n\n")
                response.append("| Term | Price | Savings | Savings % |\n")
                response.append("|------|-------|---------|----------|\n")
                
                for plan in savings_plans:
                    plan_price = plan.get("retailPrice", 0)
                    term = plan.get("term", "Unknown")
                    
                    savings_amount = regular_price - plan_price
                    savings_percent = (savings_amount / regular_price * 100) if regular_price > 0 else 0
                    
                    plan_price_str = format_currency(plan_price, params.currency.value)
                    savings_str = format_currency(savings_amount, params.currency.value)
                    
                    response.append(f"| {term} | {plan_price_str}/{unit} | {savings_str} | {savings_percent:.1f}% |\n")
                    
                    # Accumulate totals for summary
                    total_regular_cost += regular_price
                    if "1 Year" in term:
                        total_savings["1_year"] += savings_amount
                    elif "3 Year" in term:
                        total_savings["3_year"] += savings_amount
                
                response.append("\n")
        
        # Add summary
        if total_regular_cost > 0:
            response.append("## 💰 Savings Summary\n\n")
            
            if total_savings["1_year"] > 0:
                savings_1y_str = format_currency(total_savings["1_year"], params.currency.value)
                savings_1y_percent = (total_savings["1_year"] / total_regular_cost * 100)
                response.append(f"**1-Year Plans**: Save {savings_1y_str} ({savings_1y_percent:.1f}%) compared to pay-as-you-go\n")
            
            if total_savings["3_year"] > 0:
                savings_3y_str = format_currency(total_savings["3_year"], params.currency.value)
                savings_3y_percent = (total_savings["3_year"] / total_regular_cost * 100)
                response.append(f"**3-Year Plans**: Save {savings_3y_str} ({savings_3y_percent:.1f}%) compared to pay-as-you-go\n")
            
            response.append("\n**💡 Recommendation**: ")
            if total_savings["3_year"] > total_savings["1_year"] * 1.5:
                response.append("Consider 3-year plans for maximum savings if you can commit long-term.")
            else:
                response.append("1-year plans offer good savings with more flexibility.")
        
        return "".join(response)


# Server entry point
def main():
    """Main entry point for the Azure Retail Prices MCP server."""
    import sys
    
    # Parse command line arguments for transport options
    transport = "stdio"  # Default transport
    port = 8000
    
    for i, arg in enumerate(sys.argv):
        if arg == "--transport" and i + 1 < len(sys.argv):
            transport = sys.argv[i + 1]
        elif arg == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])
        elif arg in ["--help", "-h"]:
            print("Azure Retail Prices MCP Server")
            print("Usage: python azure_pricing_mcp.py [--transport stdio|http|sse] [--port PORT]")
            print("\nAvailable Tools:")
            print("- azure_get_service_prices: Get Azure service prices with filtering")
            print("- azure_compare_region_prices: Compare prices across regions")
            print("- azure_search_sku_prices: Search for SKU pricing")
            print("- azure_get_service_families: List service families")
            print("- azure_calculate_savings_plan: Calculate savings plan benefits")
            print("\nTransports:")
            print("- stdio: Standard input/output (default, for CLI integration)")
            print("- http: HTTP server (for web service deployment)")
            print("- sse: Server-sent events (for real-time applications)")
            return
    
    # Run the MCP server with specified transport
    if transport == "stdio":
        mcp.run()
    elif transport == "http":
        mcp.run(transport="streamable_http", port=port)
    elif transport == "sse":
        mcp.run(transport="sse", port=port)
    else:
        print(f"Error: Unknown transport '{transport}'. Use stdio, http, or sse.")
        sys.exit(1)


if __name__ == "__main__":
    main()
