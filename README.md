# SupplyXplorer v1.0.0

**Inventory & Cash-Flow Planning Tool**

A comprehensive supply chain planning application that helps operations teams optimize inventory levels and cash flow through data-driven forecasting and planning. Built with Python, FastAPI, and Plotly Dash for maximum flexibility and ease of deployment.

## 🚀 Features

- **Data Management**: Upload and manage forecasts, BOMs, lead times, and inventory with enhanced validation
- **Inventory Management**: Track current stock levels, minimum/maximum thresholds, and integrate with planning engine
- **Supplier Integration**: Full supplier information support in BOM files with intelligent supplier ID generation
- **Planning Engine**: Generate order schedules and cash flow projections with safety stock buffers and inventory consideration
- **Supplier Aggregation**: Consolidate orders by supplier and date for streamlined purchasing
- **Interactive Dashboard**: Visualize key metrics and planning results with Plotly charts
- **API-First Design**: RESTful API for integration and automation (FastAPI with auto-generated docs)
- **CLI Tools**: Command-line interface for batch operations and automation
- **Docker Support**: Containerized deployment ready with Docker Compose
- **Data Validation**: Comprehensive data integrity checks and error reporting
- **Export Capabilities**: Export planning results to CSV for external analysis
- **Tariff Calculations**: Built-in tariff calculation based on country of origin
- **Multiple Deployment Options**: Flexible startup scripts and server management

## 📋 Version 1.0.0 - Current Release

### Latest Enhancements
- **Inventory Integration**: New inventory management system with current stock tracking and planning integration
- **Supplier Aggregation**: New intelligent order consolidation by supplier and date for streamlined purchasing
- **Enhanced Supplier Support**: Full supplier information integration in BOM uploads with automatic supplier ID generation
- **Enhanced Data Validation**: Comprehensive data integrity checks with row-level error reporting
- **Improved CSV Upload**: Better error handling and field mapping for forecast and BOM data
- **Data Export Features**: Export order schedules and cash flow projections to CSV
- **Extended BOM Support**: Lead times, AP terms, country of origin, shipping costs, and transit times
- **Validation Endpoints**: New API endpoints for data validation and system health checks
- **Automated Server Management**: Streamlined startup scripts for easier deployment

### Technology Stack
- **Backend**: FastAPI 0.115.6 with SQLAlchemy 1.4.53
- **Frontend**: Plotly Dash 2.16.1 with Bootstrap components
- **Data Processing**: Pandas 2.2.0 and NumPy 1.26.4
- **Database**: SQLite (development) / PostgreSQL (production)
- **Container**: Docker with Docker Compose support

## CSV Upload Formats

### Forecast Data (`forecast.csv`)
```
product_id,date,quantity
PROD001,2024-01-15,100
PROD001,2024-02-15,120
PROD002,2024-01-15,50
PROD002,2024-02-15,60
```

### BOM Data (`bom.csv`) - Now includes lead times, AP terms, transit times, tariffs, and shipping costs
```
product_id,part_id,quantity,lead_time,ap_terms,transit_time,country_of_origin,shipping_cost
PROD001,PART001,2,30,30,0,USA,0.00
PROD001,PART002,1,45,60,45,China,2.50
PROD002,PART001,1,30,30,0,USA,0.00
PROD002,PART003,3,60,90,30,Germany,1.75
```

**Note:** The optional columns are:
- `lead_time`: Lead time in days (default: 30)
- `ap_terms`: Accounts payable terms in days (default: 30)
- `transit_time`: Transit time in days (default: 0)
- `country_of_origin`: Country for tariff calculation (default: USA)
- `shipping_cost`: Shipping cost per unit (default: 0.00)

**Tariff Rates:**
- China: 25% (Section 301 tariffs)
- Most other countries: 0% (Most favored nation)
- Unknown countries: 3% (default)

### Inventory Data (`inventory.csv`) - New in v1.0.0
```
part_id,part_name,current_stock,minimum_stock,maximum_stock,unit_cost,supplier_name,location,notes
PART001,Component A,150,50,500,10.50,ABC Supplier,Warehouse A,High demand item
PART002,Component B,25,30,200,25.75,XYZ Manufacturing,Warehouse B,Low stock - reorder soon
PART003,Component C,300,100,1000,5.25,DEF Components,Warehouse A,Standard part
```

**Required columns:**
- `part_id`: Unique part identifier
- `part_name`: Part name/description
- `current_stock`: Current inventory level
- `unit_cost`: Cost per unit

**Optional columns:**
- `minimum_stock`: Minimum stock level (default: 0)
- `maximum_stock`: Maximum stock level (default: none)
- `supplier_name`: Supplier name
- `location`: Storage location
- `notes`: Additional notes

## 🛠️ Quick Start

### Prerequisites
- Python 3.11+ (tested with Python 3.11 and 3.13)
- pip

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd SupplyXplorer
```

2. **Create virtual environment**
```bash
python3.11 -m venv supplyxplorer_env
source supplyxplorer_env/bin/activate  # On Windows: supplyxplorer_env\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Start the application** (Recommended - starts both servers)
```bash
# Option 1: Using the automated startup script
./start_servers.sh

# Option 2: Using Python wrapper
python run_app.py
```

**Alternative: Start servers separately**
```bash
# Terminal 1 - Backend server
python main.py

# Terminal 2 - Frontend server  
python app/dashboard.py
```

## 🌐 Access the Application

- **API Documentation**: http://localhost:8000/docs
- **Web Dashboard**: http://localhost:8050
- **API Base**: http://localhost:8000

## 🔧 Troubleshooting

If you encounter connection errors:

1. **Backend not running**: Start the backend server first with `python main.py`
2. **Test backend connection**: Run `python test_backend.py` to verify backend is working
3. **Port conflicts**: Ensure ports 8000 and 8050 are available
4. **Use the combined startup**: Run `python run_app.py` to start both servers automatically

## 📈 Usage

### Supplier Aggregation Feature
SupplyXplorer now includes intelligent supplier aggregation that consolidates multiple part orders from the same supplier on the same day. This helps with:

- **Consolidated Purchase Orders**: Group related parts into single orders per supplier per day
- **Reduced Administrative Overhead**: Fewer separate orders to manage
- **Better Supplier Relationships**: Larger, consolidated orders may qualify for better pricing
- **Simplified Cash Flow**: Clearer visibility into supplier-level payment obligations

**Example Usage:**
```bash
# Get supplier-aggregated orders
curl "http://localhost:8000/orders/by-supplier?start_date=2024-01-01T00:00:00&end_date=2024-06-30T00:00:00"

# Compare detailed vs aggregated views
curl "http://localhost:8000/orders?start_date=2024-01-01T00:00:00&end_date=2024-06-30T00:00:00"  # Detailed
curl "http://localhost:8000/orders/by-supplier?start_date=2024-01-01T00:00:00&end_date=2024-06-30T00:00:00"  # Aggregated
```

### Web Dashboard
1. Navigate to http://localhost:8050
2. Upload your CSV files in the "Data & Planning" tab
3. Set your planning period (default: 2024-01-01 to 2024-06-30)
4. Click "Run Planning Engine"
5. View results in the "Dashboard" tab

### API Usage
```bash
# Upload forecast data
curl -X POST "http://localhost:8000/upload/forecast" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@forecast.csv"

# Run planning engine
curl -X POST "http://localhost:8000/plan/run?start_date=2024-01-01T00:00:00&end_date=2024-06-30T00:00:00"

# Get key metrics
curl "http://localhost:8000/metrics?start_date=2024-01-01T00:00:00&end_date=2024-06-30T00:00:00"
```

### CLI Tools
```bash
# Upload data
python app/cli.py upload-forecast --file forecast.csv
python app/cli.py upload-bom --file bom.csv
python app/cli.py upload-leadtime --file leadtimes.csv

# Run planning
python app/cli.py run-planning --start-date 2024-01-01 --end-date 2024-06-30

# Export results
python app/cli.py export-orders --start-date 2024-01-01 --end-date 2024-06-30
python app/cli.py export-cashflow --start-date 2024-01-01 --end-date 2024-06-30
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Dashboard │    │   FastAPI API   │    │  SQLite/PostgreSQL │
│   (Plotly Dash) │◄──►│   (Python)      │◄──►│  (Database)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │ Planning Engine │
                       │   (Pandas)     │
                       └─────────────────┘
```

## 🔧 Configuration

### Environment Variables
- `DATABASE_URL`: Database connection string (default: SQLite)
- `API_HOST`: API server host (default: 0.0.0.0)
- `API_PORT`: API server port (default: 8000)
- `DASHBOARD_PORT`: Dashboard port (default: 8050)

### Database
- **Development**: SQLite (default)
- **Production**: PostgreSQL (set `DATABASE_URL`)

## 🚀 Deployment

### Docker
```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build manually
docker build -t supplyxplorer .
docker run -p 8000:8000 -p 8050:8050 supplyxplorer
```

### Production
1. Set up PostgreSQL database
2. Configure environment variables
3. Use a process manager (systemd, supervisor)
4. Set up reverse proxy (nginx, Apache)

## 📊 Key Metrics

The planning engine calculates:
- **Orders next 30/60 days**: Upcoming purchase orders
- **Cash out 90 days**: Expected cash outflows
- **Largest purchase**: Highest single order value
- **Total parts/suppliers**: Inventory complexity metrics

## 🔍 API Endpoints

### Data Management
- `POST /products` - Create product
- `POST /parts` - Create part
- `POST /suppliers` - Create supplier
- `POST /bom` - Create BOM item
- `POST /forecast` - Create forecast
- `POST /leadtime` - Create lead time
- `POST /inventory` - Create inventory record
- `GET /inventory` - Get all inventory records
- `GET /inventory/{part_id}` - Get inventory for specific part
- `PUT /inventory/{part_id}` - Update inventory record
- `DELETE /inventory/{part_id}` - Delete inventory record

### Data Validation & Health
- `GET /validate/data` - Check data integrity and identify issues
- `GET /data/summary` - Get overview of all data in the system

### Planning
- `POST /plan/run` - Run planning engine
- `GET /orders` - Get detailed order schedule
- `GET /orders/by-supplier` - Get orders aggregated by supplier and date
- `GET /cashflow` - Get cash flow projection
- `GET /metrics` - Get key metrics

### File Operations
- `POST /upload/forecast` - Upload forecast CSV with enhanced validation
- `POST /upload/bom` - Upload BOM CSV with extended field support
- `POST /upload/leadtime` - Upload lead time CSV
- `POST /upload/inventory` - Upload inventory CSV with stock level tracking
- `GET /export/orders` - Export orders CSV
- `GET /export/cashflow` - Export cash flow CSV

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🆘 Support

For issues and questions:
- Check the API documentation at http://localhost:8000/docs
- Review the sample CSV files in `sample_data/`
- Open an issue on GitHub

---

**SupplyXplorer v1.0.0** - Making supply chain planning accessible and data-driven.

*Built with Python, FastAPI, and Plotly Dash | August 2025*