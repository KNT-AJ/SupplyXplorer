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
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], assets_folder='../assets')
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
                            date=datetime(2024, 1, 1).date(),
                            display_format='YYYY-MM-DD'
                        )
                    ], width=6),
                    dbc.Col([
                        html.Label("End Date:"),
                        dcc.DatePickerSingle(
                            id='end-date',
                            date=datetime(2024, 6, 30).date(),
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
                    html.Div(id="order-schedule-display")
                ])
            ], className="mb-4"),
            
            # Cash Flow Chart
            dbc.Row([
                dbc.Col([
                    html.H4("Cash Flow Projection", className="mb-3"),
                    dcc.Graph(id="cash-flow-chart")
                ])
            ])
        ], label="Dashboard", tab_id="dashboard")
    ], id="tabs", active_tab="data-planning")
], fluid=True)

# Callbacks
@app.callback(
    Output('backend-status', 'children'),
    Input('upload-forecast', 'contents'),
    Input('upload-bom', 'contents'),
    Input('run-planning-btn', 'n_clicks'),
    prevent_initial_call=False
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
    Output('planning-status', 'children'),
    Input('run-planning-btn', 'n_clicks'),
    State('start-date', 'date'),
    State('end-date', 'date'),
    prevent_initial_call=True
)
def run_planning(n_clicks, start_date, end_date):
    if n_clicks:
        try:
            # Convert date strings to datetime
            start_dt = datetime.fromisoformat(start_date) if start_date else datetime(2024, 1, 1)
            end_dt = datetime.fromisoformat(end_date) if end_date else datetime(2024, 6, 30)
            
            # Call planning API
            response = requests.post(f"{API_BASE}/plan/run", params={
                'start_date': start_dt.isoformat(),
                'end_date': end_dt.isoformat()
            })
            
            if response.status_code == 200:
                return html.Div([
                    html.H5("Planning Complete!", className="upload-success"),
                    html.P("Results available in Dashboard tab", className="upload-success")
                ])
            else:
                return html.Div([
                    html.H5("Planning Failed", className="upload-error"),
                    html.P("Check the console for details", className="upload-error")
                ])
        except Exception as e:
            return html.Div([
                html.H5("Planning Error", className="upload-error"),
                html.P(str(e), className="upload-error")
            ])
    return ""

@app.callback(
    Output('key-metrics-display', 'children'),
    Input('tabs', 'active_tab'),
    State('start-date', 'date'),
    State('end-date', 'date'),
    prevent_initial_call=True
)
def update_key_metrics(active_tab, start_date, end_date):
    if active_tab == "dashboard":
        try:
            # Convert date strings to datetime
            start_dt = datetime.fromisoformat(start_date) if start_date else datetime(2024, 1, 1)
            end_dt = datetime.fromisoformat(end_date) if end_date else datetime(2024, 6, 30)
            
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
    Input('tabs', 'active_tab'),
    State('start-date', 'date'),
    State('end-date', 'date'),
    prevent_initial_call=True
)
def update_order_schedule(active_tab, start_date, end_date):
    if active_tab == "dashboard":
        try:
            # Convert date strings to datetime
            start_dt = datetime.fromisoformat(start_date) if start_date else datetime(2024, 1, 1)
            end_dt = datetime.fromisoformat(end_date) if end_date else datetime(2024, 6, 30)
            
            # Get orders from API
            response = requests.get(f"{API_BASE}/orders", params={
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
                    
                    return dash_table.DataTable(
                        data=df.to_dict('records'),
                        columns=[
                            {"name": "Part ID", "id": "part_id"},
                            {"name": "Description", "id": "part_description"},
                            {"name": "Order Date", "id": "order_date"},
                            {"name": "Qty", "id": "qty"},
                            {"name": "Unit Cost", "id": "unit_cost"},
                            {"name": "Total Cost", "id": "total_cost"},
                            {"name": "Payment Date", "id": "payment_date"}
                        ],
                        style_table={'overflowX': 'auto'},
                        style_cell={'textAlign': 'left', 'padding': '10px'},
                        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
                    )
                else:
                    return html.Div("No orders found for the selected date range.", style={'color': 'gray'})
            else:
                return html.Div("Error loading orders", style={'color': 'red'})
        except Exception as e:
            return html.Div(f"Error: {str(e)}", style={'color': 'red'})
    return ""

@app.callback(
    Output('cash-flow-chart', 'figure'),
    Input('tabs', 'active_tab'),
    State('start-date', 'date'),
    State('end-date', 'date'),
    prevent_initial_call=True
)
def update_cash_flow_chart(active_tab, start_date, end_date):
    if active_tab == "dashboard":
        try:
            # Convert date strings to datetime
            start_dt = datetime.fromisoformat(start_date) if start_date else datetime(2024, 1, 1)
            end_dt = datetime.fromisoformat(end_date) if end_date else datetime(2024, 6, 30)
            
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
                    fig.add_trace(go.Scatter(
                        x=df['date'],
                        y=df['cash_out'],
                        mode='lines+markers',
                        name='Cash Out',
                        line=dict(color='var(--knt-danger)', width=3),
                        marker=dict(size=10, color='var(--knt-danger)')
                    ))
                    
                    fig.update_layout(
                        title="Cash Flow Projection",
                        xaxis_title="Date",
                        yaxis_title="Cash Out ($)",
                        hovermode='x unified',
                        plot_bgcolor='var(--knt-white)',
                        paper_bgcolor='var(--knt-white)',
                        font=dict(color='var(--knt-primary)', size=14),
                        title_font=dict(size=18, color='var(--knt-primary)'),
                        xaxis=dict(
                            gridcolor='var(--knt-gray-200)',
                            zerolinecolor='var(--knt-gray-300)'
                        ),
                        yaxis=dict(
                            gridcolor='var(--knt-gray-200)',
                            zerolinecolor='var(--knt-gray-300)'
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

if __name__ == '__main__':
    app.run_server(debug=True, port=8050) 