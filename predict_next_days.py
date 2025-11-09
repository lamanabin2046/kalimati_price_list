# =========================================================
# 🍅 Tomato Price Forecasting - Custom Date Range Prediction
# =========================================================

import pandas as pd
import numpy as np
import joblib
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# =========================================================
# 🧩 Load Data and Model
# =========================================================
def load_latest_data(path="data/tomato_clean_data.csv"):
    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ Dataset not found: {path}")
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)
    print(f"📊 Loaded {len(df)} daily records from {df['Date'].min().date()} → {df['Date'].max().date()}")
    return df

def load_model(model_path="results/tomato_price_model.pkl"):
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"❌ Model not found: {model_path}")
    print(f"✅ Loaded trained model → {model_path}")
    return joblib.load(model_path)

# =========================================================
# 🧮 Lag and Rolling Features
# =========================================================
def add_lag_and_rolling_features(df, lag_features, lags=[1,3,7], rolls=[7,30]):
    df = df.copy()
    for feature in lag_features:
        for lag in lags:
            df[f"{feature}_lag{lag}"] = df[feature].shift(lag)
        for roll in rolls:
            df[f"{feature}_rollmean_{roll}"] = df[feature].shift(1).rolling(window=roll).mean()
    return df

# =========================================================
# 🔮 Recursive Forecast Function
# =========================================================
def forecast_next_days(df, model, lag_features, start_date=None, end_date=None):
    df = df.copy()
    df = add_lag_and_rolling_features(df, lag_features)
    df = df.dropna().reset_index(drop=True)

    trained_features = list(model.feature_names_in_)
    last_known = df.iloc[-1:].copy()
    forecast_results = []

    # Determine forecast horizon
    last_date = last_known["Date"].iloc[-1]
    if start_date is None:
        start_date = last_date + timedelta(days=1)
    if end_date is None:
        end_date = start_date + timedelta(days=7)

    forecast_days = (end_date - start_date).days + 1
    print(f"📅 Forecasting from {start_date.date()} → {end_date.date()} ({forecast_days} days)")

    # Step through forecast range
    for i in range(forecast_days):
        next_date = last_known["Date"].iloc[-1] + timedelta(days=1)

        df_extended = pd.concat([df, last_known], ignore_index=True)
        df_extended = add_lag_and_rolling_features(df_extended, lag_features)
        new_row = df_extended.iloc[-1:].copy()

        X_pred = new_row.drop(columns=["Average_Price", "Date"], errors="ignore")

        # Align feature columns with training
        for col in trained_features:
            if col not in X_pred.columns:
                X_pred[col] = 0
        X_pred = X_pred[trained_features]

        pred_price = model.predict(X_pred)[0]

        new_row["Date"] = next_date
        new_row["Average_Price"] = pred_price
        forecast_results.append({"Date": next_date, "Predicted_Price": pred_price})

        last_known = pd.concat([last_known, new_row]).iloc[-1:]

    return pd.DataFrame(forecast_results)

# =========================================================
# 📊 Plot Forecast
# =========================================================
def plot_forecast(df, forecast_df, days_back=30, save_path="results/forecast_plot.png", title="Tomato Price Forecast"):
    plt.figure(figsize=(10, 5))
    plt.plot(df["Date"].tail(days_back), df["Average_Price"].tail(days_back), label="Past Prices", marker="o")
    plt.plot(forecast_df["Date"], forecast_df["Predicted_Price"], label="Forecast", marker="x", color="orange")
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Average Price (NPR)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    print(f"📊 Forecast plot saved → {save_path}")

# =========================================================
# 🚀 Run Custom Forecast
# =========================================================
if __name__ == "__main__":
    print("📥 Loading dataset and trained model...")
    df = load_latest_data()
    model = load_model()

    lag_features = [
        "Average_Price",
        "Supply_Volume",
        "Dhading_Rainfall_MM",
        "Kathmandu_Rainfall_MM",
        "Kavre_Rainfall_MM",
        "Sarlahi_Rainfall_MM"
    ]

    os.makedirs("results", exist_ok=True)

    # 🔧 Define desired forecast window manually
    start_date = datetime(2025, 11, 10)
    end_date = datetime(2025, 11, 17)

    print("\n🔮 Generating forecast for custom period...")
    forecast_df = forecast_next_days(df, model, lag_features, start_date=start_date, end_date=end_date)

    # Save outputs
    forecast_df.to_csv("results/custom_forecast_2025_11_10_to_17.csv", index=False)
    print("✅ Forecast saved → results/custom_forecast_2025_11_10_to_17.csv")
    print(forecast_df)

    # Plot forecast
    plot_forecast(
        df,
        forecast_df,
        days_back=60,
        save_path="results/custom_forecast_plot_2025_11_10_to_17.png",
        title="Custom Tomato Price Forecast (2025-11-10 → 2025-11-17)"
    )

    print("\n🎯 Forecasting completed successfully!")
