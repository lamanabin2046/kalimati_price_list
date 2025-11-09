# 🌦️ openmeteo_weather.py
import requests
import pandas as pd
import os
from datetime import datetime, timezone, timedelta

URL = "https://api.open-meteo.com/v1/forecast"
OUT_DIR = "data"
OUT_FILE = os.path.join(OUT_DIR, "weather.csv")

def today_nepal_date():
    now_utc = datetime.now(timezone.utc)
    return (now_utc + timedelta(hours=5, minutes=45)).date()

def fetch_weather():
    params = {
        "latitude": 27.7172,
        "longitude": 85.3240,
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum"],
        "timezone": "Asia/Kathmandu"
    }
    r = requests.get(URL, params=params)
    r.raise_for_status()
    data = r.json()
    df = pd.DataFrame(data["daily"])
    df["date"] = pd.to_datetime(df["time"])
    return df[["date", "temperature_2m_max", "temperature_2m_min", "precipitation_sum"]]

if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    df = fetch_weather()
    if os.path.exists(OUT_FILE):
        old = pd.read_csv(OUT_FILE)
        df = pd.concat([old, df]).drop_duplicates(subset=["date"]).sort_values("date")
    df.to_csv(OUT_FILE, index=False)
    print(f"✅ Weather updated → {OUT_FILE}")
