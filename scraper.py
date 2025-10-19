# scraper.py
import csv
import os
import sys
import time
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
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
    # If the GitHub Action provides a Chrome binary, use it
    chrome_path = os.environ.get("CHROME_PATH")
    if chrome_path and os.path.exists(chrome_path):
        chrome_opts.binary_location = chrome_path

    chrome_opts.add_argument("--headless=new")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")
    chrome_opts.add_argument("--window-size=1920,1080")
    chrome_opts.add_argument("--disable-gpu")
    chrome_opts.add_argument("--disable-features=NetworkService")
    chrome_opts.add_argument("--disable-features=VizDisplayCompositor")
    chrome_opts.add_argument("--remote-debugging-port=9222")

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


def safe_click_if_present(driver, by, value):
    try:
        el = driver.find_element(by, value)
        try_click_js_first(driver, el)
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


def set_date_value(driver, wait, date_str):
    """
    Try multiple strategies to set the date:
    1) input[type='date'] via send_keys
    2) input[type='text'] via send_keys
    3) JS: set 'value' on the first visible input and dispatch events
    """
    # wait for any date-like input to exist
    date_input = wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "input[type='date'], input[type='text']")
        )
    )

    # Prefer a visible element
    inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='date'], input[type='text']")
    target = None
    for inp in inputs:
        if inp.is_displayed() and inp.is_enabled():
            target = inp
            break
    if not target:
        target = date_input

    try:
        target.clear()
        target.send_keys(date_str)
        return True
    except Exception:
        # JS fallback
        driver.execute_script("""
            const el = arguments[0];
            el.value = arguments[1];
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        """, target, date_str)
        return True


def click_search_button(driver, wait):
    # Button might be in Nepali or English; try a few text patterns.
    candidates = [
        "//button[contains(., 'मूल्य')]",
        "//button[contains(., 'जाँच')]",     # 'check' in Nepali
        "//button[contains(., 'Price')]",
        "//button[contains(., 'Check')]",
        "//button[contains(., 'Search')]",
        "//button"
    ]
    for xp in candidates:
        try:
            btn = wait.until(EC.element_to_be_clickable((By.XPATH, xp)))
            if try_click_js_first(driver, btn):
                return True
        except Exception:
            continue
    return False


def dismiss_overlays(driver):
    # In case there is any cookie/consent overlay
    # Try common labels (English/Nepali) but ignore if not present
    common_buttons = [
        (By.XPATH, "//button[contains(., 'Accept')]"),
        (By.XPATH, "//button[contains(., 'I agree')]"),
        (By.XPATH, "//button[contains(., 'स्वीकार')]"),
        (By.XPATH, "//button[contains(., 'ठिक')]"),
    ]
    for by, sel in common_buttons:
        safe_click_if_present(driver, by, sel)


def scrape_today_only():
    ensure_outdir()
    target_dt = today_nepal_date()
    target_date_str = date_str_mmddyyyy(target_dt)

    if date_already_recorded(OUT_FILE, target_date_str):
        print(f"[SKIP] {target_date_str} already present in {OUT_FILE}")
        return 0

    driver = setup_driver()
    wait = WebDriverWait(driver, 40)

    added_rows = 0
    try:
        print(f"[INFO] Fetching {target_date_str} (Nepal time)")
        driver.get(URL)
        dismiss_overlays(driver)

        # Set date
        set_date_value(driver, wait, target_date_str)

        # Click search/check price
        if not click_search_button(driver, wait):
            print("[WARN] Could not find a search/check/price button; attempting Enter key on input.")
            # Try pressing Enter on the active element
            driver.switch_to.active_element.send_keys("\n")
            time.sleep(2)

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
        # Helpful debug: dump a small piece of DOM
        try:
            html = driver.page_source
            print(f"[DEBUG] page_source length={len(html)}")
        except Exception:
            pass
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
    _ = scrape_today_only()
    # Always exit 0 so the workflow can finish and try commit if any
    sys.exit(0)
