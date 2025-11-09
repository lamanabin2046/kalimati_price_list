# =========================================================
# 🍅 Tomato Temporal Impact Analysis with Feature Importance
# =========================================================

import pandas as pd
import numpy as np
import os
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import matplotlib.pyplot as plt
from model_pipeline import load_data, add_lag_and_rolling_features

# =========================================================
# ⚙️ Temporal Configurations
# =========================================================
TEMPORAL_FEATURES = {
    "Average_Price": {"lags": [1, 3, 7], "rolls": [7, 30]},
    "Supply_Volume": {"lags": [1, 3, 7], "rolls": [7, 30]},
    "Dhading_Rainfall_MM": {"lags": [1, 3, 7, 14], "rolls": [7, 14, 30]},
    "Kathmandu_Rainfall_MM": {"lags": [1, 3, 7, 14], "rolls": [7, 14, 30]},
    "Kavre_Rainfall_MM": {"lags": [1, 3, 7, 14], "rolls": [7, 14, 30]},
    "Sarlahi_Rainfall_MM": {"lags": [1, 3, 7, 14], "rolls": [7, 14, 30]}
}

# =========================================================
# 📘 Load & Feature Engineering
# =========================================================
def generate_temporal_features(df, temporal_config):
    for feat, params in temporal_config.items():
        df = add_lag_and_rolling_features(df, [feat], params["lags"], params["rolls"])
    df = df.dropna().reset_index(drop=True)
    return df

# =========================================================
# 🧮 Evaluate Model
# =========================================================
def evaluate_model(df):
    # Target and features
    y = df["Average_Price"]
    X = df.drop(columns=["Average_Price", "Date", "commodity"], errors="ignore")

    # Split chronologically (80/20)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    num_cols = X.select_dtypes(include=["float64", "int64"]).columns.tolist()
    preprocessor = ColumnTransformer([
        ("num", StandardScaler(), num_cols)
    ], remainder="passthrough")

    pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("model", RandomForestRegressor(
            n_estimators=300,
            max_depth=15,
            random_state=42,
            n_jobs=-1
        ))
    ])

    print("🚀 Training model...")
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    # Metrics
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    print(f"📊 Results → MAE={mae:.3f}, RMSE={rmse:.3f}, R²={r2:.3f}")

    return pipeline, X_train.columns, mae, rmse, r2

# =========================================================
# 🚀 Main Runner
# =========================================================
if __name__ == "__main__":
    print("📥 Loading dataset...")
    df = load_data("data/tomato_clean_data.csv")

    print("🕒 Adding temporal (lag + rolling) features...")
    df_feat = generate_temporal_features(df, TEMPORAL_FEATURES)

    model, feature_names, mae, rmse, r2 = evaluate_model(df_feat)

    # Feature importance
    model_rf = model.named_steps["model"]
    importances = pd.Series(model_rf.feature_importances_, index=feature_names)
    top_features = importances.sort_values(ascending=False).head(20)

    print("\n🌟 Top 20 Most Important Temporal Features:")
    print(top_features)

    # Visualization
    os.makedirs("results", exist_ok=True)
    plt.figure(figsize=(10, 6))
    top_features.sort_values().plot(kind="barh", color="teal")
    plt.title("Top 20 Important Temporal Features Affecting Tomato Price")
    plt.xlabel("Importance Score")
    plt.tight_layout()
    plt.savefig("results/top_temporal_features.png")
    plt.show()

    top_features.to_csv("results/top_temporal_features.csv", index=True)
    print("💾 Saved top 20 feature importances → results/top_temporal_features.csv")

    print(f"\n✅ Model Performance Summary:")
    print(f"   MAE = {mae:.2f}")
    print(f"   RMSE = {rmse:.2f}")
    print(f"   R² = {r2:.2f}")
