# SupplyXplorer

**Inventory & Cash-Flow Planning Tool**

A comprehensive supply chain planning application that helps operations teams optimize inventory levels and cash flow through data-driven forecasting and planning.

## 🚀 Features

- **Data Management**: Upload and manage forecasts, BOMs, and lead times
- **Planning Engine**: Generate order schedules and cash flow projections
- **Interactive Dashboard**: Visualize key metrics and planning results
- **API-First Design**: RESTful API for integration and automation
- **CLI Tools**: Command-line interface for batch operations
- **Docker Support**: Containerized deployment ready

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

## 🛠️ Quick Start

### Prerequisites
- Python 3.11+
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

### Planning
- `POST /plan/run` - Run planning engine
- `GET /orders` - Get order schedule
- `GET /cashflow` - Get cash flow projection
- `GET /metrics` - Get key metrics

### File Operations
- `POST /upload/forecast` - Upload forecast CSV
- `POST /upload/bom` - Upload BOM CSV
- `POST /upload/leadtime` - Upload lead time CSV
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

**SupplyXplorer** - Making supply chain planning accessible and data-driven. 