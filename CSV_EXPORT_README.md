# CSV Export Functionality

The SupplyXplorer dashboard now includes comprehensive CSV export capabilities across all major data views. This allows users to easily export their data for external analysis, reporting, or backup purposes.

## Available Export Options

### 1. Dashboard Tab
- **Export Orders to CSV**: Exports order data based on the current view selection
  - **Detailed View**: Exports individual part orders with complete details
  - **Aggregated View**: Exports orders grouped by supplier with summary information
- **Export Cash Flow to CSV**: Exports cash flow projections for the selected date range

### 2. BOM Data Tab
- **Export to CSV**: Exports all Bill of Materials data including part information, costs, suppliers, and lead times

### 3. Forecast Data Tab
- **Export to CSV**: Exports all forecast data including SKU IDs, dates, and quantities

### 4. Inventory Tab
- **Export to CSV**: Exports current inventory levels, stock information, and supplier details

## How to Use CSV Export

1. **Navigate to the desired tab** (Dashboard, BOM Data, Forecast Data, or Inventory)
2. **For Dashboard orders**: Select your preferred view (Detailed or Aggregated) using the radio buttons
3. **Click the export button** - the button text will change based on your selected view:
   - "Export Detailed Orders to CSV" when in detailed view
   - "Export Aggregated Orders to CSV" when in aggregated view
4. **Your browser will automatically download** the CSV file with a descriptive filename

## Export File Details

### Dashboard Exports
- **Detailed Order Schedule (`detailed_order_schedule.csv`)**:
  - Columns: part_id, part_description, order_date, qty, payment_date, unit_cost, total_cost, status
  - Shows individual part orders with complete details
  - Date range: Based on your selected start and end dates

- **Aggregated Orders by Supplier (`aggregated_orders_by_supplier.csv`)**:
  - Columns: supplier_name, order_date, total_parts, total_cost, payment_date, days_until_order, days_until_payment
  - Shows orders grouped by supplier and order date
  - Date range: Based on your selected start and end dates

- **Cash Flow Projection (`cashflow_projection.csv`)**:
  - Columns: date, total_outflow, total_inflow, net_cash_flow, cumulative_cash_flow
  - Date range: Based on your selected start and end dates

### Data Exports
- **BOM Data (`bom_data.csv`)**:
  - Columns: id, product_id, part_id, part_name, quantity, unit_cost, cost_per_product, beginning_inventory, supplier_id, supplier_name, manufacturer, ap_terms, manufacturing_lead_time, shipping_lead_time, created_at, updated_at

- **Forecast Data (`forecast_data.csv`)**:
  - Columns: id, sku_id, period_start, units, created_at, updated_at

- **Inventory Data (`inventory_data.csv`)**:
  - Columns: id, part_id, part_name, current_stock, minimum_stock, maximum_stock, unit_cost, total_value, supplier_id, supplier_name, location, notes, created_at, updated_at

## API Endpoints

The CSV export functionality is powered by dedicated API endpoints:

- `GET /export/orders?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` (Detailed orders)
- `GET /export/orders-by-supplier?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` (Aggregated orders)
- `GET /export/cashflow?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
- `GET /export/bom`
- `GET /export/forecast`
- `GET /export/inventory`

These endpoints return CSV files as downloadable attachments, making them suitable for direct browser downloads or programmatic access.

## Testing CSV Export

To test the CSV export functionality:

1. **Start the backend server**:
   ```bash
   python main.py
   ```

2. **Load sample data** (optional):
   ```bash
   python load_sample_data.py
   ```

3. **Test the export endpoints**:
   ```bash
   python test_export.py
   ```

4. **Start the dashboard**:
   ```bash
   python app/dashboard.py
   ```
   
5. **Visit http://localhost:8050** and test the export buttons in each tab

## Notes

- Export buttons are only available when data exists in the corresponding tables
- Dashboard exports (orders and cash flow) require that the planning engine has been run first
- The order export button text dynamically updates based on your selected view (Detailed vs Aggregated)
- Detailed exports show individual part orders, while aggregated exports show supplier-level summaries
- All exports include timestamps and are formatted for easy import into spreadsheet applications
- File downloads use descriptive filenames to help organize exported data
- The system handles both populated and empty datasets gracefully
