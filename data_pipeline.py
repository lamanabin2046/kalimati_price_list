import pandas as pd
import os
import re
import numpy as np

# ============================================================
# 🧩 Helper: Convert Nepali digits to English
# ============================================================
def nepali_to_english(num_str):
    if pd.isna(num_str):
        return num_str
    mapping = str.maketrans("०१२३४५६७८९", "0123456789")
    return str(num_str).translate(mapping)

# ============================================================
# 🧩 Helper: Clean numeric and currency strings
# ============================================================
def clean_number(value):
    if pd.isna(value):
        return None
    value = str(value).replace("रू", "").replace(",", "").strip()
    value = nepali_to_english(value)
    try:
        return float(value)
    except:
        return None

# ============================================================
# 🧩 Helper: Clean commodity names
# ============================================================
def clean_commodity(name):
    name = re.sub(r"\(.*?\)", "", str(name)).strip()
    mapping = {
        "गोलभेडा ठूलो": "Tomato_Big",
        "गोलभेडा सानो": "Tomato_Small",
        "गोलभेडा": "Tomato"
    }
    for np_name, en_name in mapping.items():
        if np_name in name:
            return en_name
    return name

# ============================================================
# 📘 Load & Clean Price Data
# ============================================================
def load_price_data(path="data/veg_price_list.csv"):
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = df[["Date", "कृषि उपज", "औसत"]].copy()
    df.rename(columns={"कृषि उपज": "commodity", "औसत": "Average_Price"}, inplace=True)
    df["commodity"] = df["commodity"].apply(clean_commodity)
    df["Average_Price"] = df["Average_Price"].apply(clean_number)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df[df["commodity"] == "Tomato_Big"]
    df = df.dropna(subset=["Date", "Average_Price"])
    # Average if multiple entries on same date
    df = df.groupby("Date", as_index=False)["Average_Price"].mean()
    return df

# ============================================================
# 📗 Load & Clean Supply Data
# ============================================================
def load_supply_data(path="data/supply_volume.csv"):
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = df[["Date", "कृषि उपज", "आगमन"]].copy()
    df.rename(columns={"कृषि उपज": "commodity", "आगमन": "Supply_Volume"}, inplace=True)
    df["commodity"] = df["commodity"].apply(clean_commodity)
    df["Supply_Volume"] = df["Supply_Volume"].apply(clean_number)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    tomato_df = df[df["commodity"].isin(["Tomato_Big", "Tomato_Small", "Tomato"])].copy()
    tomato_sum = tomato_df.groupby("Date")["Supply_Volume"].sum().reset_index()
    return tomato_sum

# ============================================================
# 🌦️ Load Weather Data
# ============================================================
def load_weather_data(path="data/weather.csv"):
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
    return df

# ============================================================
# ⛽ Load Fuel, Inflation, Exchange (with forward fill)
# ============================================================
def load_fuel_data(path="data/fuel.csv"):
    if not os.path.exists(path):
        return pd.DataFrame(columns=["Date", "Diesel"])
    df = pd.read_csv(path)
    df.rename(columns={df.columns[0]: "Date", df.columns[1]: "Diesel"}, inplace=True)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).drop_duplicates(subset="Date", keep="last")
    df["Diesel"] = pd.to_numeric(df["Diesel"], errors="coerce")
    return df.set_index("Date").resample("D").ffill().reset_index()

def load_inflation_data(path="data/inflation.xlsx"):
    if not os.path.exists(path):
        return pd.DataFrame(columns=["Date", "Inflation"])
    df = pd.read_excel(path)
    df.rename(columns={df.columns[0]: "Month", df.columns[1]: "Inflation"}, inplace=True)
    df["Date"] = pd.to_datetime(df["Month"], errors="coerce")
    df = df.dropna(subset=["Date"]).drop_duplicates(subset="Date", keep="last")
    return df[["Date", "Inflation"]].set_index("Date").resample("D").ffill().reset_index()

def load_exchange_data(path="data/exchange.csv"):
    if not os.path.exists(path):
        return pd.DataFrame(columns=["Date", "USD_TO_NPR"])
    df = pd.read_csv(path)
    df.rename(columns={df.columns[0]: "Date", df.columns[1]: "USD_TO_NPR"}, inplace=True)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).drop_duplicates(subset="Date", keep="last")
    df["USD_TO_NPR"] = pd.to_numeric(df["USD_TO_NPR"], errors="coerce")
    return df.set_index("Date").resample("D").ffill().reset_index()

# ============================================================
# 🔗 Merge All
# ============================================================
def merge_all(price_df, supply_df, weather_df, fuel_df, inflation_df, exchange_df):
    df = pd.merge(price_df, supply_df, on="Date", how="left")
    df = pd.merge(df, exchange_df, on="Date", how="left")
    df = pd.merge(df, fuel_df, on="Date", how="left")
    df = pd.merge(df, inflation_df, on="Date", how="left")
    df = pd.merge(df, weather_df, on="Date", how="left")
    df = df.sort_values("Date").reset_index(drop=True)
    return df

# ============================================================
# 📅 Time Features
# ============================================================
def add_time_features(df):
    df["day"] = df["Date"].dt.day
    df["month"] = df["Date"].dt.month
    df["day_of_week"] = df["Date"].dt.weekday
    df["is_weekend"] = (df["day_of_week"] == 5).astype(int)  # Saturday = weekend in Nepal
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    return df

# ============================================================
# 🍂 Add Seasonal Flags (numeric)
# ============================================================
def add_seasons(df):
    df["Season_Winter"] = df["month"].isin([12, 1, 2]).astype(int)
    df["Season_Spring"] = df["month"].isin([3, 4, 5]).astype(int)
    df["Season_Monsoon"] = df["month"].isin([6, 7, 8, 9]).astype(int)
    df["Season_Autumn"] = df["month"].isin([10, 11]).astype(int)
    return df

# ============================================================
# 🏮 Add Festival & Fiscal Year
# ============================================================
def add_festival_and_fiscal(df):
    df["is_festival"] = 0

    for i, row in df.iterrows():
        m, d = row["month"], row["day"]
        if m == 3 and (1 <= d <= 20):  # Holi
            df.at[i, "is_festival"] = 1
        elif m == 4 and (10 <= d <= 20):  # New Year
            df.at[i, "is_festival"] = 1
        elif (m == 9 and d >= 25) or (m == 10 and d <= 15):  # Dashain
            df.at[i, "is_festival"] = 1
        elif m == 11 and (1 <= d <= 15):  # Tihar
            df.at[i, "is_festival"] = 1

    def get_fy(date):
        return f"FY_{date.year if date.month >= 7 else date.year - 1}_{str((date.year if date.month >= 7 else date.year - 1) + 1)[-2:]}"
    df["Fiscal_Year"] = df["Date"].apply(get_fy)
    return df

# ============================================================
# 🚀 Main Pipeline
# ============================================================
if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)

    print("🧹 Cleaning and merging Kalimati datasets...")
    price_df = load_price_data()
    supply_df = load_supply_data()
    weather_df = load_weather_data()
    fuel_df = load_fuel_data()
    inflation_df = load_inflation_data()
    exchange_df = load_exchange_data()

    print("🔗 Merging all datasets...")
    final_df = merge_all(price_df, supply_df, weather_df, fuel_df, inflation_df, exchange_df)
    final_df = add_time_features(final_df)
    final_df = add_seasons(final_df)
    final_df = add_festival_and_fiscal(final_df)

    # Final column order
    column_order = [
        "Date", "Average_Price", "Supply_Volume", "USD_TO_NPR", "Diesel", "is_festival",
        "Season_Autumn", "Season_Monsoon", "Season_Spring", "Season_Winter", "Inflation",
        "Dhading_Wind_Speed", "Dhading_Temperature", "Dhading_Precipitation", "Dhading_Rainfall_MM", "Dhading_Air_Pressure",
        "Kathmandu_Wind_Speed", "Kathmandu_Temperature", "Kathmandu_Precipitation", "Kathmandu_Rainfall_MM", "Kathmandu_Air_Pressure",
        "Kavre_Wind_Speed", "Kavre_Temperature", "Kavre_Precipitation", "Kavre_Rainfall_MM", "Kavre_Air_Pressure",
        "Sarlahi_Wind_Speed", "Sarlahi_Temperature", "Sarlahi_Precipitation", "Sarlahi_Rainfall_MM", "Sarlahi_Air_Pressure",
        "day", "month", "day_of_week", "is_weekend", "month_sin", "month_cos"
    ]
    final_df = final_df[[c for c in column_order if c in final_df.columns]]

    output_path = "data/tomato_clean_data.csv"
    final_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print("✅ Final ML-ready dataset saved →", output_path)
    print(f"Total rows: {len(final_df)}, Columns: {len(final_df.columns)}")
    print(final_df.head(5))
