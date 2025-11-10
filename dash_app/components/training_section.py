import dash
from dash import html, Output, Input, ctx, dcc
import dash_bootstrap_components as dbc
import subprocess
from datetime import datetime
import os

# Update the layout to include a loading spinner around the output area
training_layout = html.Div([
    html.H5("⚙️ Model Operations"),
    
    # Removed the "Run Full Pipeline" button
    dbc.Button("🔍 Run Hyperparameter Tuning", id="btn-tune", color="warning", className="mb-2 me-2"),
    dbc.Button("🏋️ Train Models", id="btn-train", color="primary", className="mb-2"),
    
    # Wrapping the output area with dcc.Loading for loading indicator
    dcc.Loading(
        id="loading",
        type="circle",  # You can choose between 'circle', 'dot', 'default', etc.
        children=html.Div(id="train-status", className="mt-3 text-info")
    )
])

def register_training_callbacks(app):
    @app.callback(
        Output("train-status", "children"),
        Input("btn-tune", "n_clicks"),
        Input("btn-train", "n_clicks"),
        prevent_initial_call=True
    )
    def run_operations(btn_tune, btn_train):
        triggered = ctx.triggered_id
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Removed full pipeline logic
        if triggered == "btn-tune":
            subprocess.run(["python", "src/modeling/hyperparameter_tuning.py"])
            return f"✅ Hyperparameter tuning completed at {timestamp}"

        elif triggered == "btn-train":
            subprocess.run(["python", "src/modeling/model_pipeline.py"])
            return f"✅ Model training completed at {timestamp}"
