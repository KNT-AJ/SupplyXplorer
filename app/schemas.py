from pydantic import BaseModel, Field
from typing import List, Optional, Dict
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
    shipping_mode: Optional[str] = Field(None, description="Preferred shipping mode: air/sea/courier")
    unit_weight_kg: Optional[float] = Field(None, description="Unit weight in kg for freight calc")
    unit_volume_cbm: Optional[float] = Field(None, description="Unit volume in CBM for freight calc")
    country_of_origin: Optional[str] = Field(None, description="Country of origin for tariff calculation")
    shipping_cost: Optional[float] = Field(None, description="Shipping/logistics cost per unit")
    subject_to_tariffs: Optional[str] = Field("No", description="Whether part is subject to tariffs (Yes/No)")
    hts_code: Optional[str] = Field(None, description="Harmonized Tariff Schedule code")

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
    subject_to_tariffs: Optional[str] = Field("No", description="Whether part is subject to tariffs (Yes/No)")
    hts_code: Optional[str] = Field(None, description="Harmonized Tariff Schedule code")

class PendingOrderBase(BaseModel):
    part_id: str = Field(..., description="Part identifier")
    supplier_id: Optional[str] = Field(None, description="Supplier identifier")
    supplier_name: Optional[str] = Field(None, description="Supplier name")
    order_date: datetime = Field(..., description="Date the order was placed")
    estimated_delivery_date: Optional[datetime] = Field(None, description="Estimated delivery date")
    qty: int = Field(..., description="Quantity ordered")
    unit_cost: float = Field(0.0, description="Unit cost at time of order")
    payment_date: Optional[datetime] = Field(None, description="Expected payment date")
    status: str = Field("pending", description="pending|ordered|received|cancelled")
    po_number: Optional[str] = Field(None, description="Purchase order number")
    notes: Optional[str] = Field(None, description="Notes")

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
class ProductSchema(ProductBase):
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class PartSchema(PartBase):
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class SupplierSchema(SupplierBase):
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class BOMSchema(BOMBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ForecastSchema(ForecastBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class LeadTimeSchema(LeadTimeBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class InventorySchema(InventoryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class PendingOrderCreate(PendingOrderBase):
    pass

class PendingOrderSchema(PendingOrderBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Shipping quotes schemas
class ShippingQuoteBase(BaseModel):
    provider_name: Optional[str] = Field(None, description="Logistics provider (e.g., Watco)")
    mode: Optional[str] = Field(None, description="Transport mode: air/sea/courier")
    service_level: Optional[str] = Field(None, description="Service level")
    origin: Optional[str] = Field(None, description="Origin city/country")
    destination: Optional[str] = Field(None, description="Destination city/state")
    origin_port: Optional[str] = Field(None, description="Origin airport/port")
    destination_port: Optional[str] = Field(None, description="Destination airport/port")
    valid_from: Optional[datetime] = Field(None)
    valid_to: Optional[datetime] = Field(None)
    transit_days_min: Optional[int] = Field(None)
    transit_days_max: Optional[int] = Field(None)
    transit_days: Optional[int] = Field(None)
    currency: Optional[str] = Field(None)
    cost_per_kg: Optional[float] = Field(None)
    cost_per_cbm: Optional[float] = Field(None)
    min_charge: Optional[float] = Field(None)
    fuel_surcharge_pct: Optional[float] = Field(None)
    security_fee: Optional[float] = Field(None)
    handling_fee: Optional[float] = Field(None)
    other_fees: Optional[float] = Field(None)
    total_cost: Optional[float] = Field(None)
    quote_weight_kg: Optional[float] = Field(None)
    quote_volume_cbm: Optional[float] = Field(None)
    chargeable_weight_kg: Optional[float] = Field(None)
    notes: Optional[str] = Field(None)
    is_active: Optional[str] = Field("Yes", description="Yes/No")

class ShippingQuoteCreate(ShippingQuoteBase):
    pass

class ShippingQuoteSchema(ShippingQuoteBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Enhanced inventory schemas for projection
class ProjectedInventoryBase(BaseModel):
    part_id: str = Field(..., description="Part identifier")
    part_name: str = Field(..., description="Part name/description")
    current_stock: int = Field(..., description="Current physical stock")
    pending_qty: int = Field(default=0, description="Total pending order quantity")
    allocated_qty: int = Field(default=0, description="Allocated quantity for production")
    net_available: int = Field(..., description="Net available inventory (current + pending - allocated)")
    days_of_supply: Optional[float] = Field(None, description="Days of supply based on demand")
    minimum_stock: int = Field(default=0, description="Minimum stock level")
    maximum_stock: Optional[int] = Field(None, description="Maximum stock level")
    unit_cost: float = Field(default=0.0, description="Unit cost")
    total_value: float = Field(default=0.0, description="Total inventory value")
    supplier_name: Optional[str] = Field(None, description="Primary supplier name")
    location: Optional[str] = Field(None, description="Storage location")
    shortage_risk: str = Field(default="Low", description="Shortage risk level (Low/Medium/High)")
    pending_orders_summary: Optional[str] = Field(None, description="Summary of pending orders")

class ProjectedInventorySchema(ProjectedInventoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class InventoryProjection(BaseModel):
    """Time-based inventory projection"""
    part_id: str
    part_name: str
    projection_date: datetime
    projected_stock: int
    pending_deliveries: int
    planned_consumption: int
    net_position: int
    days_of_supply: Optional[float] = None
    shortage_risk: str = "Low"

class InventoryAlert(BaseModel):
    """Inventory shortage/excess alert"""
    part_id: str
    part_name: str
    alert_type: str  # "shortage", "excess", "reorder"
    current_stock: int
    target_stock: int
    severity: str  # "low", "medium", "high", "critical"
    recommended_action: str
    days_until_shortage: Optional[int] = None
    suggested_order_qty: Optional[int] = None

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
    # Tariff and logistics detail
    country_of_origin: Optional[str] = None
    subject_to_tariffs: Optional[str] = "No"
    shipping_cost_per_unit: float = 0.0
    shipping_cost_total: float = 0.0
    tariff_rate: float = 0.0
    tariff_amount: float = 0.0
    base_cost: float = 0.0
    total_cost_without_tariff: float = 0.0

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
    # Aggregated tariff/logistics
    total_tariff_amount: float = 0.0
    total_shipping_cost: float = 0.0

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
    tariff_spend_90d: float = 0.0

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

# Tariff quote schemas
class TariffQuoteRequest(BaseModel):
    # Core classification & origin
    hts_code: Optional[str] = Field(None, description="HS/HTS code (6-10 digits as needed)")
    country_of_origin: str = Field(..., description="Country of origin")
    importing_country: str = Field("USA", description="Importing country")

    # Customs value
    invoice_value: float = Field(..., description="Invoice/transaction value in original currency")
    currency_code: str = Field("USD", description="Currency code of invoice value")
    fx_rate: float = Field(1.0, description="FX rate to convert to importing country currency (USD if USA)")
    freight_to_border: float = Field(0.0, description="Freight cost to border")
    insurance_cost: float = Field(0.0, description="Insurance cost")
    assists_tooling: float = Field(0.0, description="Assists/tooling value")
    royalties_fees: float = Field(0.0, description="Royalties and license fees")
    other_dutiable: float = Field(0.0, description="Other dutiable additions")
    incoterm: Optional[str] = Field(None, description="Incoterm (e.g., FOB Shanghai, CIF LA)")

    # Quantity & duty unit context
    quantity: Optional[float] = Field(None, description="Quantity of units")
    quantity_uom: Optional[str] = Field(None, description="Quantity unit of measure")
    net_weight_kg: Optional[float] = Field(None, description="Net weight in kg")
    volume_liters: Optional[float] = Field(None, description="Volume in liters")
    unit_of_measure_hts: Optional[str] = Field(None, description="Unit of measure used in HTS line")

    # Preference programs & special duties
    fta_eligible: bool = Field(False, description="Free trade agreement eligibility")
    fta_program: Optional[str] = Field(None, description="FTA program name")
    add_cvd_rate_pct: Optional[float] = Field(0.0, description="Anti-dumping or countervailing duty rate (%)")
    special_duty_surcharge_pct: Optional[float] = Field(0.0, description="Additional special duty surcharge rate (%) such as 301/232")

    # Shipment & entry context
    entry_date: Optional[datetime] = Field(None, description="Expected entry date")
    de_minimis: bool = Field(False, description="De minimis flag")
    port_of_entry: Optional[str] = Field(None, description="Port of entry")
    transport_mode: Optional[str] = Field(None, description="Transport mode: air, sea, courier")

class TariffQuoteResponse(BaseModel):
    # Inputs echoed back (helpful for UI)
    inputs: Dict[str, Optional[str]]

    # Valuation
    invoice_value_usd: float
    dutiable_additions: float
    dutiable_value: float

    # Duty rates
    base_ad_valorem_rate_pct: float
    effective_ad_valorem_rate_pct: float
    add_cvd_rate_pct: float
    special_surcharge_rate_pct: float

    # Duty and fees
    ad_valorem_duty: float
    add_cvd_amount: float
    special_surcharge_amount: float
    mpf_amount: float
    hmf_amount: float
    total_duties_and_fees: float
    effective_total_rate_pct: float

    # Notes and breakdown
    notes: List[str] = Field(default_factory=list)