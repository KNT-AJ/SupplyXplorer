import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session
from app.models import Product, Part, Supplier, BOM, Forecast, LeadTime, Order
from app.schemas import OrderSchedule, CashFlowProjection, KeyMetrics
from app.tariff_calculator import TariffCalculator

class SupplyPlanner:
    """Core planning engine for SupplyXplorer"""
    
    def __init__(self, db: Session):
        self.db = db
        self.tariff_calculator = TariffCalculator()
        
    def calculate_part_demand(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Calculate part demand per period based on forecast and BOM"""
        
        # Get all forecasts in date range
        forecasts = self.db.query(Forecast).filter(
            Forecast.period_start >= start_date,
            Forecast.period_start <= end_date
        ).all()
        
        # Get all BOM items
        bom_items = self.db.query(BOM).all()
        
        # Create demand calculation
        demand_data = []
        
        for forecast in forecasts:
            # Find BOM items for this SKU
            sku_bom = [bom for bom in bom_items if bom.sku_id == forecast.sku_id]
            
            for bom_item in sku_bom:
                # Calculate part demand = forecast units * BOM quantity
                part_demand = forecast.units * bom_item.qty_per
                
                demand_data.append({
                    'part_id': bom_item.part_id,
                    'period_start': forecast.period_start,
                    'demand_qty': part_demand,
                    'sku_id': forecast.sku_id
                })
        
        return pd.DataFrame(demand_data)
    
    def calculate_safety_stock(self, part: Part, avg_demand: float) -> float:
        """Calculate safety stock based on part configuration"""
        return avg_demand * part.safety_stock_pct
    
    def get_lead_time(self, part_id: str) -> int:
        """Get lead time for a part from BOM table"""
        bom_item = self.db.query(BOM).filter(BOM.part_id == part_id).first()
        if bom_item and bom_item.lead_time is not None:
            return bom_item.lead_time
        return 30  # Default lead time of 30 days
    
    def get_ap_terms(self, part_id: str) -> int:
        """Get AP terms for a part from BOM table"""
        bom_item = self.db.query(BOM).filter(BOM.part_id == part_id).first()
        if bom_item and bom_item.ap_terms is not None:
            return bom_item.ap_terms
        return 30  # Default AP terms of 30 days
    
    def get_transit_time(self, part_id: str) -> int:
        """Get transit time for a part from BOM table"""
        bom_item = self.db.query(BOM).filter(BOM.part_id == part_id).first()
        if bom_item and bom_item.transit_time is not None:
            return bom_item.transit_time
        return 0  # Default transit time of 0 days (local sourcing)
    
    def get_country_of_origin(self, part_id: str) -> str:
        """Get country of origin for a part from BOM table"""
        bom_item = self.db.query(BOM).filter(BOM.part_id == part_id).first()
        if bom_item and bom_item.country_of_origin:
            return bom_item.country_of_origin
        return "USA"  # Default to USA (no tariffs)
    
    def get_shipping_cost(self, part_id: str) -> float:
        """Get shipping cost for a part from BOM table"""
        bom_item = self.db.query(BOM).filter(BOM.part_id == part_id).first()
        if bom_item and bom_item.shipping_cost is not None:
            return bom_item.shipping_cost
        return 0.0  # Default shipping cost of $0
    
    def generate_order_schedule(self, start_date: datetime, end_date: datetime) -> List[OrderSchedule]:
        """Generate order schedule based on demand and lead times"""
        
        # Calculate part demand
        demand_df = self.calculate_part_demand(start_date, end_date)
        
        # Check if we have any demand data
        if demand_df.empty:
            return []
        
        # Get all parts and their lead times
        parts = self.db.query(Part).all()
        
        order_schedules = []
        
        for part in parts:
            # Get demand for this part
            part_demand = demand_df[demand_df['part_id'] == part.part_id]
            
            if part_demand.empty:
                continue
                
            # Group by period and sum demand
            period_demand = part_demand.groupby('period_start')['demand_qty'].sum().reset_index()
            
            # Calculate average demand for safety stock
            avg_demand = period_demand['demand_qty'].mean()
            safety_stock = self.calculate_safety_stock(part, avg_demand)
            
            # Get lead time for this part from BOM
            lead_time_days = self.get_lead_time(part.part_id)
            
            # Get transit time for this part from BOM
            transit_time_days = self.get_transit_time(part.part_id)
            
            # Generate orders
            for _, row in period_demand.iterrows():
                need_date = row['period_start']
                demand_qty = row['demand_qty']
                
                # Order date = need date - lead time - transit time
                total_lead_time = lead_time_days + transit_time_days
                order_date = need_date - timedelta(days=total_lead_time)
                
                # Payment date = order date + AP terms
                ap_terms = self.get_ap_terms(part.part_id)
                payment_date = order_date + timedelta(days=ap_terms)
                
                # Get country of origin and shipping cost for tariff calculation
                country_of_origin = self.get_country_of_origin(part.part_id)
                shipping_cost_per_unit = self.get_shipping_cost(part.part_id)
                
                # Calculate total cost including tariffs and shipping
                cost_breakdown = self.tariff_calculator.get_total_cost_with_tariffs(
                    unit_cost=part.unit_cost,
                    quantity=int(demand_qty),
                    country=country_of_origin,
                    shipping_cost_per_unit=shipping_cost_per_unit
                )
                
                # Calculate days until order/payment
                now = datetime.now()
                days_until_order = (order_date - now).days
                days_until_payment = (payment_date - now).days
                
                order_schedule = OrderSchedule(
                    part_id=part.part_id,
                    part_description=part.description,
                    order_date=order_date,
                    qty=int(demand_qty),
                    payment_date=payment_date,
                    unit_cost=part.unit_cost,
                    total_cost=cost_breakdown['total_cost'],
                    days_until_order=days_until_order,
                    days_until_payment=days_until_payment
                )
                
                order_schedules.append(order_schedule)
        
        return order_schedules
    
    def generate_cash_flow_projection(self, order_schedules: List[OrderSchedule], 
                                    start_date: datetime, end_date: datetime) -> List[CashFlowProjection]:
        """Generate cash flow projection based on order schedules"""
        
        # Group orders by payment date
        cash_flow_data = {}
        
        for order in order_schedules:
            payment_date = order.payment_date
            
            if payment_date not in cash_flow_data:
                cash_flow_data[payment_date] = {
                    'outflow': 0.0,
                    'inflow': 0.0  # Placeholder for future sales receipts
                }
            
            cash_flow_data[payment_date]['outflow'] += order.total_cost
        
        # Convert to list and sort by date
        cash_flow_list = []
        cumulative_cash_flow = 0.0
        
        for date in sorted(cash_flow_data.keys()):
            if start_date <= date <= end_date:
                outflow = cash_flow_data[date]['outflow']
                inflow = cash_flow_data[date]['inflow']
                net_cash_flow = inflow - outflow
                cumulative_cash_flow += net_cash_flow
                
                projection = CashFlowProjection(
                    date=date,
                    total_outflow=outflow,
                    total_inflow=inflow,
                    net_cash_flow=net_cash_flow,
                    cumulative_cash_flow=cumulative_cash_flow
                )
                
                cash_flow_list.append(projection)
        
        return cash_flow_list
    
    def calculate_key_metrics(self, order_schedules: List[OrderSchedule]) -> KeyMetrics:
        """Calculate key performance metrics"""
        
        now = datetime.now()
        
        # Orders in next 30/60 days
        orders_30d = [o for o in order_schedules if 0 <= o.days_until_order <= 30]
        orders_60d = [o for o in order_schedules if 0 <= o.days_until_order <= 60]
        
        # Cash out in next 90 days
        cash_out_90d = sum(o.total_cost for o in order_schedules 
                          if 0 <= o.days_until_payment <= 90)
        
        # Largest purchase
        largest_purchase = max((o.total_cost for o in order_schedules), default=0.0)
        
        # Total parts and suppliers
        total_parts = len(set(o.part_id for o in order_schedules))
        total_suppliers = len(set(o.part_id for o in order_schedules))  # Simplified
        
        return KeyMetrics(
            orders_next_30d=len(orders_30d),
            orders_next_60d=len(orders_60d),
            cash_out_90d=cash_out_90d,
            largest_purchase=largest_purchase,
            total_parts=total_parts,
            total_suppliers=total_suppliers
        )
    
    def run_planning_engine(self, start_date: datetime, end_date: datetime) -> Dict:
        """Run the complete planning engine and return results"""
        
        # Generate order schedule
        order_schedules = self.generate_order_schedule(start_date, end_date)
        
        # Generate cash flow projection
        cash_flow_projection = self.generate_cash_flow_projection(
            order_schedules, start_date, end_date
        )
        
        # Calculate key metrics
        key_metrics = self.calculate_key_metrics(order_schedules)
        
        return {
            'order_schedules': order_schedules,
            'cash_flow_projection': cash_flow_projection,
            'key_metrics': key_metrics
        } 