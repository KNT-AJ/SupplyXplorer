#!/usr/bin/env python3
"""
Simple test script for SupplyXplorer
"""

import requests
import time
import json
from datetime import datetime, timedelta

API_BASE = "http://localhost:8000"

def test_api_health():
    """Test API health endpoint"""
    try:
        response = requests.get(f"{API_BASE}/")
        print(f"✅ API Health: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ API Health Error: {e}")
        return False

def test_sample_data_creation():
    """Test creating sample data"""
    try:
        # Create sample products
        products = [
            {"sku_id": "TEST-001", "name": "Test Product A", "description": "Test product"},
            {"sku_id": "TEST-002", "name": "Test Product B", "description": "Test product"},
        ]
        
        for product in products:
            response = requests.post(f"{API_BASE}/products", json=product)
            if response.status_code == 200:
                print(f"✅ Created product: {product['name']}")
            else:
                print(f"❌ Failed to create product: {product['name']}")
        
        # Create sample suppliers
        suppliers = [
            {"supplier_id": "SUPP-001", "name": "Test Supplier", "ap_terms_days": 30},
        ]
        
        for supplier in suppliers:
            response = requests.post(f"{API_BASE}/suppliers", json=supplier)
            if response.status_code == 200:
                print(f"✅ Created supplier: {supplier['name']}")
            else:
                print(f"❌ Failed to create supplier: {supplier['name']}")
        
        # Create sample parts
        parts = [
            {"part_id": "PART-001", "description": "Test Component", "supplier_id": "SUPP-001", "unit_cost": 10.00},
        ]
        
        for part in parts:
            response = requests.post(f"{API_BASE}/parts", json=part)
            if response.status_code == 200:
                print(f"✅ Created part: {part['description']}")
            else:
                print(f"❌ Failed to create part: {part['description']}")
        
        # Create sample BOM
        bom_items = [
            {"sku_id": "TEST-001", "part_id": "PART-001", "qty_per": 2.0},
        ]
        
        for bom_item in bom_items:
            response = requests.post(f"{API_BASE}/bom", json=bom_item)
            if response.status_code == 200:
                print(f"✅ Created BOM item: {bom_item['sku_id']} -> {bom_item['part_id']}")
            else:
                print(f"❌ Failed to create BOM item: {bom_item['sku_id']} -> {bom_item['part_id']}")
        
        # Create sample forecasts
        forecasts = [
            {"sku_id": "TEST-001", "period_start": "2024-01-01T00:00:00", "units": 100},
            {"sku_id": "TEST-001", "period_start": "2024-02-01T00:00:00", "units": 120},
        ]
        
        for forecast in forecasts:
            response = requests.post(f"{API_BASE}/forecast", json=forecast)
            if response.status_code == 200:
                print(f"✅ Created forecast: {forecast['sku_id']} - {forecast['units']} units")
            else:
                print(f"❌ Failed to create forecast: {forecast['sku_id']}")
        
        # Create sample lead times
        lead_times = [
            {"part_id": "PART-001", "days": 30},
        ]
        
        for lead_time in lead_times:
            response = requests.post(f"{API_BASE}/leadtime", json=lead_time)
            if response.status_code == 200:
                print(f"✅ Created lead time: {lead_time['part_id']} - {lead_time['days']} days")
            else:
                print(f"❌ Failed to create lead time: {lead_time['part_id']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Sample data creation error: {e}")
        return False

def test_planning_engine():
    """Test the planning engine"""
    try:
        start_date = datetime.now()
        end_date = start_date + timedelta(days=365)
        
        response = requests.post(
            f"{API_BASE}/plan/run",
            params={
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
        )
        
        if response.status_code == 200:
            results = response.json()
            print(f"✅ Planning engine completed successfully!")
            print(f"📊 Generated {len(results['order_schedules'])} orders")
            print(f"💰 Cash flow projections: {len(results['cash_flow_projection'])} periods")
            return True
        else:
            print(f"❌ Planning engine failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Planning engine error: {e}")
        return False

def test_metrics():
    """Test metrics endpoint"""
    try:
        start_date = datetime.now()
        end_date = start_date + timedelta(days=365)
        
        response = requests.get(
            f"{API_BASE}/metrics",
            params={
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
        )
        
        if response.status_code == 200:
            metrics = response.json()
            print("📊 Key Metrics:")
            print(f"  Orders next 30 days: {metrics['orders_next_30d']}")
            print(f"  Orders next 60 days: {metrics['orders_next_60d']}")
            print(f"  Cash out 90 days: ${metrics['cash_out_90d']:,.2f}")
            print(f"  Largest purchase: ${metrics['largest_purchase']:,.2f}")
            return True
        else:
            print(f"❌ Metrics failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Metrics error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing SupplyXplorer Implementation")
    print("=" * 50)
    
    # Test API health
    if not test_api_health():
        print("❌ API not available. Make sure the server is running.")
        return
    
    # Test sample data creation
    print("\n📝 Testing sample data creation...")
    if not test_sample_data_creation():
        print("❌ Sample data creation failed.")
        return
    
    # Test planning engine
    print("\n⚙️ Testing planning engine...")
    if not test_planning_engine():
        print("❌ Planning engine failed.")
        return
    
    # Test metrics
    print("\n📊 Testing metrics...")
    if not test_metrics():
        print("❌ Metrics failed.")
        return
    
    print("\n✅ All tests passed! SupplyXplorer is working correctly.")
    print("\n🌐 Access the application at:")
    print("  - API: http://localhost:8000")
    print("  - Dashboard: http://localhost:8050")
    print("  - API Docs: http://localhost:8000/docs")

if __name__ == "__main__":
    main() 