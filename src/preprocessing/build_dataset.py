import os
import pandas as pd
import numpy as np

# Set the directory path directly
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
DATA_RAW = os.path.join(BASE_DIR, "data", "raw")
DATA_PROCESSED = os.path.join(BASE_DIR, "data", "processed")

# Print paths for debugging
print("BASE_DIR:", BASE_DIR)
print("DATA_RAW:", DATA_RAW)
print("DATA_PROCESSED:", DATA_PROCESSED)

# Import the required utility functions
try:
    from utils import clean_number, clean_commodity
except ImportError:
    print("Error: 'utils' module not found. Ensure 'utils.py' is present in the correct location.")
    raise

# =========================================================
# 📘 Load & Clean Price Data
# =========================================================
def load_price_data():
    path = os.path.join(DATA_RAW, "veg_price_list.csv")
    print(f"Checking if price data exists at {path}: {os.path.exists(path)}")  # Debugging
    if not os.path.exists(path):
        print(f"Error: {path} not found.")
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = df[["Date", "कृषि उपज", "औसत"]].copy()
    df.rename(columns={"कृषि उपज": "commodity", "औसत": "Average_Price"}, inplace=True)
    df["commodity"] = df["commodity"].apply(clean_commodity)
    df["Average_Price"] = df["Average_Price"].apply(clean_number)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df[df["commodity"] == "Tomato_Big"].dropna(subset=["Date", "Average_Price"])
    df = df.groupby("Date", as_index=False)["Average_Price"].mean()
    return df.sort_values("Date")


# =========================================================
# 📗 Load & Clean Supply Data
# =========================================================
def load_supply_data():
    path = os.path.join(DATA_RAW, "supply_volume.csv")
    print(f"Checking if supply data exists at {path}: {os.path.exists(path)}")  # Debugging
    if not os.path.exists(path):
        print(f"Error: {path} not found.")
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = df[["Date", "कृषि उपज", "आगमन"]].copy()
    df.rename(columns={"कृषि उपज": "commodity", "आगमन": "Supply_Volume"}, inplace=True)
    df["commodity"] = df["commodity"].apply(clean_commodity)
    df["Supply_Volume"] = df["Supply_Volume"].apply(clean_number)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    tomato_df = df[df["commodity"].isin(["Tomato_Big", "Tomato_Small", "Tomato"])].copy()
    tomato_sum = tomato_df.groupby("Date")["Supply_Volume"].sum().reset_index()
    return tomato_sum.sort_values("Date")


# =========================================================
# 🌦️ Load Weather Data
# =========================================================
def load_weather_data():
    path = os.path.join(DATA_RAW, "weather.csv")
    print(f"Checking if weather data exists at {path}: {os.path.exists(path)}")  # Debugging
    if not os.path.exists(path):
        print(f"Error: {path} not found.")
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.rename(columns={"date": "Date"}, inplace=True)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    temp_cols = [c for c in df.columns if "temp" in c.lower()]
    rain_cols = [c for c in df.columns if "rain" in c.lower() or "precipitation" in c.lower()]

    for col in temp_cols:
        df[col] = df[col].fillna(df[col].median())
    for col in rain_cols:
        df[col] = df[col].fillna(0)

    return df.sort_values("Date")


# =========================================================
# ⛽ Load Fuel, Inflation, Exchange (manual update sources)
# =========================================================
def load_fuel_data():
    path = os.path.join(DATA_RAW, "fuel.csv")
    if not os.path.exists(path):
        return pd.DataFrame(columns=["Date", "Diesel"])
    df = pd.read_csv(path)
    df.rename(columns={df.columns[0]: "Date", df.columns[1]: "Diesel"}, inplace=True)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Diesel"] = pd.to_numeric(df["Diesel"], errors="coerce")
    df = df.dropna(subset=["Date"]).drop_duplicates("Date").sort_values("Date")
    return df


def load_inflation_data():
    path = os.path.join(DATA_RAW, "inflation.csv")
    print(f"Checking if inflation data exists at {path}: {os.path.exists(path)}")  # Debugging
    if not os.path.exists(path):
        return pd.DataFrame(columns=["Date", "Inflation"])
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).drop_duplicates("Date").sort_values("Date")
    return df[["Date", "Inflation"]]


def load_exchange_data():
    path = os.path.join(DATA_RAW, "exchange.csv")
    if not os.path.exists(path):
        return pd.DataFrame(columns=["Date", "USD_TO_NPR"])
    df = pd.read_csv(path)
    df.rename(columns={df.columns[0]: "Date", df.columns[1]: "USD_TO_NPR"}, inplace=True)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["USD_TO_NPR"] = pd.to_numeric(df["USD_TO_NPR"], errors="coerce")
    df = df.dropna(subset=["Date"]).drop_duplicates("Date").sort_values("Date")
    return df


# =========================================================
# 🔗 Merge All + Handle Missing External Data
# =========================================================
def merge_all(price_df, supply_df, weather_df, fuel_df, inflation_df, exchange_df):
    df = pd.merge(price_df, supply_df, on="Date", how="left")
    df = pd.merge(df, exchange_df, on="Date", how="left")
    df = pd.merge(df, fuel_df, on="Date", how="left")
    df = pd.merge(df, inflation_df, on="Date", how="left")
    df = pd.merge(df, weather_df, on="Date", how="left")

    # ⚙️ Forward-fill macroeconomic indicators to match latest available data
    macro_cols = ["USD_TO_NPR", "Diesel", "Inflation"]
    for col in macro_cols:
        if col in df.columns:
            df[col] = df[col].ffill()

    # 🚨 Optional: Warn if macro data is stale
    last_date = df["Date"].max()
    for name, macro_df, col in [
        ("Fuel", fuel_df, "Diesel"),
        ("Exchange", exchange_df, "USD_TO_NPR"),
        ("Inflation", inflation_df, "Inflation")
    ]:
        if not macro_df.empty:
            last_update = macro_df["Date"].max()
            days_diff = (last_date - last_update).days
            if days_diff > 3:
                print(f"⚠️ {name} data not updated for {days_diff} days — using forward-fill from {last_update.date()}.")

    return df.sort_values("Date").reset_index(drop=True)


# =========================================================
# 📅 Time, Season, and Festival Features
# =========================================================
def add_time_features(df):
    df["day"] = df["Date"].dt.day
    df["month"] = df["Date"].dt.month
    df["day_of_week"] = df["Date"].dt.weekday
    df["is_weekend"] = (df["day_of_week"] == 5).astype(int)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    return df


def add_seasons(df):
    df["Season_Winter"] = df["month"].isin([12, 1, 2]).astype(int)
    df["Season_Spring"] = df["month"].isin([3, 4, 5]).astype(int)
    df["Season_Monsoon"] = df["month"].isin([6, 7, 8, 9]).astype(int)
    df["Season_Autumn"] = df["month"].isin([10, 11]).astype(int)
    return df


def add_festival_and_fiscal(df):
    df["is_festival"] = 0
    for i, row in df.iterrows():
        m, d = row["month"], row["day"]
        if m == 3 and (1 <= d <= 20): df.at[i, "is_festival"] = 1
        elif m == 4 and (10 <= d <= 20): df.at[i, "is_festival"] = 1
        elif (m == 9 and d >= 25) or (m == 10 and d <= 15): df.at[i, "is_festival"] = 1
        elif m == 11 and (1 <= d <= 15): df.at[i, "is_festival"] = 1

    def get_fy(date):
        return f"FY_{date.year if date.month >= 7 else date.year - 1}_{str((date.year if date.month >= 7 else date.year - 1) + 1)[-2:]}"
    
    df["Fiscal_Year"] = df["Date"].apply(get_fy)
    return df


# =========================================================
# 🚀 Build Final Dataset
# =========================================================
def build_dataset():
    print("🧹 Building and merging Kalimati datasets...")

    price_df = load_price_data()
    supply_df = load_supply_data()
    weather_df = load_weather_data()
    fuel_df = load_fuel_data()
    inflation_df = load_inflation_data()
    exchange_df = load_exchange_data()

    final_df = merge_all(price_df, supply_df, weather_df, fuel_df, inflation_df, exchange_df)
    final_df = add_time_features(final_df)
    final_df = add_seasons(final_df)
    final_df = add_festival_and_fiscal(final_df)

    os.makedirs(DATA_PROCESSED, exist_ok=True)
    output_path = os.path.join(DATA_PROCESSED, "tomato_clean_data.csv")
    final_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"✅ Final dataset saved → {output_path}")
    print(f"📈 Total Rows: {len(final_df)}, Columns: {len(final_df.columns)}")
    return final_df


if __name__ == "__main__":
    build_dataset()
