# SupplyXplorer - Run Instructions

## Quick Start

### Option 1: Run Both Servers Together (Recommended)
```bash
python run_app.py
```

This will start both the backend (port 8000) and frontend (port 8050) servers automatically.

### Option 2: Run Servers Separately

**Terminal 1 - Backend Server:**
```bash
python main.py
```

**Terminal 2 - Frontend Server:**
```bash
python app/dashboard.py
```

## Access the Application

- **Frontend Dashboard**: http://localhost:8050
- **Backend API**: http://localhost:8000

## Troubleshooting

If you see connection errors:

1. **Backend not running**: Start the backend server first with `python main.py`
2. **Port conflicts**: Make sure ports 8000 and 8050 are available
3. **Dependencies**: Install requirements with `pip install -r requirements.txt`

## File Upload Requirements

### Forecast Data (CSV)
Required columns: `product_id, date, quantity`

### BOM Data (CSV)  
Required columns: `product_id, part_id, quantity`
Optional columns: `lead_time, ap_terms, transit_time, country_of_origin, shipping_cost` 