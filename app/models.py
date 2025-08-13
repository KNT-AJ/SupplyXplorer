from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Product(Base):
    __tablename__ = "products"

    sku_id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships (disabled to avoid foreign key constraint issues)
    # bom_items = relationship("BOM")
    # forecasts = relationship("Forecast")

class Part(Base):
    __tablename__ = "parts"

    part_id = Column(String(50), primary_key=True)
    part_name = Column(String(200), nullable=False)
    supplier_id = Column(String(50), nullable=True)  # Removed foreign key constraint
    supplier_name = Column(String(200), nullable=True)
    manufacturer = Column(String(200), nullable=True)
    unit_cost = Column(Float, default=0.0)
    safety_stock_pct = Column(Float, default=0.1)  # 10% default safety stock
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships (without strict foreign key constraints)
    # supplier = relationship("Supplier", back_populates="parts")
    # bom_items = relationship("BOM", back_populates="part")
    # lead_times = relationship("LeadTime", back_populates="part")

class Supplier(Base):
    __tablename__ = "suppliers"

    supplier_id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False)
    ap_terms_days = Column(Integer, default=30)  # Net 30 default
    contact_email = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships (disabled to avoid foreign key constraint issues)
    # parts = relationship("Part")

class BOM(Base):
    __tablename__ = "bom"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String(50), index=True)  # Remove foreign key constraint temporarily
    part_id = Column(String(50), index=True)     # Remove foreign key constraint temporarily
    part_name = Column(String(200), nullable=False)
    quantity = Column(Float)
    unit_cost = Column(Float, default=0.0)
    cost_per_product = Column(Float, default=0.0)
    beginning_inventory = Column(Integer, default=0)
    supplier_id = Column(String(50), nullable=True)
    supplier_name = Column(String(200), nullable=True)
    manufacturer = Column(String(200), nullable=True)
    ap_terms = Column(Integer, nullable=True)  # Accounts payable terms in days, optional
    ap_month_lag_days = Column(Integer, nullable=True)  # AP month lag days
    manufacturing_lead_time = Column(Integer, nullable=True)  # Manufacturing lead time in days
    shipping_lead_time = Column(Integer, nullable=True)  # Shipping lead time in days
    shipping_mode = Column(String, nullable=True)  # Shipping mode preference: air/sea/courier
    unit_weight_kg = Column(Float, nullable=True)  # Optional weight per unit for freight calc
    unit_volume_cbm = Column(Float, nullable=True)  # Optional volume per unit for freight calc
    country_of_origin = Column(String, nullable=True)  # Country of origin for tariff calculation
    shipping_cost = Column(Float, nullable=True)  # Shipping/logistics cost per unit
    hts_code = Column(String, nullable=True)  # Harmonized Tariff Schedule code
    subject_to_tariffs = Column(String, nullable=True, default="No")  # Whether part is subject to tariffs (Yes/No)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships (without strict foreign key constraints)
    # product = relationship("Product", back_populates="bom_items")
    # part = relationship("Part", back_populates="bom_items")

class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    system_sn = Column(String(50), nullable=False)  # Changed from sku_id to system_sn
    installation_date = Column(DateTime, nullable=False)  # Changed from period_start to installation_date
    units = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships (without strict foreign key constraints)
    # product = relationship("Product", back_populates="forecasts")

class LeadTime(Base):
    __tablename__ = "lead_times"

    id = Column(Integer, primary_key=True, autoincrement=True)
    part_id = Column(String(50), nullable=False)  # Removed foreign key constraint
    days = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships (disabled to avoid foreign key constraint issues)
    # part = relationship("Part")

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    part_id = Column(String(50), nullable=False)  # Vendor-provided or extracted part identifier
    supplier_id = Column(String(50), nullable=True)  # For aggregation
    supplier_name = Column(String(200), nullable=True)  # For display and supplier-scoped matching
    order_date = Column(DateTime, nullable=False)
    estimated_delivery_date = Column(DateTime, nullable=True)
    qty = Column(Integer, nullable=False)
    unit_cost = Column(Float, default=0.0)
    payment_date = Column(DateTime, nullable=True)
    status = Column(String(20), default="pending")  # pending, ordered, received, cancelled
    po_number = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    # Mapping fields (optional)
    mapped_part_id = Column(String(50), nullable=True)  # Canonical inventory part_id when mapped
    match_confidence = Column(Integer, nullable=True)   # 0-100 confidence score
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships (disabled to avoid foreign key constraint issues)
    # part = relationship("Part")

class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    part_id = Column(String(50), nullable=False, unique=True, index=True)
    part_name = Column(String(200), nullable=False)
    current_stock = Column(Integer, nullable=False, default=0)
    minimum_stock = Column(Integer, nullable=False, default=0)
    maximum_stock = Column(Integer, nullable=True)
    unit_cost = Column(Float, nullable=False, default=0.0)
    total_value = Column(Float, nullable=False, default=0.0)
    supplier_id = Column(String(50), nullable=True)
    supplier_name = Column(String(200), nullable=True)
    location = Column(String(100), nullable=True)  # Storage location
    last_restock_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    subject_to_tariffs = Column(String, nullable=True, default="No")  # Whether part is subject to tariffs (Yes/No)
    hts_code = Column(String, nullable=True)  # Harmonized Tariff Schedule code
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PartAlias(Base):
    __tablename__ = "part_aliases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_name = Column(String(200), nullable=True, index=True)
    vendor_part_id = Column(String(200), nullable=False, index=True)
    vendor_desc = Column(Text, nullable=True)
    canonical_part_id = Column(String(50), nullable=False, index=True)
    confidence = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships (disabled to avoid foreign key constraint issues)
    # part = relationship("Part")


class ShippingQuote(Base):
    __tablename__ = "shipping_quotes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_name = Column(String(200), nullable=True)
    mode = Column(String(50), nullable=True)  # air, sea, courier
    service_level = Column(String(100), nullable=True)
    origin = Column(String(200), nullable=True)
    destination = Column(String(200), nullable=True)
    origin_port = Column(String(100), nullable=True)
    destination_port = Column(String(100), nullable=True)
    valid_from = Column(DateTime, nullable=True)
    valid_to = Column(DateTime, nullable=True)
    transit_days_min = Column(Integer, nullable=True)
    transit_days_max = Column(Integer, nullable=True)
    transit_days = Column(Integer, nullable=True)
    currency = Column(String(10), nullable=True)
    cost_per_kg = Column(Float, nullable=True)
    cost_per_cbm = Column(Float, nullable=True)
    min_charge = Column(Float, nullable=True)
    fuel_surcharge_pct = Column(Float, nullable=True)
    security_fee = Column(Float, nullable=True)
    handling_fee = Column(Float, nullable=True)
    other_fees = Column(Float, nullable=True)
    total_cost = Column(Float, nullable=True)
    quote_weight_kg = Column(Float, nullable=True)
    quote_volume_cbm = Column(Float, nullable=True)
    chargeable_weight_kg = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(String(5), nullable=True, default="Yes")  # Yes/No simple flag
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)