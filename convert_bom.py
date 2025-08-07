#!/usr/bin/env python3
"""
Convert the Excel BOM file to the correct CSV format for SupplyXplorer
"""

import pandas as pd
import os
import sys

def convert_excel_to_bom_csv(excel_file, output_csv):
    """Convert Excel BOM to the expected CSV format"""
    
    # Expected columns for SupplyXplorer BOM
    expected_columns = [
        'part_name',
        'supplier', 
        'manufacturer',
        'units_needed',
        'cost_per_unit',
        'cost_per_product',
        'beginning_inventory',
        'ap_term',
        'ap_month_lag_days',
        'manufacturing_days_lead',
        'shipping_days_lead'
    ]
    
    try:
        # Read the Excel file
        print(f"Reading Excel file: {excel_file}")
        
        # Try to read all sheets to see what's available
        excel_data = pd.ExcelFile(excel_file)
        print(f"Available sheets: {excel_data.sheet_names}")
        
        # Read the first sheet (or specify sheet name if needed)
        df = pd.read_excel(excel_file, sheet_name=0)
        
        print(f"Original columns: {list(df.columns)}")
        print(f"Original shape: {df.shape}")
        print("\nFirst few rows:")
        print(df.head())
        
        # Create a mapping of the data to expected format
        # This will need to be customized based on the actual Excel structure
        result_df = pd.DataFrame()
        
        # Based on the Excel structure, create specific mappings
        # Looking at the columns: ['Supplier', 'Column 1', 'MEDIAN of Unit Price ($)', 'MAX of Unit Mass (g)', etc.]
        
        # Filter out rows where both Supplier and Column 1 are empty/NaN
        df = df.dropna(subset=['Column 1'])
        df = df[df['Column 1'].str.strip() != '']
        
        # Fill forward the Supplier column for grouped data
        df['Supplier'] = df['Supplier'].fillna(method='ffill')
        
        # Create the mapping based on the specific Excel structure
        result_df['part_name'] = df['Column 1']  # Part names are in Column 1
        result_df['supplier'] = df['Supplier'].fillna('Unknown Supplier')
        result_df['manufacturer'] = df['Supplier'].fillna('Unknown Manufacturer')  # Use supplier as manufacturer for now
        
        # Extract quantity from various "SUM of X Pack" columns - find the first non-zero value
        quantity_columns = [col for col in df.columns if 'SUM of' in col and 'Pack' in col and not col.endswith('.1')]
        units_needed = []
        
        for _, row in df.iterrows():
            qty = 1  # Default quantity
            for qty_col in quantity_columns:
                if pd.notna(row[qty_col]) and row[qty_col] > 0:
                    # Convert to int and take the reasonable value
                    try:
                        potential_qty = int(float(row[qty_col]))
                        if potential_qty > 0 and potential_qty < 1000:  # Reasonable range
                            qty = potential_qty
                            break
                    except:
                        continue
            units_needed.append(qty)
        
        result_df['units_needed'] = units_needed
        
        # Use the MEDIAN of Unit Price as cost_per_unit
        if 'MEDIAN of Unit Price ($)' in df.columns:
            result_df['cost_per_unit'] = df['MEDIAN of Unit Price ($)'].fillna(0.0)
        else:
            result_df['cost_per_unit'] = 0.0
            
        # Calculate cost_per_product
        result_df['cost_per_product'] = result_df['cost_per_unit'] * result_df['units_needed']
        
        # Set default values for other columns
        result_df['beginning_inventory'] = 0
        result_df['ap_term'] = 'Net 30'
        result_df['ap_month_lag_days'] = 30
        result_df['manufacturing_days_lead'] = 30
        result_df['shipping_days_lead'] = 15
        
        print(f"\nColumn mappings applied:")
        print(f"  part_name -> Column 1")
        print(f"  supplier -> Supplier")
        print(f"  manufacturer -> Supplier (same as supplier)")
        print(f"  cost_per_unit -> MEDIAN of Unit Price ($)")
        print(f"  units_needed -> Extracted from SUM of X Pack columns")
        
        # Clean up the data
        # Remove rows where part_name is empty
        result_df = result_df.dropna(subset=['part_name'])
        result_df = result_df[result_df['part_name'].str.strip() != '']
        
        # Format cost columns
        for cost_col in ['cost_per_unit', 'cost_per_product']:
            if cost_col in result_df.columns:
                # Remove any currency symbols and convert to float
                result_df[cost_col] = result_df[cost_col].astype(str).str.replace('$', '').str.replace(',', '')
                result_df[cost_col] = pd.to_numeric(result_df[cost_col], errors='coerce').fillna(0.0)
                # Format as currency string
                result_df[cost_col] = result_df[cost_col].apply(lambda x: f"${x:.2f}")
        
        # Ensure numeric columns are proper
        numeric_cols = ['units_needed', 'beginning_inventory', 'ap_month_lag_days', 'manufacturing_days_lead', 'shipping_days_lead']
        for col in numeric_cols:
            if col in result_df.columns:
                result_df[col] = pd.to_numeric(result_df[col], errors='coerce').fillna(0).astype(int)
        
        print(f"\nConverted data shape: {result_df.shape}")
        print("\nFirst few rows of converted data:")
        print(result_df.head())
        
        # Save to CSV
        result_df.to_csv(output_csv, index=False)
        print(f"\n✅ Successfully converted to: {output_csv}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error converting file: {str(e)}")
        return False

def main():
    excel_file = "sample_data/bom20250806.xlsx"
    output_csv = "sample_data/bom_current.csv"
    
    if not os.path.exists(excel_file):
        print(f"❌ Excel file not found: {excel_file}")
        sys.exit(1)
    
    print("Converting BOM Excel file to CSV format")
    print("=" * 50)
    
    if convert_excel_to_bom_csv(excel_file, output_csv):
        print(f"\n🎉 Conversion complete!")
        print(f"New BOM file created: {output_csv}")
        print("\nTo make this the default BOM, the load_sample_data.py will be updated.")
    else:
        print("\n❌ Conversion failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
