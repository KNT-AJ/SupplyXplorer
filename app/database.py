from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv
import sqlite3

load_dotenv()

# Database URL - use SQLite for development, PostgreSQL for production
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./partxplorer.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def run_schema_upgrades():
    """Lightweight schema upgrades for SQLite deployments without Alembic.
    Adds missing columns used by the application if they are not present.
    Safe to run on every startup.
    """
    if not DATABASE_URL.startswith("sqlite"):
        return
    db_path = DATABASE_URL.replace("sqlite:///", "")
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        # Helper to check missing columns
        def ensure_column(table: str, column: str, ddl: str):
            cur.execute(f"PRAGMA table_info({table})")
            cols = [row[1] for row in cur.fetchall()]
            if column not in cols:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
        # Ensure HTS code columns
        ensure_column('bom', 'hts_code', 'hts_code TEXT')
        ensure_column('inventory', 'hts_code', 'hts_code TEXT')
        # Ensure new BOM shipping-related columns
        ensure_column('bom', 'shipping_mode', 'shipping_mode TEXT')
        ensure_column('bom', 'unit_weight_kg', 'unit_weight_kg REAL')
        ensure_column('bom', 'unit_volume_cbm', 'unit_volume_cbm REAL')
        # Ensure pending orders new columns
        ensure_column('orders', 'estimated_delivery_date', 'estimated_delivery_date TEXT')
        ensure_column('orders', 'unit_cost', 'unit_cost REAL DEFAULT 0')
        ensure_column('orders', 'payment_date', 'payment_date TEXT')
        ensure_column('orders', 'status', 'status TEXT DEFAULT "pending"')
        ensure_column('orders', 'po_number', 'po_number TEXT')
        ensure_column('orders', 'notes', 'notes TEXT')
        conn.commit()
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass