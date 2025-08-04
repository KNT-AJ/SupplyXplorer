#!/usr/bin/env python3
"""
SupplyXplorer CLI - Command-line interface for testing and automation
"""

import click
import pandas as pd
from datetime import datetime, timedelta
import requests
import json
from pathlib import Path

API_BASE = "http://localhost:8000"

@click.group()
def cli():
    """SupplyXplorer CLI - Inventory & Cash-Flow Planning Tool"""
    pass

@cli.command()
@click.option('--file', '-f', required=True, help='CSV file path')
def upload_forecast(file):
    """Upload sales forecast from CSV file"""
    try:
        with open(file, 'rb') as f:
            files = {'file': (Path(file).name, f, 'text/csv')}
            response = requests.post(f"{API_BASE}/upload/forecast", files=files)
            
        if response.status_code == 200:
            click.echo(f"✅ {response.json()['message']}")
        else:
            click.echo(f"❌ Error: {response.json()['detail']}")
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")

@cli.command()
@click.option('--file', '-f', required=True, help='CSV file path')
def upload_bom(file):
    """Upload Bill of Materials from CSV file"""
    try:
        with open(file, 'rb') as f:
            files = {'file': (Path(file).name, f, 'text/csv')}
            response = requests.post(f"{API_BASE}/upload/bom", files=files)
            
        if response.status_code == 200:
            click.echo(f"✅ {response.json()['message']}")
        else:
            click.echo(f"❌ Error: {response.json()['detail']}")
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")

@cli.command()
@click.option('--file', '-f', required=True, help='CSV file path')
def upload_leadtime(file):
    """Upload lead times from CSV file"""
    try:
        with open(file, 'rb') as f:
            files = {'file': (Path(file).name, f, 'text/csv')}
            response = requests.post(f"{API_BASE}/upload/leadtime", files=files)
            
        if response.status_code == 200:
            click.echo(f"✅ {response.json()['message']}")
        else:
            click.echo(f"❌ Error: {response.json()['detail']}")
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")

@cli.command()
@click.option('--start-date', '-s', default=None, help='Start date (YYYY-MM-DD)')
@click.option('--end-date', '-e', default=None, help='End date (YYYY-MM-DD)')
def run_planning(start_date, end_date):
    """Run the planning engine"""
    try:
        # Default dates if not provided
        if not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')
        if not end_date:
            end_date = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
        
        response = requests.post(
            f"{API_BASE}/plan/run",
            params={
                'start_date': f"{start_date}T00:00:00",
                'end_date': f"{end_date}T23:59:59"
            }
        )
        
        if response.status_code == 200:
            results = response.json()
            click.echo("✅ Planning completed successfully!")
            click.echo(f"📊 Generated {len(results['order_schedules'])} orders")
            click.echo(f"💰 Cash flow projections: {len(results['cash_flow_projection'])} periods")
            click.echo(f"📈 Key metrics calculated")
        else:
            click.echo(f"❌ Error: {response.text}")
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")

@cli.command()
@click.option('--start-date', '-s', default=None, help='Start date (YYYY-MM-DD)')
@click.option('--end-date', '-e', default=None, help='End date (YYYY-MM-DD)')
@click.option('--output', '-o', default='orders.csv', help='Output file path')
def export_orders(start_date, end_date, output):
    """Export order schedule to CSV"""
    try:
        # Default dates if not provided
        if not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')
        if not end_date:
            end_date = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
        
        response = requests.get(
            f"{API_BASE}/export/orders",
            params={
                'start_date': f"{start_date}T00:00:00",
                'end_date': f"{end_date}T23:59:59"
            }
        )
        
        if response.status_code == 200:
            csv_data = response.json()['csv_data']
            with open(output, 'w') as f:
                f.write(csv_data)
            click.echo(f"✅ Orders exported to {output}")
        else:
            click.echo(f"❌ Error: {response.text}")
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")

@cli.command()
@click.option('--start-date', '-s', default=None, help='Start date (YYYY-MM-DD)')
@click.option('--end-date', '-e', default=None, help='End date (YYYY-MM-DD)')
@click.option('--output', '-o', default='cashflow.csv', help='Output file path')
def export_cashflow(start_date, end_date, output):
    """Export cash flow projection to CSV"""
    try:
        # Default dates if not provided
        if not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')
        if not end_date:
            end_date = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
        
        response = requests.get(
            f"{API_BASE}/export/cashflow",
            params={
                'start_date': f"{start_date}T00:00:00",
                'end_date': f"{end_date}T23:59:59"
            }
        )
        
        if response.status_code == 200:
            csv_data = response.json()['csv_data']
            with open(output, 'w') as f:
                f.write(csv_data)
            click.echo(f"✅ Cash flow exported to {output}")
        else:
            click.echo(f"❌ Error: {response.text}")
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")

@cli.command()
@click.option('--start-date', '-s', default=None, help='Start date (YYYY-MM-DD)')
@click.option('--end-date', '-e', default=None, help='End date (YYYY-MM-DD)')
def show_metrics(start_date, end_date):
    """Show key performance metrics"""
    try:
        # Default dates if not provided
        if not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')
        if not end_date:
            end_date = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
        
        response = requests.get(
            f"{API_BASE}/metrics",
            params={
                'start_date': f"{start_date}T00:00:00",
                'end_date': f"{end_date}T23:59:59"
            }
        )
        
        if response.status_code == 200:
            metrics = response.json()
            click.echo("📊 Key Performance Metrics")
            click.echo("=" * 40)
            click.echo(f"Orders next 30 days: {metrics['orders_next_30d']}")
            click.echo(f"Orders next 60 days: {metrics['orders_next_60d']}")
            click.echo(f"Cash out 90 days: ${metrics['cash_out_90d']:,.2f}")
            click.echo(f"Largest purchase: ${metrics['largest_purchase']:,.2f}")
            click.echo(f"Total parts: {metrics['total_parts']}")
            click.echo(f"Total suppliers: {metrics['total_suppliers']}")
        else:
            click.echo(f"❌ Error: {response.text}")
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")

@cli.command()
def create_sample_data():
    """Create sample data for testing"""
    try:
        # Create sample products
        products = [
            {"sku_id": "PROD-001", "name": "Widget A", "description": "Basic widget"},
            {"sku_id": "PROD-002", "name": "Widget B", "description": "Advanced widget"},
        ]
        
        for product in products:
            response = requests.post(f"{API_BASE}/products", json=product)
            if response.status_code == 200:
                click.echo(f"✅ Created product: {product['name']}")
        
        # Create sample suppliers
        suppliers = [
            {"supplier_id": "SUPP-001", "name": "Supplier Alpha", "ap_terms_days": 30},
            {"supplier_id": "SUPP-002", "name": "Supplier Beta", "ap_terms_days": 45},
        ]
        
        for supplier in suppliers:
            response = requests.post(f"{API_BASE}/suppliers", json=supplier)
            if response.status_code == 200:
                click.echo(f"✅ Created supplier: {supplier['name']}")
        
        # Create sample parts
        parts = [
            {"part_id": "PART-001", "description": "Component X", "supplier_id": "SUPP-001", "unit_cost": 10.50},
            {"part_id": "PART-002", "description": "Component Y", "supplier_id": "SUPP-002", "unit_cost": 25.00},
            {"part_id": "PART-003", "description": "Component Z", "supplier_id": "SUPP-001", "unit_cost": 15.75},
        ]
        
        for part in parts:
            response = requests.post(f"{API_BASE}/parts", json=part)
            if response.status_code == 200:
                click.echo(f"✅ Created part: {part['description']}")
        
        # Create sample BOM
        bom_items = [
            {"sku_id": "PROD-001", "part_id": "PART-001", "qty_per": 2.0},
            {"sku_id": "PROD-001", "part_id": "PART-002", "qty_per": 1.0},
            {"sku_id": "PROD-002", "part_id": "PART-002", "qty_per": 3.0},
            {"sku_id": "PROD-002", "part_id": "PART-003", "qty_per": 1.5},
        ]
        
        for bom_item in bom_items:
            response = requests.post(f"{API_BASE}/bom", json=bom_item)
            if response.status_code == 200:
                click.echo(f"✅ Created BOM item: {bom_item['sku_id']} -> {bom_item['part_id']}")
        
        # Create sample forecasts
        forecasts = [
            {"sku_id": "PROD-001", "period_start": "2024-01-01T00:00:00", "units": 100},
            {"sku_id": "PROD-001", "period_start": "2024-02-01T00:00:00", "units": 120},
            {"sku_id": "PROD-002", "period_start": "2024-01-01T00:00:00", "units": 50},
            {"sku_id": "PROD-002", "period_start": "2024-02-01T00:00:00", "units": 75},
        ]
        
        for forecast in forecasts:
            response = requests.post(f"{API_BASE}/forecast", json=forecast)
            if response.status_code == 200:
                click.echo(f"✅ Created forecast: {forecast['sku_id']} - {forecast['units']} units")
        
        # Create sample lead times
        lead_times = [
            {"part_id": "PART-001", "days": 30},
            {"part_id": "PART-002", "days": 45},
            {"part_id": "PART-003", "days": 60},
        ]
        
        for lead_time in lead_times:
            response = requests.post(f"{API_BASE}/leadtime", json=lead_time)
            if response.status_code == 200:
                click.echo(f"✅ Created lead time: {lead_time['part_id']} - {lead_time['days']} days")
        
        click.echo("✅ Sample data created successfully!")
        
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    cli() 