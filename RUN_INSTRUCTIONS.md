# SupplyXplorer - Quick Start Guide

## Running the Application

### Recommended: Both Servers Together
```bash
python run_app.py
```
This starts both the API (port 8000) and Dashboard (port 8050) automatically.

### Alternative: Run Separately
```bash
# Terminal 1 - Backend API
python main.py

# Terminal 2 - Frontend Dashboard  
python app/dashboard.py
```

## Access Points
- **Dashboard**: http://localhost:8050
- **API Documentation**: http://localhost:8000/docs

## Load Sample Data
```bash
python load_sample_data.py
```

## Test Exports (Optional)
```bash
python test_export.py
```

See main README.md for complete documentation. 