import dash
from dash import dcc, html, dash_table, callback, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd
import requests
import json

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], assets_folder='../assets', suppress_callback_exceptions=True)
app.title = "PartXplorer Dashboard"

# API base URL
API_BASE = "http://localhost:8000"

def check_backend_connection():
    """Check if backend is running"""
    try:
        response = requests.get(f"{API_BASE}/", timeout=2)
        return response.status_code == 200
    except:
        return False

# Layout
from app.components.pending_orders_callbacks import register_callbacks as register_pending_orders_callbacks

app.layout = dbc.Container([
    # Header with logo
    dbc.Row([
        dbc.Col([
            html.H1("PartXplorer", className="text-primary mb-0"),
            html.P("Inventory & Cash-Flow Planning Tool", className="text-muted mb-0")
        ], width=8),
        dbc.Col([
            html.Img(src="/assets/KNT-logo-web.png", height="40", className="float-end", alt="KNT Logo")
        ], width=4, className="logo-container")
    ], className="header-row"),

    # Backend Status Indicator
    dbc.Row([
        dbc.Col([
            html.Div(id='backend-status', className="mb-3")
        ])
    ]),

    # Navigation tabs
    dbc.Tabs([
        dbc.Tab([
            # Upload sections
            dbc.Row([
                dbc.Col([
                    html.H4("Upload Forecast Data"),
                    dcc.Upload(
                        id='upload-forecast',
                        children=html.Div([
                            'Drag and Drop or ',
                            html.A('Select Files')
                        ]),
                        style={
                            'width': '100%',
                            'height': '60px',
                            'lineHeight': '60px',
                            'borderWidth': '1px',
                            'borderStyle': 'dashed',
                            'borderRadius': '5px',
                            'textAlign': 'center',
                            'margin': '10px'
                        },
                        multiple=False
                    ),
                    html.Div(id='upload-forecast-output'),
                    html.P("Expected columns: product_id, date, quantity", className="text-muted")
                ], width=6),
                dbc.Col([
                    html.H4("Upload BOM Data"),
                    dcc.Upload(
                        id='upload-bom',
                        children=html.Div([
                            'Drag and Drop or ',
                            html.A('Select Files')
                        ]),
                        style={
                            'width': '100%',
                            'height': '60px',
                            'lineHeight': '60px',
                            'borderWidth': '1px',


                            'borderStyle': 'dashed',
                            'borderRadius': '5px',
                            'textAlign': 'center',
                            'margin': '10px'
                        },
                        multiple=False
                    ),
                    html.Div(id='upload-bom-output'),
                    html.P("Expected columns: product_id, part_id, quantity, lead_time (optional), ap_terms (optional), transit_time (optional), country_of_origin (optional), shipping_cost (optional)", className="text-muted")
                ], width=6)
            ], className="mb-4"),

            # Planning Controls Section
            dbc.Col([
                html.H4("Planning Controls", className="mb-3"),

                dbc.Row([
                    dbc.Col([
                        html.Label("Start Date:"),
                        dcc.DatePickerSingle(
                            id='start-date',
                            date=datetime(2025, 1, 1).date(),
                            display_format='YYYY-MM-DD'
                        )
                    ], width=6),
                    dbc.Col([
                        html.Label("End Date:"),
                        dcc.DatePickerSingle(
                            id='end-date',
                            date=datetime(2025, 12, 31).date(),
                            display_format='YYYY-MM-DD'
                        )
                    ], width=6)
                ], className="mb-3"),

                dbc.Button(
                    "Run Planning Engine",
                    id="run-planning-btn",
                    color="primary",
                    size="lg",
                    className="w-100"
                ),

                html.Div(id='planning-status', className="mt-3")
            ], width=6)
        ], label="Data & Planning", tab_id="data-planning"),

        dbc.Tab([
            # Key Metrics
            dbc.Row([
                dbc.Col([
                    html.H4("Key Metrics", className="mb-3"),
                    html.Div(id="key-metrics-display")
                ])
            ], className="mb-4"),

            # Order Schedule
            dbc.Row([
                dbc.Col([
                    html.H4("Order Schedule", className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Order View:", className="mb-2"),
                            dbc.RadioItems(
                                id="order-view-toggle",
                                options=[
                                    {"label": "Detailed Orders (by Part)", "value": "detailed"},
                                    {"label": "Aggregated Orders (by Supplier)", "value": "aggregated"}
                                ],
                                value="detailed",
                                inline=True,
                                className="mb-3"
                            )
                        ], width=8),
                        dbc.Col([
                            dbc.Button(
                                "Export Orders to CSV",
                                id="export-orders-btn",
                                color="success",
                                size="sm",
                                className="float-end",
                                outline=True
                            )
                        ], width=4)
                    ]),
                    # Status/feedback for calendar export
                    html.Div(id="calendar-export-status", className="mt-2"),

                    # Order Summary Cards
                    html.Div(id="order-summary-cards", className="mb-3"),
                    # Tariff Summary
                    html.Div(id="tariff-summary"),
                    html.Div(id="order-schedule-display")
                ])
            ], className="mb-4"),

            # Cash Flow Chart
            dbc.Row([
                dbc.Col([
                    dbc.Row([
                        dbc.Col([
                            html.H4("Cash Flow Projection", className="mb-3")
                        ], width=8),
                        dbc.Col([
                            dbc.Button(
                                "Export Cash Flow to CSV",
                                id="export-cashflow-btn",
                                color="success",
                                size="sm",
                                className="float-end",
                                outline=True
                            )
                        ], width=4)
                    ]),
                    dcc.Graph(id="cash-flow-chart")
                ])
            ])
        ], label="Dashboard", tab_id="dashboard"),
        dbc.Tab([
            # BOM Data Editor
            dbc.Row([
                dbc.Col([
                    html.H4("BOM Data Editor", className="mb-3"),
                    html.P("Edit your Bill of Materials data directly. Changes are applied immediately to planning calculations.",
                           className="text-muted mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Button("Refresh BOM Data", id="refresh-bom-btn", color="primary", className="mb-3")
                        ], width=3),
                        dbc.Col([
                            dbc.Button("Save Changes", id="save-bom-btn", color="success", className="mb-3")
                        ], width=3),
                        dbc.Col([
                            dbc.Button("Export to CSV", id="export-bom-btn", color="info", className="mb-3", outline=True)
                        ], width=3),
                        dbc.Col([
                            html.Div(id="bom-save-status", className="mb-3")
                        ], width=3)
                    ]),
                    html.Div(id="bom-data-table")
                ])
            ])
        ], label="BOM Data", tab_id="bom-data"),
        dbc.Tab([
            # Forecast Data Editor
            dbc.Row([
                dbc.Col([
                    html.H4("Forecast Data Editor", className="mb-3"),
                    html.P("Edit your forecast data directly. Changes are applied immediately to planning calculations.",
                           className="text-muted mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Button("Refresh Forecast Data", id="refresh-forecast-btn", color="primary", className="mb-3")
                        ], width=3),
                        dbc.Col([
                            dbc.Button("Save Changes", id="save-forecast-btn", color="success", className="mb-3")
                        ], width=3),
                        dbc.Col([
                            dbc.Button("Export to CSV", id="export-forecast-btn", color="info", className="mb-3", outline=True)
                        ], width=3),
                        dbc.Col([
                            html.Div(id="forecast-save-status", className="mb-3")
                        ], width=3)
                    ]),
                    html.Div(id="forecast-data-table")
                ])
            ])
        ], label="Forecast Data", tab_id="forecast-data"),
        dbc.Tab([
            # Inventory Data Editor
            dbc.Row([
                dbc.Col([
                    html.H4("Inventory Management", className="mb-3"),
                    html.P("Manage your current inventory levels. This data is used by the planning engine to optimize order quantities.",
                           className="text-muted mb-3"),
                    dbc.Row([
                        dbc.Col([
                            html.H5("Upload Inventory Data"),
                            dcc.Upload(
                                id='upload-inventory',
                                children=html.Div([
                                    'Drag and Drop or ',
                                    html.A('Select CSV File')
                                ]),
                                style={
                                    'width': '100%',
                                    'height': '60px',
                                    'lineHeight': '60px',
                                    'borderWidth': '1px',
                                    'borderStyle': 'dashed',
                                    'borderRadius': '5px',
                                    'textAlign': 'center',
                                    'margin': '10px'
                                },
                                multiple=False
                            ),
                            html.Div(id='upload-inventory-output'),
                            html.P("Expected columns: part_id, part_name, current_stock, minimum_stock, maximum_stock, unit_cost, supplier_name, location, notes",
                                   className="text-muted")
                        ], width=6),
                        dbc.Col([
                            html.H5("Quick Actions"),
                            dbc.Row([
                                dbc.Col([
                                    dbc.Button("Save Changes", id="save-inventory-btn", color="success", className="mb-2 w-100")
                                ], width=12),
                                dbc.Col([
                                    dbc.Button("Export to CSV", id="export-inventory-btn", color="info", className="mb-2 w-100", outline=True)
                                ], width=12),
                                dbc.Col([
                                    html.Div(id="inventory-save-status", className="mb-3")
                                ], width=12)
                            ])
                        ], width=6)
                    ], className="mb-4"),

                    # Inventory Alerts Section
                    dbc.Row([
                        dbc.Col([
                            html.H5("Inventory Alerts", className="mb-3"),
                            html.Div(id="inventory-alerts-section")
                        ])
                    ], className="mb-4"),

                    # Main Inventory Table
                    html.Div(id="inventory-data-table")
                ])
            ])
        ], label="Inventory", tab_id="inventory"),
        dbc.Tab([
            # Pending Orders Management
            dbc.Row([
                        # View toggle for Pending Orders
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Pending Orders View:", className="mb-2"),
                                dbc.RadioItems(
                                    id="pending-order-view-toggle",
                                    options=[
                                        {"label": "Individual Orders", "value": "individual"},
                                        {"label": "Aggregated Orders (by Supplier)", "value": "aggregated"}
                                    ],
                                    value="individual",
                                    inline=True,
                                    className="mb-3"
                                )
                            ], width=12)
                        ]),

                dbc.Col([
                    html.H4("Pending Orders", className="mb-3"),
                    html.P("Track supplier POs that are placed or expected. These count as incoming supply for planning.", className="text-muted mb-3"),
                    dbc.Row([
                        dbc.Col([
                            html.H6("Upload Invoice/Quote PDF"),
                            dcc.Upload(
                                id='upload-pending-orders-pdf',
                                children=html.Div(['Drag and Drop or ', html.A('Select PDF')]),
                                style={
                                    'width': '100%',
                                    'height': '60px',
                                    'lineHeight': '60px',
                                    'borderWidth': '1px',
                                    'borderStyle': 'dashed',
                                    'borderRadius': '5px',
                                    'textAlign': 'center',
                                    'margin': '10px'
                                },
                                multiple=False
                            ),
                            html.Div(id='upload-pending-orders-pdf-output', className="mb-3")
                        ], width=12)
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Button("Refresh", id="refresh-pending-orders-btn", color="primary", className="mb-2 w-100")
                        ], width=3),
                        dbc.Col([
                            dbc.Button("Re-map", id="remap-pending-orders-btn", color="warning", outline=True, className="mb-2 w-100")
                        ], width=3),
                        dbc.Col([
                            dbc.Button("Save Changes", id="save-pending-orders-btn", color="success", className="mb-2 w-100")
                        ], width=3),
                        dbc.Col([
                            dbc.Button("Export CSV", id="export-pending-orders-btn", color="info", outline=True, className="mb-2 w-100")
                        ], width=3),
                    ]),
                    dbc.Row([
                        dbc.Col([html.Div(id="pending-orders-remap-status", className="mb-2")], width=6),
                        dbc.Col([html.Div(id="pending-orders-save-status", className="mb-2")], width=6),
                    ]),
                    html.Div(id="pending-orders-table")
                ])
            ])
        ], label="Pending Orders", tab_id="pending-orders"),
        dbc.Tab([
            # Tariff Calculator
            dbc.Row([
                dbc.Col([
                    html.H4("Tariff Calculator", className="mb-3"),
                    html.P("Enter shipment details to estimate U.S. import duties and fees.", className="text-muted"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("HTS Code"),
                            dcc.Input(id='tc-hts', type='text', placeholder='e.g., 8501.10.40', className='w-100')
                        ], width=4),
                        dbc.Col([
                            dbc.Label("Country of Origin"),
                            dcc.Input(id='tc-coo', type='text', placeholder='e.g., China', className='w-100')
                        ], width=4),
                        dbc.Col([
                            dbc.Label("Importing Country"),
                            dcc.Input(id='tc-importing', type='text', value='USA', className='w-100')
                        ], width=4)
                    ], className='mb-3'),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Invoice Value"),
                            dcc.Input(id='tc-invoice', type='number', value=0, step=0.01, className='w-100')
                        ], width=3),
                        dbc.Col([
                            dbc.Label("Currency"),
                            dcc.Input(id='tc-currency', type='text', value='USD', className='w-100')
                        ], width=2),
                        dbc.Col([
                            dbc.Label("FX Rate"),
                            dcc.Input(id='tc-fx', type='number', value=1.0, step=0.0001, className='w-100')
                        ], width=2),
                        dbc.Col([
                            dbc.Label("Incoterm"),
                            dcc.Dropdown(id='tc-incoterm', options=[
                                {'label': 'FOB (Origin)', 'value': 'FOB'},
                                {'label': 'CIF (Destination)', 'value': 'CIF'},
                                {'label': 'EXW', 'value': 'EXW'},
                                {'label': 'DAP', 'value': 'DAP'}
                            ], placeholder='Select')
                        ], width=3),
                        dbc.Col([
                            dbc.Label("Entry Date"),
                            dcc.DatePickerSingle(id='tc-entry-date')
                        ], width=2)
                    ], className='mb-3'),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Freight to Border"),
                            dcc.Input(id='tc-freight', type='number', value=0.0, step=0.01, className='w-100')
                        ], width=3),
                        dbc.Col([
                            dbc.Label("Insurance Cost"),
                            dcc.Input(id='tc-insurance', type='number', value=0.0, step=0.01, className='w-100')
                        ], width=3),
                        dbc.Col([
                            dbc.Label("Assists/Tooling"),
                            dcc.Input(id='tc-assists', type='number', value=0.0, step=0.01, className='w-100')
                        ], width=3),
                        dbc.Col([
                            dbc.Label("Royalties/Fees"),
                            dcc.Input(id='tc-royalties', type='number', value=0.0, step=0.01, className='w-100')
                        ], width=3)
                    ], className='mb-3'),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Other Dutiable Additions"),
                            dcc.Input(id='tc-other', type='number', value=0.0, step=0.01, className='w-100')
                        ], width=3),
                        dbc.Col([
                            dbc.Label("Quantity"),
                            dcc.Input(id='tc-qty', type='number', className='w-100')
                        ], width=3),
                        dbc.Col([
                            dbc.Label("Net Weight (kg)"),
                            dcc.Input(id='tc-weight', type='number', className='w-100')
                        ], width=3),
                        dbc.Col([
                            dbc.Label("Volume (L)"),
                            dcc.Input(id='tc-volume', type='number', className='w-100')
                        ], width=3)
                    ], className='mb-3'),
                    dbc.Row([
                        dbc.Col([
                            dbc.Checklist(options=[{"label": "FTA Eligible", "value": 1}], value=[], id='tc-fta', switch=True)
                        ], width=3),
                        dbc.Col([
                            dbc.Label("FTA Program"),
                            dcc.Input(id='tc-fta-program', type='text', placeholder='e.g., USMCA', className='w-100')
                        ], width=3),
                        dbc.Col([
                            dbc.Label("ADD/CVD Rate %"),
                            dcc.Input(id='tc-addcvd', type='number', value=0.0, step=0.1, className='w-100')
                        ], width=3),
                        dbc.Col([
                            dbc.Label("Special Surcharge % (e.g., 301/232)"),
                            dcc.Input(id='tc-special', type='number', value=0.0, step=0.1, className='w-100')
                        ], width=3)
                    ], className='mb-3'),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Transport Mode"),
                            dcc.Dropdown(id='tc-transport', options=[
                                {'label': 'Sea (Vessel)', 'value': 'sea'},
                                {'label': 'Air', 'value': 'air'},
                                {'label': 'Courier/Express', 'value': 'courier'}
                            ], placeholder='Select')
                        ], width=4),
                        dbc.Col([
                            dbc.Label("Port of Entry"),
                            dcc.Input(id='tc-port', type='text', placeholder='e.g., LAX, LGB', className='w-100')
                        ], width=4),
                        dbc.Col([
                            dbc.Checklist(options=[{"label": "De Minimis", "value": 1}], value=[], id='tc-deminimis', switch=True)
                        ], width=4)
                    ], className='mb-3'),
                    dbc.Row([
                        dbc.Col([
                            dbc.Button("Get Tariff Quote", id='tc-quote-btn', color='primary', className='w-100')
                        ], width=3)
                    ], className='mb-3'),
                    html.Div(id='tc-quote-output')
                ], width=12)
            ], className='mb-4'),

            # Tariff Settings
            dbc.Row([
                dbc.Col([
                    html.Hr(),
                    html.H4("Tariff Settings", className="mb-3"),
                    html.P("Manage tariff rates by country and default rate. Upload a JSON file named tariff_rates.json to override.", className="text-muted"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Default Tariff Rate (%) for Unknown Countries"),
                            dcc.Input(id='tariff-default-rate', type='number', value=3.0, step=0.5)
                        ], width=6)
                    ], className="mb-3"),
                    html.Div(id='tariff-settings-status', className='mb-3'),
                    html.H5("Upload tariff_rates.json"),
                    dcc.Upload(id='upload-tariff-json', children=html.Div(['Drag/Drop or ', html.A('Select JSON')]), multiple=False,
                               style={'width': '100%', 'height': '60px','lineHeight': '60px','borderWidth': '1px','borderStyle': 'dashed','borderRadius': '5px','textAlign': 'center','margin': '10px'}),
                    html.Div(id='upload-tariff-json-output')
                ], width=12)
            ])
        ], label="Tariffs", tab_id="tariffs")
    ], id="tabs", active_tab="data-planning"),
    dcc.Store(id='planning-results-store'),

    # Download components for CSV exports
    dcc.Download(id="download-orders"),
    dcc.Download(id="download-cashflow"),
    dcc.Download(id="download-bom"),
    dcc.Download(id="download-forecast"),
    dcc.Download(id="download-inventory"),
    dcc.Download(id="download-pending-orders")
], fluid=True)

# Callbacks
@app.callback(
    Output('backend-status', 'children'),
    Input('upload-forecast', 'contents'),
    Input('upload-bom', 'contents'),
    Input('run-planning-btn', 'n_clicks')
)
def update_backend_status(forecast_contents, bom_contents, planning_clicks):
    """Update backend connection status"""
    if check_backend_connection():
        return dbc.Alert(
            "✅ Backend server is running",
            color="success",
            dismissable=False,
            className="mb-0"
        )
    else:
        return dbc.Alert(
            "❌ Backend server is not running. Please start the backend server first.",
            color="danger",
            dismissable=False,
            className="mb-0"
        )

@app.callback(
    Output('upload-forecast-output', 'children'),
    Input('upload-forecast', 'contents'),
    State('upload-forecast', 'filename')
)
def upload_forecast(contents, filename):
    if contents is not None:
        # Check if backend is running
        if not check_backend_connection():
            return html.Div([
                html.H5("Backend Server Not Running", className="upload-error"),
                html.P("Please start the backend server first. Run 'python main.py' in a separate terminal.", className="upload-error"),
                html.P("Or use 'python run_app.py' to start both servers.", className="upload-error")
            ])

        try:
            # Parse CSV and send to API
            import base64
            import io

            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)

            # Send to API
            files = {'file': (filename, decoded, 'text/csv')}
            response = requests.post(f"{API_BASE}/upload/forecast", files=files, timeout=10)

            if response.status_code == 200:
                return html.Div([
                    html.H5("Upload Successful!", className="upload-success"),
                    html.P(response.json()["message"], className="upload-success")
                ])
            else:
                return html.Div([
                    html.H5("Upload Failed", className="upload-error"),
                    html.P(response.json()["detail"], className="upload-error")
                ])
        except requests.exceptions.ConnectionError:
            return html.Div([
                html.H5("Connection Error", className="upload-error"),
                html.P("Cannot connect to backend server. Please ensure the backend is running on http://localhost:8000", className="upload-error")
            ])
        except Exception as e:
            return html.Div([
                html.H5("Upload Error", className="upload-error"),
                html.P(str(e), className="upload-error")
            ])
    return ""

@app.callback(
    Output('upload-tariff-json-output', 'children'),
    Input('upload-tariff-json', 'contents'),
    State('upload-tariff-json', 'filename')
)
def upload_tariff_json(contents, filename):
    if contents is None:
        return ""
    try:
        import base64, io, json
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        # Validate JSON
        cfg = json.loads(decoded.decode('utf-8'))
        resp = requests.post(f"{API_BASE}/tariff-config", json=cfg, timeout=10)
        if resp.status_code == 200:
            return dbc.Alert("Tariff configuration saved.", color="success", duration=3000)
        return dbc.Alert(f"Save failed: {resp.text}", color="danger", duration=5000)
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger", duration=5000)

@app.callback(
    Output('upload-bom-output', 'children'),
    Input('upload-bom', 'contents'),
    State('upload-bom', 'filename')
)
def upload_bom(contents, filename):
    if contents is not None:
        # Check if backend is running
        if not check_backend_connection():
            return html.Div([
                html.H5("Backend Server Not Running", className="upload-error"),
                html.P("Please start the backend server first. Run 'python main.py' in a separate terminal.", className="upload-error"),
                html.P("Or use 'python run_app.py' to start both servers.", className="upload-error")
            ])

        try:
            import base64
            import io

            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)

            files = {'file': (filename, decoded, 'text/csv')}
            response = requests.post(f"{API_BASE}/upload/bom", files=files, timeout=10)

            if response.status_code == 200:
                return html.Div([
                    html.H5("Upload Successful!", className="upload-success"),
                    html.P(response.json()["message"], className="upload-success")
                ])
            else:
                return html.Div([
                    html.H5("Upload Failed", className="upload-error"),
                    html.P(response.json()["detail"], className="upload-error")
                ])
        except requests.exceptions.ConnectionError:
            return html.Div([
                html.H5("Connection Error", className="upload-error"),
                html.P("Cannot connect to backend server. Please ensure the backend is running on http://localhost:8000", className="upload-error")
            ])
        except Exception as e:
            return html.Div([
                html.H5("Upload Error", className="upload-error"),
                html.P(str(e), className="upload-error")
            ])
    return ""

@app.callback(
    Output('upload-inventory-output', 'children'),
    Input('upload-inventory', 'contents'),
    State('upload-inventory', 'filename')
)
def upload_inventory(contents, filename):
    if contents is not None:
        # Check if backend is running
        if not check_backend_connection():
            return html.Div([
                html.H5("Backend Server Not Running", className="upload-error"),
                html.P("Please start the backend server first. Run 'python main.py' in a separate terminal.", className="upload-error"),
                html.P("Or use 'python run_app.py' to start both servers.", className="upload-error")
            ])

        try:
            import base64
            import io

            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)

            files = {'file': (filename, decoded, 'text/csv')}
            response = requests.post(f"{API_BASE}/upload/inventory", files=files, timeout=10)

            if response.status_code == 200:
                return html.Div([
                    html.H5("Upload Successful!", className="upload-success"),
                    html.P(response.json()["message"], className="upload-success")
                ])
            else:
                return html.Div([
                    html.H5("Upload Failed", className="upload-error"),
                    html.P(response.json()["detail"], className="upload-error")
                ])
        except requests.exceptions.ConnectionError:
            return html.Div([
                html.H5("Connection Error", className="upload-error"),
                html.P("Cannot connect to backend server. Please ensure the backend is running on http://localhost:8000", className="upload-error")
            ])
        except Exception as e:
            return html.Div([
                html.H5("Upload Error", className="upload-error"),
                html.P(str(e), className="upload-error")
            ])
    return ""

# Tab content initialization callback
@app.callback(
    [Output('bom-data-table', 'children', allow_duplicate=True),
     Output('forecast-data-table', 'children', allow_duplicate=True),
     Output('inventory-data-table', 'children', allow_duplicate=True),
     Output('inventory-alerts-section', 'children', allow_duplicate=True),
     Output('pending-orders-table', 'children', allow_duplicate=True)],
    Input('tabs', 'active_tab'),
    prevent_initial_call=True
)
def initialize_tab_content(active_tab):
    """Initialize table content when tabs are first activated"""
    bom_content = ""
    forecast_content = ""
    inventory_content = ""
    inventory_alerts_content = ""
    pending_orders_content = ""

    if active_tab == "bom-data":
        try:
            response = requests.get(f"{API_BASE}/bom")
            if response.status_code == 200:
                bom_data = response.json()
                if bom_data:
                    df = pd.DataFrame(bom_data)

                    # Convert datetime columns to strings for display
                    if 'created_at' in df.columns:
                        df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
                    if 'updated_at' in df.columns:
                        df['updated_at'] = pd.to_datetime(df['updated_at']).dt.strftime('%Y-%m-%d %H:%M')

                    bom_content = dash_table.DataTable(
                        id='bom-data-editable-table',
                        data=df.to_dict('records'),
                        columns=[
                            {"name": "ID", "id": "id", "editable": False},
                            {"name": "Product ID", "id": "product_id", "editable": True},
                            {"name": "Part ID", "id": "part_id", "editable": True},
                            {"name": "Part Name", "id": "part_name", "editable": True},
                            {"name": "Quantity", "id": "quantity", "editable": True, "type": "numeric"},
                            {"name": "Unit Cost", "id": "unit_cost", "editable": True, "type": "numeric"},
                            {"name": "Country of Origin", "id": "country_of_origin", "editable": True},
                            {"name": "Shipping Cost (per unit)", "id": "shipping_cost", "editable": True, "type": "numeric"},
                            {"name": "Supplier ID", "id": "supplier_id", "editable": True},
                            {"name": "Supplier Name", "id": "supplier_name", "editable": True},
                            {"name": "Manufacturer", "id": "manufacturer", "editable": True},
                            {"name": "AP Terms", "id": "ap_terms", "editable": True, "type": "numeric"},
                            {"name": "Mfg Lead Time", "id": "manufacturing_lead_time", "editable": True, "type": "numeric"},
                            {"name": "Ship Lead Time", "id": "shipping_lead_time", "editable": True, "type": "numeric"},
                            {"name": "Subject to Tariffs", "id": "subject_to_tariffs", "editable": True, "presentation": "dropdown"}
                        ],
                        editable=True,
                        row_deletable=True,
                        dropdown={
                            'subject_to_tariffs': {
                                'options': [
                                    {'label': 'Yes', 'value': 'Yes'},
                                    {'label': 'No', 'value': 'No'}
                                ]
                            }
                        },
                        style_table={'overflowX': 'auto'},
                        style_cell={'textAlign': 'left', 'padding': '10px', 'minWidth': '150px'},
                        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                        style_data_conditional=[
                            {
                                'if': {'column_editable': True},
                                'backgroundColor': 'rgb(248, 248, 248)',
                            }
                        ]
                    )
                else:
                    bom_content = html.Div("No BOM data found. Please upload BOM data first.", style={'color': 'gray'})
            else:
                bom_content = html.Div("Error loading BOM data", style={'color': 'red'})
        except Exception as e:
            bom_content = html.Div(f"Error: {str(e)}", style={'color': 'red'})

    elif active_tab == "forecast-data":
        try:
            response = requests.get(f"{API_BASE}/forecast")
            if response.status_code == 200:
                forecast_data = response.json()
                if forecast_data:
                    df = pd.DataFrame(forecast_data)

                    # Convert datetime columns to strings for display
                    if 'installation_date' in df.columns:
                        df['installation_date'] = pd.to_datetime(df['installation_date']).dt.strftime('%Y-%m-%d')
                    if 'created_at' in df.columns:
                        df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
                    if 'updated_at' in df.columns:
                        df['updated_at'] = pd.to_datetime(df['updated_at']).dt.strftime('%Y-%m-%d %H:%M')

                    forecast_content = dash_table.DataTable(
                        id='forecast-data-editable-table',
                        data=df.to_dict('records'),
                        columns=[
                            {"name": "ID", "id": "id", "editable": False},
                            {"name": "System SN", "id": "system_sn", "editable": True},
                            {"name": "Installation Date", "id": "installation_date", "editable": True, "type": "datetime"},
                            {"name": "Units", "id": "units", "editable": True, "type": "numeric"}
                        ],
                        editable=True,
                        row_deletable=True,
                        style_table={'overflowX': 'auto'},
                        style_cell={'textAlign': 'left', 'padding': '10px', 'minWidth': '150px'},
                        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                        style_data_conditional=[
                            {
                                'if': {'column_editable': True},
                                'backgroundColor': 'rgb(248, 248, 248)',
                            }
                        ]
                    )
                else:
                    forecast_content = html.Div("No forecast data found. Please upload forecast data first.", style={'color': 'gray'})
            else:
                forecast_content = html.Div("Error loading forecast data", style={'color': 'red'})
        except Exception as e:
            forecast_content = html.Div(f"Error: {str(e)}", style={'color': 'red'})

    if active_tab == "inventory":
        try:
            # Use projected inventory data for enhanced view
            inventory_response = requests.get(f"{API_BASE}/inventory/projected")
            alerts_response = requests.get(f"{API_BASE}/inventory/alerts")

            if inventory_response.status_code == 200:
                inventory_data = inventory_response.json()
                if inventory_data:
                    df = pd.DataFrame(inventory_data)

                    # Convert datetime columns to strings for display
                    if 'created_at' in df.columns:
                        df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
                    if 'updated_at' in df.columns:
                        df['updated_at'] = pd.to_datetime(df['updated_at']).dt.strftime('%Y-%m-%d %H:%M')
                    if 'last_restock_date' in df.columns:
                        df['last_restock_date'] = pd.to_datetime(df['last_restock_date']).dt.strftime('%Y-%m-%d %H:%M')

                    inventory_content = html.Div([
                        dash_table.DataTable(
                            id='inventory-data-editable-table',
                            data=df.to_dict('records'),
                            columns=[
                                {"name": "Part ID", "id": "part_id", "editable": False},
                                {"name": "Part Name", "id": "part_name", "editable": True},
                                {"name": "Current Stock", "id": "current_stock", "editable": True, "type": "numeric"},
                                {"name": "Pending Qty", "id": "pending_qty", "editable": False, "type": "numeric"},
                                {"name": "Allocated Qty", "id": "allocated_qty", "editable": False, "type": "numeric"},
                                {"name": "Net Available", "id": "net_available", "editable": False, "type": "numeric"},
                                {"name": "Days Supply", "id": "days_of_supply", "editable": False, "type": "numeric", "format": {"specifier": ".1f"}},
                                {"name": "Minimum Stock", "id": "minimum_stock", "editable": True, "type": "numeric"},
                                {"name": "Unit Cost", "id": "unit_cost", "editable": True, "type": "numeric", "format": {"specifier": "$.2f"}},
                                {"name": "Supplier", "id": "supplier_name", "editable": True},
                                {"name": "Risk Level", "id": "shortage_risk", "editable": False},
                                {"name": "Pending Orders", "id": "pending_orders_summary", "editable": False}
                            ],
                            editable=True,
                            style_table={'overflowX': 'auto'},
                            style_cell={'textAlign': 'left', 'padding': '10px', 'minWidth': '120px'},
                            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                            style_data_conditional=[
                                {
                                    'if': {'filter_query': '{shortage_risk} = Critical'},
                                    'backgroundColor': '#dc3545',
                                    'color': 'white',
                                },
                                {
                                    'if': {'filter_query': '{shortage_risk} = High'},
                                    'backgroundColor': '#fd7e14',
                                    'color': 'white',
                                },
                                {
                                    'if': {'filter_query': '{shortage_risk} = Medium'},
                                    'backgroundColor': '#ffc107',
                                    'color': 'black',
                                },
                                {
                                    'if': {'filter_query': '{shortage_risk} = Low'},
                                    'backgroundColor': '#28a745',
                                    'color': 'white',
                                },
                                {
                                    'if': {'filter_query': '{net_available} < {minimum_stock}'},
                                    'fontWeight': 'bold'
                                }
                            ]
                        )
                    ])
                else:
                    inventory_content = html.Div("No inventory data found. Please upload inventory data first.", style={'color': 'gray'})
            else:
                inventory_content = html.Div("Error loading inventory data", style={'color': 'red'})

            # Process alerts
            if alerts_response.status_code == 200:
                alerts_data = alerts_response.json()
                if alerts_data:
                    alert_cards = []
                    for alert in alerts_data[:10]:  # Show top 10 alerts
                        severity_color = {
                            'critical': 'danger',
                            'high': 'warning',
                            'medium': 'info',
                            'low': 'light'
                        }.get(alert['severity'], 'light')

                        alert_cards.append(
                            dbc.Alert([
                                html.H6(f"{alert['alert_type'].title()} Alert: {alert['part_name']}", className="alert-heading"),
                                html.P(alert['recommended_action'], className="mb-1"),
                                html.Small(f"Current Stock: {alert['current_stock']} | Target: {alert['target_stock']}", className="text-muted")
                            ], color=severity_color, className="mb-2")
                        )

                    inventory_alerts_content = html.Div(alert_cards) if alert_cards else html.Div("No critical alerts")
                else:
                    inventory_alerts_content = html.Div("No alerts available")
            else:
                inventory_alerts_content = html.Div("No alerts available")

        except Exception as e:
            inventory_content = html.Div(f"Error loading inventory data: {str(e)}", style={'color': 'red'})
            inventory_alerts_content = html.Div("Error loading alerts", style={'color': 'red'})
    if active_tab == "pending-orders":
        try:
            response = requests.get(f"{API_BASE}/orders/pending")
            if response.status_code == 200:
                orders = response.json()
                df = pd.DataFrame(orders) if orders else pd.DataFrame(columns=[
                    'id','part_id','supplier_id','supplier_name','order_date','estimated_delivery_date','qty','unit_cost','payment_date','status','po_number','notes','mapped_part_id','match_confidence'
                ])
                # Always keep raw datetime for aggregation; format copies later for display
                df_raw = df.copy()

                # Fetch inventory to build dropdown options for mapped_part_id
                inv_resp = requests.get(f"{API_BASE}/inventory")
                inv_options = []
                if inv_resp.status_code == 200:
                    inv = inv_resp.json() or []
                    inv_options = [{'label': str(row.get('part_id')), 'value': str(row.get('part_id'))} for row in inv if row.get('part_id')]
                # Fallback to projected inventory if base inventory endpoint is empty
                if not inv_options:
                    proj = requests.get(f"{API_BASE}/inventory/projected")
                    if proj.status_code == 200:
                        data = proj.json() or []
                        ids = sorted({str(row.get('part_id')) for row in data if row.get('part_id')})
                        inv_options = [{'label': pid, 'value': pid} for pid in ids]
                # Add Clear Mapping option (use sentinel so menu isn't empty)
                inv_options = [{'label': '— Clear Mapping —', 'value': '__CLEAR__'}] + inv_options

                # Individual view table
                df_ind = df.copy()
                for col in ['order_date','estimated_delivery_date','payment_date','created_at','updated_at']:
                    if col in df_ind.columns:
                        s = pd.to_datetime(df_ind[col], errors='coerce', format='ISO8601')
                        df_ind[col] = s.dt.strftime('%Y-%m-%d').where(s.notna(), '')

                inv_count = max(0, len(inv_options) - 1)
                mapped_header = f"Mapped Part ({inv_count})"

                individual_table = dash_table.DataTable(
                    id='pending-orders-editable-table',
                    data=df_ind.to_dict('records'),
                    columns=[
                        {"name": "ID", "id": "id", "editable": False},
                        {"name": "Part ID", "id": "part_id", "editable": True},
                        {"name": mapped_header, "id": "mapped_part_id", "editable": True, "type": "text", "presentation": "dropdown"},
                        {"name": "Match %", "id": "match_confidence", "editable": False, "type": "numeric"},
                        {"name": "Supplier ID", "id": "supplier_id", "editable": True},
                        {"name": "Supplier Name", "id": "supplier_name", "editable": True},
                        {"name": "Order Date", "id": "order_date", "editable": True, "type": "datetime"},
                        {"name": "ETA", "id": "estimated_delivery_date", "editable": True, "type": "datetime"},
                        {"name": "Qty", "id": "qty", "editable": True, "type": "numeric"},
                        {"name": "Unit Cost", "id": "unit_cost", "editable": True, "type": "numeric"},
                        {"name": "Payment Date", "id": "payment_date", "editable": True, "type": "datetime"},
                        {"name": "Status", "id": "status", "editable": True, "presentation": "dropdown"},
                        {"name": "PO #", "id": "po_number", "editable": True},
                        {"name": "Notes", "id": "notes", "editable": True},
                    ],
                    editable=True,
                    row_deletable=True,
                    dropdown={
                        'status': {
                            'options': [
                                {'label': 'pending', 'value': 'pending'},
                                {'label': 'ordered', 'value': 'ordered'},
                                {'label': 'received', 'value': 'received'},
                                {'label': 'cancelled', 'value': 'cancelled'},
                            ]
                        },
                        'mapped_part_id': {
                            'options': inv_options
                        }
                    },
                    dropdown_conditional=[
                        {'if': {'column_id': 'mapped_part_id'}, 'options': inv_options}
                    ],
                    tooltip_header={'mapped_part_id': f"{len(inv_options)} options"},
                    css=[
                        {'selector': '.dash-spreadsheet td div', 'rule': 'display: block; overflow: visible; white-space: normal;'},
                        {'selector': '.dash-dropdown .Select-menu-outer', 'rule': 'z-index: 2000;'}
                    ],
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left', 'padding': '10px', 'minWidth': '120px', 'overflow': 'visible'},
                    style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
                )
            # Build container comprising the toggle and the tables container
            pending_orders_content = html.Div([
                # Toggle is already rendered in the Pending Orders tab layout above
                dcc.Store(id='pending-orders-raw-store', data=df_raw.to_dict('records')),
                html.Div(id='pending-orders-view-container', children=[individual_table])
            ])

        except Exception as e:
            pending_orders_content = html.Div(f"Error: {str(e)}", style={'color': 'red'})




    return bom_content, forecast_content, inventory_content, inventory_alerts_content, pending_orders_content

@app.callback(
    Output('planning-status', 'children'),
    Output('planning-results-store', 'data'),
    Input('run-planning-btn', 'n_clicks'),
    State('start-date', 'date'),
    State('end-date', 'date'),
    prevent_initial_call=True
)
def run_planning(n_clicks, start_date, end_date):
    if n_clicks:
        try:
            # Convert date strings to datetime
            start_dt = datetime.fromisoformat(start_date) if start_date else datetime(2025, 1, 1)
            end_dt = datetime.fromisoformat(end_date) if end_date else datetime(2025, 12, 31)

            # Call planning API
            response = requests.post(f"{API_BASE}/plan/run", params={
                'start_date': start_dt.isoformat(),
                'end_date': end_dt.isoformat()
            })

            if response.status_code == 200:
                # Store a timestamp to trigger updates
                return html.Div([
                    html.H5("Planning Complete!", className="upload-success"),
                    html.P("Results available in Dashboard tab", className="upload-success")
                ]), {'timestamp': datetime.now().isoformat()}
            else:
                return html.Div([
                    html.H5("Planning Failed", className="upload-error"),
                    html.P("Check the console for details", className="upload-error")
                ]), None
        except Exception as e:
            return html.Div([
                html.H5("Planning Error", className="upload-error"),
                html.P(str(e), className="upload-error")
            ]), None
    return "", None

@app.callback(
    Output('tabs', 'active_tab'),
    Input('planning-results-store', 'data'),
    prevent_initial_call=True
)
def switch_to_dashboard_tab(data):
    if data:
        return "dashboard"
    return "data-planning"

@app.callback(
    Output('key-metrics-display', 'children'),
    Input('planning-results-store', 'data'),
    State('start-date', 'date'),
    State('end-date', 'date')
)
def update_key_metrics(data, start_date, end_date):
    if data:
        try:
            # Convert date strings to datetime
            start_dt = datetime.fromisoformat(start_date) if start_date else datetime(2025, 1, 1)
            end_dt = datetime.fromisoformat(end_date) if end_date else datetime(2025, 12, 31)

            # Get metrics from API
            response = requests.get(f"{API_BASE}/metrics", params={
                'start_date': start_dt.isoformat(),
                'end_date': end_dt.isoformat()
            })

            if response.status_code == 200:
                metrics = response.json()
                return dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H3(f"{metrics['orders_next_30d']}", style={'color': 'var(--knt-primary)'}),
                                html.P("Orders Next 30 Days", className="mb-0", style={'color': 'var(--knt-gray-600)'})
                            ])
                        ], className="metrics-card")
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H3(f"{metrics['orders_next_60d']}", style={'color': 'var(--knt-primary)'}),
                                html.P("Orders Next 60 Days", className="mb-0", style={'color': 'var(--knt-gray-600)'})
                            ])
                        ], className="metrics-card")
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H3(f"${metrics['cash_out_90d']:,.0f}", style={'color': 'var(--knt-warning)'}),
                                html.P("Cash Out 90 Days", className="mb-0", style={'color': 'var(--knt-gray-600)'})
                            ])
                        ], className="metrics-card")
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H3(f"${metrics['largest_purchase']:,.0f}", style={'color': 'var(--knt-danger)'}),
                                html.P("Largest Purchase", className="mb-0", style={'color': 'var(--knt-gray-600)'})
                            ])
                        ], className="metrics-card")
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H3(f"${metrics.get('tariff_spend_90d', 0):,.0f}", style={'color': '#dc3545'}),
                                html.P("Tariff Spend 90 Days", className="mb-0", style={'color': 'var(--knt-gray-600)'})
                            ])
                        ], className="metrics-card")
                    ], width=3)
                ])
            else:
                return html.Div("Error loading metrics", style={'color': 'red'})
        except Exception as e:
            return html.Div(f"Error: {str(e)}", style={'color': 'red'})
    return ""

@app.callback(
    Output('order-schedule-display', 'children'),
    Input('planning-results-store', 'data'),
    Input('order-view-toggle', 'value'),
    State('start-date', 'date'),
    State('end-date', 'date')
)
def update_order_schedule(data, view_type, start_date, end_date):
    if data:
        try:
            # Convert date strings to datetime
            start_dt = datetime.fromisoformat(start_date) if start_date else datetime(2025, 1, 1)
            end_dt = datetime.fromisoformat(end_date) if end_date else datetime(2025, 12, 31)

            # Choose endpoint based on view type
            if view_type == "aggregated":
                endpoint = f"{API_BASE}/orders/by-supplier"
            else:
                endpoint = f"{API_BASE}/orders"

            # Get orders from API
            response = requests.get(endpoint, params={
                'start_date': start_dt.isoformat(),
                'end_date': end_dt.isoformat()
            })

            if response.status_code == 200:
                orders = response.json()
                if orders:
                    df = pd.DataFrame(orders)
                    df['order_date'] = pd.to_datetime(df['order_date']).dt.strftime('%Y-%m-%d')
                    df['payment_date'] = pd.to_datetime(df['payment_date']).dt.strftime('%Y-%m-%d')
                    if 'eta_date' in df.columns:
                        df['eta_date'] = pd.to_datetime(df['eta_date']).dt.strftime('%Y-%m-%d')
                    df['total_cost'] = df['total_cost'].apply(lambda x: f"${x:,.2f}")
                    # Dollar formatting for tariff/shipping columns if present
                    if 'total_tariff_amount' in df.columns:
                        df['total_tariff_amount'] = df['total_tariff_amount'].apply(lambda x: f"${x:,.2f}")
                    if 'total_shipping_cost' in df.columns:
                        df['total_shipping_cost'] = df['total_shipping_cost'].apply(lambda x: f"${x:,.2f}")

                    if view_type == "aggregated":
                        # Aggregated supplier view
                        # Remove the 'parts' field as it contains lists that DataTable can't handle
                        df_display = df.drop(columns=['parts'], errors='ignore')

                        # Build an Export link per row to trigger Google Calendar export
                        # Construct the API URL with query params per-row via markdown link
                        base_api = f"{API_BASE}/calendar/export/by-supplier"
                        def build_link(row):
                            # Prefer supplier_id if present
                            sid = row.get('supplier_id')
                            sname = row.get('supplier_name')
                            od = row.get('order_date')
                            params = []
                            params.append(f"start_date={start_dt.isoformat()}")
                            params.append(f"end_date={end_dt.isoformat()}")
                            if sid:
                                params.append(f"supplier_id={sid}")
                            elif sname:
                                # URL encode spaces minimally
                                params.append(f"supplier_name={requests.utils.quote(str(sname))}")
                            if od:
                                params.append(f"order_date={od}T00:00:00")
                            params.append("as_html=true")
                            return f"[Export to Calendar]({base_api}?{'&'.join(params)})"
                        df_display['export'] = df_display.apply(build_link, axis=1)

                        return dash_table.DataTable(
                            data=df_display.to_dict('records'),
                            columns=[
                                {"name": "Supplier", "id": "supplier_name"},
                                {"name": "Order Date", "id": "order_date"},
                                {"name": "ETA", "id": "eta_date"},
                                {"name": "Parts Count", "id": "total_parts"},
                                {"name": "Total Cost", "id": "total_cost"},
                                {"name": "Tariffs", "id": "total_tariff_amount"},
                                {"name": "Shipping", "id": "total_shipping_cost"},
                                {"name": "Payment Date", "id": "payment_date"},
                                {"name": "Days to Order", "id": "days_until_order"},
                                {"name": "Days to ETA", "id": "days_until_eta"},
                                {"name": "Days to Payment", "id": "days_until_payment"},
                                {"name": "Action", "id": "export", "presentation": "markdown"}
                            ],
                            style_table={'overflowX': 'auto'},
                            style_cell={'textAlign': 'left', 'padding': '10px'},
                            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                            markdown_options={"link_target": "_blank"}
                        )
                    else:
                        # Detailed part view
                        # Add supplier column if data exists
                        columns = [
                            {"name": "Part ID", "id": "part_id"},
                            {"name": "Description", "id": "part_description"},
                        ]

                        # Add supplier column if data exists
                        if 'supplier_name' in df.columns:
                            columns.append({"name": "Supplier", "id": "supplier_name"})

                        columns.extend([
                            {"name": "Order Date", "id": "order_date"},
                            {"name": "Qty", "id": "qty"},
                            {"name": "Unit Cost", "id": "unit_cost"},
                            {"name": "Total Cost", "id": "total_cost"},
                            {"name": "Tariff $", "id": "tariff_amount"},
                            {"name": "Tariff %", "id": "tariff_rate"},
                            {"name": "Shipping $", "id": "shipping_cost_total"},
                            {"name": "Origin", "id": "country_of_origin"},
                            {"name": "Tariffs?", "id": "subject_to_tariffs"},
                            {"name": "Payment Date", "id": "payment_date"},
                            {"name": "ETA", "id": "eta_date"},
                            {"name": "Days to ETA", "id": "days_until_eta"}
                        ])

                        # Dollar formatting for detailed view
                        if 'tariff_amount' in df.columns:
                            df['tariff_amount'] = df['tariff_amount'].apply(lambda x: f"${x:,.2f}")
                        if 'shipping_cost_total' in df.columns:
                            df['shipping_cost_total'] = df['shipping_cost_total'].apply(lambda x: f"${x:,.2f}")
                        if 'unit_cost' in df.columns:
                            df['unit_cost'] = df['unit_cost'].apply(lambda x: f"${x:,.2f}")

                        return dash_table.DataTable(
                            data=df.to_dict('records'),
                            columns=columns,
                            style_table={'overflowX': 'auto'},
                            style_cell={'textAlign': 'left', 'padding': '10px'},
                            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
                        )
                else:
                    return html.Div("No orders found for the selected date range.", style={'color': 'gray'})
            else:
                return html.Div(f"Error loading orders: {response.status_code}", style={'color': 'red'})
        except Exception as e:
            return html.Div(f"Error: {str(e)}", style={'color': 'red'})
    return ""

@app.callback(
    Output('tariff-summary', 'children'),
    Input('planning-results-store', 'data'),
    State('start-date', 'date'),
    State('end-date', 'date')
)
def update_tariff_summary(data, start_date, end_date):
    if data:
        try:
            start_dt = datetime.fromisoformat(start_date) if start_date else datetime(2025, 1, 1)
            end_dt = datetime.fromisoformat(end_date) if end_date else datetime(2025, 12, 31)
            detailed = requests.get(f"{API_BASE}/orders", params={'start_date': start_dt.isoformat(), 'end_date': end_dt.isoformat()})
            if detailed.status_code == 200:
                orders = detailed.json()
                if orders:
                    df = pd.DataFrame(orders)
                    total_tariffs = float(df.get('tariff_amount', pd.Series([0])).sum())
                    total_shipping = float(df.get('shipping_cost_total', pd.Series([0])).sum())
                    impacted_parts = int((df.get('subject_to_tariffs') == 'Yes').sum()) if 'subject_to_tariffs' in df.columns else 0
                    return dbc.Row([
                        dbc.Col(dbc.Card(dbc.CardBody([
                            html.H6("Tariff Spend (All)", className="mb-1"),
                            html.H3(f"${total_tariffs:,.0f}", className="text-danger")
                        ])), width=3),
                        dbc.Col(dbc.Card(dbc.CardBody([
                            html.H6("Shipping Spend (All)", className="mb-1"),
                            html.H3(f"${total_shipping:,.0f}", className="text-info")
                        ])), width=3),
                        dbc.Col(dbc.Card(dbc.CardBody([
                            html.H6("Parts Impacted by Tariffs", className="mb-1"),
                            html.H3(f"{impacted_parts:,}", className="text-warning")
                        ])), width=3)
                    ])
        except Exception:
            pass
    return ""

@app.callback(
    Output('order-summary-cards', 'children'),
    Input('planning-results-store', 'data'),
    Input('order-view-toggle', 'value'),
    State('start-date', 'date'),
    State('end-date', 'date')
)
def update_order_summary(data, view_type, start_date, end_date):
    if data:
        try:
            # Convert date strings to datetime
            start_dt = datetime.fromisoformat(start_date) if start_date else datetime(2025, 1, 1)
            end_dt = datetime.fromisoformat(end_date) if end_date else datetime(2025, 12, 31)

            # Get both detailed and aggregated orders for comparison
            detailed_response = requests.get(f"{API_BASE}/orders", params={
                'start_date': start_dt.isoformat(),
                'end_date': end_dt.isoformat()
            })

            aggregated_response = requests.get(f"{API_BASE}/orders/by-supplier", params={
                'start_date': start_dt.isoformat(),
                'end_date': end_dt.isoformat()
            })

            if detailed_response.status_code == 200 and aggregated_response.status_code == 200:
                detailed_orders = detailed_response.json()
                aggregated_orders = aggregated_response.json()

                detailed_count = len(detailed_orders)
                aggregated_count = len(aggregated_orders)

                # Calculate total costs
                detailed_total = sum(order.get('total_cost', 0) for order in detailed_orders)
                aggregated_total = sum(order.get('total_cost', 0) for order in aggregated_orders)

                # Calculate reduction percentage
                reduction_pct = ((detailed_count - aggregated_count) / detailed_count * 100) if detailed_count > 0 else 0

                # Create summary cards
                cards = dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("Detailed Orders", className="card-title"),
                                html.H3(f"{detailed_count:,}", className="text-primary"),
                                html.P("Individual part orders", className="card-text")
                            ])
                        ], color="light", outline=True)
                    ], width=4),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("Aggregated Orders", className="card-title"),
                                html.H3(f"{aggregated_count:,}", className="text-success"),
                                html.P("Consolidated supplier orders", className="card-text")
                            ])
                        ], color="light", outline=True)
                    ], width=4),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("Total Value", className="card-title"),
                                html.H3(f"${detailed_total:,.0f}", className="text-warning"),
                                html.P("Total order value", className="card-text")
                            ])
                        ], color="light", outline=True)
                    ], width=4)
                ])

                return cards

        except Exception as e:
            return html.Div(f"Error loading summary: {str(e)}", style={'color': 'red'})

    return ""

@app.callback(
    Output('pending-orders-table', 'children'),
    [Input('refresh-pending-orders-btn', 'n_clicks')],
    prevent_initial_call=True
)
def refresh_pending_orders(n_clicks):
    try:
        response = requests.get(f"{API_BASE}/orders/pending")
        if response.status_code == 200:
            orders = response.json()
            df = pd.DataFrame(orders) if orders else pd.DataFrame(columns=[
                'id','part_id','supplier_id','supplier_name','order_date','estimated_delivery_date','qty','unit_cost','payment_date','status','po_number','notes','mapped_part_id','match_confidence'
            ])
            for col in ['order_date','estimated_delivery_date','payment_date','created_at','updated_at']:
                if col in df.columns:
                    s = pd.to_datetime(df[col], errors='coerce', format='ISO8601')
                    df[col] = s.dt.strftime('%Y-%m-%d').where(s.notna(), '')

            # Fetch inventory options for mapped_part_id dropdown
            inv_resp = requests.get(f"{API_BASE}/inventory")
            inv_options = []
            if inv_resp.status_code == 200:
                inv = inv_resp.json() or []
                inv_options = [{'label': str(row.get('part_id')), 'value': str(row.get('part_id'))} for row in inv if row.get('part_id')]
            if not inv_options:
                proj = requests.get(f"{API_BASE}/inventory/projected")
                if proj.status_code == 200:
                    data = proj.json() or []
                    ids = sorted({str(row.get('part_id')) for row in data if row.get('part_id')})
                    inv_options = [{'label': pid, 'value': pid} for pid in ids]
            inv_options = [{'label': '— Clear Mapping —', 'value': '__CLEAR__'}] + inv_options

            return dash_table.DataTable(
                id='pending-orders-editable-table',
                data=df.to_dict('records'),
                columns=[
                    {"name": "ID", "id": "id", "editable": False},
                    {"name": "Part ID", "id": "part_id", "editable": True},
                    {"name": f"Mapped Part ({max(0, len(inv_options)-1)})", "id": "mapped_part_id", "editable": True, "type": "text", "presentation": "dropdown"},
                    {"name": "Match %", "id": "match_confidence", "editable": False, "type": "numeric"},
                    {"name": "Supplier ID", "id": "supplier_id", "editable": True},
                    {"name": "Supplier Name", "id": "supplier_name", "editable": True},
                    {"name": "Order Date", "id": "order_date", "editable": True, "type": "datetime"},
                    {"name": "ETA", "id": "estimated_delivery_date", "editable": True, "type": "datetime"},
                    {"name": "Qty", "id": "qty", "editable": True, "type": "numeric"},
                    {"name": "Unit Cost", "id": "unit_cost", "editable": True, "type": "numeric"},
                    {"name": "Payment Date", "id": "payment_date", "editable": True, "type": "datetime"},
                    {"name": "Status", "id": "status", "editable": True, "presentation": "dropdown"},
                    {"name": "PO #", "id": "po_number", "editable": True},
                    {"name": "Notes", "id": "notes", "editable": True},
                ],
                editable=True,
                row_deletable=True,
                dropdown={
                    'status': {
                        'options': [
                            {'label': 'pending', 'value': 'pending'},
                            {'label': 'ordered', 'value': 'ordered'},
                            {'label': 'received', 'value': 'received'},
                            {'label': 'cancelled', 'value': 'cancelled'},
                        ]
                    },
                    'mapped_part_id': {
                        'options': inv_options
                    }
                },
                dropdown_conditional=[
                    {'if': {'column_id': 'mapped_part_id'}, 'options': inv_options}
                ],
                tooltip_header={'mapped_part_id': f"{len(inv_options)} options"},
                css=[
                    {'selector': '.dash-spreadsheet td div', 'rule': 'display: block; overflow: visible; white-space: normal;'},
                    {'selector': '.dash-dropdown .Select-menu-outer', 'rule': 'z-index: 2000;'}
                ],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '10px', 'minWidth': '120px', 'overflow': 'visible'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
            )
        else:
            return html.Div("Error loading pending orders", style={'color': 'red'})
    except Exception as e:
        return html.Div(f"Error: {str(e)}", style={'color': 'red'})

@app.callback(
    Output('upload-pending-orders-pdf-output', 'children'),
    Input('upload-pending-orders-pdf', 'contents'),
    State('upload-pending-orders-pdf', 'filename'),
    prevent_initial_call=True
)
def handle_upload_pending_orders_pdf(contents, filename):
    if contents is None:
        return dash.no_update
    try:
        import base64
        header, b64data = contents.split(',')
        pdf_bytes = base64.b64decode(b64data)
        files = {'file': (filename or 'pending.pdf', pdf_bytes, 'application/pdf')}
        r = requests.post(f"{API_BASE}/orders/pending/upload-pdf", files=files, timeout=60)
        if r.status_code == 200:
            data = r.json()
            inserted = data.get('inserted', [])
            errors = data.get('errors', [])
            msg = f"Inserted {len(inserted)} orders from {filename}."
            if errors:
                msg += f" Warnings: {min(len(errors), 3)} (details in console)."
                print('PDF extraction warnings:', errors)
            return dbc.Alert(msg, color="success")
        else:
            return dbc.Alert(f"Upload failed: {r.status_code} {r.text}", color="danger")
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger")

@app.callback(
    Output('pending-orders-save-status', 'children', allow_duplicate=True),
    Input('save-pending-orders-btn', 'n_clicks'),
    State('pending-orders-editable-table', 'data'),
    prevent_initial_call=True
)
def save_pending_orders(n_clicks, table_data):
    if not n_clicks:
        return ""
    try:
        # Upsert each row
        saved = 0
        present_ids = set()
        for row in (table_data or []):
            payload = {
                'part_id': row.get('part_id',''),
                'supplier_id': row.get('supplier_id'),
                'supplier_name': row.get('supplier_name'),
                'order_date': row.get('order_date'),
                'estimated_delivery_date': row.get('estimated_delivery_date'),
                'qty': int(row.get('qty', 0) or 0),
                'unit_cost': float(row.get('unit_cost', 0) or 0.0),
                'payment_date': row.get('payment_date'),
                'status': row.get('status') or 'pending',
                'po_number': row.get('po_number'),
                'notes': row.get('notes'),
                'mapped_part_id': row.get('mapped_part_id') or None,
                'match_confidence': int(row.get('match_confidence') or 0),
            }
            order_id = row.get('id')
            if order_id:
                present_ids.add(order_id)
                r = requests.put(f"{API_BASE}/orders/pending/{order_id}", json=payload)
            else:
                r = requests.post(f"{API_BASE}/orders/pending", json=payload)
                if r.status_code in [200, 201]:
                    try:
                        present_ids.add(r.json().get('id'))
                    except Exception:
                        pass
            if r.status_code in [200,201]:
                saved += 1
        # Delete orders that were removed from the table
        try:
            existing = requests.get(f"{API_BASE}/orders/pending")
            if existing.status_code == 200:
                existing_ids = {row.get('id') for row in (existing.json() or [])}
                to_delete = [oid for oid in existing_ids if oid and oid not in present_ids]
                for oid in to_delete:
                    requests.delete(f"{API_BASE}/orders/pending/{oid}")
        except Exception:
            pass
        return dbc.Alert(f"Saved {saved} pending orders", color="success", duration=3000)
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger", duration=5000)


@app.callback(
    Output('pending-orders-save-status', 'children', allow_duplicate=True),
    Input('pending-orders-editable-table', 'data_timestamp'),
    State('pending-orders-editable-table', 'data'),
    State('pending-orders-editable-table', 'active_cell'),
    prevent_initial_call=True
)
def persist_mapped_part_on_change(ts, rows, active_cell):
    try:
        # Only react to edits in the Mapped Part column
        if not rows or not active_cell or active_cell.get('column_id') != 'mapped_part_id':
            return no_update
        i = active_cell.get('row')
        if i is None or i >= len(rows):
            return no_update
        row = rows[i]
        oid = row.get('id')
        mapped = row.get('mapped_part_id')
        if oid is None:
            return no_update
        # Interpret clear sentinel
        if mapped == '__CLEAR__':
            mapped = None
        # Normalize helper converts "" -> None
        def nz(val):
            return None if val in (None, '', 'null', 'None') else val
        payload = {
            'part_id': row.get('part_id',''),
            'supplier_id': nz(row.get('supplier_id')),
            'supplier_name': nz(row.get('supplier_name')),
            'order_date': nz(row.get('order_date')),
            'estimated_delivery_date': nz(row.get('estimated_delivery_date')),
            'qty': int(row.get('qty', 0) or 0),
            'unit_cost': float(row.get('unit_cost', 0) or 0.0),
            'payment_date': nz(row.get('payment_date')),
            'status': (row.get('status') or 'pending'),
            'po_number': nz(row.get('po_number')),
            'notes': nz(row.get('notes')),
        }
        # If user selected Clear Mapping, set to null; else set mapped and confidence 100
        if mapped:
            payload['mapped_part_id'] = mapped
            payload['match_confidence'] = 100
        else:
            payload['mapped_part_id'] = None
            payload['match_confidence'] = 0
        r = requests.put(f"{API_BASE}/orders/pending/{oid}", json=payload)
        if r.status_code in [200,201]:
            return dbc.Alert(f"Updated mapping for order {oid}", color="success", duration=2000)
        else:
            return dbc.Alert(f"Update failed: {r.status_code} {r.text}", color="danger", duration=4000)
    except Exception as e:
        return dbc.Alert(f"Error updating mappings: {str(e)}", color="danger", duration=4000)


@app.callback(
    Output('pending-orders-remap-status', 'children'),
    Input('remap-pending-orders-btn', 'n_clicks'),
    prevent_initial_call=True
)
def remap_pending_orders_btn(n_clicks):
    try:
        r = requests.post(f"{API_BASE}/orders/pending/remap")
        if r.status_code == 200:
            data = r.json()
            updated = data.get('updated', 0)
            count = data.get('count', 0)
            return dbc.Alert(f"Re-mapped {updated} of {count} orders", color="warning", duration=3000)
        else:
            return dbc.Alert(f"Remap failed: {r.status_code} {r.text}", color="danger", duration=5000)
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger", duration=5000)

        # End save handler
        # (note: delete of missing rows already performed above)
        return dbc.Alert(f"Saved {saved} pending orders", color="success", duration=3000)
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger", duration=5000)

@app.callback(
    Output('download-pending-orders', 'data'),
    Input('export-pending-orders-btn', 'n_clicks'),
    prevent_initial_call=True
)
def export_pending_orders(n_clicks):
    try:
        resp = requests.get(f"{API_BASE}/export/orders-pending")
        if resp.status_code == 200:
            return dict(content=resp.content.decode('utf-8'), filename='pending_orders.csv')
        return None
    except Exception:
        return None

@app.callback(
    Output('cash-flow-chart', 'figure'),
    Input('planning-results-store', 'data'),
    State('start-date', 'date'),
    State('end-date', 'date')
)
def update_cash_flow_chart(data, start_date, end_date):
    if data:
        try:
            # Convert date strings to datetime
            start_dt = datetime.fromisoformat(start_date) if start_date else datetime(2025, 1, 1)
            end_dt = datetime.fromisoformat(end_date) if end_date else datetime(2025, 12, 31)

            # Get cash flow from API
            response = requests.get(f"{API_BASE}/cashflow", params={
                'start_date': start_dt.isoformat(),
                'end_date': end_dt.isoformat()
            })

            if response.status_code == 200:
                cash_flow = response.json()
                if cash_flow:
                    df = pd.DataFrame(cash_flow)
                    df['date'] = pd.to_datetime(df['date'])

                    fig = go.Figure()

                    # Add total outflow (cash out)
                    fig.add_trace(go.Scatter(
                        x=df['date'],
                        y=df['total_outflow'],
                        mode='lines+markers',
                        name='Cash Outflow',
                        line=dict(color='#dc3545', width=3),
                        marker=dict(size=8, color='#dc3545')
                    ))

                    # Add cumulative cash flow
                    fig.add_trace(go.Scatter(
                        x=df['date'],
                        y=df['cumulative_cash_flow'],
                        mode='lines+markers',
                        name='Cumulative Cash Flow',
                        line=dict(color='#6f42c1', width=3),
                        marker=dict(size=8, color='#6f42c1')
                    ))

                    # Add net cash flow
                    fig.add_trace(go.Scatter(
                        x=df['date'],
                        y=df['net_cash_flow'],
                        mode='lines+markers',
                        name='Net Cash Flow',
                        line=dict(color='#fd7e14', width=3),
                        marker=dict(size=8, color='#fd7e14')
                    ))

                    fig.update_layout(
                        title="Cash Flow Projection",
                        xaxis_title="Date",
                        yaxis_title="Cash Flow ($)",
                        hovermode='x unified',
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        font=dict(color='#212529', size=12),
                        title_font=dict(size=18, color='#212529'),
                        xaxis=dict(
                            gridcolor='#e9ecef',
                            zerolinecolor='#dee2e6'
                        ),
                        yaxis=dict(
                            gridcolor='#e9ecef',
                            zerolinecolor='#dee2e6',
                            tickformat='$,.0f'
                        ),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1
                        )
                    )

                    return fig
                else:
                    # Return empty chart with message
                    fig = go.Figure()
                    fig.add_annotation(
                        text="No cash flow data available",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, showarrow=False,
                        font=dict(size=16, color="var(--knt-gray-500)")
                    )
                    fig.update_layout(
                        title="Cash Flow Projection",
                        xaxis_title="Date",
                        yaxis_title="Cash Out ($)",
                        plot_bgcolor='var(--knt-white)',
                        paper_bgcolor='var(--knt-white)',
                        font=dict(color='var(--knt-primary)', size=14),
                        title_font=dict(size=18, color='var(--knt-primary)')
                    )
                    return fig
            else:
                # Return error chart
                fig = go.Figure()
                fig.add_annotation(
                    text="Error loading cash flow data",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=16, color="var(--knt-danger)")
                )
                fig.update_layout(
                    plot_bgcolor='var(--knt-white)',
                    paper_bgcolor='var(--knt-white)',
                    font=dict(color='var(--knt-primary)', size=14),
                    title_font=dict(size=18, color='var(--knt-primary)')
                )
                return fig
        except Exception as e:
            # Return error chart
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="var(--knt-danger)")
            )
            fig.update_layout(
                plot_bgcolor='var(--knt-white)',
                paper_bgcolor='var(--knt-white)',
                font=dict(color='var(--knt-primary)', size=14),
                title_font=dict(size=18, color='var(--knt-primary)')
            )
            return fig
    return go.Figure()

# BOM Data Editor callbacks
@app.callback(
    Output('bom-data-table', 'children'),
    [Input('refresh-bom-btn', 'n_clicks')],
    prevent_initial_call=True
)
def update_bom_table(n_clicks):
    try:
        response = requests.get(f"{API_BASE}/bom")
        if response.status_code == 200:
            bom_data = response.json()
            if bom_data:
                df = pd.DataFrame(bom_data)

                # Convert datetime columns to strings for display
                if 'created_at' in df.columns:
                    df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
                if 'updated_at' in df.columns:
                    df['updated_at'] = pd.to_datetime(df['updated_at']).dt.strftime('%Y-%m-%d %H:%M')

                return dash_table.DataTable(
                    id='bom-data-editable-table',
                    data=df.to_dict('records'),
                    columns=[
                        {"name": "ID", "id": "id", "editable": False},
                        {"name": "Product ID", "id": "product_id", "editable": True},
                        {"name": "Part ID", "id": "part_id", "editable": True},
                        {"name": "Part Name", "id": "part_name", "editable": True},
                        {"name": "Quantity", "id": "quantity", "editable": True, "type": "numeric"},
                        {"name": "Unit Cost", "id": "unit_cost", "editable": True, "type": "numeric"},
                        {"name": "Cost per Product", "id": "cost_per_product", "editable": True, "type": "numeric"},
                        {"name": "Country of Origin", "id": "country_of_origin", "editable": True},
                        {"name": "Shipping Cost (per unit)", "id": "shipping_cost", "editable": True, "type": "numeric"},
                        {"name": "Beginning Inventory", "id": "beginning_inventory", "editable": True, "type": "numeric"},
                        {"name": "Supplier ID", "id": "supplier_id", "editable": True},
                        {"name": "Supplier Name", "id": "supplier_name", "editable": True},
                        {"name": "Manufacturer", "id": "manufacturer", "editable": True},
                        {"name": "AP Terms", "id": "ap_terms", "editable": True, "type": "numeric"},
                        {"name": "Manufacturing Lead Time", "id": "manufacturing_lead_time", "editable": True, "type": "numeric"},
                        {"name": "Shipping Lead Time", "id": "shipping_lead_time", "editable": True, "type": "numeric"},
                        {"name": "Subject to Tariffs", "id": "subject_to_tariffs", "editable": True, "presentation": "dropdown"}
                    ],
                    editable=True,
                    row_deletable=True,
                    dropdown={
                        'subject_to_tariffs': {
                            'options': [
                                {'label': 'Yes', 'value': 'Yes'},
                                {'label': 'No', 'value': 'No'}
                            ]
                        }
                    },
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left', 'padding': '10px', 'minWidth': '100px'},
                    style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                    style_data_conditional=[
                        {
                            'if': {'column_editable': True},
                            'backgroundColor': 'rgb(248, 248, 248)',
                        }
                    ]
                )
            else:
                return html.Div("No BOM data found. Please upload BOM data first.", style={'color': 'gray'})
        else:
            return html.Div("Error loading BOM data", style={'color': 'red'})
    except Exception as e:
        return html.Div(f"Error: {str(e)}", style={'color': 'red'})

@app.callback(
    Output('bom-save-status', 'children'),
    Input('save-bom-btn', 'n_clicks'),
    State('bom-data-editable-table', 'data'),
    prevent_initial_call=True
)
def save_bom_data(n_clicks, table_data):
    if not n_clicks:
        return ""

    if not table_data:
        return dbc.Alert("No data to save", color="warning", duration=3000)

    try:
        # Prepare data for API
        bom_data = []
        for row in table_data:
            # Remove read-only fields and convert types
            bom_record = {
                'id': row.get('id'),  # Include ID for updates
                'product_id': row.get('product_id', ''),
                'part_id': row.get('part_id', ''),
                'part_name': row.get('part_name', ''),
                'quantity': float(row.get('quantity', 0)) if row.get('quantity') else 0.0,
                'unit_cost': float(row.get('unit_cost', 0)) if row.get('unit_cost') else 0.0,
                'cost_per_product': float(row.get('cost_per_product', 0)) if row.get('cost_per_product') else 0.0,
                'beginning_inventory': int(row.get('beginning_inventory', 0)) if row.get('beginning_inventory') else 0,
                'country_of_origin': row.get('country_of_origin'),
                'shipping_cost': float(row.get('shipping_cost', 0)) if row.get('shipping_cost') else 0.0,
                'supplier_id': row.get('supplier_id'),
                'supplier_name': row.get('supplier_name'),
                'manufacturer': row.get('manufacturer'),
                'ap_terms': int(row.get('ap_terms')) if row.get('ap_terms') else None,
                'manufacturing_lead_time': int(row.get('manufacturing_lead_time')) if row.get('manufacturing_lead_time') else None,
                'shipping_lead_time': int(row.get('shipping_lead_time')) if row.get('shipping_lead_time') else None,
                'subject_to_tariffs': row.get('subject_to_tariffs', 'No')
            }
            bom_data.append(bom_record)

        # Save to API
        response = requests.put(f"{API_BASE}/bom/bulk", json=bom_data)

        if response.status_code == 200:
            result = response.json()
            return dbc.Alert(result.get('message', 'BOM data saved successfully!'), color="success", duration=3000)
        else:
            return dbc.Alert(f"Error saving BOM data: {response.status_code}", color="danger", duration=5000)
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger", duration=5000)

# Forecast Data Editor callbacks
@app.callback(
    Output('forecast-data-table', 'children'),
    [Input('refresh-forecast-btn', 'n_clicks')],
    prevent_initial_call=True
)
def update_forecast_table(n_clicks):
    try:
        response = requests.get(f"{API_BASE}/forecast")
        if response.status_code == 200:
            forecast_data = response.json()
            if forecast_data:
                df = pd.DataFrame(forecast_data)

                # Convert datetime columns to strings for display
                if 'period_start' in df.columns:
                    df['period_start'] = pd.to_datetime(df['period_start']).dt.strftime('%Y-%m-%d')
                if 'created_at' in df.columns:
                    df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
                if 'updated_at' in df.columns:
                    df['updated_at'] = pd.to_datetime(df['updated_at']).dt.strftime('%Y-%m-%d %H:%M')

                return dash_table.DataTable(
                    id='forecast-data-editable-table',
                    data=df.to_dict('records'),
                    columns=[
                        {"name": "ID", "id": "id", "editable": False},
                        {"name": "SKU ID", "id": "sku_id", "editable": True},
                        {"name": "Period Start", "id": "period_start", "editable": True, "type": "datetime"},
                        {"name": "Units", "id": "units", "editable": True, "type": "numeric"}
                    ],
                    editable=True,
                    row_deletable=True,
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left', 'padding': '10px', 'minWidth': '150px'},
                    style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                    style_data_conditional=[
                        {
                            'if': {'column_editable': True},
                            'backgroundColor': 'rgb(248, 248, 248)',
                        }
                    ]
                )
            else:
                return html.Div("No forecast data found. Please upload forecast data first.", style={'color': 'gray'})
        else:
            return html.Div("Error loading forecast data", style={'color': 'red'})
    except Exception as e:
        return html.Div(f"Error: {str(e)}", style={'color': 'red'})

@app.callback(
    Output('forecast-save-status', 'children'),
    Input('save-forecast-btn', 'n_clicks'),
    State('forecast-data-editable-table', 'data'),
    prevent_initial_call=True
)
def save_forecast_data(n_clicks, table_data):
    if not n_clicks:
        return ""

    if not table_data:
        return dbc.Alert("No data to save", color="warning", duration=3000)

    try:
        # Prepare data for API
        forecast_data = []
        for row in table_data:
            # Convert types and format date
            forecast_record = {
                'id': row.get('id'),  # Include ID for updates
                'sku_id': row.get('sku_id', ''),
                'period_start': row.get('period_start', ''),
                'units': int(row.get('units', 0)) if row.get('units') else 0
            }
            forecast_data.append(forecast_record)

        # Save to API
        response = requests.put(f"{API_BASE}/forecast/bulk", json=forecast_data)

        if response.status_code == 200:
            result = response.json()
            return dbc.Alert(result.get('message', 'Forecast data saved successfully!'), color="success", duration=3000)
        else:
            return dbc.Alert(f"Error saving forecast data: {response.status_code}", color="danger", duration=5000)
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger", duration=5000)
    return ""

# Inventory Data Editor callbacks
# Inventory refresh callback removed - data now loads automatically on tab initialization

@app.callback(
    Output('inventory-save-status', 'children'),
    Input('save-inventory-btn', 'n_clicks'),
    State('inventory-data-editable-table', 'data'),
    prevent_initial_call=True
)
def save_inventory_data(n_clicks, table_data):
    if not n_clicks:
        return ""

    if not table_data:
        return dbc.Alert("No data to save", color="warning", duration=3000)

    try:
        # Prepare data for API
        inventory_data = []
        for row in table_data:
            # Calculate total value
            current_stock = int(row.get('current_stock', 0)) if row.get('current_stock') else 0
            unit_cost = float(row.get('unit_cost', 0)) if row.get('unit_cost') else 0.0
            total_value = current_stock * unit_cost

            inventory_record = {
                'part_id': row.get('part_id', ''),
                'part_name': row.get('part_name', ''),
                'current_stock': current_stock,
                'minimum_stock': int(row.get('minimum_stock', 0)) if row.get('minimum_stock') else 0,
                'maximum_stock': int(row.get('maximum_stock')) if row.get('maximum_stock') else None,
                'unit_cost': unit_cost,
                'total_value': total_value,
                'supplier_id': row.get('supplier_id'),
                'supplier_name': row.get('supplier_name'),
                'location': row.get('location'),
                'subject_to_tariffs': row.get('subject_to_tariffs', 'No'),
                'notes': row.get('notes')
            }
            inventory_data.append(inventory_record)

        # Save each inventory item via API (since we don't have bulk update endpoint yet)
        updated_count = 0
        for item in inventory_data:
            part_id = item['part_id']
            if part_id:
                # Try to update existing record first
                response = requests.put(f"{API_BASE}/inventory/{part_id}", json=item)
                if response.status_code == 404:
                    # If not found, create new record
                    response = requests.post(f"{API_BASE}/inventory", json=item)

                if response.status_code in [200, 201]:
                    updated_count += 1

        return dbc.Alert(f"Successfully saved {updated_count} inventory records!", color="success", duration=3000)
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger", duration=5000)
    return ""

# Update export button text based on view selection
@app.callback(
    Output('export-orders-btn', 'children'),
    Input('order-view-toggle', 'value')
)
def update_export_button_text(view_type):
    if view_type == "aggregated":
        return "Export Aggregated Orders to CSV"
    else:
        return "Export Detailed Orders to CSV"

# CSV Export callbacks
@app.callback(
    Output('download-orders', 'data'),
    Input('export-orders-btn', 'n_clicks'),
    State('start-date', 'date'),
    State('end-date', 'date'),
    State('order-view-toggle', 'value'),
    prevent_initial_call=True
)
def export_orders_csv(n_clicks, start_date, end_date, view_type):
    if n_clicks:
        try:
            # Convert date strings to datetime
            start_dt = datetime.fromisoformat(start_date) if start_date else datetime(2025, 1, 1)
            end_dt = datetime.fromisoformat(end_date) if end_date else datetime(2025, 12, 31)

            # Choose endpoint and filename based on view type
            if view_type == "aggregated":
                endpoint = f"{API_BASE}/export/orders-by-supplier"
                filename = "aggregated_orders_by_supplier.csv"
            else:
                endpoint = f"{API_BASE}/export/orders"
                filename = "detailed_order_schedule.csv"

            # Get data from API
            response = requests.get(endpoint, params={
                'start_date': start_dt.isoformat(),
                'end_date': end_dt.isoformat()
            })

            if response.status_code == 200:
                return dict(content=response.text, filename=filename, type="text/csv")
        except Exception as e:
            print(f"Error exporting orders: {e}")
    return None

# Tariff Calculator callbacks
@app.callback(
    Output('tc-quote-output', 'children'),
    Input('tc-quote-btn', 'n_clicks'),
    State('tc-hts', 'value'),
    State('tc-coo', 'value'),
    State('tc-importing', 'value'),
    State('tc-invoice', 'value'),
    State('tc-currency', 'value'),
    State('tc-fx', 'value'),
    State('tc-incoterm', 'value'),
    State('tc-entry-date', 'date'),
    State('tc-freight', 'value'),
    State('tc-insurance', 'value'),
    State('tc-assists', 'value'),
    State('tc-royalties', 'value'),
    State('tc-other', 'value'),
    State('tc-qty', 'value'),
    State('tc-weight', 'value'),
    State('tc-volume', 'value'),
    State('tc-fta', 'value'),
    State('tc-fta-program', 'value'),
    State('tc-addcvd', 'value'),
    State('tc-special', 'value'),
    State('tc-transport', 'value'),
    State('tc-port', 'value'),
    prevent_initial_call=True
)
def get_tariff_quote(n_clicks, hts, coo, importing, invoice, currency, fx, incoterm, entry_date,
                     freight, insurance, assists, royalties, other, qty, weight, volume, fta_vals,
                     fta_program, addcvd, special, transport, port):
    if not n_clicks:
        return ""
    try:
        payload = {
            'hts_code': hts,
            'country_of_origin': coo,
            'importing_country': importing or 'USA',
            'invoice_value': float(invoice or 0.0),
            'currency_code': currency or 'USD',
            'fx_rate': float(fx or 1.0),
            'freight_to_border': float(freight or 0.0),
            'insurance_cost': float(insurance or 0.0),
            'assists_tooling': float(assists or 0.0),
            'royalties_fees': float(royalties or 0.0),
            'other_dutiable': float(other or 0.0),
            'incoterm': incoterm,
            'quantity': float(qty) if qty is not None else None,
            'net_weight_kg': float(weight) if weight is not None else None,
            'volume_liters': float(volume) if volume is not None else None,
            'fta_eligible': bool(fta_vals) and len(fta_vals) > 0,
            'fta_program': fta_program,
            'add_cvd_rate_pct': float(addcvd or 0.0),
            'special_duty_surcharge_pct': float(special or 0.0),
            'entry_date': entry_date,
            'port_of_entry': port,
            'transport_mode': transport,
            'de_minimis': False
        }
        resp = requests.post(f"{API_BASE}/tariff/quote", json=payload, timeout=10)
        if resp.status_code != 200:
            return dbc.Alert(f"Quote failed: {resp.text}", color='danger')
        q = resp.json()
        # Nicely format
        rows = [
            ("Invoice Value (USD)", q['invoice_value_usd']),
            ("Dutiable Additions", q['dutiable_additions']),
            ("Dutiable Value", q['dutiable_value']),
            ("Base Ad-Valorem %", q['base_ad_valorem_rate_pct']),
            ("Effective Ad-Valorem %", q['effective_ad_valorem_rate_pct']),
            ("ADD/CVD %", q['add_cvd_rate_pct']),
            ("Special Surcharge %", q['special_surcharge_rate_pct']),
            ("Ad-Valorem Duty", q['ad_valorem_duty']),
            ("ADD/CVD Amount", q['add_cvd_amount']),
            ("Special Surcharge Amount", q['special_surcharge_amount']),
            ("MPF", q['mpf_amount']),
            ("HMF", q['hmf_amount']),
            ("Total Duties & Fees", q['total_duties_and_fees']),
            ("Effective Total %", q['effective_total_rate_pct'])
        ]
        table = dash_table.DataTable(
            data=[{"Metric": k, "Amount": (f"${v:,.2f}" if isinstance(v, (int, float)) else v)} for k, v in rows],
            columns=[{"name": "Metric", "id": "Metric"}, {"name": "Amount", "id": "Amount"}],
            style_cell={'textAlign': 'left', 'padding': '8px'},
            style_header={'backgroundColor': 'rgb(230,230,230)', 'fontWeight': 'bold'},
        )
        notes = q.get('notes', [])
        notes_el = html.Ul([html.Li(n) for n in notes]) if notes else ""
        return html.Div([
            html.H5("Quote Results", className='mb-2'),
            table,
            html.Div(notes_el, className='mt-3')
        ])
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color='danger')
@app.callback(
    Output('download-cashflow', 'data'),
    Input('export-cashflow-btn', 'n_clicks'),
    State('start-date', 'date'),
    State('end-date', 'date'),
    prevent_initial_call=True
)
def export_cashflow_csv(n_clicks, start_date, end_date):
    if n_clicks:
        try:
            # Convert date strings to datetime
            start_dt = datetime.fromisoformat(start_date) if start_date else datetime(2025, 1, 1)
            end_dt = datetime.fromisoformat(end_date) if end_date else datetime(2025, 12, 31)

            # Get data from API
            response = requests.get(f"{API_BASE}/export/cashflow", params={
                'start_date': start_dt.isoformat(),
                'end_date': end_dt.isoformat()
            })

            if response.status_code == 200:
                return dict(content=response.text, filename="cashflow_projection.csv", type="text/csv")
        except Exception as e:
            print(f"Error exporting cashflow: {e}")
    return None

@app.callback(
    Output('download-bom', 'data'),
    Input('export-bom-btn', 'n_clicks'),
    prevent_initial_call=True
)
def export_bom_csv(n_clicks):
    if n_clicks:
        try:
            # Get data from API
            response = requests.get(f"{API_BASE}/export/bom")

            if response.status_code == 200:
                return dict(content=response.text, filename="bom_data.csv", type="text/csv")
        except Exception as e:
            print(f"Error exporting BOM: {e}")
    return None

@app.callback(
    Output('download-forecast', 'data'),
    Input('export-forecast-btn', 'n_clicks'),
    prevent_initial_call=True
)
def export_forecast_csv(n_clicks):
    if n_clicks:
        try:
            # Get data from API
            response = requests.get(f"{API_BASE}/export/forecast")

            if response.status_code == 200:
                return dict(content=response.text, filename="forecast_data.csv", type="text/csv")
        except Exception as e:
            print(f"Error exporting forecast: {e}")
    return None

@app.callback(
    Output('download-inventory', 'data'),
    Input('export-inventory-btn', 'n_clicks'),
    prevent_initial_call=True
)
def export_inventory_csv(n_clicks):
    if n_clicks:
        try:
            # Get data from API
            response = requests.get(f"{API_BASE}/export/inventory")

            if response.status_code == 200:


                return dict(content=response.text, filename="inventory_data.csv", type="text/csv")
        except Exception as e:
            print(f"Error exporting inventory: {e}")
    return None
# Register external callbacks that use allow_duplicate outputs
try:
    from app.components.pending_orders_callbacks import register_callbacks as register_pending_orders_callbacks
    register_pending_orders_callbacks(app, API_BASE)
except Exception:
    pass


if __name__ == '__main__':
    app.run_server(debug=True, port=8050)