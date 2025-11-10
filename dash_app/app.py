import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from components.data_collection_preprocessing import data_collection_preprocessing_layout, register_data_collection_preprocessing_callbacks
from components.training_section import training_layout, register_training_callbacks
from components.reports_section import reports_layout, register_report_callbacks

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.SANDSTONE])
app.title = "🍅 Kalimati Tomato Forecasting Dashboard"
server = app.server  # Useful for deployment (e.g., Render, Heroku, etc.)

# App layout with combined upload and processing section
app.layout = dbc.Container([
    html.H2("🍅 Kalimati Tomato Price Forecasting Dashboard", className="text-center mt-3 mb-4"),

    dbc.Row([
        dbc.Col(data_collection_preprocessing_layout, width=6),  # Data Collection & Preprocessing
        dbc.Col(training_layout, width=4),  # Model Training
        dbc.Col(reports_layout, width=4)  # Placeholder for Reports
    ], justify="center"),

    html.Hr(),
    html.Footer("Developed by Kalimati ML Team", className="text-center text-muted mt-4 mb-2")
], fluid=True)

# Register callbacks for upload, data collection, and training actions
register_data_collection_preprocessing_callbacks(app)
register_training_callbacks(app)
register_report_callbacks(app)

# Run the server
if __name__ == "__main__":
    print("🌐 Running Dash app at http://127.0.0.1:8050/")
    app.run(debug=True, port=8050)
