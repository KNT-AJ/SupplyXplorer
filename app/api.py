from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import pandas as pd
from datetime import datetime, timedelta
import io
from collections import defaultdict

from app.database import get_db
from app.models import Product, Part, Supplier, BOM, Forecast, LeadTime, Inventory, Order
from app.schemas import (
    ProductCreate, ProductSchema,
    PartCreate, PartSchema,
    SupplierCreate, SupplierSchema,
    BOMCreate, BOMSchema,
    ForecastCreate, ForecastSchema,
    LeadTimeCreate, LeadTimeSchema,
    InventoryCreate, InventorySchema,
    OrderSchedule, CashFlowProjection, KeyMetrics, SupplierOrderSummary,
    ForecastUpload, BOMUpload, LeadTimeUpload, InventoryUpload,
    PendingOrderCreate, PendingOrderSchema,
    ProjectedInventoryBase, InventoryProjection, InventoryAlert
)
from app.planner import SupplyPlanner
from app.inventory_service import InventoryService
from app.tariff_utils import (
    is_supplier_subject_to_tariffs,
    DEFAULT_COUNTRY_OF_ORIGIN_TARIFFED,
    DEFAULT_HTS_CODE,
    DEFAULT_IMPORTING_COUNTRY,
)
from fastapi import Body
import json
import os
from app.tariff_calculator import TariffCalculator, TariffInputs
from app.pdf_llm_extractor import extract_pending_orders_from_pdf
from app.schemas import TariffQuoteRequest, TariffQuoteResponse

app = FastAPI(
    title="PartXplorer API",
    description="Inventory & Cash-Flow Planning Tool",
    version="1.0.0"
)

from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from app.google_calendar import (
    require_credentials,
    build_calendar_service,
    build_event_all_day,
    fetch_and_store_credentials,
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
    return {"message": "PartXplorer API is running"}

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
                            # Handle date conversion for installation_date
                            if key == 'installation_date' and isinstance(value, str):
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

# Enhanced Inventory endpoints with projections (MUST come before parameterized routes)
@app.get("/inventory/projected")
def get_projected_inventory(part_id: str = None, db: Session = Depends(get_db)):
    """Get projected inventory with pending orders and allocations"""
    inventory_service = InventoryService(db)
    projected_items = inventory_service.get_projected_inventory(part_id)
    # Convert to dict to avoid pydantic model issues
    return [item.model_dump() for item in projected_items]

@app.get("/inventory/projections")
def get_inventory_projections(
    start_date: datetime,
    end_date: datetime,
    part_id: str = None,
    db: Session = Depends(get_db)
):
    """Get time-based inventory projections"""
    inventory_service = InventoryService(db)
    projections = inventory_service.get_inventory_projections(start_date, end_date, part_id)
    # Convert to dict to avoid pydantic model issues
    return [proj.model_dump() for proj in projections]

@app.get("/inventory/alerts")
def get_inventory_alerts(days_ahead: int = 90, db: Session = Depends(get_db)):
    """Get inventory alerts for shortages and recommendations"""
    inventory_service = InventoryService(db)
    alerts = inventory_service.get_inventory_alerts(days_ahead)
    # Convert to dict to avoid pydantic model issues
    return [alert.model_dump() for alert in alerts]

@app.get("/inventory/recommendations")
def get_inventory_based_recommendations(
    start_date: datetime = None,
    end_date: datetime = None,
    db: Session = Depends(get_db)
):
    """Get order recommendations based on inventory projections"""
    if not start_date:
        start_date = datetime.now()
    if not end_date:
        end_date = start_date + timedelta(days=365)

    planner = SupplyPlanner(db)
    return planner.generate_inventory_based_recommendations(start_date, end_date)

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

# Pending Orders endpoints
@app.post("/orders/pending", response_model=PendingOrderSchema)
def create_pending_order(order: PendingOrderCreate, db: Session = Depends(get_db)):
    db_order = Order(**order.dict())
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

@app.get("/orders/pending", response_model=List[PendingOrderSchema])
def list_pending_orders(db: Session = Depends(get_db)):
    return db.query(Order).order_by(Order.order_date.desc()).all()

@app.put("/orders/pending/{order_id}", response_model=PendingOrderSchema)
def update_pending_order(order_id: int, order: PendingOrderCreate, db: Session = Depends(get_db)):
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    for key, value in order.dict().items():
        setattr(db_order, key, value)
    db_order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_order)
    return db_order

@app.delete("/orders/pending/{order_id}")
def delete_pending_order(order_id: int, db: Session = Depends(get_db)):
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    db.delete(db_order)
    db.commit()
    return {"message": f"Order {order_id} deleted"}

@app.post("/orders/pending/remap")
def remap_pending_orders(high_thresh: int = 90, low_thresh: int = 75, db: Session = Depends(get_db)):
    """Re-run mapping for all pending/ordered rows. Persists mapped_part_id/match_confidence.
    Returns a summary of mappings applied.
    """
    from app.matching import build_inventory_index, map_order_to_part, upsert_alias

    orders = db.query(Order).filter(Order.status.in_(["pending", "ordered"])) .all()
    inv_index = build_inventory_index(db)
    updated = 0
    results = []
    for o in orders:
        try:
            mapped, conf = map_order_to_part(db, o, inv_index, high_thresh=high_thresh, low_thresh=low_thresh)
            if mapped and (o.mapped_part_id != mapped or (o.match_confidence or 0) != conf):
                o.mapped_part_id = mapped
                o.match_confidence = conf
                updated += 1
                if conf >= 90:
                    upsert_alias(db, o.supplier_name, o.part_id, mapped, conf)
            results.append({
                'id': o.id,
                'part_id': o.part_id,
                'mapped_part_id': o.mapped_part_id,
                'match_confidence': o.match_confidence,
            })
        except Exception:
            results.append({
                'id': o.id,
                'part_id': o.part_id,
                'mapped_part_id': o.mapped_part_id,
                'match_confidence': o.match_confidence,
            })
    db.commit()
    return {"updated": updated, "count": len(orders), "results": results}


@app.post("/orders/pending/upload-pdf")
async def upload_pending_orders_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload an invoice/quote PDF, extract pending orders via LLM fallback chain, and insert.

    Uses providers in this order: Gemini 2.0 Flash → GPT-4o mini → Gemini 2.5 Flash Lite.
    Returns inserted orders and any provider errors encountered.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file")

    orders, extractor_errors = extract_pending_orders_from_pdf(contents)
    if not orders:
        raise HTTPException(status_code=422, detail={
            "message": "Could not extract orders from PDF",
            "providers": extractor_errors,
        })

    created: list = []
    from app.matching import build_inventory_index, map_order_to_part, upsert_alias

    inv_index = build_inventory_index(db)

    for o in orders:
        try:
            # Normalize and coerce fields defensively
            payload = {
                'part_id': str(o.get('part_id', '')).strip(),
                'supplier_id': (str(o.get('supplier_id')).strip() if o.get('supplier_id') is not None else None),
                'supplier_name': (str(o.get('supplier_name')).strip() if o.get('supplier_name') is not None else None),
                'order_date': pd.to_datetime(o.get('order_date')).to_pydatetime() if o.get('order_date') else datetime.utcnow(),
                'estimated_delivery_date': (pd.to_datetime(o.get('estimated_delivery_date')).to_pydatetime() if o.get('estimated_delivery_date') else None),
                'qty': int(float(o.get('qty', 0) or 0)),
                'unit_cost': float(str(o.get('unit_cost', 0)).replace('$','').replace(',','')) if o.get('unit_cost') is not None else 0.0,
                'payment_date': (pd.to_datetime(o.get('payment_date')).to_pydatetime() if o.get('payment_date') else None),
                'status': (str(o.get('status') or 'pending')).strip().lower(),
                'po_number': (str(o.get('po_number')).strip() if o.get('po_number') else None),
                'notes': (str(o.get('notes')).strip() if o.get('notes') else None),
            }
            if not payload['part_id'] or payload['qty'] <= 0:
                continue
            db_order = Order(**payload)
            db.add(db_order)
            db.commit()
            db.refresh(db_order)

            # Attempt to map to canonical inventory part
            mapped, conf = map_order_to_part(db, db_order, inv_index)
            if mapped:
                db_order.mapped_part_id = mapped
                db_order.match_confidence = conf
                db.commit()
                # If high confidence, upsert alias for vendor_part_id
                if conf >= 90:
                    upsert_alias(db, db_order.supplier_name, db_order.part_id, mapped, conf)

            created.append(db_order)
        except Exception as e:
            db.rollback()
            # Skip bad rows but report later
            extractor_errors.append(f"insert:error:{str(e)}")

    return {
        "inserted": [
            {
                'id': c.id,
                'part_id': c.part_id,
                'supplier_id': c.supplier_id,
                'supplier_name': c.supplier_name,
                'order_date': c.order_date.isoformat() if c.order_date else None,
                'estimated_delivery_date': c.estimated_delivery_date.isoformat() if c.estimated_delivery_date else None,
                'qty': c.qty,
                'unit_cost': c.unit_cost,
                'payment_date': c.payment_date.isoformat() if c.payment_date else None,
                'status': c.status,
                'po_number': c.po_number,
                'notes': c.notes,
                'mapped_part_id': c.mapped_part_id,
                'match_confidence': c.match_confidence,
            }
            for c in created
        ],
        "errors": extractor_errors,
        "filename": file.filename,
    }

# --- Google Calendar OAuth callbacks ---
@app.get("/auth/google/callback")
async def google_oauth_callback(request: Request):
    """OAuth redirect URI to capture the auth code and persist credentials."""
    try:
        params = dict(request.query_params)
        code = params.get("code")
        state = params.get("state")
        if not code:
            raise HTTPException(status_code=400, detail="Missing authorization code")
        # Build base URL from incoming request
        base_url = str(request.base_url).rstrip("/")
        fetch_and_store_credentials(base_url, code)
        # Bounce back to dashboard if state carries a return URL
        if state:
            return RedirectResponse(url=state, status_code=302)
        return HTMLResponse(content="<html><body><h3>Google authorization complete. You can close this window.</h3></body></html>")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}")


@app.get("/calendar/export/by-supplier")
def export_supplier_orders_to_calendar(
    start_date: datetime,
    end_date: datetime,
    supplier_id: str | None = None,
    supplier_name: str | None = None,
    order_date: datetime | None = None,
    calendar_id: str = "primary",
    as_html: bool = True,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Create calendar events for a single supplier group.

    If order_date is provided, exports only that supplier+order_date group. Otherwise
    exports all groups for the supplier within the date range.
    """
    # Ensure credentials or trigger OAuth flow
    base_url = str(request.base_url).rstrip("/")
    # Use the current URL as return_to so OAuth bounces back here and completes export
    return_to = str(request.url)
    creds_or_redirect = require_credentials(base_url, return_to=return_to)
    if isinstance(creds_or_redirect, RedirectResponse):
        return creds_or_redirect

    creds = creds_or_redirect
    service = build_calendar_service(creds)

    planner = SupplyPlanner(db)
    order_schedules = planner.generate_order_schedule(start_date, end_date)
    supplier_groups = planner.aggregate_orders_by_supplier(order_schedules)

    # Filter groups
    def matches(group):
        sid = group.supplier_id or None
        sname = group.supplier_name or None
        cond_supplier = True
        if supplier_id:
            cond_supplier = (sid == supplier_id)
        elif supplier_name:
            cond_supplier = (sname == supplier_name)
        cond_date = True
        if order_date is not None:
            try:
                od = order_date.date() if isinstance(order_date, datetime) else order_date
                cond_date = (group.order_date.date() == od)
            except Exception:
                cond_date = True
        return cond_supplier and cond_date

    target_groups = [g for g in supplier_groups if matches(g)] if (supplier_id or supplier_name) else supplier_groups

    # Prepare and insert events
    created: list[dict] = []
    for g in target_groups:
        # Build event title and description
        title = f"Supplier Order: {g.supplier_name} — {g.order_date.strftime('%Y-%m-%d')} (Parts: {g.total_parts}, Total: ${g.total_cost:,.2f})"

        # Find detailed line items from raw order schedules for this group
        def order_matches_group(o):
            sid = o.supplier_id or None
            sname = o.supplier_name or None
            cond_supplier = True
            if g.supplier_id:
                cond_supplier = (sid == g.supplier_id)
            else:
                cond_supplier = (sname == g.supplier_name)
            return cond_supplier and (o.order_date.date() == g.order_date.date())

        group_orders = [o for o in order_schedules if order_matches_group(o)]

        # Description with details
        desc_lines = [
            f"Supplier: {g.supplier_name}",
            f"Order Date: {g.order_date.strftime('%Y-%m-%d')}",
            f"ETA: {g.eta_date.strftime('%Y-%m-%d') if getattr(g, 'eta_date', None) else 'N/A'}",
            f"Payment Date: {g.payment_date.strftime('%Y-%m-%d')}",
            f"Total Parts: {g.total_parts}",
            f"Total Cost: ${g.total_cost:,.2f}",
        ]
        if hasattr(g, 'total_tariff_amount'):
            desc_lines.append(f"Tariffs: ${float(getattr(g, 'total_tariff_amount') or 0):,.2f}")
        if hasattr(g, 'total_shipping_cost'):
            desc_lines.append(f"Shipping: ${float(getattr(g, 'total_shipping_cost') or 0):,.2f}")

        if group_orders:
            desc_lines.append("\nItems:")
            for o in group_orders:
                line_total = float(getattr(o, 'total_cost', 0.0) or 0.0)
                desc_lines.append(
                    f" - {o.part_name} | Qty: {o.qty} @ ${o.unit_cost:,.2f} = ${line_total:,.2f}"
                )

        description = "\n".join(desc_lines)

        event_date = g.order_date.date()
        body = build_event_all_day(title, event_date, description)
        res = service.events().insert(calendarId=calendar_id, body=body, sendUpdates="none").execute()
        created.append({"id": res.get("id"), "htmlLink": res.get("htmlLink"), "summary": res.get("summary")})

        # Optionally create ETA and Payment events
        if getattr(g, 'eta_date', None):
            eta_title = f"ETA: {g.supplier_name} — {g.eta_date.strftime('%Y-%m-%d')} (Order {g.order_date.strftime('%Y-%m-%d')})"
            eta_desc = f"Shipment ETA for supplier order placed on {g.order_date.strftime('%Y-%m-%d')}\n\n" + description
            eta_body = build_event_all_day(eta_title, g.eta_date.date(), eta_desc)
            res_eta = service.events().insert(calendarId=calendar_id, body=eta_body, sendUpdates="none").execute()
            created.append({"id": res_eta.get("id"), "htmlLink": res_eta.get("htmlLink"), "summary": res_eta.get("summary")})

        if getattr(g, 'payment_date', None):
            pay_title = f"Payment: {g.supplier_name} — {g.payment_date.strftime('%Y-%m-%d')} (Order {g.order_date.strftime('%Y-%m-%d')})"
            pay_desc = f"Payment due for supplier order placed on {g.order_date.strftime('%Y-%m-%d')}\n\n" + description
            pay_body = build_event_all_day(pay_title, g.payment_date.date(), pay_desc)
            res_pay = service.events().insert(calendarId=calendar_id, body=pay_body, sendUpdates="none").execute()
            created.append({"id": res_pay.get("id"), "htmlLink": res_pay.get("htmlLink"), "summary": res_pay.get("summary")})

    if as_html:
        # Render minimal HTML with results and links for planned orders export
        items = "".join([
            f"<li><a target=\"_blank\" href=\"{e.get('htmlLink','')}\">{e.get('summary','Event')}</a></li>"
            for e in created
        ])
        html = f"""
        <html><body>
        <h3>Created {len(created)} calendar event(s)</h3>
        <ul>{items}</ul>
        <p><a target=\"_blank\" href=\"https://calendar.google.com/calendar\">Open Google Calendar</a></p>
        </body></html>
        """
        return HTMLResponse(content=html)

@app.get("/calendar/export/pending-orders-by-supplier")
def export_pending_orders_to_calendar(
    supplier_id: str | None = None,
    supplier_name: str | None = None,
    order_date: datetime | None = None,
    calendar_id: str = "primary",
    as_html: bool = True,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Create calendar events for a specific supplier+order_date group from Pending Orders.

    Finds pending orders matching the supplier (by id or name) and the given order_date (date-only).
    Creates an all-day Order event, and optional ETA and Payment events.
    """
    base_url = str(request.base_url).rstrip("/")
    return_to = str(request.url)
    creds_or_redirect = require_credentials(base_url, return_to=return_to)
    if isinstance(creds_or_redirect, RedirectResponse):
        return creds_or_redirect

    creds = creds_or_redirect
    service = build_calendar_service(creds)

    # Fetch all pending orders
    orders = db.query(Order).all()

    # Filter for supplier + date
    def order_matches(o: Order) -> bool:
        sid = o.supplier_id or None
        sname = o.supplier_name or None
        ok_supplier = True
        if supplier_id:
            ok_supplier = (sid == supplier_id)
        elif supplier_name:
            ok_supplier = (sname == supplier_name)
        ok_date = True
        if order_date is not None and o.order_date:
            try:
                od = order_date.date() if isinstance(order_date, datetime) else order_date
                ok_date = (o.order_date.date() == od)
            except Exception:
                ok_date = True
        return ok_supplier and ok_date

    group_orders = [o for o in orders if order_matches(o)]
    if not group_orders:
        raise HTTPException(status_code=404, detail="No pending orders found for the specified group")

    # Aggregate details
    supplier_display = supplier_name or (group_orders[0].supplier_name or "Unknown Supplier")
    order_date_dt = group_orders[0].order_date
    latest_eta = max([o.estimated_delivery_date for o in group_orders if o.estimated_delivery_date], default=None)
    latest_payment = max([o.payment_date for o in group_orders if o.payment_date], default=None)
    total_parts = len(group_orders)
    total_cost = sum([(o.qty or 0) * (o.unit_cost or 0.0) for o in group_orders])

    # Build description with line items
    desc_lines = [
        f"Supplier: {supplier_display}",
        f"Order Date: {order_date_dt.strftime('%Y-%m-%d') if order_date_dt else 'N/A'}",
        f"ETA: {latest_eta.strftime('%Y-%m-%d') if latest_eta else 'N/A'}",
        f"Payment Date: {latest_payment.strftime('%Y-%m-%d') if latest_payment else 'N/A'}",
        f"Total Orders: {total_parts}",
        f"Total Cost: ${total_cost:,.2f}",
        "",
        "Items:",
    ]
    for o in group_orders:
        desc_lines.append(
            f" - Part: {o.part_id} | Qty: {o.qty} @ ${o.unit_cost:,.2f} | Supplier: {o.supplier_name or ''}"
        )
    description = "\n".join(desc_lines)

    # Create order event
    event_title = f"Pending Supplier Order: {supplier_display} — {order_date_dt.strftime('%Y-%m-%d') if order_date_dt else ''} (Orders: {total_parts}, Total: ${total_cost:,.2f})"
    order_event = build_event_all_day(event_title, order_date_dt.date(), description)
    res = service.events().insert(calendarId=calendar_id, body=order_event, sendUpdates="none").execute()

    created = [{"id": res.get("id"), "htmlLink": res.get("htmlLink"), "summary": res.get("summary")}]

    # Optional ETA
    if latest_eta:
        eta_title = f"ETA: {supplier_display} — {latest_eta.strftime('%Y-%m-%d')} (Order {order_date_dt.strftime('%Y-%m-%d') if order_date_dt else ''})"
        eta_body = build_event_all_day(eta_title, latest_eta.date(), description)
        res_eta = service.events().insert(calendarId=calendar_id, body=eta_body, sendUpdates="none").execute()
        created.append({"id": res_eta.get("id"), "htmlLink": res_eta.get("htmlLink"), "summary": res_eta.get("summary")})

    # Optional Payment
    if latest_payment:
        pay_title = f"Payment: {supplier_display} — {latest_payment.strftime('%Y-%m-%d')} (Order {order_date_dt.strftime('%Y-%m-%d') if order_date_dt else ''})"
        pay_body = build_event_all_day(pay_title, latest_payment.date(), description)
        res_pay = service.events().insert(calendarId=calendar_id, body=pay_body, sendUpdates="none").execute()
        created.append({"id": res_pay.get("id"), "htmlLink": res_pay.get("htmlLink"), "summary": res_pay.get("summary")})

    if as_html:
        items = "".join([f"<li><a target=\"_blank\" href=\"{e.get('htmlLink','')}\">{e.get('summary','Event')}</a></li>" for e in created])
        html = f"""
        <html><body>
        <h3>Created {len(created)} calendar event(s) for pending orders</h3>
        <ul>{items}</ul>
        <p><a target=\"_blank\" href=\"https://calendar.google.com/calendar\">Open Google Calendar</a></p>
        </body></html>
        """
        return HTMLResponse(content=html)

    return {"created": created, "count": len(created)}


from fastapi.responses import StreamingResponse

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

# CSV upload endpoints
@app.post("/upload/forecast", response_model=ForecastUpload)
async def upload_forecast(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload forecast data from CSV"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be CSV")

    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))

        # Support both old and new column formats
        # New format: System SN, Installation Date, quantity
        # Old format: sku_id, date, quantity
        if 'System SN' in df.columns and 'Installation Date' in df.columns:
            # New format - use existing System SN
            required_columns = ['System SN', 'Installation Date', 'quantity']
            if not all(col in df.columns for col in required_columns):
                raise HTTPException(status_code=400, detail="CSV must contain: System SN, Installation Date, quantity")

            # Clear existing forecast data
            db.query(Forecast).delete()

            forecast_items_created = 0
            for _, row in df.iterrows():
                forecast_item = Forecast(
                    system_sn=row['System SN'],
                    installation_date=pd.to_datetime(row['Installation Date']),
                    units=int(row['quantity'])
                )
                db.add(forecast_item)
                forecast_items_created += 1

        elif 'sku_id' in df.columns and 'date' in df.columns:
            # Old format - generate System SN automatically
            required_columns = ['sku_id', 'date', 'quantity']
            if not all(col in df.columns for col in required_columns):
                raise HTTPException(status_code=400, detail="CSV must contain: sku_id, date, quantity")

            # Sort by date to ensure consistent System SN generation
            df = df.sort_values('date').reset_index(drop=True)
            df['date'] = pd.to_datetime(df['date'])

            # Clear existing forecast data
            db.query(Forecast).delete()

            # Initialize sequence counter for System SN generation
            sequence_counter = defaultdict(int)

            forecast_items_created = 0
            for _, row in df.iterrows():
                installation_date = row['date']
                system_sn = generate_system_sn(installation_date, sequence_counter)

                forecast_item = Forecast(
                    system_sn=system_sn,
                    installation_date=installation_date,
                    units=int(row['quantity'])
                )
                db.add(forecast_item)
                forecast_items_created += 1
        else:
            raise HTTPException(status_code=400, detail="CSV must contain either (System SN, Installation Date, quantity) or (sku_id, date, quantity)")

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
            'shipping_days_lead': 'shipping_lead_time',
            'country_of_origin': 'country_of_origin',
            'shipping_cost': 'shipping_cost',
            'hts_code': 'hts_code',
            'subject_to_tariffs': 'subject_to_tariffs'
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

                # Optional: country of origin and shipping cost
                country_of_origin = clean_text(str(row.get('country_of_origin', '')).strip()) if pd.notna(row.get('country_of_origin')) else None
                shipping_cost_val = clean_currency(row.get('shipping_cost', 0))
                # Subject to tariffs: use provided or infer from supplier
                subject_to_tariffs = None
                if 'subject_to_tariffs' in df.columns and pd.notna(row.get('subject_to_tariffs')):
                    val = clean_text(str(row.get('subject_to_tariffs'))).strip()
                    subject_to_tariffs = 'Yes' if val.lower() in ['yes', 'y', 'true', '1'] else 'No'
                else:
                    subject_to_tariffs = is_supplier_subject_to_tariffs(supplier_name) if supplier_name else 'No'

                # If subject to tariffs and COO missing, assume China by default
                if subject_to_tariffs == 'Yes' and (not country_of_origin or not country_of_origin.strip()):
                    country_of_origin = DEFAULT_COUNTRY_OF_ORIGIN_TARIFFED

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
                    shipping_lead_time=int(row['shipping_days_lead']) if pd.notna(row.get('shipping_days_lead')) else None,
                    country_of_origin=country_of_origin,
                    shipping_cost=shipping_cost_val,
                    subject_to_tariffs=subject_to_tariffs,
                    hts_code=(
                        clean_text(str(row.get('hts_code', '')).strip()) if pd.notna(row.get('hts_code')) and str(row.get('hts_code', '')).strip() else DEFAULT_HTS_CODE if subject_to_tariffs == 'Yes' else None
                    )
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
            'eta_date': getattr(order, 'eta_date', None).strftime('%Y-%m-%d') if getattr(order, 'eta_date', None) else None,
            'days_until_eta': getattr(order, 'days_until_eta', None),
            'unit_cost': order.unit_cost,
            'total_cost': order.total_cost,
            'status': order.status,
            'supplier_name': order.supplier_name,
            'country_of_origin': getattr(order, 'country_of_origin', None),
            'subject_to_tariffs': getattr(order, 'subject_to_tariffs', None),
            'shipping_cost_per_unit': getattr(order, 'shipping_cost_per_unit', 0.0),
            'shipping_cost_total': getattr(order, 'shipping_cost_total', 0.0),
            'tariff_rate': getattr(order, 'tariff_rate', 0.0),
            'tariff_amount': getattr(order, 'tariff_amount', 0.0),
            'base_cost': getattr(order, 'base_cost', 0.0),
            'total_cost_without_tariff': getattr(order, 'total_cost_without_tariff', 0.0)
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
            'country_of_origin': bom.country_of_origin,
            'shipping_cost': bom.shipping_cost,
            'hts_code': bom.hts_code,
            'subject_to_tariffs': bom.subject_to_tariffs,
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

@app.get("/export/orders-pending")
def export_pending_orders_csv(db: Session = Depends(get_db)):
    """Export pending orders to CSV"""
    orders = db.query(Order).all()
    data = []
    for o in orders:
        data.append({
            'id': o.id,
            'part_id': o.part_id,
            'supplier_id': o.supplier_id,
            'supplier_name': o.supplier_name,
            'order_date': o.order_date.strftime('%Y-%m-%d') if o.order_date else None,
            'estimated_delivery_date': o.estimated_delivery_date.strftime('%Y-%m-%d') if o.estimated_delivery_date else None,
            'qty': o.qty,
            'unit_cost': o.unit_cost,
            'payment_date': o.payment_date.strftime('%Y-%m-%d') if o.payment_date else None,
            'status': o.status,
            'po_number': o.po_number,
            'notes': o.notes
        })
    df = pd.DataFrame(data)
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=pending_orders.csv"}
    )

@app.post("/tariff-config")
def update_tariff_config(config: dict = Body(...)):
    """Save tariff rate overrides to a JSON file the planner will read on init."""
    try:
        # Project root is parent of app directory
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        path = os.path.join(project_root, 'tariff_rates.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        return {"message": "Tariff configuration saved", "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save config: {str(e)}")

@app.get("/export/forecast")
def export_forecast_csv(db: Session = Depends(get_db)):
    """Export forecast data to CSV"""
    forecast_records = db.query(Forecast).all()

    # Convert to DataFrame
    data = []
    for forecast in forecast_records:
        data.append({
            'id': forecast.id,
            'system_sn': forecast.system_sn,
            'installation_date': forecast.installation_date.strftime('%Y-%m-%d') if forecast.installation_date else None,
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
            'eta_date': getattr(order, 'eta_date', None).strftime('%Y-%m-%d') if getattr(order, 'eta_date', None) else None,
            'total_parts': order.total_parts,
            'total_cost': order.total_cost,
            'payment_date': order.payment_date.strftime('%Y-%m-%d'),
            'days_until_order': order.days_until_order,
            'days_until_eta': getattr(order, 'days_until_eta', None),
            'days_until_payment': order.days_until_payment,
            'total_tariff_amount': getattr(order, 'total_tariff_amount', 0.0),
            'total_shipping_cost': getattr(order, 'total_shipping_cost', 0.0)
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
            'hts_code': inventory.hts_code,
            'subject_to_tariffs': inventory.subject_to_tariffs,
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

    # Check for orphaned BOMs (BOMs without matching forecast System SNs)
    forecast_system_sns = set(sn[0] for sn in db.query(Forecast.system_sn).distinct().all())
    bom_products = set(product[0] for product in db.query(BOM.product_id).distinct().all())
    orphaned_boms = bom_products - forecast_system_sns
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
        earliest = db.query(Forecast.installation_date).order_by(Forecast.installation_date.asc()).first()
        latest = db.query(Forecast.installation_date).order_by(Forecast.installation_date.desc()).first()
        summary["forecast_date_range"] = {
            "earliest": earliest[0].strftime('%Y-%m-%d') if earliest else None,
            "latest": latest[0].strftime('%Y-%m-%d') if latest else None
        }
    else:
        summary["forecast_date_range"] = None

    return summary

# Tariff quote endpoint
@app.post("/tariff/quote", response_model=TariffQuoteResponse)
def quote_tariff(payload: TariffQuoteRequest):
    """Calculate a tariff quote based on provided shipment and classification context."""
    calc = TariffCalculator()
    inputs = TariffInputs(
        hts_code=payload.hts_code,
        country_of_origin=payload.country_of_origin,
        importing_country=payload.importing_country or "USA",
        invoice_value=payload.invoice_value,
        currency_code=payload.currency_code or "USD",
        fx_rate=payload.fx_rate or 1.0,
        freight_to_border=payload.freight_to_border or 0.0,
        insurance_cost=payload.insurance_cost or 0.0,
        assists_tooling=payload.assists_tooling or 0.0,
        royalties_fees=payload.royalties_fees or 0.0,
        other_dutiable=payload.other_dutiable or 0.0,
        incoterm=payload.incoterm,
        quantity=payload.quantity,
        quantity_uom=payload.quantity_uom,
        net_weight_kg=payload.net_weight_kg,
        volume_liters=payload.volume_liters,
        unit_of_measure_hts=payload.unit_of_measure_hts,
        fta_eligible=payload.fta_eligible,
        fta_program=payload.fta_program,
        add_cvd_rate_pct=payload.add_cvd_rate_pct or 0.0,
        special_duty_surcharge_pct=payload.special_duty_surcharge_pct or 0.0,
        entry_date=payload.entry_date.isoformat() if payload.entry_date else None,
        de_minimis=payload.de_minimis,
        port_of_entry=payload.port_of_entry,
        transport_mode=payload.transport_mode,
    )
    result = calc.quote_duties(inputs)
    return result
