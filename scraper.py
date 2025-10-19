# scraper.py
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


URL = "https://kalimatimarket.gov.np/price"
OUT_DIR = "data"
OUT_FILE = os.path.join(OUT_DIR, "price_list.csv")


def today_nepal_date():
    """Return today's date at 00:00 in Nepal time (UTC+05:45)."""
    npt = datetime.utcnow() + timedelta(hours=5, minutes=45)
    return npt.replace(hour=0, minute=0, second=0, microsecond=0)


def date_str_mmddyyyy(dt: datetime) -> str:
    return dt.strftime("%m/%d/%Y")


def ensure_outdir():
    os.makedirs(OUT_DIR, exist_ok=True)


def date_already_recorded(csv_path: str, date_str: str) -> bool:
    """Return True if first column contains date_str (skip header)."""
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        return False
    with open(csv_path, newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        for i, row in enumerate(r):
            if not row:
                continue
            if i == 0 and row[0].strip().lower() == "date":
                continue
            if row[0].strip() == date_str:
                return True
    return False


def setup_driver():
    chrome_opts = Options()
    chrome_opts.add_argument("--headless=new")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")
    chrome_opts.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=chrome_opts)


def try_click_js_first(driver, elem):
    try:
        driver.execute_script("arguments[0].click();", elem)
        return True
    except WebDriverException:
        try:
            elem.click()
            return True
        except Exception:
            return False


def get_rows_after_load(driver, wait: WebDriverWait):
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table")))
    time.sleep(1.5)  # small buffer for table render
    return driver.find_elements(By.CSS_SELECTOR, "table tr")


def write_header_if_needed(csv_writer, rows, header_written_flag: bool) -> bool:
    """Detect header from <th> row and write once."""
    if header_written_flag:
        return True
    for r in rows:
        ths = r.find_elements(By.TAG_NAME, "th")
        if ths:
            header = ["Date"] + [th.text.strip() for th in ths]
            csv_writer.writerow(header)
            return True
    return header_written_flag


def scrape_today_only():
    ensure_outdir()
    target_dt = today_nepal_date()
    target_date_str = date_str_mmddyyyy(target_dt)

    if date_already_recorded(OUT_FILE, target_date_str):
        print(f"[SKIP] {target_date_str} already present in {OUT_FILE}")
        return 0

    driver = setup_driver()
    wait = WebDriverWait(driver, 30)

    added_rows = 0
    try:
        print(f"[INFO] Fetching {target_date_str} (Nepal time)")

        driver.get(URL)

        # Find a date input — the page may use type='text' or 'date'
        date_input = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[type='text'], input[type='date']")
            )
        )
        date_input.clear()
        date_input.send_keys(target_date_str)

        # Button text commonly contains Nepali 'मूल्य' (price) or English 'Price/Check'
        btn = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[contains(., 'मूल्य') or contains(., 'Price') or contains(., 'Check')]",
                )
            )
        )
        try_click_js_first(driver, btn)

        rows = get_rows_after_load(driver, wait)

        # Open CSV (append) and ensure header exists
        header_written = os.path.exists(OUT_FILE) and os.path.getsize(OUT_FILE) > 0
        with open(OUT_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            header_written = write_header_if_needed(writer, rows, header_written)

            # Collect and write data rows
            data_rows = []
            for r in rows:
                tds = r.find_elements(By.TAG_NAME, "td")
                if tds:
                    data_rows.append([td.text.strip() for td in tds])

            has_data = any(any(cell for cell in row) for row in data_rows)
            if not has_data:
                print(f"[WARN] No price data available for {target_date_str}")
                return 0

            for row in data_rows:
                writer.writerow([target_date_str] + row)
                added_rows += 1

        print(f"[OK] Added {added_rows} rows for {target_date_str}")
        return added_rows

    except TimeoutException:
        print(f"[ERROR] Timeout while scraping {target_date_str}")
        return 0
    except Exception as e:
        print(f"[ERROR] {target_date_str}: {e}")
        return 0
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    rows = scrape_today_only()
    # Exit 0 even if zero rows; GitHub Action will still continue to commit if needed.
    sys.exit(0)
