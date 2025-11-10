# =========================================================
# 🚚 Kalimati Daily Supply Volume Scraper (Auto-Resume Version)
# =========================================================
import csv
import os
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ---------------------------------------------------------
# 🌐 URLs and Output Paths
# ---------------------------------------------------------
URL = "https://kalimatimarket.gov.np/daily-arrivals"
OUT_DIR = "data/raw"
OUT_FILE = os.path.join(OUT_DIR, "supply_volume.csv")
START_DATE_STR = "01/01/2022"

# ---------------------------------------------------------
# 🕒 Date utilities (timezone-safe for GitHub Actions)
# ---------------------------------------------------------
def today_nepal_date():
    """Return today's date in Nepal Time (naive datetime for safe comparisons)."""
    now_utc = datetime.utcnow()
    nepal_time = now_utc + timedelta(hours=5, minutes=45)
    return nepal_time.replace(hour=0, minute=0, second=0, microsecond=0)

def date_str(dt):
    return dt.strftime("%m/%d/%Y")

def parse_date(s):
    try:
        return datetime.strptime(s, "%m/%d/%Y")
    except Exception:
        return None

# ---------------------------------------------------------
# 📁 CSV helpers
# ---------------------------------------------------------
def latest_date_in_csv(path):
    """Return the latest date in the CSV file (if exists)."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return None
    with open(path, encoding="utf-8") as f:
        next(f, None)  # skip header
        dates = [parse_date(row.split(",")[0]) for row in f if row.strip()]
    return max((d for d in dates if d), default=None)

# ---------------------------------------------------------
# 🧭 Selenium setup
# ---------------------------------------------------------
def setup_driver():
    """Initialize headless Chrome (optimized for GitHub Actions)."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")
    return webdriver.Chrome(options=options)

# ---------------------------------------------------------
# ⏰ Set the date on the Kalimati website
# ---------------------------------------------------------
def set_date(driver, date_str):
    """Try to set the target date in the date input field."""
    try:
        inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='date'], input[type='text']")
        for el in inputs:
            if el.is_displayed() and el.is_enabled():
                driver.execute_script("""
                    el = arguments[0];
                    el.value = arguments[1];
                    if ('valueAsDate' in el) {
                        el.valueAsDate = new Date(arguments[1]);
                    }
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                """, el, date_str)
                return True
    except Exception as e:
        print(f"[WARN] Error setting date: {e}")
    return False

# ---------------------------------------------------------
# 📊 Scrape data for a specific date
# ---------------------------------------------------------
def scrape_arrival_for_date(driver, wait, date_str):
    print(f"📅 Scraping arrival data for {date_str} ...")
    driver.get(URL)
    time.sleep(2)

    if not set_date(driver, date_str):
        print(f"[WARN] Could not set date {date_str}")
        return 0

    try:
        btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'आगमन डाटा जाँच्नुहोस्')]")))
        driver.execute_script("arguments[0].click();", btn)
    except Exception:
        print(f"[WARN] Could not click button for {date_str}")
        return 0

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table")))
        time.sleep(2)
    except:
        print(f"[WARN] Table not found for {date_str}")
        return 0

    if "टेबलमा डाटा उपलब्ध भएन" in driver.page_source:
        print(f"🚫 No arrival data for {date_str}")
        return 0

    rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
    added = 0
    os.makedirs(OUT_DIR, exist_ok=True)

    with open(OUT_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        # Write header if file is empty
        if os.path.getsize(OUT_FILE) == 0:
            headers = ["Date"] + [th.text.strip() for th in rows[0].find_elements(By.TAG_NAME, "th")]
            w.writerow(headers)

        # Append new rows
        for row in rows[1:]:
            cols = [td.text.strip() for td in row.find_elements(By.TAG_NAME, "td")]
            if cols:
                w.writerow([date_str] + cols)
                added += 1

    print(f"✅ Added {added} arrival rows for {date_str}")
    return added

# ---------------------------------------------------------
# 🚀 Main entry point
# ---------------------------------------------------------
if __name__ == "__main__":
    # Base date (start of dataset)
    start = parse_date(START_DATE_STR)

    # Today's date (Nepal)
    end = today_nepal_date()

    # Find last recorded date in CSV (if any)
    last_date = latest_date_in_csv(OUT_FILE)

    # Resume logic
    if last_date:
        if last_date >= end:
            print(f"🟢 Data already up-to-date. Last entry: {date_str(last_date)}")
            exit()
        print(f"⏩ Resuming from {date_str(last_date)}")
        start = last_date + timedelta(days=1)
    else:
        print("📄 No previous data found. Starting fresh.")

    # Start scraping
    driver = setup_driver()
    wait = WebDriverWait(driver, 25)
    total = 0

    try:
        while start <= end:
            ds = date_str(start)
            total += scrape_arrival_for_date(driver, wait, ds)
            start += timedelta(days=1)
            time.sleep(1)
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        driver.quit()

    print(f"🏁 Done! Total new arrival rows: {total}")
