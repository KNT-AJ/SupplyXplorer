"""
Enhanced inventory service with projected inventory calculations
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Inventory, Order, BOM, Forecast
from app.schemas import (
    ProjectedInventoryBase,
    InventoryProjection,
    InventoryAlert
)


class InventoryService:
    """Enhanced inventory service with projections and alerts"""

    def __init__(self, db: Session):
        self.db = db

    def get_projected_inventory(self, part_id: Optional[str] = None, threshold: int = 80) -> List[ProjectedInventoryBase]:
        """Get projected inventory with pending orders and allocations
        Uses fuzzy mapping between pending orders and inventory to compute pending_qty.
        """

        # Base inventory query
        query = self.db.query(Inventory)
        if part_id:
            query = query.filter(Inventory.part_id == part_id)

        inventory_items = query.all()
        projected_items = []

        # Build a map of pending qty by inventory part using fuzzy mapping once
        pending_map, earliest_map = self._get_pending_qty_map(threshold)

        for item in inventory_items:
            # Pending quantities via mapping (fallback to legacy method if missing)
            pending_qty = pending_map.get(item.part_id)
            if pending_qty is None:
                pending_qty = self._get_pending_quantity(item.part_id)

            # Calculate allocated quantities (for production)
            allocated_qty = self._get_allocated_quantity(item.part_id)

            # Calculate net available
            net_available = item.current_stock + pending_qty - allocated_qty

            # Calculate days of supply
            days_of_supply = self._calculate_days_of_supply(item.part_id, net_available)

            # Determine shortage risk
            shortage_risk = self._assess_shortage_risk(
                item.current_stock,
                net_available,
                item.minimum_stock,
                days_of_supply
            )

            # Pending orders summary using earliest mapped date if available
            earliest_date = earliest_map.get(item.part_id)
            if earliest_date:
                pending_summary = f"{pending_qty} units expected by {earliest_date.strftime('%Y-%m-%d')}"
            else:
                pending_summary = self._get_pending_orders_summary(item.part_id)

            projected_item = ProjectedInventoryBase(
                part_id=item.part_id,
                part_name=item.part_name,
                current_stock=item.current_stock,
                pending_qty=pending_qty,
                allocated_qty=allocated_qty,
                net_available=net_available,
                days_of_supply=days_of_supply,
                minimum_stock=item.minimum_stock,
                maximum_stock=item.maximum_stock,
                unit_cost=item.unit_cost,
                total_value=item.total_value,
                supplier_name=item.supplier_name,
                location=item.location,
                shortage_risk=shortage_risk,
                pending_orders_summary=pending_summary
            )
            projected_items.append(projected_item)

        return projected_items

    def _get_pending_qty_map(self, threshold: int = 80) -> Tuple[Dict[str, int], Dict[str, Optional[datetime]]]:
        """Build a mapping from inventory part_id -> aggregated pending qty using fuzzy matching.
        Returns a tuple of (qty_map, earliest_eta_map).
        """
        # Gather data
        inventory_items = self.db.query(Inventory).all()
        orders = self.db.query(Order).filter(Order.status.in_(["pending", "ordered"])) .all()
        qty_map: Dict[str, int] = {inv.part_id: 0 for inv in inventory_items}
        eta_map: Dict[str, Optional[datetime]] = {}

        if not orders:
            return qty_map, eta_map

        # Prepare strings for matching: prefer part_id; fallback to part_name if available
        try:
            from rapidfuzz import fuzz, process
            inv_keys = []
            key_to_part = {}
            for inv in inventory_items:
                keys = [inv.part_id]
                if inv.part_name and inv.part_name not in keys:
                    keys.append(inv.part_name)
                for k in keys:
                    inv_keys.append(k)
                    key_to_part[k] = inv.part_id

            for o in orders:
                candidate = o.part_id or ""
                # try best among both IDs and names
                best = process.extractOne(candidate, inv_keys, scorer=fuzz.token_set_ratio)
                if best and best[1] >= threshold:
                    mapped_part = key_to_part[best[0]]
                    qty_map[mapped_part] = qty_map.get(mapped_part, 0) + int(o.qty or 0)
                    eta = o.estimated_delivery_date
                    if eta:
                        prev = eta_map.get(mapped_part)
                        eta_map[mapped_part] = min(prev, eta) if prev else eta
        except Exception:
            # Fallback: exact match on part_id only
            for o in orders:
                if o.part_id in qty_map:
                    qty_map[o.part_id] += int(o.qty or 0)
                    eta = o.estimated_delivery_date
                    if eta:
                        prev = eta_map.get(o.part_id)
                        eta_map[o.part_id] = min(prev, eta) if prev else eta

        return qty_map, eta_map

    def get_inventory_projections(
        self,
        start_date: datetime,
        end_date: datetime,
        part_id: Optional[str] = None
    ) -> List[InventoryProjection]:
        """Get time-based inventory projections"""

        projections = []

        # Get relevant parts
        if part_id:
            parts = [part_id]
        else:
            parts = [item.part_id for item in self.db.query(Inventory.part_id).distinct()]

        # Generate weekly projections
        current_date = start_date
        while current_date <= end_date:
            for part in parts:
                projection = self._calculate_inventory_projection(part, current_date)
                if projection:
                    projections.append(projection)
            current_date += timedelta(days=7)  # Weekly intervals

        return projections

    def get_inventory_alerts(self, days_ahead: int = 90) -> List[InventoryAlert]:
        """Generate inventory alerts for shortages and recommendations"""

        alerts = []
        end_date = datetime.now() + timedelta(days=days_ahead)

        inventory_items = self.db.query(Inventory).all()

        for item in inventory_items:
            # Get projected inventory
            projected = self.get_projected_inventory(item.part_id)[0]

            # Check for immediate shortage
            if projected.current_stock <= projected.minimum_stock:
                alert = InventoryAlert(
                    part_id=item.part_id,
                    part_name=item.part_name,
                    alert_type="shortage",
                    current_stock=projected.current_stock,
                    target_stock=projected.minimum_stock,
                    severity="high" if projected.current_stock == 0 else "medium",
                    recommended_action=f"Order {projected.minimum_stock - projected.current_stock + 50} units immediately",
                    days_until_shortage=0,
                    suggested_order_qty=projected.minimum_stock - projected.current_stock + 50
                )
                alerts.append(alert)

            # Check for future shortage based on projections
            elif projected.days_of_supply and projected.days_of_supply < 30:
                days_until_shortage = int(projected.days_of_supply)
                suggested_qty = self._calculate_suggested_order_quantity(item.part_id)

                alert = InventoryAlert(
                    part_id=item.part_id,
                    part_name=item.part_name,
                    alert_type="reorder",
                    current_stock=projected.current_stock,
                    target_stock=projected.minimum_stock,
                    severity="low" if days_until_shortage > 14 else "medium",
                    recommended_action=f"Consider ordering {suggested_qty} units within {days_until_shortage - 7} days",
                    days_until_shortage=days_until_shortage,
                    suggested_order_qty=suggested_qty
                )
                alerts.append(alert)

            # Check for excess inventory
            elif projected.maximum_stock and projected.net_available > projected.maximum_stock:
                excess_qty = projected.net_available - projected.maximum_stock
                alert = InventoryAlert(
                    part_id=item.part_id,
                    part_name=item.part_name,
                    alert_type="excess",
                    current_stock=projected.current_stock,
                    target_stock=projected.maximum_stock,
                    severity="low",
                    recommended_action=f"Consider reducing future orders - excess of {excess_qty} units",
                    suggested_order_qty=-excess_qty
                )
                alerts.append(alert)

        # Sort alerts by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        alerts.sort(key=lambda x: severity_order.get(x.severity, 4))

        return alerts

    def _get_pending_quantity(self, part_id: str) -> int:
        """Get total pending quantity for a part with fuzzy matching"""
        # First try exact match
        result = self.db.query(func.sum(Order.qty)).filter(
            Order.part_id == part_id,
            Order.status.in_(["pending", "ordered"])
        ).scalar()

        if result and result > 0:
            return result

        # If no exact match, try fuzzy matching
        try:
            from rapidfuzz import fuzz, process

            # Get all pending orders
            all_orders = self.db.query(Order).filter(
                Order.status.in_(["pending", "ordered"])
            ).all()

            if not all_orders:
                return 0

            # Create list of part_ids from orders
            order_part_ids = [order.part_id for order in all_orders if order.part_id]

            if not order_part_ids:
                return 0

            # Find best fuzzy match
            best_match = process.extractOne(
                part_id,
                order_part_ids,
                scorer=fuzz.ratio
            )

            # Use match if confidence is high enough (80% threshold)
            if best_match and best_match[1] >= 80:
                matched_part_id = best_match[0]
                fuzzy_result = self.db.query(func.sum(Order.qty)).filter(
                    Order.part_id == matched_part_id,
                    Order.status.in_(["pending", "ordered"])
                ).scalar()
                return fuzzy_result or 0

        except ImportError:
            # rapidfuzz not available, fallback to exact match only
            pass
        except Exception:
            # Any other error, fallback to exact match
            pass

        return 0

    def _get_allocated_quantity(self, part_id: str, days_ahead: int = 90) -> int:
        """Calculate allocated quantity based on production forecasts"""

        # Get BOM requirements for this part
        bom_items = self.db.query(BOM).filter(BOM.part_id == part_id).all()
        if not bom_items:
            return 0

        # Get forecasts for the next period
        end_date = datetime.now() + timedelta(days=days_ahead)
        forecasts = self.db.query(Forecast).filter(
            Forecast.installation_date <= end_date
        ).all()

        total_allocated = 0
        for bom_item in bom_items:
            for forecast in forecasts:
                if forecast.system_sn == bom_item.product_id:
                    total_allocated += int(bom_item.quantity * forecast.units)

        return total_allocated

    def _calculate_days_of_supply(self, part_id: str, available_qty: int) -> Optional[float]:
        """Calculate days of supply based on demand"""

        if available_qty <= 0:
            return 0.0

        # Calculate average daily demand based on recent forecasts
        end_date = datetime.now() + timedelta(days=365)
        forecasts = self.db.query(Forecast).filter(
            Forecast.installation_date <= end_date
        ).all()

        # Get BOM requirements
        bom_items = self.db.query(BOM).filter(BOM.part_id == part_id).all()
        if not bom_items:
            return None

        annual_demand = 0
        for bom_item in bom_items:
            for forecast in forecasts:
                if forecast.system_sn == bom_item.product_id:
                    annual_demand += bom_item.quantity * forecast.units

        if annual_demand == 0:
            return None

        daily_demand = annual_demand / 365
        return available_qty / daily_demand if daily_demand > 0 else None

    def _assess_shortage_risk(
        self,
        current_stock: int,
        net_available: int,
        minimum_stock: int,
        days_of_supply: Optional[float]
    ) -> str:
        """Assess shortage risk level"""

        if current_stock <= 0:
            return "Critical"
        elif current_stock <= minimum_stock:
            return "High"
        elif net_available <= minimum_stock:
            return "High"
        elif days_of_supply and days_of_supply < 14:
            return "High"
        elif days_of_supply and days_of_supply < 30:
            return "Medium"
        else:
            return "Low"

    def _get_pending_orders_summary(self, part_id: str) -> Optional[str]:
        """Get summary of pending orders for a part with fuzzy matching"""

        # First try exact match
        orders = self.db.query(Order).filter(
            Order.part_id == part_id,
            Order.status.in_(["pending", "ordered"])
        ).all()

        # If no exact match, try fuzzy matching
        if not orders:
            try:
                from rapidfuzz import fuzz, process

                # Get all pending orders
                all_orders = self.db.query(Order).filter(
                    Order.status.in_(["pending", "ordered"])
                ).all()

                if not all_orders:
                    return None

                # Create list of part_ids from orders
                order_part_ids = [order.part_id for order in all_orders if order.part_id]

                if not order_part_ids:
                    return None

                # Find best fuzzy match
                best_match = process.extractOne(
                    part_id,
                    order_part_ids,
                    scorer=fuzz.ratio
                )

                # Use match if confidence is high enough (80% threshold)
                if best_match and best_match[1] >= 80:
                    matched_part_id = best_match[0]
                    orders = self.db.query(Order).filter(
                        Order.part_id == matched_part_id,
                        Order.status.in_(["pending", "ordered"])
                    ).all()

            except ImportError:
                # rapidfuzz not available, fallback to exact match only
                pass
            except Exception:
                # Any other error, fallback to exact match
                pass

        if not orders:
            return None

        total_qty = sum(order.qty for order in orders)
        earliest_date = min(order.estimated_delivery_date for order in orders if order.estimated_delivery_date)

        if earliest_date:
            return f"{total_qty} units expected by {earliest_date.strftime('%Y-%m-%d')}"
        else:
            return f"{total_qty} units pending"

    def _calculate_inventory_projection(self, part_id: str, projection_date: datetime) -> Optional[InventoryProjection]:
        """Calculate inventory projection for a specific date"""

        # Get current inventory
        inventory = self.db.query(Inventory).filter(Inventory.part_id == part_id).first()
        if not inventory:
            return None

        # Calculate pending deliveries by this date
        pending_deliveries = self.db.query(func.sum(Order.qty)).filter(
            Order.part_id == part_id,
            Order.status.in_(["pending", "ordered"]),
            Order.estimated_delivery_date <= projection_date
        ).scalar() or 0

        # Calculate planned consumption by this date
        planned_consumption = self._get_allocated_quantity(part_id, (projection_date - datetime.now()).days)

        # Calculate projected stock
        projected_stock = inventory.current_stock + pending_deliveries - planned_consumption
        net_position = max(0, projected_stock)

        # Calculate days of supply for this projection
        days_of_supply = self._calculate_days_of_supply(part_id, net_position)

        # Assess risk
        shortage_risk = self._assess_shortage_risk(
            projected_stock,
            net_position,
            inventory.minimum_stock,
            days_of_supply
        )

        return InventoryProjection(
            part_id=part_id,
            part_name=inventory.part_name,
            projection_date=projection_date,
            projected_stock=projected_stock,
            pending_deliveries=pending_deliveries,
            planned_consumption=planned_consumption,
            net_position=net_position,
            days_of_supply=days_of_supply,
            shortage_risk=shortage_risk
        )

    def _calculate_suggested_order_quantity(self, part_id: str) -> int:
        """Calculate suggested order quantity"""

        inventory = self.db.query(Inventory).filter(Inventory.part_id == part_id).first()
        if not inventory:
            return 0

        # Simple reorder logic: bring up to maximum or 2x minimum
        target_qty = inventory.maximum_stock or (inventory.minimum_stock * 2)
        current_and_pending = inventory.current_stock + self._get_pending_quantity(part_id)

        return max(0, target_qty - current_and_pending)
