import csv
import os
import sys
import time
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# =========================================================
# 🌐 URLs and File Paths
# =========================================================
PRICE_URL = "https://kalimatimarket.gov.np/price"
ARRIVAL_URL = "https://kalimatimarket.gov.np/daily-arrivals"

OUT_DIR = "data"
PRICE_FILE = os.path.join(OUT_DIR, "veg_price_list.csv")
ARRIVAL_FILE = os.path.join(OUT_DIR, "supply_volume.csv")

START_DATE_STR = "01/01/2022"  # mm/dd/YYYY


# =========================================================
# 🕒 Time and Date Utilities
# =========================================================
def today_nepal_date():
    """Return today's date at 00:00 in Nepal time (UTC+05:45)."""
    npt = datetime.utcnow() + timedelta(hours=5, minutes=45)
    return npt.replace(hour=0, minute=0, second=0, microsecond=0)


def date_str_mmddyyyy(dt: datetime) -> str:
    return dt.strftime("%m/%d/%Y")


def parse_mmddyyyy(s: str):
    try:
        return datetime.strptime(s, "%m/%d/%Y")
    except Exception:
        return None


# =========================================================
# 📂 File Utilities
# =========================================================
def ensure_outdir():
    os.makedirs(OUT_DIR, exist_ok=True)


def date_already_recorded(csv_path: str, date_str: str) -> bool:
    """Check if a given date string is already present in the CSV."""
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        return False
    with open(csv_path, newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.reader(f)):
            if not row or row[0].strip().lower() == "date":
                continue
            if row[0].strip() == date_str:
                return True
    return False


def latest_date_in_csv(csv_path: str):
    """Return the latest date in a CSV, or None if empty."""
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        return None
    latest = None
    with open(csv_path, newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.reader(f)):
            if not row or row[0].strip().lower() == "date":
                continue
            d = parse_mmddyyyy(row[0].strip())
            if d and (latest is None or d > latest):
                latest = d
    return latest


# =========================================================
# 🧭 Selenium Helpers
# =========================================================
def setup_driver():
    chrome_opts = Options()
    chrome_path = os.environ.get("CHROME_PATH")
    if chrome_path and os.path.exists(chrome_path):
        chrome_opts.binary_location = chrome_path

    chrome_opts.add_argument("--headless=new")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")
    chrome_opts.add_argument("--window-size=1920,1080")
    chrome_opts.add_argument("--disable-gpu")
    chrome_opts.add_argument("--disable-features=NetworkService, VizDisplayCompositor")
    chrome_opts.add_argument("--remote-debugging-port=9222")

    return webdriver.Chrome(options=chrome_opts)


def try_click_js_first(driver, elem):
    try:
        driver.execute_script("arguments[0].click();", elem)
        return True
    except Exception:
        try:
            elem.click()
            return True
        except Exception:
            return False


def dismiss_overlays(driver):
    """Close cookie or modal banners if present."""
    candidates = [
        (By.XPATH, "//button[contains(., 'Accept')]"),
        (By.XPATH, "//button[contains(., 'ठिक')]"),
        (By.XPATH, "//button[contains(., 'स्वीकार')]"),
    ]
    for by, sel in candidates:
        try:
            driver.find_element(by, sel).click()
        except Exception:
            continue


def set_date_value(driver, wait, date_str):
    """Set the date input field value."""
    date_input = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='date'], input[type='text']"))
    )
    inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='date'], input[type='text']")
    target = next((i for i in inputs if i.is_displayed() and i.is_enabled()), date_input)
    try:
        target.clear()
        target.send_keys(date_str)
    except Exception:
        driver.execute_script(
            """
            const el = arguments[0];
            el.value = arguments[1];
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            """,
            target,
            date_str,
        )


def click_button(driver, wait, keywords):
    """Try clicking buttons containing any of the given keywords."""
    for kw in keywords:
        try:
            btn = wait.until(EC.element_to_be_clickable((By.XPATH, f"//button[contains(., '{kw}')]")))
            if try_click_js_first(driver, btn):
                return True
        except Exception:
            continue
    return False


def get_rows_after_load(driver, wait):
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table")))
    time.sleep(1.2)
    return driver.find_elements(By.CSS_SELECTOR, "table tr")


def write_header_if_needed(csv_writer, rows, header_written_flag):
    """Write table header if missing."""
    if header_written_flag:
        return True
    for r in rows:
        ths = r.find_elements(By.TAG_NAME, "th")
        if ths:
            header = ["Date"] + [th.text.strip() for th in ths]
            csv_writer.writerow(header)
            return True
    return header_written_flag


# =========================================================
# 🥦 Core Scraping
# =========================================================
def scrape_one_date(driver, wait, date_str, url, outfile, button_keywords, retries=3):
    """Scrape a single page for one date with retry logic."""
    for attempt in range(retries):
        try:
            print(f"[INFO] Fetching {date_str} from {url} (Attempt {attempt + 1})", flush=True)
            driver.get(url)
            dismiss_overlays(driver)
            set_date_value(driver, wait, date_str)
            if not click_button(driver, wait, button_keywords):
                driver.switch_to.active_element.send_keys("\n")
                time.sleep(2)

            rows = get_rows_after_load(driver, wait)
            header_written = os.path.exists(outfile) and os.path.getsize(outfile) > 0
            added_rows = 0

            with open(outfile, "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                header_written = write_header_if_needed(w, rows, header_written)
                data_rows = []
                for r in rows:
                    tds = r.find_elements(By.TAG_NAME, "td")
                    if tds:
                        data_rows.append([td.text.strip() for td in tds])

                if not any(any(c for c in row) for row in data_rows):
                    print(f"[WARN] No data for {date_str}", flush=True)
                    return 0

                for row in data_rows:
                    w.writerow([date_str] + row)
                    added_rows += 1

            print(f"[OK] Added {added_rows} rows for {date_str}", flush=True)
            return added_rows

        except TimeoutException:
            print(f"[TIMEOUT] Retrying {date_str}...", flush=True)
            time.sleep(4)
        except WebDriverException as e:
            print(f"[ERROR] WebDriver issue on {date_str}: {e}", flush=True)
            time.sleep(5)
        except Exception as e:
            print(f"[ERROR] Generic failure on {date_str}: {e}", flush=True)
            time.sleep(5)
    print(f"[FAIL] Skipped {date_str} after {retries} attempts.", flush=True)
    return 0


# =========================================================
# 🚀 Main Scraper Logic
# =========================================================
def scrape_range(start_dt, end_dt):
    ensure_outdir()
    driver = setup_driver()
    wait = WebDriverWait(driver, 40)

    try:
        current = start_dt
        total_price = 0
        total_arrivals = 0
        total_days = (end_dt - start_dt).days + 1

        print(f"📅 Starting scraping from {date_str_mmddyyyy(start_dt)} to {date_str_mmddyyyy(end_dt)}", flush=True)
        print(f"🔍 Total days to scrape: {total_days}\n", flush=True)

        while current <= end_dt:
            date_str = date_str_mmddyyyy(current)

            # ---- Price Data ----
            if not date_already_recorded(PRICE_FILE, date_str):
                total_price += scrape_one_date(
                    driver, wait, date_str, PRICE_URL, PRICE_FILE,
                    ["मूल्य", "Price", "Check"]
                )
            else:
                print(f"[SKIP] Price data for {date_str} already exists", flush=True)

            # ---- Arrival Data ----
            if not date_already_recorded(ARRIVAL_FILE, date_str):
                total_arrivals += scrape_one_date(
                    driver, wait, date_str, ARRIVAL_URL, ARRIVAL_FILE,
                    ["आगमन", "Arrival", "Check"]
                )
            else:
                print(f"[SKIP] Arrival data for {date_str} already exists", flush=True)

            # ✅ Log progress
            print(f"[PROGRESS] {date_str} done → Price: {total_price}, Arrival: {total_arrivals}\n", flush=True)

            current += timedelta(days=1)
            time.sleep(1.5)

        print(f"[DONE] ✅ Added {total_price} price rows and {total_arrivals} arrival rows.", flush=True)

    finally:
        driver.quit()


# =========================================================
# 🏁 Entrypoint
# =========================================================
if __name__ == "__main__":
    start = parse_mmddyyyy(START_DATE_STR)
    end = today_nepal_date()

    if start is None:
        print("[FATAL] Invalid start date format.", flush=True)
        sys.exit(1)

    # Resume from latest existing date if available
    last_price = latest_date_in_csv(PRICE_FILE)
    last_arrival = latest_date_in_csv(ARRIVAL_FILE)
    last_done = max(d for d in [last_price, last_arrival] if d is not None) if (last_price or last_arrival) else None
    if last_done and last_done > start:
        start = last_done + timedelta(days=1)
        print(f"⏩ Resuming from next date after {date_str_mmddyyyy(last_done)}", flush=True)

    scrape_range(start, end)
    sys.exit(0)
