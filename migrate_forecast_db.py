#!/usr/bin/env python3
"""
Database migration script to update forecast table column names.
Changes:
- sku_id -> system_sn
- period_start -> installation_date
"""

import sqlite3
import pandas as pd
from datetime import datetime
import os

def migrate_forecast_table():
    """Migrate the forecast table to use new column names."""
    
    db_path = "/Users/ajdavis/GitHub/SupplyXplorer/supplyxplorer.db"
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return
    
    # Create backup of database
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if old columns exist
        cursor.execute("PRAGMA table_info(forecasts)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"Current forecast table columns: {columns}")
        
        if 'sku_id' in columns and 'period_start' in columns:
            print("Migrating forecast table from old to new column names...")
            
            # Create backup
            print(f"Creating backup at: {backup_path}")
            import shutil
            shutil.copy2(db_path, backup_path)
            
            # Create new table with updated schema
            cursor.execute("""
                CREATE TABLE forecasts_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    system_sn VARCHAR(50) NOT NULL,
                    installation_date DATETIME NOT NULL,
                    units INTEGER NOT NULL,
                    created_at DATETIME,
                    updated_at DATETIME
                )
            """)
            
            # Copy data from old table to new table
            cursor.execute("""
                INSERT INTO forecasts_new (id, system_sn, installation_date, units, created_at, updated_at)
                SELECT id, sku_id, period_start, units, created_at, updated_at
                FROM forecasts
            """)
            
            # Drop old table and rename new table
            cursor.execute("DROP TABLE forecasts")
            cursor.execute("ALTER TABLE forecasts_new RENAME TO forecasts")
            
            print("Migration completed successfully!")
            
        elif 'system_sn' in columns and 'installation_date' in columns:
            print("Database already uses new column names. No migration needed.")
            
        else:
            print("Unexpected column schema. Manual intervention may be required.")
            print(f"Found columns: {columns}")
        
        # Commit changes
        conn.commit()
        
    except Exception as e:
        print(f"Error during migration: {e}")
        if 'conn' in locals():
            conn.rollback()
        
        # Restore from backup if it exists
        if os.path.exists(backup_path):
            print(f"Restoring from backup: {backup_path}")
            import shutil
            shutil.copy2(backup_path, db_path)
            
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    migrate_forecast_table()
