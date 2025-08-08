# SupplyXplorer v1.0.0

Inventory & Cash-Flow Planning Tool

Plan part purchases and cash outflows from a sales/installation forecast using BOM multipliers, current inventory, lead times, AP terms, and tariffs. Built with Python, FastAPI, Plotly Dash, and Pandas. August 2025.

## 🚀 Features

- Data uploads: Forecast, BOM, Inventory (CSV) with robust parsing and validation
- Inventory-aware planning: respects current stock, minimums, and pending supplier POs
- Supplier aggregation: consolidate orders by supplier and order date
- Tariff-aware costs: HTS/origin-based tariff logic + shipping cost per unit
- Dashboard: upload data, run plan, visualize orders and cash flow, inline data editors
- API-first: full REST API with OpenAPI docs, CSV exports for all views
- Pending Orders: track placed/expected POs and import from invoice/quote PDFs (LLM extractor)
- Docker & Compose: easy containerized deployment; SQLite (dev) or PostgreSQL (prod)

### Tech stack
- FastAPI 0.115.6, SQLAlchemy 1.4.53, Pydantic 2.10.4
- Dash 2.16.1 + dash-bootstrap-components 1.5.0, Plotly 5.18.0
- Pandas 2.2.0, NumPy 1.26.4
- SQLite (default) or PostgreSQL (via DATABASE_URL)

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

Access:
- API docs: http://localhost:8000/docs
- Dashboard: http://localhost:8050

See also: RUN_INSTRUCTIONS.md

## 📥 CSV upload formats (current)

### Forecast upload
Two supported formats:
- New format (preferred):
```
System SN,Installation Date,quantity
JT080001,2025-08-15,2
JT090001,2025-09-01,1
```

- Legacy format (auto-generates System SN per month):
```
sku_id,date,quantity
PROD-001,2025-08-06,2
```
Notes:
- System SN format is [YearCode][MM][####], e.g., JT080001 (see “Planning engine details” for mapping and logic)
- On legacy uploads, System SNs are generated sequentially per month and year

### BOM upload (K&T format)
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

## 🔎 Planning engine details

Source: app/planner.py (class SupplyPlanner)

High-level flow:
1) Part demand from forecast × BOM
  - Read forecasts in range [start_date, end_date]
  - For each forecast row, find BOM rows where BOM.product_id == forecast.system_sn
  - Fallback: if BOM only has one unique product_id, use that BOM for all forecasts
  - Demand rows: part_id, part_name, installation_date, demand_qty = units × quantity

2) For each part with demand, compute orders over time
  - Current inventory: inventory.current_stock and minimum_stock (defaults 0)
  - Safety stock: max(avg(period demand) × 10%, minimum_stock)
  - Lead time: total = manufacturing_lead_time + shipping_lead_time (defaults 30 + 0)
  - Pending orders: add incoming qty to running stock if ETA ≤ need date and status in [pending, ordered]
  - For each need date:
    - available_for_demand = max(0, running_stock − safety_stock)
    - net_demand = max(0, demand − available_for_demand)
    - If net_demand > 0:
     - order_qty = net_demand (+ safety stock top-up if running_stock < safety_stock)
     - order_date = need_date − total_lead_time
     - payment_date = order_date + (ap_terms or 30)

3) Costing, tariffs, and shipping
  - shipping_cost_total = shipping_cost_per_unit × qty
  - Tariff rate via TariffCalculator:
    - If subject_to_tariffs == Yes: use country_of_origin (defaults to China) and HTS (defaults to 7307.29.0090)
    - Special rule: HTS 7307.29.0090 of China into USA: 30% (5% MFN + 25% Section 301)
    - Else use country-level default map; unknown defaults to 3%
  - total_cost = base_cost + shipping + tariff

4) Supplier aggregation
  - Group by (supplier_id/name, order_date)
  - Sum total_cost, tariff_amount, shipping; collect parts

5) Cash flow
  - Group order total_cost by payment_date → outflows; compute cumulative/net

6) Metrics
  - Orders in next 30/60 days (by order_date relative to now)
  - Cash out and tariff spend next 90 days (by payment_date)
  - Largest purchase, unique parts and suppliers

Inputs/outputs contract:
- Inputs: Forecast, BOM, Inventory (optional), Pending Orders (optional)
- Outputs: OrderSchedule[], SupplierOrderSummary[], CashFlowProjection[], KeyMetrics

Edge cases handled:
- No demand → returns empty
- Missing BOM fields → sensible defaults (30d lead, 30d AP, USA origin, no tariff)
- Safety stock never below minimum_stock
- Pending orders counted once per need date

System SN logic:
- Format: [YearCode][MM][####] where #### is monthly sequence
- Year codes include 2025→JT, 2026→JW, … (see app/system_sn_utils.py)
- Legacy forecast uploads auto-generate SNs in date order per month

## 📊 Dashboard

Tabs:
- Data & Planning: upload Forecast/BOM/Inventory, set dates, run plan
- Dashboard: metrics, order schedule (detailed/aggregated), cash flow chart, CSV export
- BOM Data / Forecast Data / Inventory: inline editable tables with bulk save and CSV export
- Pending Orders: manage placed/expected POs, PDF upload to extract, CSV export
- Tariffs: interactive quote calculator and config upload (tariff_rates.json)

## 🔌 API highlights

Planning & reports:
- POST /plan/run
- GET /orders, /orders/by-supplier, /cashflow, /metrics
- GET /export/orders, /export/orders-by-supplier, /export/cashflow

Uploads & data:
- POST /upload/forecast, /upload/bom, /upload/inventory
- GET/POST/PUT/DELETE inventory
- GET/POST/PUT/DELETE orders/pending and POST /orders/pending/upload-pdf
- GET /export/bom, /export/forecast, /export/inventory, /export/orders-pending
- POST /tariff-config and POST /tariff/quote

All endpoints are documented at /docs.

## 🐳 Docker & Compose

Dockerfile runs both API (8000) and Dash (8050) in one container. docker-compose.yml includes Postgres. Set DATABASE_URL for the app service when using Postgres.

Quick use:
```bash
docker compose up -d
```

## ⚙️ Configuration

- DATABASE_URL (default sqlite:///./supplyxplorer.db)
- API_HOST, API_PORT (default 0.0.0.0:8000)
- DASHBOARD_PORT (default 8050)

SQLite deployments use a lightweight migration helper at startup to add missing columns.

## 🧪 Testing & troubleshooting

- Health: GET http://localhost:8000/
- Exports test: run test_export.py (starts require API running)
- If dashboard says backend not running, start API first or use python run_app.py
- Ports: ensure 8000 and 8050 are free

## 📦 Sample data

Sample CSVs are in sample_data/. Use load_sample_data.py to quickly populate the database for demos.

## 🧭 Architecture

```
Dash (8050)  ↔  FastAPI (8000)  ↔  SQLite/PostgreSQL
                  ↘
                Planner (Pandas)
```

## 📄 License

MIT License (see LICENSE)

---

Requirements coverage: README updated to reflect current codebase (endpoints, CSV formats, startup, Docker) and includes detailed planning engine logic based on app/planner.py.