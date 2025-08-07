#!/usr/bin/env python3
"""
Update inventory data from Bev_Parts-Inventory-2025-02-05 - Inventory.csv

This script:
1. Reads the current inventory from the database
2. Reads the Bev Parts inventory CSV file
3. Matches part names using fuzzy string matching
4. Updates current_stock (from Stocked Qty) and minimum_stock (from Target Quantity)
5. Sets current_stock to 0 for parts not found in the CSV
"""

import pandas as pd
import sqlite3
from datetime import datetime
import os
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_bev_parts_data(file_path):
    """Load and process the Bev Parts inventory data"""
    logger.info(f"Loading Bev Parts data from: {file_path}")
    
    # Read the CSV file
    df = pd.read_csv(file_path)
    
    # Display columns to understand the structure
    logger.info(f"Columns in CSV: {list(df.columns)}")
    
    # Clean and process the data
    df_clean = df.copy()
    
    # Extract relevant columns
    # Part_Name, Target Quantity, Stocked Qty.
    required_cols = ['Part_Name', 'Target Quantity', 'Stocked Qty.']
    
    # Check if required columns exist
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        logger.error(f"Missing required columns: {missing_cols}")
        return None
    
    # Remove rows where Part_Name is empty
    df_clean = df_clean.dropna(subset=['Part_Name'])
    df_clean = df_clean[df_clean['Part_Name'].str.strip() != '']
    
    # Fill NaN values in quantity columns with 0
    df_clean['Target Quantity'] = pd.to_numeric(df_clean['Target Quantity'], errors='coerce').fillna(0)
    df_clean['Stocked Qty.'] = pd.to_numeric(df_clean['Stocked Qty.'], errors='coerce').fillna(0)
    
    # Group by Part_Name and sum quantities (in case there are duplicates)
    bev_parts = df_clean.groupby('Part_Name').agg({
        'Target Quantity': 'sum',
        'Stocked Qty.': 'sum'
    }).reset_index()
    
    # Rename columns for consistency
    bev_parts = bev_parts.rename(columns={
        'Part_Name': 'part_name',
        'Target Quantity': 'minimum_stock',
        'Stocked Qty.': 'current_stock'
    })
    
    logger.info(f"Loaded {len(bev_parts)} unique parts from Bev Parts inventory")
    
    # Display sample of data
    logger.info("Sample of Bev Parts data:")
    logger.info(bev_parts.head().to_string())
    
    return bev_parts

def load_current_inventory(db_path):
    """Load current inventory from the database"""
    logger.info("Loading current inventory from database")
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Read current inventory
        current_inventory = pd.read_sql_query("""
            SELECT id, part_id, part_name, current_stock, minimum_stock, 
                   maximum_stock, unit_cost, supplier_name, location, notes
            FROM inventory
        """, conn)
        
        conn.close()
        
        logger.info(f"Loaded {len(current_inventory)} parts from current inventory")
        return current_inventory
        
    except Exception as e:
        logger.error(f"Error loading inventory from database: {e}")
        return None

def find_best_match(part_name, part_list, threshold=60):
    """Find the best fuzzy match for a part name"""
    if not part_list:
        return None, 0
    
    # Use fuzzywuzzy to find the best match
    match = process.extractOne(part_name, part_list, scorer=fuzz.token_sort_ratio)
    
    if match and match[1] >= threshold:
        return match[0], match[1]
    
    return None, 0

def update_inventory(db_path, current_inventory, bev_parts_data):
    """Update inventory with data from Bev Parts file"""
    logger.info("Starting inventory update process")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get list of part names from bev_parts for fuzzy matching
        bev_part_names = bev_parts_data['part_name'].tolist()
        
        updates_made = 0
        matches_found = 0
        no_matches = []
        
        # Process each part in current inventory
        for idx, row in current_inventory.iterrows():
            current_part_name = row['part_name']
            part_id = row['part_id']
            
            # Try to find a match in Bev Parts data
            best_match, score = find_best_match(current_part_name, bev_part_names, threshold=60)
            
            if best_match:
                matches_found += 1
                
                # Get the corresponding data from bev_parts
                bev_data = bev_parts_data[bev_parts_data['part_name'] == best_match].iloc[0]
                
                new_current_stock = int(bev_data['current_stock'])
                new_minimum_stock = int(bev_data['minimum_stock'])
                
                logger.info(f"Match found (score {score}): '{current_part_name}' -> '{best_match}'")
                logger.info(f"  Updating stock: {row['current_stock']} -> {new_current_stock}")
                logger.info(f"  Updating min stock: {row['minimum_stock']} -> {new_minimum_stock}")
                
                # Update the database
                cursor.execute("""
                    UPDATE inventory 
                    SET current_stock = ?, minimum_stock = ?, updated_at = ?
                    WHERE part_id = ?
                """, (new_current_stock, new_minimum_stock, datetime.utcnow(), part_id))
                
                updates_made += 1
                
            else:
                # No match found - set current stock to 0
                no_matches.append(current_part_name)
                
                logger.info(f"No match found for: '{current_part_name}' - setting stock to 0")
                
                # Update the database - set current stock to 0
                cursor.execute("""
                    UPDATE inventory 
                    SET current_stock = 0, updated_at = ?
                    WHERE part_id = ?
                """, (datetime.utcnow(), part_id))
                
                updates_made += 1
        
        # Commit changes
        conn.commit()
        conn.close()
        
        logger.info(f"\nInventory update completed!")
        logger.info(f"Total parts processed: {len(current_inventory)}")
        logger.info(f"Matches found: {matches_found}")
        logger.info(f"No matches (set to 0 stock): {len(no_matches)}")
        logger.info(f"Total updates made: {updates_made}")
        
        if no_matches:
            logger.info(f"\nParts with no matches (set to 0 stock):")
            for part in no_matches:
                logger.info(f"  - {part}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating inventory: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def main():
    """Main function to orchestrate the inventory update"""
    
    # File paths
    bev_parts_file = "/Users/ajdavis/GitHub/SupplyXplorer/sample_data/Bev_Parts-Inventory-2025-02-05 - Inventory.csv"
    db_path = "/Users/ajdavis/GitHub/SupplyXplorer/supplyxplorer.db"
    
    # Check if files exist
    if not os.path.exists(bev_parts_file):
        logger.error(f"Bev Parts file not found: {bev_parts_file}")
        return False
    
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        return False
    
    # Load data
    bev_parts_data = load_bev_parts_data(bev_parts_file)
    if bev_parts_data is None:
        logger.error("Failed to load Bev Parts data")
        return False
    
    current_inventory = load_current_inventory(db_path)
    if current_inventory is None:
        logger.error("Failed to load current inventory")
        return False
    
    # Perform update
    success = update_inventory(db_path, current_inventory, bev_parts_data)
    
    if success:
        logger.info("Inventory update completed successfully!")
    else:
        logger.error("Inventory update failed!")
    
    return success

if __name__ == "__main__":
    main()
