from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# Base schemas
class ProductBase(BaseModel):
    sku_id: str = Field(..., description="Product SKU identifier")
    name: str = Field(..., description="Product name")
    description: Optional[str] = None

class PartBase(BaseModel):
    part_id: str = Field(..., description="Part identifier")
    part_name: str = Field(..., description="Part name/description")
    supplier_id: Optional[str] = Field(None, description="Supplier identifier")
    supplier_name: Optional[str] = Field(None, description="Supplier name")
    manufacturer: Optional[str] = Field(None, description="Manufacturer name")
    unit_cost: float = Field(default=0.0, description="Unit cost")
    safety_stock_pct: float = Field(default=0.1, description="Safety stock percentage")

class SupplierBase(BaseModel):
    supplier_id: str = Field(..., description="Supplier identifier")
    name: str = Field(..., description="Supplier name")
    ap_terms_days: int = Field(default=30, description="AP terms in days")
    contact_email: Optional[str] = None

class BOMBase(BaseModel):
    product_id: str = Field(..., description="Product ID")
    part_id: str = Field(..., description="Part ID")
    part_name: str = Field(..., description="Part name/description")
    quantity: float = Field(..., description="Quantity required")
    unit_cost: float = Field(..., description="Unit cost")
    cost_per_product: float = Field(..., description="Total cost per product")
    beginning_inventory: int = Field(default=0, description="Beginning inventory level")
    supplier_id: Optional[str] = Field(None, description="Supplier identifier")
    supplier_name: Optional[str] = Field(None, description="Supplier name")
    manufacturer: Optional[str] = Field(None, description="Manufacturer name")
    ap_terms: Optional[int] = Field(None, description="Accounts payable terms in days")
    ap_month_lag_days: Optional[int] = Field(None, description="AP month lag days")
    manufacturing_lead_time: Optional[int] = Field(None, description="Manufacturing lead time in days")
    shipping_lead_time: Optional[int] = Field(None, description="Shipping lead time in days")
    country_of_origin: Optional[str] = Field(None, description="Country of origin for tariff calculation")
    shipping_cost: Optional[float] = Field(None, description="Shipping/logistics cost per unit")

class ForecastBase(BaseModel):
    system_sn: str = Field(..., description="System Serial Number")
    installation_date: datetime = Field(..., description="Installation date")
    units: int = Field(..., description="Forecasted units")

class LeadTimeBase(BaseModel):
    part_id: str = Field(..., description="Part identifier")
    days: int = Field(..., description="Lead time in days")

class InventoryBase(BaseModel):
    part_id: str = Field(..., description="Part identifier")
    part_name: str = Field(..., description="Part name/description")
    current_stock: int = Field(..., description="Current stock level")
    minimum_stock: int = Field(default=0, description="Minimum stock level")
    maximum_stock: Optional[int] = Field(None, description="Maximum stock level")
    unit_cost: float = Field(default=0.0, description="Unit cost")
    total_value: float = Field(default=0.0, description="Total inventory value")
    supplier_id: Optional[str] = Field(None, description="Supplier identifier")
    supplier_name: Optional[str] = Field(None, description="Supplier name")
    location: Optional[str] = Field(None, description="Storage location")
    last_restock_date: Optional[datetime] = Field(None, description="Last restock date")
    notes: Optional[str] = Field(None, description="Additional notes")

# Create schemas
class ProductCreate(ProductBase):
    pass

class PartCreate(PartBase):
    pass

class SupplierCreate(SupplierBase):
    pass

class BOMCreate(BOMBase):
    pass

class ForecastCreate(ForecastBase):
    pass

class LeadTimeCreate(LeadTimeBase):
    pass

class InventoryCreate(InventoryBase):
    pass

# Response schemas
class Product(ProductBase):
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class Part(PartBase):
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class Supplier(SupplierBase):
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class BOM(BOMBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class Forecast(ForecastBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class LeadTime(LeadTimeBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class Inventory(InventoryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Planning results schemas
class OrderSchedule(BaseModel):
    part_id: str
    part_name: str
    part_description: str
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    order_date: datetime
    qty: int
    payment_date: datetime
    unit_cost: float
    total_cost: float
    status: str = "planned"
    days_until_order: int
    days_until_payment: int

class SupplierOrderSummary(BaseModel):
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    order_date: datetime
    payment_date: datetime
    total_parts: int
    total_cost: float
    parts: List[str]  # List of part names
    days_until_order: int
    days_until_payment: int

class CashFlowProjection(BaseModel):
    date: datetime
    total_outflow: float
    total_inflow: float
    net_cash_flow: float
    cumulative_cash_flow: float

class KeyMetrics(BaseModel):
    orders_next_30d: int
    orders_next_60d: int
    cash_out_90d: float
    largest_purchase: float
    total_parts: int
    total_suppliers: int

# Bulk upload schemas
class ForecastUpload(BaseModel):
    filename: str
    message: str

class BOMUpload(BaseModel):
    filename: str
    message: str

class LeadTimeUpload(BaseModel):
    filename: str
    message: str

class InventoryUpload(BaseModel):
    filename: str
    message: str

# K&T BOM specific schemas
class KTBOMItem(BaseModel):
    part_name: str = Field(..., description="Part name/description")
    supplier: Optional[str] = Field(None, description="Supplier name")
    manufacturer: Optional[str] = Field(None, description="Manufacturer name")
    units_needed: int = Field(..., description="Units needed per product")
    cost_per_unit: float = Field(..., description="Cost per unit")
    cost_per_product: float = Field(..., description="Total cost per product")
    beginning_inventory: int = Field(default=0, description="Beginning inventory level")
    ap_term: str = Field(default="Net 30", description="AP terms")
    ap_month_lag_days: int = Field(default=30, description="AP month lag days")
    manufacturing_days_lead: int = Field(default=30, description="Manufacturing lead time in days")
    shipping_days_lead: int = Field(default=30, description="Shipping lead time in days")

class KTBOMUpload(BaseModel):
    bom_items: List[KTBOMItem]
    product_name: str = Field(..., description="Product name (e.g., 'Shredder')") 