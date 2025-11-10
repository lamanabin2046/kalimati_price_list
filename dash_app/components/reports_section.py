from dash import html, dcc, Output, Input
import dash_bootstrap_components as dbc
import pandas as pd
import os

# =========================================================
# 📊 Layout for Reports Section
# =========================================================
reports_layout = dbc.Card([
    dbc.CardHeader("📈 Model Reports"),
    dbc.CardBody([
        html.P("Select a trained model to view its performance metrics."),
        dcc.Dropdown(id="model-dropdown", placeholder="Select a model"),
        html.Div(id="model-metrics", className="mt-3"),
        html.Hr(),
        dcc.Graph(id="performance-chart")
    ])
], className="shadow-sm p-2")


# =========================================================
# 🔗 Callbacks
# =========================================================
def register_report_callbacks(app):

    @app.callback(
        Output("model-dropdown", "options"),
        Output("model-dropdown", "value"),
        Input("model-dropdown", "id")
    )
    def load_model_list(_):
        """Load available models from registry CSV."""
        registry_path = "outputs/results/model_registry.csv"
        if not os.path.exists(registry_path):
            return [], None
        df = pd.read_csv(registry_path)
        models = df["Model"].unique().tolist()
        return [{"label": m, "value": m} for m in models], (models[-1] if models else None)

    @app.callback(
        Output("model-metrics", "children"),
        Output("performance-chart", "figure"),
        Input("model-dropdown", "value")
    )
    def update_report(selected_model):
        """Display model metrics + simple chart."""
        import plotly.express as px
        registry_path = "outputs/results/model_registry.csv"

        if not os.path.exists(registry_path) or not selected_model:
            return html.P("No models found or selected."), {}

        df = pd.read_csv(registry_path)
        df_model = df[df["Model"] == selected_model]

        metrics = html.Ul([
            html.Li(f"Latest MAE: {df_model['MAE'].iloc[-1]}"),
            html.Li(f"Latest R²: {df_model['R2'].iloc[-1]}")
        ])

        fig = px.bar(df_model, x="Date", y="MAE", color="Model", title="Model MAE Over Time")

        return metrics, fig
