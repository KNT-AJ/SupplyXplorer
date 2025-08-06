#!/usr/bin/env python3
"""
Script to load sample data for testing CSV export functionality
"""

import requests
import sys
import os

API_BASE = "http://localhost:8000"

def upload_file(file_path, endpoint):
    """Upload a CSV file to the specified endpoint"""
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'text/csv')}
            response = requests.post(f"{API_BASE}{endpoint}", files=files, timeout=30)
            
        if response.status_code == 200:
            result = response.json()
            print(f"✅ {os.path.basename(file_path)}: {result.get('message', 'Uploaded successfully')}")
            return True
        else:
            print(f"❌ {os.path.basename(file_path)}: HTTP {response.status_code}")
            if response.headers.get('content-type', '').startswith('application/json'):
                try:
                    error_detail = response.json().get('detail', 'Unknown error')
                    print(f"   Error: {error_detail}")
                except:
                    pass
            return False
            
    except Exception as e:
        print(f"❌ {os.path.basename(file_path)}: Error - {str(e)}")
        return False

def test_connection():
    """Test if the API is available"""
    try:
        response = requests.get(f"{API_BASE}/", timeout=5)
        return response.status_code == 200
    except:
        return False

def main():
    print("Loading Sample Data for CSV Export Testing")
    print("=" * 50)
    
    if not test_connection():
        print("❌ API server is not running at http://localhost:8000")
        print("Please start the backend server first:")
        print("  python main.py")
        sys.exit(1)
    
    print("✅ API server is running")
    print("\nUploading sample data files...")
    
    # Upload sample files
    sample_files = [
        ("sample_data/bom_sample_with_suppliers.csv", "/upload/bom"),
        ("sample_data/forecast_sample.csv", "/upload/forecast"),
        ("sample_data/inventory_sample.csv", "/upload/inventory")
    ]
    
    success_count = 0
    for file_path, endpoint in sample_files:
        if os.path.exists(file_path):
            if upload_file(file_path, endpoint):
                success_count += 1
        else:
            print(f"❌ {file_path}: File not found")
    
    print(f"\n📊 Successfully uploaded {success_count}/{len(sample_files)} files")
    
    if success_count > 0:
        print("\n✅ Sample data loaded! You can now test CSV exports.")
        print("Run: python test_export.py")
    else:
        print("\n❌ No data was loaded. CSV exports may return empty files.")

if __name__ == "__main__":
    main()
