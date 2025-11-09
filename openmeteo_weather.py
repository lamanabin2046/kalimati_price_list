# openmeteo_weather.py
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
from datetime import date

cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

districts = {
    "Kathmandu": {"latitude": 27.7172, "longitude": 85.3240},
    "Dhading": {"latitude": 27.9100, "longitude": 84.9000},
    "Kavre": {"latitude": 27.6000, "longitude": 85.5500},
    "Sarlahi": {"latitude": 26.9830, "longitude": 85.5500}
}

url = "https://archive-api.open-meteo.com/v1/archive"
start_date = "2022-01-01"
end_date = str(date.today())

weather_vars = ["temperature_2m", "relative_humidity_2m", "precipitation", "rain", "pressure_msl", "wind_speed_10m"]

all_data = []
for district, coords in districts.items():
    print(f"Fetching {district}...")
    params = {
        "latitude": coords["latitude"],
        "longitude": coords["longitude"],
        "start_date": start_date,
        "end_date": end_date,
        "hourly": weather_vars,
        "timezone": "Asia/Kathmandu"
    }
    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]
    hourly = response.Hourly()
    hourly_data = {
        "Date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        )
    }
    for i, var in enumerate(weather_vars):
        hourly_data[f"{district}_{var}"] = hourly.Variables(i).ValuesAsNumpy()
    df = pd.DataFrame(hourly_data)
    all_data.append(df)

final_df = all_data[0]
for df in all_data[1:]:
    final_df = pd.merge(final_df, df, on="Date", how="outer")

final_df["Date"] = pd.to_datetime(final_df["Date"]).dt.date
daily_avg_df = final_df.groupby("Date").mean(numeric_only=True).reset_index()
daily_avg_df.to_csv("data/nepal_weather_daily_avg.csv", index=False)
print("✅ Updated weather data saved.")
