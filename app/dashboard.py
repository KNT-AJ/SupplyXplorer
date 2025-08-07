import dash
from dash import dcc, html, dash_table, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd
import requests
import json

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], assets_folder='../assets', suppress_callback_exceptions=True)
app.title = "SupplyXplorer Dashboard"

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
app.layout = dbc.Container([
    # Header with logo
    dbc.Row([
        dbc.Col([
            html.H1("SupplyXplorer", className="text-primary mb-0"),
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
                    # Order Summary Cards
                    html.Div(id="order-summary-cards", className="mb-3"),
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
                                    dbc.Button("Refresh Inventory Data", id="refresh-inventory-btn", color="primary", className="mb-2 w-100")
                                ], width=12),
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
                    html.Div(id="inventory-data-table")
                ])
            ])
        ], label="Inventory", tab_id="inventory")
    ], id="tabs", active_tab="data-planning"),
    dcc.Store(id='planning-results-store'),
    
    # Download components for CSV exports
    dcc.Download(id="download-orders"),
    dcc.Download(id="download-cashflow"),
    dcc.Download(id="download-bom"),
    dcc.Download(id="download-forecast"),
    dcc.Download(id="download-inventory")
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
     Output('inventory-data-table', 'children', allow_duplicate=True)],
    Input('tabs', 'active_tab'),
    prevent_initial_call=True
)
def initialize_tab_content(active_tab):
    """Initialize table content when tabs are first activated"""
    bom_content = ""
    forecast_content = ""
    inventory_content = ""
    
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
                            {"name": "Supplier ID", "id": "supplier_id", "editable": True},
                            {"name": "Supplier Name", "id": "supplier_name", "editable": True},
                            {"name": "Manufacturer", "id": "manufacturer", "editable": True},
                            {"name": "AP Terms", "id": "ap_terms", "editable": True, "type": "numeric"},
                            {"name": "Mfg Lead Time", "id": "manufacturing_lead_time", "editable": True, "type": "numeric"},
                            {"name": "Ship Lead Time", "id": "shipping_lead_time", "editable": True, "type": "numeric"}
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
            response = requests.get(f"{API_BASE}/inventory")
            if response.status_code == 200:
                inventory_data = response.json()
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
                                {"name": "ID", "id": "id", "editable": False},
                                {"name": "Part ID", "id": "part_id", "editable": True},
                                {"name": "Part Name", "id": "part_name", "editable": True},
                                {"name": "Current Stock", "id": "current_stock", "editable": True, "type": "numeric"},
                                {"name": "Minimum Stock", "id": "minimum_stock", "editable": True, "type": "numeric"},
                                {"name": "Maximum Stock", "id": "maximum_stock", "editable": True, "type": "numeric"},
                                {"name": "Unit Cost", "id": "unit_cost", "editable": True, "type": "numeric"},
                                {"name": "Total Value", "id": "total_value", "editable": False, "type": "numeric"},
                                {"name": "Supplier ID", "id": "supplier_id", "editable": True},
                                {"name": "Supplier Name", "id": "supplier_name", "editable": True},
                                {"name": "Location", "id": "location", "editable": True},
                                {"name": "Notes", "id": "notes", "editable": True}
                            ],
                            editable=True,
                            row_deletable=True,
                            style_table={'overflowX': 'auto'},
                            style_cell={'textAlign': 'left', 'padding': '10px', 'minWidth': '120px'},
                            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                            style_data_conditional=[
                                {
                                    'if': {'column_editable': True},
                                    'backgroundColor': 'rgb(248, 248, 248)',
                                },
                                {
                                    'if': {'filter_query': '{current_stock} < {minimum_stock}'},
                                    'backgroundColor': '#ffcccc',
                                    'color': 'black',
                                }
                            ]
                        )
                    ])
                else:
                    inventory_content = html.Div([
                        html.Div("No inventory data found. Please upload inventory data first.", style={'color': 'gray'}),
                        dash_table.DataTable(
                            id='inventory-data-editable-table',
                            data=[],
                            columns=[
                                {"name": "ID", "id": "id", "editable": False},
                                {"name": "Part ID", "id": "part_id", "editable": True},
                                {"name": "Part Name", "id": "part_name", "editable": True},
                                {"name": "Current Stock", "id": "current_stock", "editable": True, "type": "numeric"},
                                {"name": "Minimum Stock", "id": "minimum_stock", "editable": True, "type": "numeric"},
                                {"name": "Maximum Stock", "id": "maximum_stock", "editable": True, "type": "numeric"},
                                {"name": "Unit Cost", "id": "unit_cost", "editable": True, "type": "numeric"},
                                {"name": "Total Value", "id": "total_value", "editable": False, "type": "numeric"},
                                {"name": "Supplier ID", "id": "supplier_id", "editable": True},
                                {"name": "Supplier Name", "id": "supplier_name", "editable": True},
                                {"name": "Location", "id": "location", "editable": True},
                                {"name": "Notes", "id": "notes", "editable": True}
                            ],
                            editable=True,
                            row_deletable=True,
                            style_table={'overflowX': 'auto', 'display': 'none'},  # Hide empty table
                            style_cell={'textAlign': 'left', 'padding': '10px', 'minWidth': '120px'},
                            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
                        )
                    ])
            else:
                inventory_content = html.Div([
                    html.Div("Error loading inventory data", style={'color': 'red'}),
                    dash_table.DataTable(
                        id='inventory-data-editable-table',
                        data=[],
                        columns=[
                            {"name": "ID", "id": "id", "editable": False},
                            {"name": "Part ID", "id": "part_id", "editable": True},
                            {"name": "Part Name", "id": "part_name", "editable": True},
                            {"name": "Current Stock", "id": "current_stock", "editable": True, "type": "numeric"},
                            {"name": "Minimum Stock", "id": "minimum_stock", "editable": True, "type": "numeric"},
                            {"name": "Maximum Stock", "id": "maximum_stock", "editable": True, "type": "numeric"},
                            {"name": "Unit Cost", "id": "unit_cost", "editable": True, "type": "numeric"},
                            {"name": "Total Value", "id": "total_value", "editable": False, "type": "numeric"},
                            {"name": "Supplier ID", "id": "supplier_id", "editable": True},
                            {"name": "Supplier Name", "id": "supplier_name", "editable": True},
                            {"name": "Location", "id": "location", "editable": True},
                            {"name": "Notes", "id": "notes", "editable": True}
                        ],
                        editable=True,
                        row_deletable=True,
                        style_table={'overflowX': 'auto', 'display': 'none'},  # Hide empty table
                        style_cell={'textAlign': 'left', 'padding': '10px', 'minWidth': '120px'},
                        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
                    )
                ])
        except Exception as e:
            inventory_content = html.Div([
                html.Div(f"Error: {str(e)}", style={'color': 'red'}),
                dash_table.DataTable(
                    id='inventory-data-editable-table',
                    data=[],
                    columns=[
                        {"name": "ID", "id": "id", "editable": False},
                        {"name": "Part ID", "id": "part_id", "editable": True},
                        {"name": "Part Name", "id": "part_name", "editable": True},
                        {"name": "Current Stock", "id": "current_stock", "editable": True, "type": "numeric"},
                        {"name": "Minimum Stock", "id": "minimum_stock", "editable": True, "type": "numeric"},
                        {"name": "Maximum Stock", "id": "maximum_stock", "editable": True, "type": "numeric"},
                        {"name": "Unit Cost", "id": "unit_cost", "editable": True, "type": "numeric"},
                        {"name": "Total Value", "id": "total_value", "editable": False, "type": "numeric"},
                        {"name": "Supplier ID", "id": "supplier_id", "editable": True},
                        {"name": "Supplier Name", "id": "supplier_name", "editable": True},
                        {"name": "Location", "id": "location", "editable": True},
                        {"name": "Notes", "id": "notes", "editable": True}
                    ],
                    editable=True,
                    row_deletable=True,
                    style_table={'overflowX': 'auto', 'display': 'none'},  # Hide empty table
                    style_cell={'textAlign': 'left', 'padding': '10px', 'minWidth': '120px'},
                    style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
                )
            ])
    
    return bom_content, forecast_content, inventory_content

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
                    df['total_cost'] = df['total_cost'].apply(lambda x: f"${x:,.2f}")
                    
                    if view_type == "aggregated":
                        # Aggregated supplier view
                        # Remove the 'parts' field as it contains lists that DataTable can't handle
                        df_display = df.drop(columns=['parts'], errors='ignore')
                        
                        return dash_table.DataTable(
                            data=df_display.to_dict('records'),
                            columns=[
                                {"name": "Supplier", "id": "supplier_name"},
                                {"name": "Order Date", "id": "order_date"},
                                {"name": "Parts Count", "id": "total_parts"},
                                {"name": "Total Cost", "id": "total_cost"},
                                {"name": "Payment Date", "id": "payment_date"},
                                {"name": "Days to Order", "id": "days_until_order"},
                                {"name": "Days to Payment", "id": "days_until_payment"}
                            ],
                            style_table={'overflowX': 'auto'},
                            style_cell={'textAlign': 'left', 'padding': '10px'},
                            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
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
                            {"name": "Payment Date", "id": "payment_date"}
                        ])
                        
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
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("Aggregated Orders", className="card-title"),
                                html.H3(f"{aggregated_count:,}", className="text-success"),
                                html.P("Consolidated supplier orders", className="card-text")
                            ])
                        ], color="light", outline=True)
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("Order Reduction", className="card-title"),
                                html.H3(f"{reduction_pct:.1f}%", className="text-info"),
                                html.P("Fewer orders to manage", className="card-text")
                            ])
                        ], color="light", outline=True)
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("Total Value", className="card-title"),
                                html.H3(f"${detailed_total:,.0f}", className="text-warning"),
                                html.P("Same cost, simplified", className="card-text")
                            ])
                        ], color="light", outline=True)
                    ], width=3)
                ])
                
                return cards
                
        except Exception as e:
            return html.Div(f"Error loading summary: {str(e)}", style={'color': 'red'})
    
    return ""

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
                        {"name": "Beginning Inventory", "id": "beginning_inventory", "editable": True, "type": "numeric"},
                        {"name": "Supplier ID", "id": "supplier_id", "editable": True},
                        {"name": "Supplier Name", "id": "supplier_name", "editable": True},
                        {"name": "Manufacturer", "id": "manufacturer", "editable": True},
                        {"name": "AP Terms", "id": "ap_terms", "editable": True, "type": "numeric"},
                        {"name": "Manufacturing Lead Time", "id": "manufacturing_lead_time", "editable": True, "type": "numeric"},
                        {"name": "Shipping Lead Time", "id": "shipping_lead_time", "editable": True, "type": "numeric"}
                    ],
                    editable=True,
                    row_deletable=True,
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
                'supplier_id': row.get('supplier_id'),
                'supplier_name': row.get('supplier_name'),
                'manufacturer': row.get('manufacturer'),
                'ap_terms': int(row.get('ap_terms')) if row.get('ap_terms') else None,
                'manufacturing_lead_time': int(row.get('manufacturing_lead_time')) if row.get('manufacturing_lead_time') else None,
                'shipping_lead_time': int(row.get('shipping_lead_time')) if row.get('shipping_lead_time') else None
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
@app.callback(
    Output('inventory-data-table', 'children'),
    [Input('refresh-inventory-btn', 'n_clicks')],
    prevent_initial_call=True
)
def update_inventory_table(n_clicks):
    try:
        response = requests.get(f"{API_BASE}/inventory")
        if response.status_code == 200:
            inventory_data = response.json()
            if inventory_data:
                df = pd.DataFrame(inventory_data)
                
                # Convert datetime columns to strings for display
                if 'created_at' in df.columns:
                    df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
                if 'updated_at' in df.columns:
                    df['updated_at'] = pd.to_datetime(df['updated_at']).dt.strftime('%Y-%m-%d %H:%M')
                if 'last_restock_date' in df.columns:
                    df['last_restock_date'] = pd.to_datetime(df['last_restock_date']).dt.strftime('%Y-%m-%d %H:%M')
                
                return html.Div([
                    dash_table.DataTable(
                        id='inventory-data-editable-table',
                        data=df.to_dict('records'),
                        columns=[
                            {"name": "ID", "id": "id", "editable": False},
                            {"name": "Part ID", "id": "part_id", "editable": True},
                            {"name": "Part Name", "id": "part_name", "editable": True},
                            {"name": "Current Stock", "id": "current_stock", "editable": True, "type": "numeric"},
                            {"name": "Minimum Stock", "id": "minimum_stock", "editable": True, "type": "numeric"},
                            {"name": "Maximum Stock", "id": "maximum_stock", "editable": True, "type": "numeric"},
                            {"name": "Unit Cost", "id": "unit_cost", "editable": True, "type": "numeric"},
                            {"name": "Total Value", "id": "total_value", "editable": False, "type": "numeric"},
                            {"name": "Supplier ID", "id": "supplier_id", "editable": True},
                            {"name": "Supplier Name", "id": "supplier_name", "editable": True},
                            {"name": "Location", "id": "location", "editable": True},
                            {"name": "Notes", "id": "notes", "editable": True}
                        ],
                        editable=True,
                        row_deletable=True,
                        style_table={'overflowX': 'auto'},
                        style_cell={'textAlign': 'left', 'padding': '10px', 'minWidth': '120px'},
                        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                        style_data_conditional=[
                            {
                                'if': {'column_editable': True},
                                'backgroundColor': 'rgb(248, 248, 248)',
                            },
                            {
                                'if': {'filter_query': '{current_stock} < {minimum_stock}'},
                                'backgroundColor': '#ffcccc',
                                'color': 'black',
                            }
                        ]
                    )
                ])
            else:
                return html.Div([
                    html.Div("No inventory data found. Please upload inventory data first.", style={'color': 'gray'}),
                    dash_table.DataTable(
                        id='inventory-data-editable-table',
                        data=[],
                        columns=[
                            {"name": "ID", "id": "id", "editable": False},
                            {"name": "Part ID", "id": "part_id", "editable": True},
                            {"name": "Part Name", "id": "part_name", "editable": True},
                            {"name": "Current Stock", "id": "current_stock", "editable": True, "type": "numeric"},
                            {"name": "Minimum Stock", "id": "minimum_stock", "editable": True, "type": "numeric"},
                            {"name": "Maximum Stock", "id": "maximum_stock", "editable": True, "type": "numeric"},
                            {"name": "Unit Cost", "id": "unit_cost", "editable": True, "type": "numeric"},
                            {"name": "Total Value", "id": "total_value", "editable": False, "type": "numeric"},
                            {"name": "Supplier ID", "id": "supplier_id", "editable": True},
                            {"name": "Supplier Name", "id": "supplier_name", "editable": True},
                            {"name": "Location", "id": "location", "editable": True},
                            {"name": "Notes", "id": "notes", "editable": True}
                        ],
                        editable=True,
                        row_deletable=True,
                        style_table={'overflowX': 'auto', 'display': 'none'},  # Hide empty table
                        style_cell={'textAlign': 'left', 'padding': '10px', 'minWidth': '120px'},
                        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
                    )
                ])
        else:
            return html.Div([
                html.Div("Error loading inventory data", style={'color': 'red'}),
                dash_table.DataTable(
                    id='inventory-data-editable-table',
                    data=[],
                    columns=[
                        {"name": "ID", "id": "id", "editable": False},
                        {"name": "Part ID", "id": "part_id", "editable": True},
                        {"name": "Part Name", "id": "part_name", "editable": True},
                        {"name": "Current Stock", "id": "current_stock", "editable": True, "type": "numeric"},
                        {"name": "Minimum Stock", "id": "minimum_stock", "editable": True, "type": "numeric"},
                        {"name": "Maximum Stock", "id": "maximum_stock", "editable": True, "type": "numeric"},
                        {"name": "Unit Cost", "id": "unit_cost", "editable": True, "type": "numeric"},
                        {"name": "Total Value", "id": "total_value", "editable": False, "type": "numeric"},
                        {"name": "Supplier ID", "id": "supplier_id", "editable": True},
                        {"name": "Supplier Name", "id": "supplier_name", "editable": True},
                        {"name": "Location", "id": "location", "editable": True},
                        {"name": "Notes", "id": "notes", "editable": True}
                    ],
                    editable=True,
                    row_deletable=True,
                    style_table={'overflowX': 'auto', 'display': 'none'},  # Hide empty table
                    style_cell={'textAlign': 'left', 'padding': '10px', 'minWidth': '120px'},
                    style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
                )
            ])
    except Exception as e:
        return html.Div([
            html.Div(f"Error: {str(e)}", style={'color': 'red'}),
            dash_table.DataTable(
                id='inventory-data-editable-table',
                data=[],
                columns=[
                    {"name": "ID", "id": "id", "editable": False},
                    {"name": "Part ID", "id": "part_id", "editable": True},
                    {"name": "Part Name", "id": "part_name", "editable": True},
                    {"name": "Current Stock", "id": "current_stock", "editable": True, "type": "numeric"},
                    {"name": "Minimum Stock", "id": "minimum_stock", "editable": True, "type": "numeric"},
                    {"name": "Maximum Stock", "id": "maximum_stock", "editable": True, "type": "numeric"},
                    {"name": "Unit Cost", "id": "unit_cost", "editable": True, "type": "numeric"},
                    {"name": "Total Value", "id": "total_value", "editable": False, "type": "numeric"},
                    {"name": "Supplier ID", "id": "supplier_id", "editable": True},
                    {"name": "Supplier Name", "id": "supplier_name", "editable": True},
                    {"name": "Location", "id": "location", "editable": True},
                    {"name": "Notes", "id": "notes", "editable": True}
                ],
                editable=True,
                row_deletable=True,
                style_table={'overflowX': 'auto', 'display': 'none'},  # Hide empty table
                style_cell={'textAlign': 'left', 'padding': '10px', 'minWidth': '120px'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
            )
        ])

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

if __name__ == '__main__':
    app.run_server(debug=True, port=8050)