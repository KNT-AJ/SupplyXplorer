#!/usr/bin/env python3
"""
Script to update forecast data with new column names and System SN auto-gen    # Show System SNs for August dates (matching user examples)
    print("\nSystem SNs for August dates (matching user examples):")
    
    # Group by year-month to show sequential numbering within month
    updated_df['year_month'] = pd.to_datetime(updated_df['Installation Date']).dt.strftime('%Y-%m')
    august_2025 = updated_df[updated_df['year_month'] == '2025-08']
    
    print("August 2025 entries (should be JT080001, JT080002, etc.):")
    for _, row in august_2025.head(10).iterrows():  # Show first 10
        print(f"  {row['System SN']} - {row['Installation Date']} - {row['quantity']} units")pdates:
- Column "sku_id" -> "System SN" 
- Column "date" -> "Installation Date"
- Auto-generate System SN following convention: JT[MM][DD][###]
"""

import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict
import os

def generate_system_sn(installation_date, sequence_counter):
    """
    Generate System SN based on installation date and sequence number.
    Format: [YearCode][MM][####] where #### is sequential within the month
    
    Args:
        installation_date: datetime object
        sequence_counter: dict to track sequence numbers per month
    
    Returns:
        str: Generated System SN
    """
    # Year code mapping
    year_codes = {
        2025: "JT", 2026: "JW", 2027: "JX", 2028: "JY", 2029: "JZ",
        2030: "KB", 2031: "KH", 2032: "KJ", 2033: "KK", 2034: "KS",
        2035: "KT", 2036: "KW", 2037: "KX", 2038: "KY", 2039: "KZ",
        2040: "SB", 2041: "SH", 2042: "SJ", 2043: "SK", 2044: "SS",
        2045: "ST", 2046: "SW", 2047: "SX", 2048: "SY", 2049: "SZ",
        2050: "TB", 2051: "TH", 2052: "TJ", 2053: "TK", 2054: "TS",
        2055: "TT", 2056: "TW", 2057: "TX", 2058: "TY", 2059: "TZ",
        2060: "WB", 2061: "WH", 2062: "WJ", 2063: "WK", 2064: "WS",
        2065: "WT", 2066: "WW", 2067: "WX", 2068: "WY", 2069: "WZ",
        2070: "XB", 2071: "XH", 2072: "XJ", 2073: "XK", 2074: "XS",
        2075: "XT", 2076: "XW", 2077: "XX", 2078: "XY", 2079: "XZ",
        2080: "YB", 2081: "YH"
    }
    
    # Get year code and month
    year = installation_date.year
    year_code = year_codes.get(year, "JT")  # Default to JT if year not found
    month = f"{installation_date.month:02d}"
    
    # Create month key for sequence tracking (year-month combination)
    month_key = f"{year}-{month}"
    
    # Increment sequence for this month
    sequence_counter[month_key] += 1
    sequence = f"{sequence_counter[month_key]:04d}"
    
    # Format: YearCode + MM + ####
    system_sn = f"{year_code}{month}{sequence}"
    
    return system_sn

def update_forecast_data():
    """Update the forecast sample data with new column names and System SN generation."""
    
    # Read the current forecast data
    input_file = "/Users/ajdavis/GitHub/SupplyXplorer/sample_data/forecast_sample.csv"
    
    print(f"Reading forecast data from: {input_file}")
    df = pd.read_csv(input_file)
    
    print(f"Original data shape: {df.shape}")
    print(f"Original columns: {list(df.columns)}")
    
    # Convert date column to datetime for processing
    df['date'] = pd.to_datetime(df['date'])
    
    # Sort by date to ensure consistent System SN generation
    df = df.sort_values('date').reset_index(drop=True)
    
    # Initialize sequence counter for each date
    sequence_counter = defaultdict(int)
    
    # Generate System SN for each row
    system_sns = []
    for _, row in df.iterrows():
        installation_date = row['date']
        system_sn = generate_system_sn(installation_date, sequence_counter)
        system_sns.append(system_sn)
    
    # Create new dataframe with updated column names and System SN
    updated_df = pd.DataFrame({
        'System SN': system_sns,
        'Installation Date': df['date'].dt.strftime('%m/%d/%y'),  # Match original date format
        'quantity': df['quantity']
    })
    
    print(f"Updated data shape: {updated_df.shape}")
    print(f"Updated columns: {list(updated_df.columns)}")
    
    # Show sample of generated System SNs
    print("\nSample of generated System SNs:")
    print(updated_df.head(10))
    
    # Show System SNs for August 6th and 19th as examples
    print("\nSystem SNs for August dates (matching user examples):")
    
    # Group by year-month to show sequential numbering within month
    df['year_month'] = pd.to_datetime(df['Installation Date']).dt.strftime('%Y-%m')
    august_2025 = df[df['year_month'] == '2025-08']
    
    print("August 2025 entries (should be JT080001, JT080002, etc.):")
    for _, row in august_2025.head(10).iterrows():  # Show first 10
        print(f"  {row['System SN']} - {row['Installation Date']} - {row['quantity']} units")
    
    # Save updated forecast data
    output_file = "/Users/ajdavis/GitHub/SupplyXplorer/sample_data/forecast_sample_updated.csv"
    updated_df.to_csv(output_file, index=False)
    print(f"\nUpdated forecast data saved to: {output_file}")
    
    # Create backup of original file
    backup_file = "/Users/ajdavis/GitHub/SupplyXplorer/sample_data/forecast_sample_backup.csv"
    if not os.path.exists(backup_file):
        df_original = pd.read_csv(input_file)
        df_original.to_csv(backup_file, index=False)
        print(f"Original file backed up to: {backup_file}")
    
    return updated_df

if __name__ == "__main__":
    updated_df = update_forecast_data()
    print(f"\nCompleted forecast data update!")
    print(f"Total records processed: {len(updated_df)}")
