# =========================================================
# 🍅 Tomato Price Prediction - Time Series ML Pipeline with Hyperparameter Tuning
# =========================================================

import pandas as pd
import numpy as np
import os
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

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
# 🕒 2. Add Lag and Rolling Features
# =========================================================
def add_lag_and_rolling_features(df, lag_features, lags=[1, 3, 7], rolls=[7, 30]):
    df = df.copy()
    df = df.sort_values("Date")
    for feature in lag_features:
        for lag in lags:
            df[f"{feature}_lag{lag}"] = df[feature].shift(lag)
        for roll in rolls:
            df[f"{feature}_rollmean_{roll}"] = df[feature].shift(1).rolling(window=roll).mean()
    df = df.dropna().reset_index(drop=True)
    return df

# =========================================================
# ⚙️ 3. Define and Tune Model
# =========================================================
def tune_model(X_train, y_train):
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", RandomForestRegressor(random_state=42))
    ])

    param_grid = {
        "model__n_estimators": [100, 200],
        "model__max_depth": [10, 20, None],
        "model__min_samples_split": [2, 5, 10],
        "model__min_samples_leaf": [1, 2, 4]
    }

    tscv = TimeSeriesSplit(n_splits=5)

    grid_search = GridSearchCV(
        estimator=pipeline,
        param_grid=param_grid,
        cv=tscv,
        scoring="neg_mean_absolute_error",
        n_jobs=-1,
        verbose=2
    )

    print("🔍 Starting hyperparameter tuning...")
    grid_search.fit(X_train, y_train)

    print(f"✅ Best Parameters: {grid_search.best_params_}")
    print(f"🏆 Best CV MAE: {-grid_search.best_score_:.3f}")

    return grid_search.best_estimator_

# =========================================================
# 🧩 4. Main Execution
# =========================================================
if __name__ == "__main__":
    print("📥 Loading dataset...")
    df = load_data()

    # 🎯 Define which features to create lag/rolling for
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

    # Define target and features
    target = "Average_Price"
    X = df.drop(columns=[target, "Date"])
    y = df[target]

    # Chronological split (80% train, 20% test)
    train_size = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:train_size], X.iloc[train_size:]
    y_train, y_test = y.iloc[:train_size], y.iloc[train_size:]

    print(f"📊 Training samples: {len(X_train)}, Testing samples: {len(X_test)}")

    # Tune model with time-series aware CV
    best_model = tune_model(X_train, y_train)

    # Evaluate on test set
    print("🧪 Evaluating best model on test data...")
    y_pred = best_model.predict(X_test)

    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print(f"📈 Test MAE: {mae:.3f}")
    print(f"📊 Test R²: {r2:.3f}")

    # Save predictions
    results = pd.DataFrame({
        "Date": df["Date"].iloc[train_size:].reset_index(drop=True),
        "Actual": y_test.reset_index(drop=True),
        "Predicted": y_pred
    })
    os.makedirs("results", exist_ok=True)
    results.to_csv("results/predictions.csv", index=False)
    print("✅ Saved predictions → results/predictions.csv")
