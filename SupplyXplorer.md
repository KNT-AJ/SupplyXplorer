# Product Requirements Document (PRD)

## 1 Overview

A lightweight **Inventory & Cash‑Flow Planning Tool** that converts a sales forecast into part‑level purchase plans and cash‑flow projections.  The MVP is Python‑centric—using familiar data‑science libraries (Pandas, Plotly, FastAPI) so operations teams can self‑host, extend, and automate the workflow without large‑scale ERP licensing.

## 2 Goals & Success Metrics

| Goal                               | KPI / Success Metric                                         |
| ---------------------------------- | ------------------------------------------------------------ |
| Avoid stock‑outs                   | ≤ 1% missed production due to part shortages                 |
| Improve working‑capital visibility | 100% of upcoming AP captured; weekly cash‑flow variance ≤ 5% |
| Reduce manual planning time        | Planning run completed in < 30 sec for ≤ 5 000 part SKUs     |

## 3 Key Personas & User Stories

- **Supply Planner (primary)** – “As a planner, I upload a 12‑month forecast and instantly see when to place each part order so that I never run out of stock.”
- **Operations Manager** – “As Ops, I need color‑coded alerts so I can prioritise purchase orders that risk production.”
- **CFO / Controller** – “As Finance, I need to overlay AP cash outflows against expected sales receipts to manage working capital.”

## 4 Functional Requirements

### 4.1 Key Inputs Module

| ID   | Description               | Acceptance Criteria                                                               |
| ---- | ------------------------- | --------------------------------------------------------------------------------- |
|  F‑1 | **Sales Forecast Upload** | CSV/Excel upload + in‑app editable table; period dropdown (3/6/12 mo)             |
|  F‑2 | **BOM Auto‑Linking**      | Each SKU maps to parts with quantity multiplier; validation for missing links     |
|  F‑3 | **Lead‑Time Editor**      | Editable grid; validation for positive integers; flag LT > threshold → bottleneck |
|  F‑4 | **AP Terms**              | Store per‑supplier terms (Net X); defaults to 30 days; editable                   |

### 4.2 Planning Engine

| ID   | Description                                                                |
| ---- | -------------------------------------------------------------------------- |
|  F‑5 | Calculate part demand per period = Σ (Forecast × BOM QTY)                  |
|  F‑6 | Safety‑stock buffer % configurable per part                                |
|  F‑7 | Order date = Need‑by date – Lead Time; Payment date = Order date + AP term |
|  F‑8 | Generate **order schedule** & **cash‑flow schedule** tables                |

### 4.3 Dashboard & Visuals

| ID    | Description                                                                                               |
| ----- | --------------------------------------------------------------------------------------------------------- |
|  F‑9  | **Part Orders View** – table + Plotly Gantt; color status Green/Yellow/Red                                |
|  F‑10 | **Cash‑Flow Timeline** – stacked bar (outflows) with toggle to show inflows; weekly & monthly aggregation |
|  F‑11 | **Key Metrics Panel** – upcoming orders 30/60 d, cash‑out 90 d, largest purchase                          |

### 4.4 Data Management & Integrations

- CSV/Bulk upload & download endpoints
- Optional REST hooks: push POs to ERP, pull receipts from accounting

## 5 Non‑Functional Requirements

- **Performance:** 10k‑row forecast processed < 3 s (local), 30 s (web‑hosted)
- **Security:** OAuth2 login; role‑based access (Admin, Planner, Viewer)
- **Portability:** Docker‑compose deployment; supports Linux/macOS/Windows
- **Extensibility:** Modular services; Python packages; clear API docs via OpenAPI

## 6 System Architecture (Python‑Lean)

```
+-------------+     REST/JSON      +-----------------+
| Front‑End   | <---------------→ | FastAPI Backend |
|  (Dash/React)|                  |  (uvicorn)      |
+-------------+                   +--------+--------+
                                          |
                                  +-------v--------+
                                  |  Planner Core  |  (Pandas/NumPy)
                                  +-------+--------+
                                          |
                                  +-------v--------+
                                  | Postgres       |
```

- **Front‑End:** Plotly Dash (pure‑Python) or React + Plotly JS
- **Backend:** FastAPI + Pydantic validation; async endpoints
- **Scheduler:** APScheduler / Celery for nightly recompute & email alerts
- **Data Layer:** SQLAlchemy ORM to PostgreSQL or SQLite (dev)

## 7 Data Model (simplified)

| Table        | Key Fields                                           |
| ------------ | ---------------------------------------------------- |
| `products`   | sku\_id PK, name                                     |
| `bom`        | sku\_id FK → products, part\_id FK → parts, qty\_per |
| `parts`      | part\_id PK, description, supplier\_id FK            |
| `suppliers`  | supplier\_id PK, ap\_terms\_days                     |
| `forecasts`  | id PK, sku\_id FK, period\_start, units              |
| `lead_times` | part\_id FK, days                                    |
| `orders`     | id PK, part\_id FK, order\_date, qty, payment\_date  |

## 8 API Sketch (FastAPI)

| Endpoint    | Verb  | Description                   |
| ----------- | ----- | ----------------------------- |
| `/forecast` | POST  | Upload forecast CSV           |
| `/bom`      | POST  | Upload BOM                    |
| `/leadtime` | PATCH | Update lead‑times             |
| `/plan/run` | POST  | Trigger planning engine       |
| `/orders`   | GET   | Retrieve order schedule       |
| `/cashflow` | GET   | Retrieve cash‑flow projection |

## 9 UI / UX Wireframe Notes

```
----------------------------------------------------------------
| Header (Brand)     [Run Plan]                               |
|-------------------------------------------------------------|
| Sidebar:  Forecast | BOM | Lead Times | AP Terms            |
|-------------------------------------------------------------|
|   🔴  PART ORDERS (Table / Gantt)                           |
|   Part A  | Order by Aug‑15 | Qty 500 | Pay by Sep‑15       |
|   Part B  | Order by Aug‑10 | Qty 200 | Pay by Aug‑30       |
|-------------------------------------------------------------|
|   💵  CASH‑FLOW TIMELINE (Stacked Bar)                      |
|-------------------------------------------------------------|
|   📊  Key Metrics: Orders next 30 d = 7 | Cash‑90 d $215k   |
----------------------------------------------------------------
```

## 10 Risks & Mitigations

| Risk                               | Impact      | Mitigation                             |
| ---------------------------------- | ----------- | -------------------------------------- |
| Inaccurate lead‑time data          | Stock‑outs  | Import from ERP nightly; flag outliers |
| Large SKU/part sets slow dashboard | Poor UX     | Virtualised table, async pagination    |
| User adoption (Excel inertia)      | Tool unused | Provide XLSX export parity             |

## 11 Milestones & Timeline (T‑shirt sizing)

| Phase                     | Duration | Deliverables                         |
| ------------------------- | -------- | ------------------------------------ |
|  Discovery                | 1 wk     | Finalised PRD, wireframes            |
|  Sprint 1 (MVP backend)   | 2 wks    | Data model, planning engine, CLI PoC |
|  Sprint 2 (Dashboards)    | 2 wks    | Dash front‑end, Gantt & cash charts  |
|  Sprint 3 (Alerts & Auth) | 1 wk     | Email alerts, OAuth2                 |
|  Pilot & Feedback         | 1 wk     | Pilot with ops team                  |

## 12 Future Enhancements

- AI demand‑forecast import (Prophet / scikit‑ts)
- Vendor‑managed‑inventory API hooks
- Multi‑currency cash planning
- What‑if scenarios & Monte Carlo safety‑stock calculator

---

**Document Owner:** Adam J. Davis (@adam.j.davis)\
**Last Updated:** 2025‑07‑30

