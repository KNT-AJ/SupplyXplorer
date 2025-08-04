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
    
    # Relationships
    bom_items = relationship("BOM", back_populates="product")
    forecasts = relationship("Forecast", back_populates="product")

class Part(Base):
    __tablename__ = "parts"
    
    part_id = Column(String(50), primary_key=True)
    part_name = Column(String(200), nullable=False)
    supplier_id = Column(String(50), ForeignKey("suppliers.supplier_id"), nullable=True)
    supplier_name = Column(String(200), nullable=True)
    manufacturer = Column(String(200), nullable=True)
    unit_cost = Column(Float, default=0.0)
    safety_stock_pct = Column(Float, default=0.1)  # 10% default safety stock
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    supplier = relationship("Supplier", back_populates="parts")
    bom_items = relationship("BOM", back_populates="part")
    lead_times = relationship("LeadTime", back_populates="part")
    orders = relationship("Order", back_populates="part")

class Supplier(Base):
    __tablename__ = "suppliers"
    
    supplier_id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False)
    ap_terms_days = Column(Integer, default=30)  # Net 30 default
    contact_email = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    parts = relationship("Part", back_populates="supplier")

class BOM(Base):
    __tablename__ = "bom"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String, index=True)
    part_id = Column(String, index=True)
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
    country_of_origin = Column(String, nullable=True)  # Country of origin for tariff calculation
    shipping_cost = Column(Float, nullable=True)  # Shipping/logistics cost per unit
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="bom_items")
    part = relationship("Part", back_populates="bom_items")

class Forecast(Base):
    __tablename__ = "forecasts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sku_id = Column(String(50), ForeignKey("products.sku_id"), nullable=False)
    period_start = Column(DateTime, nullable=False)
    units = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="forecasts")

class LeadTime(Base):
    __tablename__ = "lead_times"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    part_id = Column(String(50), ForeignKey("parts.part_id"), nullable=False)
    days = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    part = relationship("Part", back_populates="lead_times")

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    part_id = Column(String(50), ForeignKey("parts.part_id"), nullable=False)
    order_date = Column(DateTime, nullable=False)
    qty = Column(Integer, nullable=False)
    payment_date = Column(DateTime, nullable=False)
    status = Column(String(20), default="planned")  # planned, ordered, received
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    part = relationship("Part", back_populates="orders")