#!/usr/bin/env python3
"""
Test script for Azure Retail Prices MCP Server

This script demonstrates how to use the Azure pricing MCP server to:
1. Get virtual machine prices
2. Compare regional pricing
3. Search for specific SKUs
4. Calculate savings plan benefits

Run this script to test the MCP server functionality.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the current directory to the Python path so we can import our server
sys.path.insert(0, str(Path(__file__).parent))

# Import the MCP server components
from azure_pricing_mcp import (
    AzurePricingClient,
    ServicePricesInput,
    RegionComparisonInput,
    SKUSearchInput,
    SavingsPlanInput,
    ResponseFormat,
    CurrencyCode,
    ServiceFamily,
    PriceType
)


async def test_service_prices():
    """Test getting service prices for Virtual Machines."""
    print("🔍 Testing Service Prices...")
    
    async with AzurePricingClient() as client:
        # Test the actual API call
        api_params = {
            "$filter": "serviceName eq 'Virtual Machines' and armRegionName eq 'eastus'",
            "$top": 5
        }
        
        try:
            data = await client.make_request(api_params)
            items = data.get("Items", [])
            print(f"✅ Successfully fetched {len(items)} VM pricing items")
            
            if items:
                sample_item = items[0]
                print(f"   Sample: {sample_item.get('skuName')} - ${sample_item.get('retailPrice')}/hour")
        except Exception as e:
            print(f"❌ Error fetching VM prices: {e}")


async def test_storage_prices():
    """Test getting storage service prices."""
    print("\n💾 Testing Storage Prices...")
    
    async with AzurePricingClient() as client:
        api_params = {
            "$filter": "serviceFamily eq 'Storage'",
            "$top": 5
        }
        
        try:
            data = await client.make_request(api_params)
            items = data.get("Items", [])
            print(f"✅ Successfully fetched {len(items)} storage pricing items")
            
            if items:
                sample_item = items[0]
                service = sample_item.get('serviceName', 'Unknown')
                price = sample_item.get('retailPrice', 0)
                unit = sample_item.get('unitOfMeasure', 'unit')
                print(f"   Sample: {service} - ${price}/{unit}")
        except Exception as e:
            print(f"❌ Error fetching storage prices: {e}")


async def test_regional_comparison():
    """Test comparing prices across regions."""
    print("\n🌍 Testing Regional Price Comparison...")
    
    async with AzurePricingClient() as client:
        regions = ['eastus', 'westeurope']
        service_name = 'Virtual Machines'
        
        print(f"   Comparing {service_name} prices between {', '.join(regions)}")
        
        region_data = {}
        
        for region in regions:
            api_params = {
                "$filter": f"serviceName eq '{service_name}' and armRegionName eq '{region}'",
                "$top": 3
            }
            
            try:
                data = await client.make_request(api_params)
                items = data.get("Items", [])
                region_data[region] = len(items)
                print(f"   {region}: Found {len(items)} pricing items")
            except Exception as e:
                print(f"   ❌ Error for region {region}: {e}")
                region_data[region] = 0
        
        total_items = sum(region_data.values())
        if total_items > 0:
            print(f"✅ Regional comparison successful - {total_items} total items found")
        else:
            print("❌ No regional pricing data found")


async def test_sku_search():
    """Test searching for specific SKU patterns."""
    print("\n🔎 Testing SKU Search...")
    
    async with AzurePricingClient() as client:
        search_term = "Standard_D"
        
        api_params = {
            "$filter": f"contains(skuName, '{search_term}')",
            "$top": 5
        }
        
        try:
            data = await client.make_request(api_params)
            items = data.get("Items", [])
            print(f"✅ SKU search for '{search_term}' found {len(items)} items")
            
            if items:
                unique_skus = set(item.get('skuName') for item in items)
                print(f"   Found SKUs: {', '.join(list(unique_skus)[:3])}{'...' if len(unique_skus) > 3 else ''}")
        except Exception as e:
            print(f"❌ Error in SKU search: {e}")


async def test_savings_plans():
    """Test finding items with savings plans."""
    print("\n💰 Testing Savings Plans...")
    
    async with AzurePricingClient() as client:
        api_params = {
            "$filter": "serviceName eq 'Virtual Machines'",
            "$top": 20
        }
        
        try:
            data = await client.make_request(api_params)
            items = data.get("Items", [])
            savings_items = [item for item in items if item.get("savingsPlan")]
            
            print(f"✅ Found {len(savings_items)} items with savings plans out of {len(items)} total")
            
            if savings_items:
                sample_item = savings_items[0]
                sku = sample_item.get('skuName', 'Unknown')
                regular_price = sample_item.get('retailPrice', 0)
                plans = sample_item.get('savingsPlan', [])
                
                print(f"   Sample: {sku} - Regular: ${regular_price}/hour")
                for plan in plans[:2]:  # Show first 2 plans
                    plan_price = plan.get('retailPrice', 0)
                    term = plan.get('term', 'Unknown')
                    savings = regular_price - plan_price
                    print(f"           {term}: ${plan_price}/hour (Save ${savings:.4f})")
        except Exception as e:
            print(f"❌ Error finding savings plans: {e}")


async def test_currency_support():
    """Test different currency support."""
    print("\n💱 Testing Currency Support...")
    
    async with AzurePricingClient() as client:
        currencies = ['USD', 'EUR', 'GBP']
        
        for currency in currencies:
            api_params = {
                "currencyCode": f"'{currency}'",
                "$filter": "serviceName eq 'Virtual Machines'",
                "$top": 2
            }
            
            try:
                data = await client.make_request(api_params)
                items = data.get("Items", [])
                if items:
                    sample_price = items[0].get('retailPrice', 0)
                    currency_code = items[0].get('currencyCode', currency)
                    print(f"   {currency}: ✅ Sample price {sample_price} {currency_code}")
                else:
                    print(f"   {currency}: ❌ No pricing data")
            except Exception as e:
                print(f"   {currency}: ❌ Error - {e}")


async def test_api_connectivity():
    """Test basic API connectivity and response structure."""
    print("🔗 Testing API Connectivity...")
    
    async with AzurePricingClient() as client:
        # Test basic API call
        api_params = {"$top": 1}
        
        try:
            data = await client.make_request(api_params)
            
            # Check response structure
            required_fields = ["Items", "BillingCurrency", "CustomerEntityId", "CustomerEntityType"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if not missing_fields:
                print("✅ API connectivity successful - response structure valid")
                print(f"   Billing Currency: {data.get('BillingCurrency')}")
                print(f"   Customer Type: {data.get('CustomerEntityType')}")
                
                items = data.get("Items", [])
                if items:
                    sample = items[0]
                    print(f"   Sample item has {len(sample)} fields")
                    
                    # Check for important pricing fields
                    key_fields = ["retailPrice", "serviceName", "skuName", "armRegionName"]
                    present_fields = [field for field in key_fields if field in sample]
                    print(f"   Key fields present: {', '.join(present_fields)}")
            else:
                print(f"❌ Response missing fields: {', '.join(missing_fields)}")
                
        except Exception as e:
            print(f"❌ API connectivity failed: {e}")


async def main():
    """Run all tests."""
    print("🚀 Azure Retail Prices MCP Server Test Suite")
    print("=" * 50)
    
    tests = [
        test_api_connectivity,
        test_service_prices,
        test_storage_prices,
        test_regional_comparison,
        test_sku_search,
        test_savings_plans,
        test_currency_support
    ]
    
    for test in tests:
        try:
            await test()
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
        
        await asyncio.sleep(0.5)  # Small delay between tests
    
    print("\n" + "=" * 50)
    print("✅ Test suite completed!")
    print("\nℹ️  If all tests passed, your MCP server is ready to use!")
    print("ℹ️  You can now integrate it with Claude Desktop or other MCP clients.")


if __name__ == "__main__":
    asyncio.run(main())
