from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import pandas as pd
from datetime import datetime, timedelta
import io

from app.database import get_db
from app.models import Product, Part, Supplier, BOM, Forecast, LeadTime, Inventory
from app.schemas import (
    ProductCreate, Product as ProductSchema,
    PartCreate, Part as PartSchema,
    SupplierCreate, Supplier as SupplierSchema,
    BOMCreate, BOM as BOMSchema,
    ForecastCreate, Forecast as ForecastSchema,
    LeadTimeCreate, LeadTime as LeadTimeSchema,
    InventoryCreate, Inventory as InventorySchema,
    OrderSchedule, CashFlowProjection, KeyMetrics, SupplierOrderSummary,
    ForecastUpload, BOMUpload, LeadTimeUpload, InventoryUpload
)
from app.planner import SupplyPlanner

app = FastAPI(
    title="SupplyXplorer API",
    description="Inventory & Cash-Flow Planning Tool",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/")
async def root():
    return {"message": "SupplyXplorer API is running"}

# Product endpoints
@app.post("/products", response_model=ProductSchema)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.get("/products", response_model=List[ProductSchema])
def get_products(db: Session = Depends(get_db)):
    return db.query(Product).all()

# Part endpoints
@app.post("/parts", response_model=PartSchema)
def create_part(part: PartCreate, db: Session = Depends(get_db)):
    db_part = Part(**part.dict())
    db.add(db_part)
    db.commit()
    db.refresh(db_part)
    return db_part

@app.get("/parts", response_model=List[PartSchema])
def get_parts(db: Session = Depends(get_db)):
    return db.query(Part).all()

# Supplier endpoints
@app.post("/suppliers", response_model=SupplierSchema)
def create_supplier(supplier: SupplierCreate, db: Session = Depends(get_db)):
    db_supplier = Supplier(**supplier.dict())
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier

@app.get("/suppliers", response_model=List[SupplierSchema])
def get_suppliers(db: Session = Depends(get_db)):
    return db.query(Supplier).all()

# BOM endpoints
@app.post("/bom", response_model=BOMSchema)
def create_bom(bom: BOMCreate, db: Session = Depends(get_db)):
    db_bom = BOM(**bom.dict())
    db.add(db_bom)
    db.commit()
    db.refresh(db_bom)
    return db_bom

@app.get("/bom", response_model=List[BOMSchema])
def get_bom(db: Session = Depends(get_db)):
    return db.query(BOM).all()

@app.put("/bom/bulk")
def bulk_update_bom(updates: List[dict], db: Session = Depends(get_db)):
    """Bulk update BOM records - replaces all data with provided records"""
    try:
        # Get IDs from the incoming data
        incoming_ids = set()
        for update in updates:
            record_id = update.get('id')
            if record_id:
                incoming_ids.add(record_id)
        
        # First, update existing records that are in the incoming data
        for update in updates:
            record_id = update.get('id')
            if record_id:
                # Get existing record
                existing_record = db.query(BOM).filter(BOM.id == record_id).first()
                if existing_record:
                    # Update only provided fields
                    for key, value in update.items():
                        if key != 'id' and hasattr(existing_record, key):
                            setattr(existing_record, key, value)
                    existing_record.updated_at = datetime.utcnow()
        
        # Delete records that are not in the incoming data
        all_existing_records = db.query(BOM).all()
        for record in all_existing_records:
            if record.id not in incoming_ids:
                db.delete(record)
        
        db.commit()
        deleted_count = len(all_existing_records) - len(incoming_ids)
        return {"message": f"Updated {len(updates)} BOM records, deleted {deleted_count} records"}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating BOM data: {str(e)}")

@app.put("/forecast/bulk")
def bulk_update_forecast(updates: List[dict], db: Session = Depends(get_db)):
    """Bulk update forecast records - replaces all data with provided records"""
    try:
        # Get IDs from the incoming data
        incoming_ids = set()
        for update in updates:
            record_id = update.get('id')
            if record_id:
                incoming_ids.add(record_id)
        
        # First, update existing records that are in the incoming data
        for update in updates:
            record_id = update.get('id')
            if record_id:
                # Get existing record
                existing_record = db.query(Forecast).filter(Forecast.id == record_id).first()
                if existing_record:
                    # Update only provided fields
                    for key, value in update.items():
                        if key != 'id' and hasattr(existing_record, key):
                            # Handle date conversion for period_start
                            if key == 'period_start' and isinstance(value, str):
                                try:
                                    value = datetime.strptime(value, '%Y-%m-%d').date()
                                except ValueError:
                                    continue  # Skip invalid date formats
                            setattr(existing_record, key, value)
                    existing_record.updated_at = datetime.utcnow()
        
        # Delete records that are not in the incoming data
        all_existing_records = db.query(Forecast).all()
        for record in all_existing_records:
            if record.id not in incoming_ids:
                db.delete(record)
        
        db.commit()
        deleted_count = len(all_existing_records) - len(incoming_ids)
        return {"message": f"Updated {len(updates)} forecast records, deleted {deleted_count} records"}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating forecast data: {str(e)}")

# Forecast endpoints
@app.post("/forecast", response_model=ForecastSchema)
def create_forecast(forecast: ForecastCreate, db: Session = Depends(get_db)):
    db_forecast = Forecast(**forecast.dict())
    db.add(db_forecast)
    db.commit()
    db.refresh(db_forecast)
    return db_forecast

@app.get("/forecast", response_model=List[ForecastSchema])
def get_forecasts(db: Session = Depends(get_db)):
    return db.query(Forecast).all()

# Lead time endpoints
@app.post("/leadtime", response_model=LeadTimeSchema)
def create_lead_time(lead_time: LeadTimeCreate, db: Session = Depends(get_db)):
    db_lead_time = LeadTime(**lead_time.dict())
    db.add(db_lead_time)
    db.commit()
    db.refresh(db_lead_time)
    return db_lead_time

@app.get("/leadtime", response_model=List[LeadTimeSchema])
def get_lead_times(db: Session = Depends(get_db)):
    return db.query(LeadTime).all()

# Inventory endpoints
@app.post("/inventory", response_model=InventorySchema)
def create_inventory(inventory: InventoryCreate, db: Session = Depends(get_db)):
    # Calculate total value
    inventory_data = inventory.dict()
    inventory_data['total_value'] = inventory_data['current_stock'] * inventory_data['unit_cost']
    
    db_inventory = Inventory(**inventory_data)
    db.add(db_inventory)
    db.commit()
    db.refresh(db_inventory)
    return db_inventory

@app.get("/inventory", response_model=List[InventorySchema])
def get_inventory(db: Session = Depends(get_db)):
    return db.query(Inventory).all()

@app.get("/inventory/{part_id}", response_model=InventorySchema)
def get_inventory_by_part(part_id: str, db: Session = Depends(get_db)):
    inventory = db.query(Inventory).filter(Inventory.part_id == part_id).first()
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
    return inventory

@app.put("/inventory/{part_id}", response_model=InventorySchema)
def update_inventory(part_id: str, inventory: InventoryCreate, db: Session = Depends(get_db)):
    db_inventory = db.query(Inventory).filter(Inventory.part_id == part_id).first()
    if not db_inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
    
    # Update fields
    for key, value in inventory.dict().items():
        setattr(db_inventory, key, value)
    
    # Recalculate total value
    db_inventory.total_value = db_inventory.current_stock * db_inventory.unit_cost
    db_inventory.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_inventory)
    return db_inventory

@app.delete("/inventory/{part_id}")
def delete_inventory(part_id: str, db: Session = Depends(get_db)):
    inventory = db.query(Inventory).filter(Inventory.part_id == part_id).first()
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
    
    db.delete(inventory)
    db.commit()
    return {"message": f"Inventory for part {part_id} deleted successfully"}

# Planning engine endpoints
@app.post("/plan/run")
def run_planning_engine(
    start_date: datetime,
    end_date: datetime,
    db: Session = Depends(get_db)
):
    """Run the planning engine and return results"""
    planner = SupplyPlanner(db)
    results = planner.run_planning_engine(start_date, end_date)
    return results

@app.get("/orders", response_model=List[OrderSchedule])
def get_order_schedule(
    start_date: datetime,
    end_date: datetime,
    db: Session = Depends(get_db)
):
    """Get order schedule for date range"""
    planner = SupplyPlanner(db)
    return planner.generate_order_schedule(start_date, end_date)

@app.get("/orders/by-supplier", response_model=List[SupplierOrderSummary])
def get_orders_by_supplier(
    start_date: datetime,
    end_date: datetime,
    db: Session = Depends(get_db)
):
    """Get orders aggregated by supplier and order date"""
    planner = SupplyPlanner(db)
    order_schedules = planner.generate_order_schedule(start_date, end_date)
    return planner.aggregate_orders_by_supplier(order_schedules)

@app.get("/cashflow", response_model=List[CashFlowProjection])
def get_cash_flow_projection(
    start_date: datetime,
    end_date: datetime,
    db: Session = Depends(get_db)
):
    """Get cash flow projection for date range"""
    planner = SupplyPlanner(db)
    order_schedules = planner.generate_order_schedule(start_date, end_date)
    return planner.generate_cash_flow_projection(order_schedules, start_date, end_date)

@app.get("/metrics", response_model=KeyMetrics)
def get_key_metrics(
    start_date: datetime,
    end_date: datetime,
    db: Session = Depends(get_db)
):
    """Get key performance metrics"""
    planner = SupplyPlanner(db)
    order_schedules = planner.generate_order_schedule(start_date, end_date)
    return planner.calculate_key_metrics(order_schedules)

# CSV upload endpoints
@app.post("/upload/forecast", response_model=ForecastUpload)
async def upload_forecast(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload forecast data from CSV"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be CSV")
    
    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        # Expected columns: sku_id, date, quantity
        required_columns = ['sku_id', 'date', 'quantity']
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(status_code=400, detail="CSV must contain: sku_id, date, quantity")
        
        # Clear existing forecast data
        db.query(Forecast).delete()
        
        forecast_items_created = 0
        for _, row in df.iterrows():
            forecast_item = Forecast(
                sku_id=row['sku_id'],
                period_start=pd.to_datetime(row['date']),
                units=int(row['quantity'])
            )
            db.add(forecast_item)
            forecast_items_created += 1
        
        db.commit()
        return {"message": f"Created {forecast_items_created} forecast items", "filename": file.filename}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing CSV: {str(e)}")

@app.post("/upload/bom", response_model=BOMUpload)
async def upload_bom(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload BOM data with lead times included"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        # Read CSV content with proper encoding handling
        content = await file.read()
        
        # Try different encodings to handle the file properly
        text_content = None
        for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
            try:
                text_content = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if text_content is None:
            raise HTTPException(status_code=400, detail="Could not decode file with any supported encoding")
        
        # Clean up problematic characters
        def clean_text(text):
            """Clean up text by replacing problematic characters"""
            if not isinstance(text, str):
                return text
            
            # First pass: Replace Unicode replacement characters and common problematic chars
            replacements = {
                '�': '',  # Remove replacement characters entirely
                '–': '-',  # En dash
                '—': '-',  # Em dash  
                ''': "'",  # Left single quote
                ''': "'",  # Right single quote
                '"': '"',  # Left double quote
                '"': '"',  # Right double quote
                '…': '...',  # Ellipsis
            }
            
            for old_char, new_char in replacements.items():
                text = text.replace(old_char, new_char)
            
            # Second pass: Clean up excessive quotes and normalize spacing
            # Remove multiple consecutive quotes
            while '""' in text:
                text = text.replace('""', '"')
            
            # Clean up quote patterns that are obviously wrong
            text = text.replace('"-"', '-')  # Remove quotes around dashes
            text = text.replace('"x"', 'x')  # Remove quotes around 'x'
            text = text.replace('"\'"', "'")  # Fix quote/apostrophe combinations
            
            # Remove leading/trailing quotes if they wrap the entire string
            if text.startswith('"') and text.endswith('"') and text.count('"') == 2:
                text = text[1:-1]
            
            # Remove trailing quotes that are left over
            if text.endswith('"') and not text.startswith('"'):
                text = text[:-1]
            
            # Remove leading quotes that are left over  
            if text.startswith('"') and not text.endswith('"'):
                text = text[1:]
            
            return text.strip()
        
        # Clean the entire content and fix CSV formatting issues
        text_content = clean_text(text_content)
        
        # Try to parse with different options to handle malformed CSV
        try:
            df = pd.read_csv(io.StringIO(text_content))
        except pd.errors.ParserError:
            # If normal parsing fails, try with error handling
            try:
                df = pd.read_csv(io.StringIO(text_content), on_bad_lines='skip')
            except:
                # Last resort: try with different quoting options
                df = pd.read_csv(io.StringIO(text_content), quoting=3)  # QUOTE_NONE
        
        # Handle different CSV formats - check what columns we actually have
        actual_columns = df.columns.tolist()
        
        # Map common column variations to our expected names
        column_mapping = {
            'part_name': 'part_name',
            'units_needed': 'quantity',
            'cost_per_unit': 'unit_cost',
            'cost_per_product': 'cost_per_product',
            'beginning_inventory': 'beginning_inventory',
            'supplier': 'supplier_name',
            'manufacturer': 'manufacturer',
            'ap_term': 'ap_terms',
            'ap_month_lag_days': 'ap_month_lag_days',
            'manufacturing_days_lead': 'manufacturing_lead_time',
            'shipping_days_lead': 'shipping_lead_time'
        }
        
        # Check for required columns (flexible approach)
        if 'part_name' not in df.columns:
            raise HTTPException(
                status_code=400, 
                detail="Missing required column: 'part_name'. Found columns: " + ", ".join(actual_columns)
            )
        
        if 'units_needed' not in df.columns:
            raise HTTPException(
                status_code=400, 
                detail="Missing required column: 'units_needed'. Found columns: " + ", ".join(actual_columns)
            )
        
        # Clear existing BOM data
        db.query(BOM).delete()
        
        # Insert new BOM data
        bom_records = []
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Generate a unique part_id from part_name if not provided
                part_name = clean_text(str(row['part_name']).strip())
                part_id = part_name.replace(' ', '_').replace('"', '').replace('–', '-').replace('—', '-')
                
                # For product_id, we'll use a default since it's not in the sample file
                product_id = "DEFAULT_PRODUCT"  # This can be customized later
                
                # Clean up cost values - remove $ and commas
                def clean_currency(value):
                    if pd.isna(value):
                        return 0.0
                    val_str = str(value).replace('$', '').replace(',', '').strip()
                    try:
                        return float(val_str)
                    except:
                        return 0.0
                
                # Parse AP terms (e.g., "Net 30" -> 30)
                def parse_ap_terms(value):
                    if pd.isna(value):
                        return None
                    val_str = clean_text(str(value)).strip().lower()
                    if 'net' in val_str:
                        import re
                        numbers = re.findall(r'\d+', val_str)
                        return int(numbers[0]) if numbers else None
                    try:
                        return int(value)
                    except:
                        return None
                
                # Generate supplier_id from supplier_name
                supplier_name = clean_text(str(row['supplier'])).strip() if pd.notna(row.get('supplier')) and str(row['supplier']).strip() else None
                supplier_id = None
                if supplier_name:
                    # Create a standardized supplier_id from supplier_name
                    supplier_id = supplier_name.upper().replace(' ', '_').replace('&', 'AND').replace('.', '').replace(',', '')
                    # Remove any remaining special characters
                    import re
                    supplier_id = re.sub(r'[^A-Z0-9_]', '', supplier_id)

                bom_record = BOM(
                    product_id=product_id,
                    part_id=part_id,
                    part_name=part_name,
                    quantity=float(row['units_needed']),
                    unit_cost=clean_currency(row.get('cost_per_unit', 0)),
                    cost_per_product=clean_currency(row.get('cost_per_product', 0)),
                    beginning_inventory=int(row.get('beginning_inventory', 0)) if pd.notna(row.get('beginning_inventory')) else 0,
                    supplier_id=supplier_id,
                    supplier_name=supplier_name,
                    manufacturer=clean_text(str(row['manufacturer'])).strip() if pd.notna(row.get('manufacturer')) and str(row['manufacturer']).strip() else None,
                    ap_terms=parse_ap_terms(row.get('ap_term')),
                    ap_month_lag_days=int(row['ap_month_lag_days']) if pd.notna(row.get('ap_month_lag_days')) else None,
                    manufacturing_lead_time=int(row['manufacturing_days_lead']) if pd.notna(row.get('manufacturing_days_lead')) else None,
                    shipping_lead_time=int(row['shipping_days_lead']) if pd.notna(row.get('shipping_days_lead')) else None
                )
                bom_records.append(bom_record)
            except (ValueError, TypeError) as e:
                errors.append(f"Row {index + 1}: {str(e)}")
        
        if errors:
            raise HTTPException(status_code=400, detail=f"Data validation errors: {'; '.join(errors[:5])}")
        
        if not bom_records:
            raise HTTPException(status_code=400, detail="No valid BOM records found in the file")
        
        db.add_all(bom_records)
        db.commit()
        
        return {"message": f"Successfully uploaded {len(bom_records)} BOM records", "filename": file.filename}
        
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="CSV file is empty or corrupted")
    except pd.errors.ParserError as e:
        raise HTTPException(status_code=400, detail=f"CSV parsing error: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing BOM file: {str(e)}")

@app.post("/upload/inventory", response_model=InventoryUpload)
async def upload_inventory(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload inventory data from CSV"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        # Expected columns: part_id, part_name, current_stock, minimum_stock, maximum_stock, unit_cost, supplier_name, location
        required_columns = ['part_id', 'part_name', 'current_stock', 'unit_cost']
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(status_code=400, detail=f"CSV must contain: {', '.join(required_columns)}")
        
        # Clear existing inventory data
        db.query(Inventory).delete()
        
        inventory_items_created = 0
        for _, row in df.iterrows():
            # Calculate total value
            current_stock = int(row['current_stock']) if pd.notna(row['current_stock']) else 0
            unit_cost = float(row['unit_cost']) if pd.notna(row['unit_cost']) else 0.0
            total_value = current_stock * unit_cost
            
            # Generate supplier_id from supplier_name if provided
            supplier_id = None
            supplier_name = None
            if 'supplier_name' in df.columns and pd.notna(row.get('supplier_name')):
                supplier_name = str(row['supplier_name']).strip()
                if supplier_name:
                    supplier_id = supplier_name.upper().replace(' ', '_').replace('&', 'AND').replace('.', '').replace(',', '')
                    import re
                    supplier_id = re.sub(r'[^A-Z0-9_]', '', supplier_id)
            
            inventory_item = Inventory(
                part_id=str(row['part_id']).strip(),
                part_name=str(row['part_name']).strip(),
                current_stock=current_stock,
                minimum_stock=int(row.get('minimum_stock', 0)) if pd.notna(row.get('minimum_stock')) else 0,
                maximum_stock=int(row.get('maximum_stock')) if pd.notna(row.get('maximum_stock')) else None,
                unit_cost=unit_cost,
                total_value=total_value,
                supplier_id=supplier_id,
                supplier_name=supplier_name,
                location=str(row.get('location', '')).strip() if pd.notna(row.get('location')) else None,
                notes=str(row.get('notes', '')).strip() if pd.notna(row.get('notes')) else None
            )
            db.add(inventory_item)
            inventory_items_created += 1
        
        db.commit()
        return {"message": f"Created {inventory_items_created} inventory items", "filename": file.filename}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing CSV: {str(e)}")

# Data export endpoints
from fastapi.responses import StreamingResponse

@app.get("/export/orders")
def export_orders_csv(
    start_date: datetime,
    end_date: datetime,
    db: Session = Depends(get_db)
):
    """Export order schedule to CSV"""
    planner = SupplyPlanner(db)
    order_schedules = planner.generate_order_schedule(start_date, end_date)
    
    # Convert to DataFrame
    data = []
    for order in order_schedules:
        data.append({
            'part_id': order.part_id,
            'part_description': order.part_description,
            'order_date': order.order_date.strftime('%Y-%m-%d'),
            'qty': order.qty,
            'payment_date': order.payment_date.strftime('%Y-%m-%d'),
            'unit_cost': order.unit_cost,
            'total_cost': order.total_cost,
            'status': order.status
        })
    
    df = pd.DataFrame(data)
    
    # Create CSV output
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    # Return as downloadable file
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=order_schedule.csv"}
    )

@app.get("/export/cashflow")
def export_cashflow_csv(
    start_date: datetime,
    end_date: datetime,
    db: Session = Depends(get_db)
):
    """Export cash flow projection to CSV"""
    planner = SupplyPlanner(db)
    order_schedules = planner.generate_order_schedule(start_date, end_date)
    cash_flow = planner.generate_cash_flow_projection(order_schedules, start_date, end_date)
    
    # Convert to DataFrame
    data = []
    for cf in cash_flow:
        data.append({
            'date': cf.date.strftime('%Y-%m-%d'),
            'total_outflow': cf.total_outflow,
            'total_inflow': cf.total_inflow,
            'net_cash_flow': cf.net_cash_flow,
            'cumulative_cash_flow': cf.cumulative_cash_flow
        })
    
    df = pd.DataFrame(data)
    
    # Create CSV output
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    # Return as downloadable file
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cashflow_projection.csv"}
    )

@app.get("/export/bom")
def export_bom_csv(db: Session = Depends(get_db)):
    """Export BOM data to CSV"""
    bom_records = db.query(BOM).all()
    
    # Convert to DataFrame
    data = []
    for bom in bom_records:
        data.append({
            'id': bom.id,
            'product_id': bom.product_id,
            'part_id': bom.part_id,
            'part_name': bom.part_name,
            'quantity': bom.quantity,
            'unit_cost': bom.unit_cost,
            'cost_per_product': bom.cost_per_product,
            'beginning_inventory': bom.beginning_inventory,
            'supplier_id': bom.supplier_id,
            'supplier_name': bom.supplier_name,
            'manufacturer': bom.manufacturer,
            'ap_terms': bom.ap_terms,
            'manufacturing_lead_time': bom.manufacturing_lead_time,
            'shipping_lead_time': bom.shipping_lead_time,
            'created_at': bom.created_at.strftime('%Y-%m-%d %H:%M:%S') if bom.created_at else None,
            'updated_at': bom.updated_at.strftime('%Y-%m-%d %H:%M:%S') if bom.updated_at else None
        })
    
    df = pd.DataFrame(data)
    
    # Create CSV output
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    # Return as downloadable file
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bom_data.csv"}
    )

@app.get("/export/forecast")
def export_forecast_csv(db: Session = Depends(get_db)):
    """Export forecast data to CSV"""
    forecast_records = db.query(Forecast).all()
    
    # Convert to DataFrame
    data = []
    for forecast in forecast_records:
        data.append({
            'id': forecast.id,
            'sku_id': forecast.sku_id,
            'period_start': forecast.period_start.strftime('%Y-%m-%d') if forecast.period_start else None,
            'units': forecast.units,
            'created_at': forecast.created_at.strftime('%Y-%m-%d %H:%M:%S') if forecast.created_at else None,
            'updated_at': forecast.updated_at.strftime('%Y-%m-%d %H:%M:%S') if forecast.updated_at else None
        })
    
    df = pd.DataFrame(data)
    
    # Create CSV output
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    # Return as downloadable file
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=forecast_data.csv"}
    )

@app.get("/export/orders-by-supplier")
def export_orders_by_supplier_csv(
    start_date: datetime,
    end_date: datetime,
    db: Session = Depends(get_db)
):
    """Export aggregated orders by supplier to CSV"""
    planner = SupplyPlanner(db)
    order_schedules = planner.generate_order_schedule(start_date, end_date)
    supplier_orders = planner.aggregate_orders_by_supplier(order_schedules)
    
    # Convert to DataFrame
    data = []
    for order in supplier_orders:
        data.append({
            'supplier_name': order.supplier_name,
            'order_date': order.order_date.strftime('%Y-%m-%d'),
            'total_parts': order.total_parts,
            'total_cost': order.total_cost,
            'payment_date': order.payment_date.strftime('%Y-%m-%d'),
            'days_until_order': order.days_until_order,
            'days_until_payment': order.days_until_payment
        })
    
    df = pd.DataFrame(data)
    
    # Create CSV output
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    # Return as downloadable file
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=aggregated_orders_by_supplier.csv"}
    )

@app.get("/export/inventory")
def export_inventory_csv(db: Session = Depends(get_db)):
    """Export inventory data to CSV"""
    inventory_records = db.query(Inventory).all()
    
    # Convert to DataFrame
    data = []
    for inventory in inventory_records:
        data.append({
            'id': inventory.id,
            'part_id': inventory.part_id,
            'part_name': inventory.part_name,
            'current_stock': inventory.current_stock,
            'minimum_stock': inventory.minimum_stock,
            'maximum_stock': inventory.maximum_stock,
            'unit_cost': inventory.unit_cost,
            'total_value': inventory.total_value,
            'supplier_id': inventory.supplier_id,
            'supplier_name': inventory.supplier_name,
            'location': inventory.location,
            'notes': inventory.notes,
            'created_at': inventory.created_at.strftime('%Y-%m-%d %H:%M:%S') if inventory.created_at else None,
            'updated_at': inventory.updated_at.strftime('%Y-%m-%d %H:%M:%S') if inventory.updated_at else None
        })
    
    df = pd.DataFrame(data)
    
    # Create CSV output
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    # Return as downloadable file
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=inventory_data.csv"}
    ) 

# Data validation and summary endpoints
@app.get("/validate/data")
def validate_data_integrity(db: Session = Depends(get_db)):
    """Validate data integrity and return issues"""
    issues = []
    
    # Check if we have forecast data
    forecast_count = db.query(Forecast).count()
    if forecast_count == 0:
        issues.append("No forecast data found")
    
    # Check if we have BOM data
    bom_count = db.query(BOM).count()
    if bom_count == 0:
        issues.append("No BOM data found")
    
    # Check for orphaned BOMs (BOMs without matching forecast SKUs)
    forecast_skus = set(sku[0] for sku in db.query(Forecast.sku_id).distinct().all())
    bom_products = set(product[0] for product in db.query(BOM.product_id).distinct().all())
    orphaned_boms = bom_products - forecast_skus
    if orphaned_boms:
        issues.append(f"BOM products without forecasts: {', '.join(list(orphaned_boms)[:5])}")
    
    # Check for missing parts in BOM
    bom_parts = set(part[0] for part in db.query(BOM.part_id).distinct().all())
    actual_parts = set(part[0] for part in db.query(Part.part_id).distinct().all())
    missing_parts = bom_parts - actual_parts
    if missing_parts:
        issues.append(f"BOM references missing parts: {', '.join(list(missing_parts)[:5])}")
    
    return {
        "valid": len(issues) == 0,
        "forecast_count": forecast_count,
        "bom_count": bom_count,
        "issues": issues
    }

@app.get("/data/summary")
def get_data_summary(db: Session = Depends(get_db)):
    """Get summary of all data in the system"""
    summary = {
        "products": db.query(Product).count(),
        "parts": db.query(Part).count(),
        "suppliers": db.query(Supplier).count(),
        "bom_items": db.query(BOM).count(),
        "forecasts": db.query(Forecast).count(),
        "lead_times": db.query(LeadTime).count()
    }
    
    # Add forecast date range if we have forecasts
    if summary["forecasts"] > 0:
        earliest = db.query(Forecast.period_start).order_by(Forecast.period_start.asc()).first()
        latest = db.query(Forecast.period_start).order_by(Forecast.period_start.desc()).first()
        summary["forecast_date_range"] = {
            "earliest": earliest[0].strftime('%Y-%m-%d') if earliest else None,
            "latest": latest[0].strftime('%Y-%m-%d') if latest else None
        }
    else:
        summary["forecast_date_range"] = None
    
    return summary
