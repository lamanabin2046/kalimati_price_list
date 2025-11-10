import os
import pandas as pd
import numpy as np
import joblib
from datetime import date
from sklearn.model_selection import TimeSeriesSplit
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.pipeline import Pipeline

# Optional (ensure xgboost installed)
try:
    from xgboost import XGBRegressor
except ImportError:
    XGBRegressor = None

# Base directory path
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))

# =========================================================
# 📘 1. Load Dataset with Absolute Path Fix
# =========================================================
def load_data(path="data/processed/tomato_clean_data_lag_roll.csv"):
    """Load processed dataset with lag and rolling features."""
    # Get absolute path of the file
    full_path = os.path.join(base_dir, path)

    if not os.path.exists(full_path):
        raise FileNotFoundError(f"❌ File not found: {full_path}")
    
    df = pd.read_csv(full_path, encoding="utf-8-sig")
    
    # Ensure that 'Date' column is datetime type
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    
    # Drop rows where 'Date' could not be converted to datetime
    df = df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    
    # Drop the 'Fiscal_Year' column if it exists (we no longer need it)
    if 'Fiscal_Year' in df.columns:
        df = df.drop(columns=['Fiscal_Year'])
        print("❌ Dropped 'Fiscal_Year' column.")

    # Identify categorical columns
    categorical_columns = df.select_dtypes(include=['object']).columns.tolist()
    
    # Handle categorical columns
    for col in categorical_columns:
        print(f"Processing column: {col}")
        if df[col].nunique() < 10:  # Label Encoding for fewer unique values
            encoder = LabelEncoder()
            df[col] = encoder.fit_transform(df[col])
        else:  # One-Hot Encoding for more unique values
            df = pd.get_dummies(df, columns=[col], drop_first=True)
    
    # Check if there are still any string columns left and convert them to numeric
    for col in df.columns:
        if df[col].dtype == 'object':  # If the column is still a string, we attempt conversion
            print(f"Converting column {col} to numeric.")
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Drop rows with NaN values that might have resulted from conversion
    df = df.dropna()

    print(f"✅ Loaded dataset → {full_path}")
    print(f"📈 Total Rows: {len(df)}, Columns: {len(df.columns)}")
    return df


# =========================================================
# ⚙️ 2. Train + Evaluate a Single Model
# =========================================================
def train_and_evaluate_model(model_name, model, X_train, X_test, y_train, y_test):
    """Train a single model and return its performance metrics."""
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", model)
    ])
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    print(f"✅ {model_name}: MAE={mae:.3f}, R²={r2:.3f}")
    return pipeline, mae, r2, y_pred


# =========================================================
# 🧩 3. Master Training Function
# =========================================================
def train_all_models(df, target="Average_Price"):
    """Train multiple models and log performance."""
    if target not in df.columns:
        raise ValueError(f"❌ Target column '{target}' not found in dataset.")

    X = df.drop(columns=[target, "Date"], errors="ignore")
    y = df[target]

    # Chronological split (80/20)
    train_size = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:train_size], X.iloc[train_size:]
    y_train, y_test = y.iloc[:train_size], y.iloc[train_size:]

    print(f"📊 Training samples: {len(X_train)}, Testing samples: {len(X_test)}")

    today = date.today().isoformat()
    os.makedirs("outputs/models", exist_ok=True)
    os.makedirs("outputs/results", exist_ok=True)

    # Define candidate models
    models = {
        "random_forest": RandomForestRegressor(
            n_estimators=200, max_depth=20, random_state=42, n_jobs=-1
        ),
        "gradient_boost": GradientBoostingRegressor(
            n_estimators=200, learning_rate=0.1, max_depth=5, random_state=42
        )
    }

    if XGBRegressor:
        models["xgboost"] = XGBRegressor(
            n_estimators=300, learning_rate=0.05, max_depth=8, random_state=42, n_jobs=-1
        )

    results = []

    for name, model in models.items():
        print(f"\n🚀 Training {name} model...")
        trained_model, mae, r2, y_pred = train_and_evaluate_model(name, model, X_train, X_test, y_train, y_test)

        # Save model
        model_path = f"outputs/models/{name}_{today}.joblib"
        joblib.dump(trained_model, model_path)

        # Save predictions
        pred_path = f"outputs/results/predictions_{name}_{today}.csv"
        pd.DataFrame({
            "Date": df["Date"].iloc[-len(y_test):].reset_index(drop=True),
            "Actual": y_test.reset_index(drop=True),
            "Predicted": y_pred
        }).to_csv(pred_path, index=False)

        results.append({
            "Date": today,
            "Model": name,
            "MAE": round(mae, 3),
            "R2": round(r2, 3),
            "Model_Path": model_path,
            "Predictions_Path": pred_path
        })

        print(f"💾 Saved {name} model → {model_path}")

    # Update registry
    registry_path = "outputs/results/model_registry.csv"
    registry_df = pd.DataFrame(results)

    if os.path.exists(registry_path):
        old = pd.read_csv(registry_path)
        registry_df = pd.concat([old, registry_df], ignore_index=True)

    registry_df.to_csv(registry_path, index=False)
    print(f"\n📘 Updated model registry → {registry_path}")

    print("\n🏁 Training complete for all models!")
    return registry_df


# =========================================================
# 🚀 4. Main Execution
# =========================================================
if __name__ == "__main__":
    print("📥 Loading feature-engineered dataset...")
    df = load_data()

    print("⚙️ Training Random Forest, XGBoost, and Gradient Boost models...")
    registry_df = train_all_models(df)

    print("\n✅ All models trained and logged successfully!")
    print(registry_df.tail())
