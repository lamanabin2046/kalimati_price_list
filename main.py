"""
main.py
--------
Central entry point for the Kalimati Tomato Price Forecasting project.

You can:
- Run the entire data + model pipeline
- Or launch the interactive Dash dashboard
"""

import os
import argparse
import subprocess
import sys

def run_pipeline():
    """Runs the complete ETL → Feature Engineering → Model Training pipeline."""
    print("🚀 Starting full data + model pipeline...\n")

    python_exec = sys.executable  # ✅ Use current Python interpreter (venv)
    subprocess.run([python_exec, "src/preprocessing/build_dataset.py"], check=True)
    subprocess.run([python_exec, "src/preprocessing/feature_engineering.py"], check=True)
    subprocess.run([python_exec, "src/modeling/model_pipeline.py"], check=True)

    print("\n✅ Full pipeline completed successfully!")


def run_dashboard():
    """Launches the Dash web application."""
    print("🌐 Launching Dash app at http://127.0.0.1:8050/")

    python_exec = sys.executable  # ✅ Use same Python environment
    subprocess.run([python_exec, "dash_app/app.py"], check=True)


def main():
    parser = argparse.ArgumentParser(description="Kalimati Tomato Price Forecasting Main Controller")
    parser.add_argument("--mode", choices=["pipeline", "dashboard"], required=True,
                        help="Choose to run the data pipeline or the Dash dashboard")

    args = parser.parse_args()

    if args.mode == "pipeline":
        run_pipeline()
    elif args.mode == "dashboard":
        run_dashboard()
    else:
        print("❌ Invalid mode. Use --mode pipeline or --mode dashboard")


if __name__ == "__main__":
    main()
