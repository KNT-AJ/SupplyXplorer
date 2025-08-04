#!/usr/bin/env python3
"""
Simple test script to check if the SupplyXplorer backend is running
"""

import requests
import sys
import time

def test_backend():
    """Test if the backend server is running and responding"""
    base_url = "http://localhost:8000"
    
    print("Testing SupplyXplorer Backend...")
    print("=" * 40)
    
    try:
        # Test basic connectivity
        print("1. Testing basic connectivity...")
        response = requests.get(f"{base_url}/", timeout=5)
        
        if response.status_code == 200:
            print("✅ Backend is running and responding!")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Backend responded with status code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend server")
        print("   Make sure the backend is running with: python main.py")
        return False
    except requests.exceptions.Timeout:
        print("❌ Backend connection timed out")
        return False
    except Exception as e:
        print(f"❌ Error testing backend: {e}")
        return False
    
    # Test upload endpoints
    print("\n2. Testing upload endpoints...")
    
    # Test forecast upload endpoint
    try:
        response = requests.get(f"{base_url}/forecast", timeout=5)
        print("✅ Forecast endpoint is accessible")
    except Exception as e:
        print(f"❌ Forecast endpoint error: {e}")
    
    # Test BOM upload endpoint
    try:
        response = requests.get(f"{base_url}/bom", timeout=5)
        print("✅ BOM endpoint is accessible")
    except Exception as e:
        print(f"❌ BOM endpoint error: {e}")
    
    print("\n" + "=" * 40)
    print("✅ Backend is ready to use!")
    print("   Frontend should now be able to connect successfully.")
    return True

if __name__ == "__main__":
    success = test_backend()
    sys.exit(0 if success else 1) 