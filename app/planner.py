import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session
from app.models import Product, Part, Supplier, BOM, Forecast, LeadTime, Order, Inventory
from app.schemas import OrderSchedule, CashFlowProjection, KeyMetrics, SupplierOrderSummary
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
            Forecast.installation_date >= start_date,
            Forecast.installation_date <= end_date
        ).all()
        
        # Get all BOM items
        bom_items = self.db.query(BOM).all()
        
        # Create demand calculation
        demand_data = []
        
        for forecast in forecasts:
            # Find BOM items for this System SN/Product
            # First try exact match
            system_sn_bom = [bom for bom in bom_items if bom.product_id == forecast.system_sn]
            
            # If no exact match and we have a single product in BOM (common case)
            # Use the BOM for that product for all forecasts
            if not system_sn_bom:
                unique_products = list(set(bom.product_id for bom in bom_items))
                if len(unique_products) == 1:
                    system_sn_bom = [bom for bom in bom_items if bom.product_id == unique_products[0]]
            
            for bom_item in system_sn_bom:
                # Calculate part demand = forecast units * BOM quantity
                part_demand = forecast.units * bom_item.quantity
                
                demand_data.append({
                    'part_id': bom_item.part_id,
                    'part_name': bom_item.part_name,
                    'installation_date': forecast.installation_date,
                    'demand_qty': part_demand,
                    'system_sn': forecast.system_sn,
                    'unit_cost': bom_item.unit_cost
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
        
        # Get unique parts that have demand
        unique_parts = demand_df['part_id'].unique()
        
        order_schedules = []
        
        for part_id in unique_parts:
            # Get demand for this part
            part_demand = demand_df[demand_df['part_id'] == part_id]
            
            if part_demand.empty:
                continue
            
            # Get part information from BOM (since we may not have Part records)
            bom_item = self.db.query(BOM).filter(BOM.part_id == part_id).first()
            if not bom_item:
                continue
                
            # Group by installation date and sum demand
            period_demand = part_demand.groupby('installation_date')['demand_qty'].sum().reset_index()
            
            # Get current inventory for this part
            inventory_record = self.db.query(Inventory).filter(Inventory.part_id == part_id).first()
            current_stock = inventory_record.current_stock if inventory_record else 0
            minimum_stock = inventory_record.minimum_stock if inventory_record else 0
            
            # Calculate average demand for safety stock (using default 10% if no part record)
            avg_demand = period_demand['demand_qty'].mean()
            safety_stock_pct = 0.1  # Default 10%
            safety_stock = max(avg_demand * safety_stock_pct, minimum_stock)
            
            # Get lead times from BOM
            manufacturing_lead_time = bom_item.manufacturing_lead_time or 30
            shipping_lead_time = bom_item.shipping_lead_time or 0
            total_lead_time = manufacturing_lead_time + shipping_lead_time
            
            # Track running inventory levels
            running_stock = current_stock
            
            # Generate orders
            for _, row in period_demand.iterrows():
                need_date = row['installation_date']
                demand_qty = row['demand_qty']
                
                # Calculate net demand (demand - available stock)
                available_for_demand = max(0, running_stock - safety_stock)
                net_demand = max(0, demand_qty - available_for_demand)
                
                # Update running stock
                running_stock = max(0, running_stock - demand_qty)
                
                # Only create order if we have net demand
                if net_demand <= 0:
                    continue
                
                # Order quantity = net demand + safety stock replenishment if needed
                order_qty = net_demand
                if running_stock < safety_stock:
                    order_qty += (safety_stock - running_stock)
                
                # Update running stock with incoming order
                running_stock += order_qty
                
                # Order date = need date - total lead time
                order_date = need_date - timedelta(days=total_lead_time)
                
                # Payment date = order date + AP terms
                ap_terms = bom_item.ap_terms or 30
                payment_date = order_date + timedelta(days=ap_terms)
                
                # Get country of origin and shipping cost for tariff calculation
                country_of_origin = bom_item.country_of_origin or "USA"
                shipping_cost_per_unit = bom_item.shipping_cost or 0.0
                
                # Calculate total cost including tariffs and shipping
                cost_breakdown = self.tariff_calculator.get_total_cost_with_tariffs(
                    unit_cost=bom_item.unit_cost,
                    quantity=int(order_qty),
                    country=country_of_origin,
                    shipping_cost_per_unit=shipping_cost_per_unit
                )
                
                # Calculate days until order/payment
                now = datetime.now()
                days_until_order = (order_date - now).days
                days_until_payment = (payment_date - now).days
                
                order_schedule = OrderSchedule(
                    part_id=part_id,
                    part_name=bom_item.part_name,
                    part_description=bom_item.part_name,  # Use part_name for description too
                    supplier_id=bom_item.supplier_id,
                    supplier_name=bom_item.supplier_name,
                    order_date=order_date,
                    qty=int(order_qty),
                    payment_date=payment_date,
                    unit_cost=bom_item.unit_cost,
                    total_cost=cost_breakdown['total_cost'],
                    days_until_order=days_until_order,
                    days_until_payment=days_until_payment,
                    status="pending"
                )
                
                order_schedules.append(order_schedule)
        
        return order_schedules
    
    def aggregate_orders_by_supplier(self, order_schedules: List[OrderSchedule]) -> List[SupplierOrderSummary]:
        """Aggregate orders by supplier and order date for consolidated purchasing"""
        
        # Group orders by supplier_id and order_date
        supplier_groups = {}
        
        for order in order_schedules:
            # Use supplier_id if available, otherwise use supplier_name, otherwise use "UNKNOWN"
            supplier_key = order.supplier_id or order.supplier_name or "UNKNOWN_SUPPLIER"
            order_date_key = order.order_date.date()  # Use just the date part
            
            # Create a composite key for supplier + date
            group_key = (supplier_key, order_date_key)
            
            if group_key not in supplier_groups:
                supplier_groups[group_key] = {
                    'supplier_id': order.supplier_id,
                    'supplier_name': order.supplier_name or "Unknown Supplier",
                    'order_date': order.order_date,
                    'payment_date': order.payment_date,  # Will be updated to latest payment date
                    'orders': [],
                    'total_cost': 0.0
                }
            
            supplier_groups[group_key]['orders'].append(order)
            supplier_groups[group_key]['total_cost'] += order.total_cost
            
            # Update payment date to the latest payment date in the group
            if order.payment_date > supplier_groups[group_key]['payment_date']:
                supplier_groups[group_key]['payment_date'] = order.payment_date
        
        # Convert to SupplierOrderSummary objects
        supplier_summaries = []
        now = datetime.now()
        
        for (supplier_key, order_date), group_data in supplier_groups.items():
            parts_list = [f"{order.part_name} (qty: {order.qty})" for order in group_data['orders']]
            days_until_order = (group_data['order_date'] - now).days
            days_until_payment = (group_data['payment_date'] - now).days
            
            summary = SupplierOrderSummary(
                supplier_id=group_data['supplier_id'],
                supplier_name=group_data['supplier_name'],
                order_date=group_data['order_date'],
                payment_date=group_data['payment_date'],
                total_parts=len(group_data['orders']),
                total_cost=group_data['total_cost'],
                parts=parts_list,
                days_until_order=days_until_order,
                days_until_payment=days_until_payment
            )
            
            supplier_summaries.append(summary)
        
        # Sort by order date
        supplier_summaries.sort(key=lambda x: x.order_date)
        
        return supplier_summaries
    
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
        # Count unique suppliers (use supplier_id if available, otherwise supplier_name)
        suppliers = set()
        for o in order_schedules:
            if o.supplier_id:
                suppliers.add(o.supplier_id)
            elif o.supplier_name:
                suppliers.add(o.supplier_name)
            else:
                suppliers.add("UNKNOWN")
        total_suppliers = len(suppliers)
        
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
        
        # Aggregate orders by supplier
        supplier_order_summaries = self.aggregate_orders_by_supplier(order_schedules)
        
        # Generate cash flow projection
        cash_flow_projection = self.generate_cash_flow_projection(
            order_schedules, start_date, end_date
        )
        
        # Calculate key metrics
        key_metrics = self.calculate_key_metrics(order_schedules)
        
        return {
            'order_schedules': order_schedules,
            'supplier_order_summaries': supplier_order_summaries,
            'cash_flow_projection': cash_flow_projection,
            'key_metrics': key_metrics
        } 