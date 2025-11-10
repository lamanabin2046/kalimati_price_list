import dash
from dash import html, dcc, Output, Input, State, dash_table
from dash import ctx  # <-- Add this line to import ctx
import dash_bootstrap_components as dbc
import subprocess
from datetime import datetime
import os
import base64
import pandas as pd

UPLOAD_FOLDER = "data/raw"

# Layout for combined Data Collection, Upload, and Preprocessing Section
data_collection_preprocessing_layout = html.Div([
    html.H5("📤 Upload and Data Collection & Preprocessing"),

    # File Uploads for Fuel, Inflation, and Exchange Rate Data
    dcc.Upload(id="upload-fuel", children=html.Div(["📈 Upload Fuel CSV"]), className="upload-box", multiple=False),
    dcc.Upload(id="upload-inflation", children=html.Div(["💰 Upload Inflation XLSX"]), className="upload-box", multiple=False),
    dcc.Upload(id="upload-exchange", children=html.Div(["💱 Upload Exchange CSV"]), className="upload-box", multiple=False),

    # Buttons for Data Collection and Preprocessing
    dbc.Button("📥 Collect Data (Scraping)", id="btn-scrape-data", color="info", className="mb-2 me-2"),
    dbc.Button("🧑‍💻 Preprocess Data", id="btn-preprocess-data", color="success", className="mb-2 me-2"),

    # Status messages
    html.Div(id="data-collection-status", className="mt-3 text-info"),
    html.Div(id="upload-status", className="mt-2 text-success"),

    # Display the last 5 rows of the latest data
    html.H6("🔍 Displaying last 5 rows of the latest data:"),
    dash_table.DataTable(id="data-display-table", style_table={'height': '300px', 'overflowY': 'auto'})
])

def register_data_collection_preprocessing_callbacks(app):
    @app.callback(
        [Output("data-collection-status", "children"),
         Output("upload-status", "children"),
         Output("data-display-table", "data")],
        [Input("upload-fuel", "contents"),
         Input("upload-inflation", "contents"),
         Input("upload-exchange", "contents"),
         Input("btn-scrape-data", "n_clicks"),
         Input("btn-preprocess-data", "n_clicks")],
        [State("upload-fuel", "filename"),
         State("upload-inflation", "filename"),
         State("upload-exchange", "filename")],
        prevent_initial_call=True
    )
    def upload_and_process(fuel_content, inflation_content, exchange_content, btn_scrape_data, btn_preprocess_data, fuel_name, inf_name, exch_name):
        triggered = ctx.triggered_id  # Now ctx is properly imported
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        uploaded = []
        df_display = []  # Placeholder for the data to display

        # Handle file uploads
        if triggered in ["upload-fuel", "upload-inflation", "upload-exchange"]:
            for content, name in zip([fuel_content, inflation_content, exchange_content], [fuel_name, inf_name, exch_name]):
                if content:
                    content_type, content_string = content.split(",")
                    decoded = base64.b64decode(content_string)
                    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                    save_path = os.path.join(UPLOAD_FOLDER, name)
                    with open(save_path, "wb") as f:
                        f.write(decoded)
                    uploaded.append(name)

            upload_status = f"✅ Updated files: {', '.join(uploaded)}"
            return dash.no_update, upload_status, dash.no_update

        # Handle data collection (scraping)
        elif triggered == "btn-scrape-data":
            try:
                subprocess.run(["python", "src/scrapers/scraper_arrival.py"], check=True)
                subprocess.run(["python", "src/scrapers/scraper_price.py"], check=True)
                subprocess.run(["python", "src/scrapers/weather.py"], check=True)

                # Check if the raw data files exist and load them
                data_files = {
                    "supply_volume.csv": 'data/raw/supply_volume.csv',
                    "veg_price_list.csv": 'data/raw/veg_price_list.csv',
                    "weather.csv": 'data/raw/weather.csv'
                }

                # Collect the first 4 columns and the last 5 rows of each dataset
                for file_name, file_path in data_files.items():
                    if os.path.exists(file_path):
                        df = pd.read_csv(file_path).iloc[:, :4].tail(5)  # Select first 4 columns and last 5 rows
                        df_display.extend(df.to_dict('records'))  # Flatten the data into a single list

                # Return the data display and success message
                return f"✅ Data collection (scraping) completed successfully at {timestamp}", dash.no_update, df_display

            except subprocess.CalledProcessError as e:
                return f"❌ Error during data scraping: {e}", dash.no_update, dash.no_update

        # Handle preprocessing step
        elif triggered == "btn-preprocess-data":
            try:
                subprocess.run(["python", "src/preprocessing/build_dataset.py"], check=True)
                subprocess.run(["python", "src/preprocessing/feature_engineering.py"], check=True)

                # Load the processed dataset (for displaying)
                df_display = pd.read_csv('data/processed/tomato_clean_data.csv').iloc[:, :4].tail(5).to_dict('records')  # Adjust path as needed
                return dash.no_update, dash.no_update, df_display

            except subprocess.CalledProcessError as e:
                return f"❌ Error during data preprocessing: {e}", dash.no_update, dash.no_update

        return dash.no_update, dash.no_update, dash.no_update
