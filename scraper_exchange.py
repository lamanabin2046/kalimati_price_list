# =========================================================
# 💱 Nepal Rastra Bank - Automated USD Exchange Extractor
# =========================================================
import os
import time
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

# ---------------------------------------------------------
# 🌐 Configuration
# ---------------------------------------------------------
URL = "https://www.nrb.org.np/forex/"
HOME = os.path.expanduser("~")
OUT_DIR = os.path.join(HOME, "Desktop", "Tomato", "Data")
os.makedirs(OUT_DIR, exist_ok=True)

FROM_DATE = "01/01/2022"
TO_DATE = datetime.now().strftime("%m/%d/%Y")
EXPORT_FORMAT = "CSV"  # can change to "JSON" if you prefer

# ---------------------------------------------------------
# 🧭 Chrome Setup
# ---------------------------------------------------------
def setup_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    # set download directory to /data
    prefs = {
        "download.default_directory": os.path.abspath(OUT_DIR),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)
    return webdriver.Chrome(options=options)

# ---------------------------------------------------------
# 📥 Download Forex Data
# ---------------------------------------------------------
def download_forex_data():
    driver = setup_driver()
    wait = WebDriverWait(driver, 20)
    driver.get(URL)
    print("🌍 Opened NRB Forex Export Page")

    # wait for fields
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='From']")))

    # input from/to
    driver.execute_script("arguments[0].value = arguments[1];", driver.find_element(By.CSS_SELECTOR, "input[placeholder='From']"), FROM_DATE)
    driver.execute_script("arguments[0].value = arguments[1];", driver.find_element(By.CSS_SELECTOR, "input[placeholder='To']"), TO_DATE)

    # select export format
    Select(driver.find_element(By.CSS_SELECTOR, "select")).select_by_visible_text(EXPORT_FORMAT)

    # click export
    driver.find_element(By.XPATH, "//button[contains(text(),'Export')]").click()
    print("📤 Export initiated...")

    # wait for file download
    time.sleep(10)
    driver.quit()

    # find latest downloaded CSV file
    files = [f for f in os.listdir(OUT_DIR) if f.endswith(".csv")]
    latest = max([os.path.join(OUT_DIR, f) for f in files], key=os.path.getctime)
    print(f"✅ Download complete: {latest}")
    return latest

# ---------------------------------------------------------
# 🧮 Extract USD Sell Column
# ---------------------------------------------------------
def extract_usd_sell(csv_path):
    df = pd.read_csv(csv_path)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # keep only date and usd_sell
    if "usd_sell" not in df.columns:
        raise ValueError("❌ Column 'usd_sell' not found in the CSV. Check NRB file format.")
    cleaned = df[["date", "usd_sell"]].copy()

    # sort & save
    cleaned["date"] = pd.to_datetime(cleaned["date"])
    cleaned = cleaned.sort_values("date")
    save_path = os.path.join(OUT_DIR, "exchange.csv")
    cleaned.to_csv(save_path, index=False)
    print(f"💰 Cleaned file saved to: {save_path}")
    return cleaned

# ---------------------------------------------------------
# 🚀 Run
# ---------------------------------------------------------
if __name__ == "__main__":
    csv_file = download_forex_data()
    result_df = extract_usd_sell(csv_file)
    print(result_df.head())
