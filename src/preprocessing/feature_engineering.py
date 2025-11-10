"""
feature_engineering.py
----------------------
Adds lag and rolling window features to the processed Kalimati tomato dataset.
"""

import os
import pandas as pd


# ============================================================
# 📥 Load Processed Dataset
# ============================================================
def load_data(path="data/processed/tomato_clean_data.csv"):
    """Load the processed dataset created by build_dataset.py."""
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    return df


# ============================================================
# 🕒 Add Lag and Rolling Features
# ============================================================
def add_lag_and_rolling_features(df, columns, lags, windows):
    """Add lag and rolling window features for given columns."""
    for col in columns:
        if col not in df.columns:
            print(f"⚠️ Warning: Column '{col}' not found in dataset. Skipping.")
            continue
        for lag in lags:
            df[f"{col}_lag{lag}"] = df[col].shift(lag)
        for window in windows:
            df[f"{col}_roll{window}"] = df[col].rolling(window).mean()
    return df


# ============================================================
# ⚙️ Temporal Feature Configuration
# ============================================================
TEMPORAL_FEATURES = {
    "Average_Price": {"lags": [1, 3, 7], "rolls": [7, 30]},
    "Supply_Volume": {"lags": [1, 3, 7], "rolls": [7, 30]},
    "Dhading_Rainfall_MM": {"lags": [1, 3, 7, 14], "rolls": [7, 14, 30]},
    "Kathmandu_Rainfall_MM": {"lags": [1, 3, 7, 14], "rolls": [7, 14, 30]},
    "Kavre_Rainfall_MM": {"lags": [1, 3, 7, 14], "rolls": [7, 14, 30]},
    "Sarlahi_Rainfall_MM": {"lags": [1, 3, 7, 14], "rolls": [7, 14, 30]},
}


# ============================================================
# 🧮 Generate Temporal Features
# ============================================================
def generate_temporal_features(df, temporal_config):
    """Generate lag and rolling features for all configured columns."""
    for feat, params in temporal_config.items():
        df = add_lag_and_rolling_features(df, [feat], params["lags"], params["rolls"])
    df = df.dropna().reset_index(drop=True)
    return df


# ============================================================
# 🚀 Main Runner
# ============================================================
if __name__ == "__main__":
    print("📥 Loading processed dataset...")
    df = load_data("data/processed/tomato_clean_data.csv")

    print("🧩 Generating temporal (lag + rolling) features...")
    df_features = generate_temporal_features(df, TEMPORAL_FEATURES)

    os.makedirs("data/processed", exist_ok=True)
    output_path = "data/processed/tomato_clean_data_lag_roll.csv"
    df_features.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"✅ Feature-engineered dataset saved → {output_path}")
    print(f"📈 Total Rows: {len(df_features)}, Columns: {len(df_features.columns)}")
