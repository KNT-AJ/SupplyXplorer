from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import pandas as pd
from datetime import datetime, timedelta
import io

from app.database import get_db
from app.models import Product, Part, Supplier, BOM, Forecast, LeadTime
from app.schemas import (
    ProductCreate, Product as ProductSchema,
    PartCreate, Part as PartSchema,
    SupplierCreate, Supplier as SupplierSchema,
    BOMCreate, BOM as BOMSchema,
    ForecastCreate, Forecast as ForecastSchema,
    LeadTimeCreate, LeadTime as LeadTimeSchema,
    OrderSchedule, CashFlowProjection, KeyMetrics,
    ForecastUpload, BOMUpload, LeadTimeUpload
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
@app.post("/upload/forecast")
async def upload_forecast(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload forecast data from CSV"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be CSV")
    
    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        # Expected columns: product_id, date, quantity
        required_columns = ['product_id', 'date', 'quantity']
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(status_code=400, detail="CSV must contain: product_id, date, quantity")
        
        # Clear existing forecast data
        db.query(Forecast).delete()
        
        forecast_items_created = 0
        for _, row in df.iterrows():
            forecast_item = Forecast(
                product_id=row['product_id'],
                date=pd.to_datetime(row['date']).date(),
                quantity=int(row['quantity'])
            )
            db.add(forecast_item)
            forecast_items_created += 1
        
        db.commit()
        return {"message": f"Created {forecast_items_created} forecast items"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing CSV: {str(e)}")

@app.post("/upload/bom")
async def upload_bom(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload BOM data with lead times included"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        # Read CSV content
        content = await file.read()
        df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        
        # Validate required columns
        required_columns = ['product_id', 'part_id', 'quantity']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required columns: {missing_columns}. Required: {required_columns}, Optional: lead_time, ap_terms, transit_time, country_of_origin, shipping_cost"
            )
        
        # Clear existing BOM data
        db.query(BOM).delete()
        
        # Insert new BOM data
        bom_records = []
        for _, row in df.iterrows():
            bom_record = BOM(
                product_id=str(row['product_id']),
                part_id=str(row['part_id']),
                quantity=float(row['quantity']),
                lead_time=int(row['lead_time']) if 'lead_time' in df.columns and pd.notna(row['lead_time']) else None,
                ap_terms=int(row['ap_terms']) if 'ap_terms' in df.columns and pd.notna(row['ap_terms']) else None,
                transit_time=int(row['transit_time']) if 'transit_time' in df.columns and pd.notna(row['transit_time']) else None,
                country_of_origin=str(row['country_of_origin']) if 'country_of_origin' in df.columns and pd.notna(row['country_of_origin']) else None,
                shipping_cost=float(row['shipping_cost']) if 'shipping_cost' in df.columns and pd.notna(row['shipping_cost']) else None
            )
            bom_records.append(bom_record)
        
        db.add_all(bom_records)
        db.commit()
        
        return {"message": f"Successfully uploaded {len(bom_records)} BOM records with lead times, AP terms, transit times, tariffs, and shipping costs"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing BOM file: {str(e)}")

# Data export endpoints
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
    
    # Return CSV as string
    csv_string = df.to_csv(index=False)
    return {"csv_data": csv_string}

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
    
    # Return CSV as string
    csv_string = df.to_csv(index=False)
    return {"csv_data": csv_string} 