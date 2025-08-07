#!/usr/bin/env python3
"""
Script to synchronize inventory data with BOM data.
This will ensure that the inventory tab has the exact same parts as the BOM data.
"""

import sqlite3
import pandas as pd
from datetime import datetime

def sync_inventory_with_bom():
    """
    Synchronize inventory data with BOM data.
    This will create inventory records for all parts in the BOM.
    """
    
    # Connect to the database
    conn = sqlite3.connect('supplyxplorer.db')
    cursor = conn.cursor()
    
    try:
        # Get all parts from BOM
        print("Getting BOM parts...")
        bom_df = pd.read_sql_query('''
            SELECT DISTINCT 
                part_id, 
                part_name, 
                unit_cost,
                supplier_id,
                supplier_name,
                manufacturer
            FROM bom 
            ORDER BY part_name
        ''', conn)
        
        print(f"Found {len(bom_df)} unique parts in BOM")
        
        # Clear existing inventory data
        print("Clearing existing inventory data...")
        cursor.execute("DELETE FROM inventory")
        
        # Insert new inventory records for each BOM part
        print("Creating inventory records for BOM parts...")
        created_count = 0
        
        for _, row in bom_df.iterrows():
            # Set default inventory values
            current_stock = 0  # Default to 0 current stock
            minimum_stock = 10  # Default minimum stock
            maximum_stock = 100  # Default maximum stock
            unit_cost = row['unit_cost'] if pd.notna(row['unit_cost']) else 0.0
            total_value = current_stock * unit_cost
            
            # Use BOM supplier info if available
            supplier_id = row['supplier_id'] if pd.notna(row['supplier_id']) else None
            supplier_name = row['supplier_name'] if pd.notna(row['supplier_name']) else None
            
            # Default location and notes
            location = "Warehouse"
            notes = f"Auto-created from BOM data - {row['manufacturer']}" if pd.notna(row['manufacturer']) else "Auto-created from BOM data"
            
            # Insert inventory record
            cursor.execute('''
                INSERT INTO inventory (
                    part_id, part_name, current_stock, minimum_stock, maximum_stock,
                    unit_cost, total_value, supplier_id, supplier_name,
                    location, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['part_id'],
                row['part_name'], 
                current_stock,
                minimum_stock,
                maximum_stock,
                unit_cost,
                total_value,
                supplier_id,
                supplier_name,
                location,
                notes,
                datetime.utcnow(),
                datetime.utcnow()
            ))
            
            created_count += 1
        
        # Commit the changes
        conn.commit()
        
        print(f"Successfully created {created_count} inventory records")
        
        # Verify the results
        print("\nVerifying results...")
        inventory_count = cursor.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
        bom_count = cursor.execute("SELECT COUNT(DISTINCT part_id) FROM bom").fetchone()[0]
        
        print(f"Inventory records: {inventory_count}")
        print(f"Unique BOM parts: {bom_count}")
        
        if inventory_count == bom_count:
            print("✅ SUCCESS: Inventory and BOM parts are now synchronized!")
        else:
            print("⚠️  WARNING: Count mismatch between inventory and BOM parts")
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        conn.rollback()
        raise
    
    finally:
        conn.close()

if __name__ == "__main__":
    sync_inventory_with_bom()
