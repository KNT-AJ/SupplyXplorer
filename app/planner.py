import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session
from app.models import Product, Part, Supplier, BOM, Forecast, LeadTime, Order, Inventory
from app.schemas import OrderSchedule, CashFlowProjection, KeyMetrics, SupplierOrderSummary
from app.inventory_service import InventoryService
from app.tariff_calculator import TariffCalculator
from app.tariff_utils import (
    DEFAULT_COUNTRY_OF_ORIGIN_TARIFFED,
    DEFAULT_HTS_CODE,
    DEFAULT_IMPORTING_COUNTRY,
)

class SupplyPlanner:
    """Core planning engine for PartXplorer"""
    
    def __init__(self, db: Session):
        self.db = db
        self.tariff_calculator = TariffCalculator()
        self.inventory_service = InventoryService(db)
        
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
            
            # Track running inventory levels, including pending incoming orders that are expected before need date
            running_stock = current_stock
            # Bring in pending orders for this part within the window
            try:
                from app.models import Order as PendingOrder
                pending_orders = self.db.query(PendingOrder).filter(PendingOrder.part_id == part_id).all()
            except Exception:
                pending_orders = []
            
            # Generate orders
            for _, row in period_demand.iterrows():
                need_date = row['installation_date']
                demand_qty = row['demand_qty']
                
                # Add any pending orders that are expected to arrive before this need date
                for po in pending_orders:
                    eta = getattr(po, 'estimated_delivery_date', None)
                    if eta and eta <= need_date and getattr(po, 'status', 'pending') in ['pending', 'ordered']:
                        running_stock += int(getattr(po, 'qty', 0))
                
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

                # Consider shipping quote to override transit time and cost
                raw_country_of_origin = bom_item.country_of_origin
                country_of_origin = raw_country_of_origin or "USA"
                shipping_cost_per_unit = bom_item.shipping_cost or 0.0
                effective_shipping_lead_time = shipping_lead_time
                selected_quote = None
                try:
                    from app.models import ShippingQuote
                    preferred_mode = getattr(bom_item, 'shipping_mode', None)
                    q = (
                        self.db.query(ShippingQuote)
                        .filter((ShippingQuote.is_active == 'Yes'))
                        .order_by(ShippingQuote.created_at.desc())
                        .all()
                    )
                    for cand in q:
                        if preferred_mode:
                            if (cand.mode or '').lower() == preferred_mode.lower():
                                selected_quote = cand
                                break
                        else:
                            selected_quote = cand
                            break
                    if selected_quote:
                        # Override shipping lead time using quote transit days
                        td = None
                        if getattr(selected_quote, 'transit_days', None):
                            td = int(selected_quote.transit_days)
                        else:
                            tmin = getattr(selected_quote, 'transit_days_min', None)
                            tmax = getattr(selected_quote, 'transit_days_max', None)
                            if tmin and tmax:
                                td = int(round((tmin + tmax) / 2))
                            elif tmin:
                                td = int(tmin)
                        if td is not None and td >= 0:
                            effective_shipping_lead_time = td
                        # Estimate shipping cost per unit using quote
                        unit_weight = getattr(bom_item, 'unit_weight_kg', None)
                        unit_volume = getattr(bom_item, 'unit_volume_cbm', None)
                        est = 0.0
                        if unit_weight and getattr(selected_quote, 'cost_per_kg', None):
                            est = float(unit_weight) * float(selected_quote.cost_per_kg)
                        elif unit_volume and getattr(selected_quote, 'cost_per_cbm', None):
                            est = float(unit_volume) * float(selected_quote.cost_per_cbm)
                        if getattr(selected_quote, 'min_charge', None) and est > 0:
                            est = max(est, float(selected_quote.min_charge) / max(int(order_qty), 1))
                        if getattr(selected_quote, 'fuel_surcharge_pct', None) and est > 0:
                            est = est * (1.0 + float(selected_quote.fuel_surcharge_pct) / 100.0)
                        fees = 0.0
                        for fee_name in ['security_fee', 'handling_fee', 'other_fees']:
                            fee_val = getattr(selected_quote, fee_name, None)
                            if fee_val:
                                fees += float(fee_val)
                        if fees > 0:
                            est += fees / max(int(order_qty), 1)
                        if est > 0:
                            shipping_cost_per_unit = est
                except Exception:
                    pass

                # Recompute order date using possibly updated shipping lead time
                order_date = need_date - timedelta(days=(manufacturing_lead_time + effective_shipping_lead_time))
                # Payment date = order date + AP terms
                ap_terms = bom_item.ap_terms or 30
                payment_date = order_date + timedelta(days=ap_terms)

                subject_to_tariffs = (bom_item.subject_to_tariffs or "No")

                # Calculate total cost including tariffs and shipping
                # Determine effective country for tariff calculation
                effective_country = (
                    (raw_country_of_origin or DEFAULT_COUNTRY_OF_ORIGIN_TARIFFED)
                    if subject_to_tariffs == "Yes"
                    else "USA"
                )

                # Choose HTS for tariff calculation; default to stainless fittings when tariffed
                effective_hts = (
                    (bom_item.hts_code or DEFAULT_HTS_CODE)
                    if subject_to_tariffs == "Yes"
                    else (bom_item.hts_code or None)
                )

                cost_breakdown = self.tariff_calculator.get_total_cost_with_tariffs(
                    unit_cost=bom_item.unit_cost,
                    quantity=int(order_qty),
                    country=effective_country,
                    shipping_cost_per_unit=shipping_cost_per_unit,
                    hts_code=effective_hts,
                    importing_country=DEFAULT_IMPORTING_COUNTRY,
                    entry_date=None
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
                    status="pending",
                    country_of_origin=country_of_origin,
                    subject_to_tariffs=subject_to_tariffs,
                    shipping_cost_per_unit=shipping_cost_per_unit,
                    shipping_cost_total=cost_breakdown['shipping_cost'],
                    tariff_rate=cost_breakdown['tariff_rate'],
                    tariff_amount=cost_breakdown['tariff_amount'],
                    base_cost=cost_breakdown['base_cost'],
                    total_cost_without_tariff=(cost_breakdown['base_cost'] + cost_breakdown['shipping_cost'])
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
            total_tariff_amount = sum(getattr(order, 'tariff_amount', 0.0) for order in group_data['orders'])
            total_shipping_cost = sum(getattr(order, 'shipping_cost_total', 0.0) for order in group_data['orders'])
            
            summary = SupplierOrderSummary(
                supplier_id=group_data['supplier_id'],
                supplier_name=group_data['supplier_name'],
                order_date=group_data['order_date'],
                payment_date=group_data['payment_date'],
                total_parts=len(group_data['orders']),
                total_cost=group_data['total_cost'],
                parts=parts_list,
                days_until_order=days_until_order,
                days_until_payment=days_until_payment,
                total_tariff_amount=total_tariff_amount,
                total_shipping_cost=total_shipping_cost
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
        
        # Cash out in next 90 days and tariff spend
        cash_out_90d = 0.0
        tariff_spend_90d = 0.0
        for o in order_schedules:
            if 0 <= o.days_until_payment <= 90:
                cash_out_90d += o.total_cost
                tariff_spend_90d += getattr(o, 'tariff_amount', 0.0)
        
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
            total_suppliers=total_suppliers,
            tariff_spend_90d=tariff_spend_90d
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
    
    def generate_inventory_based_recommendations(self, start_date: datetime, end_date: datetime) -> Dict:
        """Generate order recommendations based on enhanced inventory projections"""
        
        # Get inventory alerts
        alerts = self.inventory_service.get_inventory_alerts()
        
        # Get projected inventory
        projected_inventory = self.inventory_service.get_projected_inventory()
        
        # Convert alerts to order recommendations
        urgent_orders = []
        recommended_orders = []
        
        for alert in alerts:
            if alert.alert_type == "shortage" and alert.severity in ["critical", "high"]:
                # Create urgent order recommendation
                order_date = datetime.now()
                estimated_delivery = order_date + timedelta(days=30)  # Default lead time
                
                urgent_order = OrderSchedule(
                    part_id=alert.part_id,
                    part_name=alert.part_name,
                    part_description=alert.part_name,
                    supplier_id=None,
                    supplier_name=None,
                    order_date=order_date,
                    qty=alert.suggested_order_qty or 50,
                    payment_date=order_date + timedelta(days=30),
                    unit_cost=0.0,  # To be filled from inventory data
                    total_cost=0.0,
                    status="urgent_recommendation",
                    days_until_order=0,
                    days_until_payment=30
                )
                urgent_orders.append(urgent_order)
                
            elif alert.alert_type == "reorder":
                # Create standard reorder recommendation
                order_date = datetime.now() + timedelta(days=alert.days_until_shortage or 14)
                estimated_delivery = order_date + timedelta(days=30)
                
                recommended_order = OrderSchedule(
                    part_id=alert.part_id,
                    part_name=alert.part_name,
                    part_description=alert.part_name,
                    supplier_id=None,
                    supplier_name=None,
                    order_date=order_date,
                    qty=alert.suggested_order_qty or 100,
                    payment_date=order_date + timedelta(days=30),
                    unit_cost=0.0,
                    total_cost=0.0,
                    status="recommended",
                    days_until_order=alert.days_until_shortage or 14,
                    days_until_payment=(alert.days_until_shortage or 14) + 30
                )
                recommended_orders.append(recommended_order)
        
        # Fill in unit costs from projected inventory
        for proj_item in projected_inventory:
            # Update urgent orders
            for order in urgent_orders:
                if order.part_id == proj_item.part_id:
                    order.unit_cost = proj_item.unit_cost
                    order.total_cost = order.qty * order.unit_cost
                    order.supplier_name = proj_item.supplier_name
            
            # Update recommended orders
            for order in recommended_orders:
                if order.part_id == proj_item.part_id:
                    order.unit_cost = proj_item.unit_cost
                    order.total_cost = order.qty * order.unit_cost
                    order.supplier_name = proj_item.supplier_name
        
        return {
            'urgent_orders': urgent_orders,
            'recommended_orders': recommended_orders,
            'alerts': alerts,
            'projected_inventory': projected_inventory
        } 