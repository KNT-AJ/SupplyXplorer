# SupplyXplorer v1.0.0

Inventory & Cash-Flow Planning Tool

Plan part purchases and cash outflows from a sales/installation forecast using BOM multipliers, current inventory, lead times, AP terms, and tariffs. Built with Python, FastAPI, Plotly Dash, and Pandas. August 2025.

## 🚀 Features

- **Data Management**: Upload Forecast, BOM, Inventory (CSV) with robust parsing and validation
- **Smart Inventory Planning**: Inventory-aware planning with projected stock levels, pending orders integration, and automated shortage alerts
- **Advanced Inventory Analytics**:
  - Real-time projected inventory with pending deliveries and allocated quantities
  - Shortage risk assessment with days-of-supply calculations
  - Time-based inventory projections and alerts
  - Automated reorder recommendations
- **Pending Orders Management**: Track placed/expected POs with PDF upload and AI-powered extraction (multi-LLM fallback: Gemini 2.0 → GPT-4o mini → Gemini 2.5)
- **Supplier Intelligence**: Consolidate orders by supplier and order date with payment scheduling
- **Tariff-Aware Costing**: HTS/origin-based tariff logic with real-time rate calculations and shipping costs
- **Interactive Dashboard**: Upload data, run planning, visualize orders and cash flow with inline editors and export capabilities
- **Production-Ready API**: Full REST API with OpenAPI docs, comprehensive validation, and CSV exports

### Repository structure

```
SupplyXplorer/
├─ app/
│  ├─ api.py                 # FastAPI app and endpoints (planning, uploads, exports, inventory)
│  ├─ planner.py             # Planning engine (SupplyPlanner)
│  ├─ inventory_service.py   # Projected inventory, alerts, recommendations
│  ├─ models.py              # SQLAlchemy models including ShippingQuote
│  ├─ schemas.py             # Pydantic schemas
│  ├─ database.py            # DB setup and lightweight SQLite schema upgrades
│  ├─ dashboard.py           # Dash UI
│  ├─ cli.py                 # Simple CLI helpers
│  ├─ pdf_llm_extractor.py   # Multi-LLM PDF extraction for pending orders
│  ├─ tariff_calculator.py   # Tariff and duties calculator
│  └─ system_sn_utils.py     # System SN mapping/validation
├─ assets/                   # Logo and dashboard custom CSS
├─ sample_data/              # Example CSVs and PDFs
├─ run_app.py                # Convenience launcher (starts API and Dashboard)
├─ main.py                   # API entry point
├─ requirements.txt          # Python dependencies
├─ Dockerfile, docker-compose.yml
└─ README.md
```

- **Flexible Deployment**: Docker & Compose support; SQLite (dev) or PostgreSQL (prod)

### Tech stack
- **Backend**: FastAPI 0.115.6, SQLAlchemy 1.4.53, Pydantic 2.10.4
- **Frontend**: Dash 2.16.1 + dash-bootstrap-components 1.5.0, Plotly 5.18.0
- **Data Processing**: Pandas 2.2.0, NumPy 1.26.4



- **AI/ML**: Google Generative AI 1.2.0, OpenAI 1.43.0 (multi-LLM PDF extraction)
- **Document Processing**: pdfplumber 0.11.4, text analysis with fuzzy matching (rapidfuzz 3.9.6)
- **Database**: SQLite (default) or PostgreSQL (via DATABASE_URL)
- **Configuration**: PyYAML 6.0.2 for supplier aliases and tariff configurations

## �️ Quick start

Prereqs: Python 3.11+ and pip

1) Create venv and install deps
```bash
python3.11 -m venv supplyxplorer_env
source supplyxplorer_env/bin/activate
pip install -r requirements.txt
```

2) Start both servers (recommended)
```bash
python run_app.py
```

Alternative: start separately
```bash
python main.py            # API at :8000
python app/dashboard.py   # Dashboard at :8050
```

Note: run_app.py uses absolute paths to a local virtualenv; if it fails on your setup, start the API and Dashboard separately as shown above.


Access:
- API docs: http://localhost:8000/docs
- Dashboard: http://localhost:8050


### Data model (simplified)

Core tables (see app/models.py):
- Product(sku_id, name, description)
- Part(part_id, part_name, supplier_id/name, unit_cost, safety_stock_pct)
- Supplier(supplier_id, name, ap_terms_days)
- BOM(product_id, part_id, part_name, quantity, unit_cost, ap_terms, manufacturing_lead_time, shipping_lead_time, shipping_mode, unit_weight_kg, unit_volume_cbm, country_of_origin, shipping_cost, subject_to_tariffs, hts_code)
- Forecast(system_sn, installation_date, units)
- Inventory(part_id unique, current_stock, minimum_stock, maximum_stock, unit_cost, subject_to_tariffs, hts_code)
- Order(pending orders: part_id, qty, unit_cost, order_date, estimated_delivery_date, payment_date, status, po_number)
- ShippingQuote(provider_name, mode, transit_days/min/max, cost_per_kg/cbm, min_charge, fuel_surcharge_pct, fees, is_active)

These map to Pydantic response models in app/schemas.py used by the API.

See also: RUN_INSTRUCTIONS.md


## 🧰 CLI (optional)

Simple command-line helpers for automation and testing live against the running API.

Examples:
```bash
# Upload CSVs
python app/cli.py upload_forecast -f sample_data/forecast_sample.csv
python app/cli.py upload_bom -f sample_data/bom_sample_with_suppliers.csv


# Run planner and view metrics
python app/cli.py run_planning --start-date 2025-01-01 --end-date 2025-12-31
python app/cli.py show_metrics --start-date 2025-01-01 --end-date 2025-12-31

# Export results to CSV
python app/cli.py export_orders --start-date 2025-01-01 --end-date 2025-12-31 --output orders.csv
python app/cli.py export_cashflow --start-date 2025-01-01 --end-date 2025-12-31 --output cashflow.csv
```

Note: The CLI expects the API to be running at http://localhost:8000.

## 📥 CSV upload formats (current)

### Forecast upload
Two supported formats:
- New format (preferred):
```
System SN,Installation Date,quantity
JT080001,2025-08-15,2
JT090001,2025-09-01,1
```

Notes:
- System SN format is [YearCode][MM][####], e.g., JT080001 (see “Planning engine details” for mapping and logic)
- On legacy uploads, System SNs are generated sequentially per month and year

### BOM upload
Expected minimum columns (flexible mapping handled in code):
- part_name, units_needed, cost_per_unit

Optional/recognized columns: cost_per_product, beginning_inventory, supplier, manufacturer, ap_term, ap_month_lag_days, manufacturing_days_lead, shipping_days_lead, country_of_origin, shipping_cost, hts_code, subject_to_tariffs

Example:
```
part_name,units_needed,cost_per_unit,supplier,manufacturer,ap_term,manufacturing_days_lead,shipping_days_lead,country_of_origin,shipping_cost,subject_to_tariffs
Stainless Tee 1/2",2,3.25,Oak Stills,Oak Stills,Net 30,30,45,China,0.20,Yes
```
Behavior:
- supplier → supplier_name and a normalized supplier_id
- ap_term like “Net 30” → AP terms days
- If subject_to_tariffs == Yes and COO missing, defaults to China
- hts_code defaults to 7307.29.0090 if tariffed

### Inventory upload
Required: part_id, part_name, current_stock, unit_cost

Optional: minimum_stock, maximum_stock, supplier_name, location, notes, subject_to_tariffs, hts_code

Example:
```
part_id,part_name,current_stock,minimum_stock,maximum_stock,unit_cost,supplier_name,location,notes
TEE_1_2_SS,Stainless Tee 1/2",150,50,500,3.25,Oak Stills,Warehouse A,High demand
```

- **Enhanced Features:**
- **Projected inventory calculations** - Automatically calculates net available stock (current + pending - allocated)
- **Shortage risk assessment** - Color-coded alerts based on days-of-supply and minimum stock levels
- **Pending orders integration** - Shows expected deliveries and their impact on future stock levels
- **Reorder recommendations** - AI-driven suggestions for optimal order quantities and timing

### PDF Invoice/Quote Processing
The system includes AI-powered extraction of pending orders from supplier invoices and quotes:

**Supported formats:** PDF invoices, quotes, purchase confirmations

**Extraction process:**
- Upload PDF through dashboard or API endpoint
- Multi-LLM fallback chain ensures high success rate:
  1. **Gemini 2.0 Flash** (primary) - Latest Google model with advanced reasoning
  2. **GPT-4o mini** (fallback) - OpenAI's efficient model for structured extraction
  3. **Gemini 2.5 Flash Lite** (final fallback) - Lightweight but capable extraction

**Extracted data:**
- Part IDs and descriptions
- Supplier information
- Order dates and delivery estimates
- Quantities and unit costs
- PO numbers and status
- Payment terms and dates

**Validation & Integration:**
- Automatic data validation and normalization
- Direct integration with inventory projections
- Status tracking (pending → ordered → received)
- Bulk editing and export capabilities

## 🔎 Planning engine details

Source: app/planner.py (class SupplyPlanner). Auxiliary services: app.inventory_service.InventoryService, app.tariff_calculator.TariffCalculator.

Inputs
- Forecast rows: system_sn, installation_date, units
- BOM rows: product_id, part_id, part_name, quantity, unit_cost, supplier_name/id, ap_terms, manufacturing_lead_time, shipping_lead_time, shipping_mode, unit_weight_kg, unit_volume_cbm, country_of_origin, subject_to_tariffs, hts_code, shipping_cost
- Inventory rows (optional): part_id, current_stock, minimum_stock, maximum_stock
- Pending Orders (optional): part_id, qty, status, estimated_delivery_date
- Tariff config (optional): tariff_rates.json overrides
- Shipping quotes (optional): app.models.ShippingQuote rows to override lead time and estimate freight

Algorithm overview
1) Demand derivation (forecast × BOM)
   - Read all forecasts within [start_date, end_date]
   - For each forecast row, gather BOM items where BOM.product_id == forecast.system_sn
   - If no exact match and BOM contains a single product_id, use that BOM for all forecasts (common case)
   - Emit demand rows: part_id, part_name, installation_date, demand_qty = forecast.units × BOM.quantity

2) Per‑part time-phased planning
   For each part_id with demand (sorted by installation_date):
   - Initialize running_stock = current_stock (from Inventory or 0);
     minimum_stock = Inventory.minimum_stock or 0
   - Safety stock = max(avg(period_demand) × 10%, minimum_stock)
   - Total lead = manufacturing_lead_time + shipping_lead_time (defaults 30 + 0)
   - Before each need_date, add pending orders: for any Order with status in [pending, ordered] and ETA ≤ need_date, running_stock += qty
   - available_for_demand = max(0, running_stock − safety_stock)
   - net_demand = max(0, demand_qty − available_for_demand)
   - Consume demand: running_stock = max(0, running_stock − demand_qty)
   - If net_demand > 0, create a planned order:
     - order_qty = net_demand; if running_stock < safety_stock, top up by (safety_stock − running_stock)
     - Candidate shipping lead time/cost from BOM; may be overridden by ShippingQuote (see next)
     - order_date = need_date − (manufacturing_lead_time + effective_shipping_lead_time)
     - payment_date = order_date + (ap_terms or 30)

3) Freight and lead time overrides via ShippingQuote (optional)
   - If any active ShippingQuote exists, optionally filtered by BOM.shipping_mode, choose the most recent matching quote
   - effective_shipping_lead_time uses quote.transit_days, or avg(transit_days_min, transit_days_max)
   - shipping_cost_per_unit is estimated from quote and BOM dimensional data:
     - If unit_weight_kg and cost_per_kg → weight × cost_per_kg; else if unit_volume_cbm and cost_per_cbm → volume × cost_per_cbm
     - Enforce min_charge per order (amortized per unit) and apply fuel/fees (fuel_surcharge_pct, security_fee, handling_fee, other_fees)

4) Costing and tariffs
   - Base cost = unit_cost × qty; Shipping = shipping_cost_per_unit × qty
   - Effective tariff rate from TariffCalculator.get_effective_tariff_rate(country_of_origin, hts_code, importing_country="USA")


     - Special rule: HTS 7307.29.0090 of China into USA → 30% (5% MFN + 25% Section 301)
     - Otherwise country map with default 3% for unknowns
   - Tariff amount = base_cost × tariff_rate; total_cost = base + shipping + tariff
   - OrderSchedule records include cost breakdown: base_cost, shipping_cost_total, tariff_amount, tariff_rate, total_cost

5) Supplier aggregation
   - Group OrderSchedule by (supplier_id/name, order_date), summing total_cost, tariff_amount, shipping; collect part names
   - Compute payment_date per group via AP terms; expose SupplierOrderSummary

6) Cash flow projection
   - Group total_cost by payment_date to compute outflows; calculate daily net and cumulative balances

7) Key metrics
   - Orders next 30/60 days (by order_date)
   - Cash out and tariff spend next 90 days (by payment_date)
   - Largest purchase, counts of unique parts and suppliers

Edge cases and defaults
- No demand → returns empty results
- Missing BOM fields → defaults: manufacturing_lead_time 30d, shipping_lead_time 0d, ap_terms 30d, USA origin, no tariff
- Safety stock never below minimum_stock; pending orders counted once per need date

System SN logic
- Format: [YearCode][MM][####] where #### is the monthly sequence
- Year codes map 2025→JT, 2026→JW, … (see app/system_sn_utils.py)
- Legacy forecast uploads can auto-generate sequential SNs per month

Inventory-driven recommendations
- The planner can also produce urgent/reorder suggestions from InventoryService projections and alerts (/inventory/alerts, /inventory/recommendations) to surface near-term actions

## 📊 Dashboard

### Tabs Overview:
- **Data & Planning**: Upload Forecast/BOM/Inventory, set date ranges, run planning engine
- **Dashboard**: Key metrics, order schedules (detailed/aggregated views), cash flow charts, CSV exports
- **BOM Data / Forecast Data**: Inline editable tables with bulk save and CSV export capabilities
- **Inventory**: Enhanced inventory management with:
  - Real-time projected stock levels (current + pending - allocated)
  - Shortage risk alerts with color-coded severity levels
  - Days-of-supply calculations and reorder recommendations
  - Pending orders integration showing expected deliveries
- **Pending Orders**: Comprehensive PO management with:
  - PDF invoice/quote upload with AI-powered data extraction
  - Multi-LLM fallback chain (Gemini 2.0 Flash → GPT-4o mini → Gemini 2.5 Flash Lite)
  - Inline editing, status tracking, and delivery date management
  - Integration with inventory projections for accurate planning
- **Tariffs**: Interactive tariff calculator and configuration management (tariff_rates.json)

## 🔌 API highlights

### Planning & Analytics:
- **POST /plan/run** - Execute planning engine with inventory projections
- **GET /orders, /orders/by-supplier, /cashflow, /metrics** - Retrieve planning results
- **GET /export/orders, /export/orders-by-supplier, /export/cashflow** - CSV exports

### Enhanced Inventory Management:
- **GET /inventory/projected** - Real-time projected inventory with pending orders and allocations
- **GET /inventory/projections** - Time-based inventory forecasting with shortage predictions
- **GET /inventory/alerts** - Automated shortage/excess alerts with reorder recommendations
- **GET /inventory/recommendations** - AI-driven order suggestions based on demand patterns

### Pending Orders & AI Extraction:
- **POST /orders/pending/upload-pdf** - Upload invoice/quote PDFs with multi-LLM extraction
- **GET/POST/PUT/DELETE /orders/pending** - Full CRUD operations for pending orders
- **GET /export/orders-pending** - Export pending orders data

### Data Management:
- **POST /upload/forecast, /upload/bom, /upload/inventory** - Bulk data uploads with validation
- **GET/POST/PUT/DELETE /inventory** - Complete inventory management
- **GET /export/bom, /export/forecast, /export/inventory** - Data exports

### Tariff & Configuration:
- **POST /tariff-config** - Upload tariff rate configurations
- **POST /tariff/quote** - Real-time tariff calculations

All endpoints documented at **/docs** with interactive testing interface.

## 🐳 Docker & Compose

Dockerfile runs both API (8000) and Dash (8050) in one container. docker-compose.yml includes Postgres. Set DATABASE_URL for the app service when using Postgres.

Quick use:
```bash
docker compose up -d
```

## ⚙️ Configuration

### Environment Variables
- **DATABASE_URL** (default: sqlite:///./supplyxplorer.db)
- **API_HOST, API_PORT** (default: 0.0.0.0:8000)
- **DASHBOARD_PORT** (default: 8050)

### AI PDF Extraction (Optional)
For automated PDF processing, configure API keys in your environment:
- **GOOGLE_API_KEY** - For Gemini models (primary extraction)
- **OPENAI_API_KEY** - For GPT-4o mini (fallback extraction)

**Note:** PDF extraction works with the multi-LLM fallback chain. If no API keys are configured, PDFs can still be uploaded but will require manual data entry.

### Additional Configuration Files
- **supplier_aliases.yaml** - Supplier name normalization mappings
- **tariff_rates.json** - Custom tariff rate configurations by HTS code and country

SQLite deployments use a lightweight migration helper at startup to add missing columns.

## 🧪 Testing & troubleshooting

- **Health Check**: GET http://localhost:8000/
- **Export Testing**: Run `test_export.py` (requires API server running)
- **AI PDF Extraction**: Test with sample PDFs in `sample_data/` directory
- **Inventory Projections**: Verify alerts and recommendations in Inventory tab
- **Dashboard Issues**: If dashboard shows "backend not running", start API first or use `python run_app.py`
- **Port Conflicts**: Ensure ports 8000 and 8050 are available
- **AI Features**: Check API key configuration if PDF extraction fails

## 📦 Sample data

Sample CSVs are in sample_data/. Use load_sample_data.py to quickly populate the database for demos.

## 🧭 Architecture

```
Dash Dashboard (8050)  ↔  FastAPI (8000)  ↔  SQLite/PostgreSQL
                            ↓
                    InventoryService (projections)
                            ↓
                      Planner (Pandas)
                            ↓
                     AI PDF Extractor
                      (Multi-LLM Chain)
                    ↙         ↓        ↘
            Gemini 2.0  →  GPT-4o mini  →  Gemini 2.5
```

**Key Components:**
- **FastAPI Backend**: RESTful API with comprehensive validation and error handling
- **Inventory Service**: Advanced inventory analytics with projections and alerts
- **Planning Engine**: Pandas-based supply planning with safety stock calculations
- **AI PDF Processor**: Multi-provider extraction chain for document processing
- **Interactive Dashboard**: Real-time data visualization and management interface

## 📄 License

MIT License (see LICENSE)

---

Requirements coverage: README updated to reflect current codebase (endpoints, CSV formats, startup, Docker) and includes detailed planning engine logic based on app/planner.py.