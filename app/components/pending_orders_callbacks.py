from dash import html, dcc, dash_table, Input, Output, State
import pandas as pd
import requests


def register_callbacks(app, api_base: str):
    @app.callback(
        Output('pending-orders-view-container', 'children', allow_duplicate=True),
        Input('pending-order-view-toggle', 'value'),
        State('pending-orders-raw-store', 'data'),
        prevent_initial_call=True,
    )
    def switch_pending_orders_view(view_type, raw_data):
        try:
            df_raw = pd.DataFrame(raw_data) if raw_data else pd.DataFrame()
            if view_type == 'aggregated' and not df_raw.empty:
                df_raw['order_date_dt'] = pd.to_datetime(df_raw['order_date'], errors='coerce')
                grp = df_raw.groupby(['supplier_id','supplier_name', df_raw['order_date_dt'].dt.date], dropna=False)
                agg = grp.agg(
                    total_parts=('id','count'),
                    total_cost=('id', lambda s: float((df_raw.loc[s.index, 'qty'].fillna(0).astype(float) * df_raw.loc[s.index, 'unit_cost'].fillna(0).astype(float)).sum())),
                    latest_eta=('estimated_delivery_date', lambda s: pd.to_datetime(s, errors='coerce').max()),
                    latest_payment=('payment_date', lambda s: pd.to_datetime(s, errors='coerce').max())
                ).reset_index()
                agg = agg.rename(columns={'order_date_dt':'order_date'})
                agg['order_date'] = pd.to_datetime(agg['order_date']).dt.strftime('%Y-%m-%d')
                agg['eta_date'] = pd.to_datetime(agg['latest_eta']).dt.strftime('%Y-%m-%d').fillna('')
                agg['payment_date'] = pd.to_datetime(agg['latest_payment']).dt.strftime('%Y-%m-%d').fillna('')
                agg['total_cost'] = agg['total_cost'].apply(lambda x: f"${x:,.2f}")

                base_api = f"{api_base}/calendar/export/pending-orders-by-supplier"
                def build_link(row):
                    sid = row.get('supplier_id')
                    sname = row.get('supplier_name')
                    od = row.get('order_date')
                    params = []
                    if sid:
                        params.append(f"supplier_id={sid}")
                    elif sname:
                        params.append(f"supplier_name={requests.utils.quote(str(sname))}")
                    if od:
                        params.append(f"order_date={od}T00:00:00")
                    params.append("as_html=true")
                    return f"[Export to Calendar]({base_api}?{'&'.join(params)})"
                agg['export'] = agg.apply(build_link, axis=1)

                aggregated_table = dash_table.DataTable(
                    id='pending-orders-aggregated-table',
                    data=agg.to_dict('records'),
                    columns=[
                        {"name": "Supplier", "id": "supplier_name"},
                        {"name": "Order Date", "id": "order_date"},
                        {"name": "ETA", "id": "eta_date"},
                        {"name": "Parts Count", "id": "total_parts"},
                        {"name": "Total Cost", "id": "total_cost"},
                        {"name": "Payment Date", "id": "payment_date"},
                        {"name": "Action", "id": "export", "presentation": "markdown"}
                    ],
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left', 'padding': '10px'},
                    style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                    markdown_options={"link_target": "_blank"}
                )
                return [aggregated_table]
            else:
                # Fallback: individual view
                df_ind = df_raw.copy()
                for col in ['order_date','estimated_delivery_date','payment_date','created_at','updated_at']:
                    if col in df_ind.columns:
                        s = pd.to_datetime(df_ind[col], errors='coerce', format='ISO8601')
                        df_ind[col] = s.dt.strftime('%Y-%m-%d').where(s.notna(), '')

                return [dash_table.DataTable(
                    id='pending-orders-editable-table',
                    data=df_ind.to_dict('records'),
                    columns=[
                        {"name": "ID", "id": "id", "editable": False},
                        {"name": "Part ID", "id": "part_id", "editable": True},
                        {"name": "Mapped Part", "id": "mapped_part_id", "editable": False},
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
                        }
                    },
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left', 'padding': '10px', 'minWidth': '120px'},
                    style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}
                )]
        except Exception as e:
            return [html.Div(f"Error switching view: {str(e)}", style={'color': 'red'})]

