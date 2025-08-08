#!/usr/bin/env python3
"""
Migration script to add subject_to_tariffs column to BOM and Inventory tables
"""

import sqlite3
from datetime import datetime

def add_tariff_columns():
    """Add subject_to_tariffs column to BOM and Inventory tables"""
    
    # Connect to the database
    conn = sqlite3.connect('supplyxplorer.db')
    cursor = conn.cursor()
    
    try:
        print("Adding subject_to_tariffs column to BOM table...")
        # Add column to BOM table
        cursor.execute('''
            ALTER TABLE bom 
            ADD COLUMN subject_to_tariffs VARCHAR(3) DEFAULT 'No'
        ''')
        
        print("Adding subject_to_tariffs column to Inventory table...")
        # Add column to Inventory table
        cursor.execute('''
            ALTER TABLE inventory 
            ADD COLUMN subject_to_tariffs VARCHAR(3) DEFAULT 'No'
        ''')
        
        # Define international suppliers subject to tariffs
        international_suppliers = ['Sansun', 'Oak Stills', 'P&E', 'QILI']
        
        print("Updating BOM records for international suppliers...")
        # Update BOM records for international suppliers
        for supplier in international_suppliers:
            cursor.execute('''
                UPDATE bom 
                SET subject_to_tariffs = 'Yes' 
                WHERE supplier_name = ?
            ''', (supplier,))
            affected_rows = cursor.rowcount
            print(f"  Updated {affected_rows} BOM records for supplier: {supplier}")
        
        print("Updating Inventory records for international suppliers...")
        # Update Inventory records for international suppliers
        for supplier in international_suppliers:
            cursor.execute('''
                UPDATE inventory 
                SET subject_to_tariffs = 'Yes' 
                WHERE supplier_name = ?
            ''', (supplier,))
            affected_rows = cursor.rowcount
            print(f"  Updated {affected_rows} Inventory records for supplier: {supplier}")
        
        # Commit the changes
        conn.commit()
        
        print("\n✅ SUCCESS: Added subject_to_tariffs column and updated records")
        
        # Verify the results
        print("\nVerifying results...")
        
        # Check BOM table
        cursor.execute('''
            SELECT supplier_name, subject_to_tariffs, COUNT(*) as count
            FROM bom 
            WHERE subject_to_tariffs = 'Yes'
            GROUP BY supplier_name
        ''')
        bom_results = cursor.fetchall()
        print(f"BOM records with tariffs:")
        for row in bom_results:
            print(f"  {row[0]}: {row[2]} parts")
        
        # Check Inventory table
        cursor.execute('''
            SELECT supplier_name, subject_to_tariffs, COUNT(*) as count
            FROM inventory 
            WHERE subject_to_tariffs = 'Yes'
            GROUP BY supplier_name
        ''')
        inventory_results = cursor.fetchall()
        print(f"Inventory records with tariffs:")
        for row in inventory_results:
            print(f"  {row[0]}: {row[2]} parts")
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        conn.rollback()
        raise
    
    finally:
        conn.close()

if __name__ == "__main__":
    add_tariff_columns()
