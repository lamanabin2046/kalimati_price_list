# =========================================================
# 🍅 Tomato Price Prediction - Automatic Feature Pruning Pipeline (Safe Version)
# =========================================================

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings("ignore")

# ✅ Use a headless (non-GUI) backend for Matplotlib to avoid Tkinter thread errors
import matplotlib
if os.environ.get("DISPLAY", "") == "":
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.feature_selection import RFE

# =========================================================
# 📘 1. Load Dataset
# =========================================================
def load_data(path="data/tomato_clean_data.csv"):
    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ File not found: {path}")
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    return df

# =========================================================
# 🕒 2. Add Lag & Rolling Features
# =========================================================
def add_lag_and_rolling_features(df, lag_features, lags=[1, 3, 7], rolls=[7, 30]):
    df = df.copy().sort_values("Date")
    for feature in lag_features:
        for lag in lags:
            df[f"{feature}_lag{lag}"] = df[feature].shift(lag)
        for roll in rolls:
            df[f"{feature}_rollmean_{roll}"] = df[feature].shift(1).rolling(window=roll).mean()
    df = df.dropna().reset_index(drop=True)
    return df

# =========================================================
# ⚙️ 3. Model Evaluation Helper
# =========================================================
def evaluate_model(model, X_train, X_test, y_train, y_test):
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    return mae, rmse, r2, y_pred

# =========================================================
# 🚀 4. Main Execution
# =========================================================
if __name__ == "__main__":
    print("📥 Loading dataset...")
    df = load_data()

    # Select lag and rolling features
    lag_features = [
        "Average_Price",
        "Supply_Volume",
        "Dhading_Rainfall_MM",
        "Kathmandu_Rainfall_MM",
        "Kavre_Rainfall_MM",
        "Sarlahi_Rainfall_MM"
    ]

    print("🕒 Adding lag and rolling features...")
    df = add_lag_and_rolling_features(df, lag_features)

    # Target and features
    target = "Average_Price"
    X = df.drop(columns=[target, "Date"], errors="ignore")
    y = df[target]

    # Chronological split (80/20)
    train_size = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:train_size], X.iloc[train_size:]
    y_train, y_test = y.iloc[:train_size], y.iloc[train_size:]

    # Define base model
    base_model = Pipeline([
        ("scaler", StandardScaler()),
        ("rf", RandomForestRegressor(
            n_estimators=300,
            max_depth=15,
            random_state=42,
            n_jobs=-1
        ))
    ])

    print("🚀 Training baseline model...")
    mae_base, rmse_base, r2_base, y_pred_base = evaluate_model(
        base_model, X_train, X_test, y_train, y_test
    )

    print(f"📊 Baseline → MAE={mae_base:.3f}, RMSE={rmse_base:.3f}, R²={r2_base:.3f}")

    # Feature importances
    rf_model = base_model.named_steps["rf"]
    rf_model.fit(X_train, y_train)
    importances = pd.Series(rf_model.feature_importances_, index=X_train.columns).sort_values(ascending=False)

    os.makedirs("results", exist_ok=True)
    plt.figure(figsize=(10, 6))
    importances.head(20).sort_values().plot(kind="barh", color="teal")
    plt.title("Top 20 Important Features (Baseline)")
    plt.xlabel("Importance")
    plt.tight_layout()
    plt.savefig("results/top_features_baseline.png")
    plt.close()

    print("\n🌟 Top 10 Important Features (Baseline):")
    print(importances.head(10))

    # =========================================================
    # 🔍 5. Recursive Feature Elimination (RFE)
    # =========================================================
    print("\n🔍 Performing Recursive Feature Elimination (RFE)...")
    estimator = RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=-1)
    rfe = RFE(estimator, n_features_to_select=20)
    rfe.fit(X_train, y_train)

    selected_features = X_train.columns[rfe.support_]
    print("✅ Selected top features by RFE:")
    print(selected_features.tolist())

    # Subset dataset
    X_train_rfe = X_train[selected_features]
    X_test_rfe = X_test[selected_features]

    # Retrain on selected features
    refined_model = Pipeline([
        ("scaler", StandardScaler()),
        ("rf", RandomForestRegressor(
            n_estimators=300,
            max_depth=15,
            random_state=42,
            n_jobs=-1
        ))
    ])

    print("\n🚀 Training refined model (with selected features)...")
    mae_new, rmse_new, r2_new, y_pred_new = evaluate_model(
        refined_model, X_train_rfe, X_test_rfe, y_train, y_test
    )

    print(f"📈 Refined → MAE={mae_new:.3f}, RMSE={rmse_new:.3f}, R²={r2_new:.3f}")

    # Compare performance
    improvement = (mae_base - mae_new) / mae_base * 100
    print(f"\n🎯 MAE Improvement after pruning: {improvement:.2f}%")

    # Save results
    results = pd.DataFrame({
        "Metric": ["MAE", "RMSE", "R²"],
        "Baseline": [mae_base, rmse_base, r2_base],
        "Refined": [mae_new, rmse_new, r2_new]
    })
    results.to_csv("results/model_comparison.csv", index=False)
    importances.to_csv("results/feature_importances_baseline.csv", index=True)
    pd.Series(selected_features).to_csv("results/selected_features_rfe.csv", index=False)

    preds_df = pd.DataFrame({
        "Date": df["Date"].iloc[train_size:].reset_index(drop=True),
        "Actual": y_test.reset_index(drop=True),
        "Predicted_Baseline": y_pred_base,
        "Predicted_Refined": y_pred_new
    })
    preds_df.to_csv("results/predictions_comparison.csv", index=False)

    print("\n💾 Results saved in 'results/' folder:")
    print("   • model_comparison.csv")
    print("   • feature_importances_baseline.csv")
    print("   • selected_features_rfe.csv")
    print("   • predictions_comparison.csv")
    print("   • top_features_baseline.png")

    print("\n✅ Feature pruning pipeline completed successfully!")


import joblib

# Save the refined (best) model for future predictions
model_path = "results/tomato_price_model.pkl"
joblib.dump(refined_model, model_path)

print(f"\n💾 Trained model saved successfully → {model_path}")