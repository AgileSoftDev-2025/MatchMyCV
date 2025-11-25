# features/analyze-cv/steps/analyze-cv.py
from behave import given, when, then
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from urllib.parse import urljoin
from datetime import datetime
import os
import time
import json

# ======================================================
# Konfigurasi Global
# ======================================================
CHROMEDRIVER_PATH = os.path.join(os.getcwd(), "chromedriver.exe")
BASE_URL = "http://127.0.0.1:8000/"
TEST_FILES_DIR = os.path.join(os.getcwd(), "test_files")

# Default timeout (detik) untuk menunggu proses analisis selesai.
ANALYSIS_TIMEOUT = int(os.getenv("ANALYSIS_TIMEOUT", "120"))

def build_url(path: str) -> str:
    return urljoin(BASE_URL, path.lstrip("/"))


def _scroll_into_view(driver, el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)


def _hover(driver, el):
    ActionChains(driver).move_to_element(el).pause(0.2).perform()


def find_element(context, identifier, by_type=None):
    """Cari elemen dengan berbagai strategi."""
    wait = WebDriverWait(context.driver, 10)
    
    if by_type == "id":
        try:
            return wait.until(EC.presence_of_element_located((By.ID, identifier)))
        except TimeoutException:
            raise AssertionError(f"Element with id='{identifier}' not found")
    
    if by_type == "css":
        try:
            return wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, identifier)))
        except TimeoutException:
            raise AssertionError(f"Element with CSS selector '{identifier}' not found")
    
    # Auto-detect strategy
    strategies = [
        (By.ID, identifier),
        (By.CSS_SELECTOR, f"[data-testid='{identifier}']"),
        (By.CSS_SELECTOR, f"[data-test='{identifier}']"),
        (By.CSS_SELECTOR, f".{identifier}"),
        (By.XPATH, f"//*[contains(text(), '{identifier}')]")
    ]
    
    for by, value in strategies:
        try:
            return wait.until(EC.presence_of_element_located((by, value)))
        except TimeoutException:
            continue
    
    raise AssertionError(f"Element '{identifier}' not found")


# ======================================================
# Helper: tunggu analisis selesai (beberapa sinyal)
# ======================================================
def wait_for_analysis_complete(context, timeout=ANALYSIS_TIMEOUT):
    """
    Menunggu sampai salah satu kondisi:
      - URL mengandung '/hasil-rekomendasi/'
      - Elemen 'CV-Summary' visible
      - Elemen progress-percent berisi '100%'
    Mengembalikan tuple (True, reason) atau (False, 'timeout').
    """
    wait = WebDriverWait(context.driver, timeout)

    def check_any(driver):
        try:
            # 1) cek URL redirect
            current = driver.current_url
            if "/hasil-rekomendasi/" in current:
                return "url"

            # 2) cek progress text
            try:
                progress_el = driver.find_element(By.ID, "progress-percent")
                progress_text = progress_el.text or ""
                if "100%" in progress_text:
                    return "progress_100"
            except Exception:
                pass

            # 3) cek CV-Summary element hadir & visible
            try:
                el = driver.find_element(By.ID, "CV-Summary")
                if el.is_displayed():
                    return "cv_summary"
            except Exception:
                pass

            return False
        except WebDriverException:
            return False

    try:
        result = wait.until(check_any)
        return True, result
    except TimeoutException:
        return False, "timeout"


def _save_debug_artifacts(context, prefix="debug"):
    """Simpan screenshot, page source (partial), dan console logs bila memungkinkan."""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        ss_path = os.path.join(TEST_FILES_DIR, f"{prefix}_screenshot_{ts}.png")
        context.driver.save_screenshot(ss_path)
    except Exception:
        ss_path = None

    try:
        ps_path = os.path.join(TEST_FILES_DIR, f"{prefix}_page_partial_{ts}.html")
        with open(ps_path, "w", encoding="utf-8") as f:
            f.write(context.driver.page_source[:20000])
    except Exception:
        ps_path = None

    logs_path = None
    try:
        # chrome-specific: may raise if not supported
        browser_logs = context.driver.get_log("browser")
        logs_path = os.path.join(TEST_FILES_DIR, f"{prefix}_browser_logs_{ts}.log")
        with open(logs_path, "w", encoding="utf-8") as f:
            for entry in browser_logs:
                f.write(json.dumps(entry, default=str) + "\n")
    except Exception:
        # tidak semua webdriver expose logs
        logs_path = None

    return ss_path, ps_path, logs_path


# ======================================================
# GIVEN Steps
# ======================================================

@given('I am on the "/analisis-cv/" page')
def step_go_to_analysis_page(context):
    service = Service(CHROMEDRIVER_PATH)
    context.driver = webdriver.Chrome(service=service)
    context.driver.maximize_window()
    context.driver.get(build_url("/analisis-cv/"))
    time.sleep(1)  # small wait for initial load
    # buat flag debug opsional agar tidak auto-close (set di environment jika perlu)
    context.debug_keep_browser = os.getenv("DEBUG_KEEP_BROWSER", "false").lower() in ("1", "true", "yes")


@given('I select "{location}" from the "location" dropdown')
def step_select_location(context, location):
    dropdown = Select(find_element(context, "location", "id"))
    
    # Map text to value
    location_map = {
        "All Locations": "all",
        "Jakarta": "jakarta",
        "Surabaya": "surabaya",
        "Bandung": "bandung",
        "Yogyakarta": "yogyakarta"
    }
    
    value = location_map.get(location, location.lower())
    try:
        dropdown.select_by_value(value)
    except Exception:
        # fallback: select by visible text
        dropdown.select_by_visible_text(location)
    context.selected_location = location


# ======================================================
# WHEN Steps
# ======================================================

@when('I press "Upload CV" button')
def step_press_upload_cv(context):
    btn = find_element(context, "upload-btn", "id")
    _scroll_into_view(context.driver, btn)
    time.sleep(0.2)
    btn.click()  # FIXED: Changed from btn.press() to btn.click()
    time.sleep(0.5)


@when('I upload the file "{filename}"')
def step_upload_file(context, filename):
    context.file_path = os.path.join(TEST_FILES_DIR, filename)
    
    if not os.path.exists(context.file_path):
        raise AssertionError(f"Test file not found: {context.file_path}")
    
    # Trigger file input (hidden element)
    file_input = find_element(context, "cv-upload", "id")
    file_input.send_keys(context.file_path)
    time.sleep(0.5)
    
    context.uploaded_filename = filename


@when('the file format should be "{ext}"')
def step_validate_format(context, ext):
    if not context.file_path.lower().endswith(f".{ext.lower()}"):
        raise AssertionError(f"Expected .{ext} file, got: {context.file_path}")


@when('the file size should be below 10MB')
def step_validate_small_size(context):
    size = os.path.getsize(context.file_path)
    size_mb = size / (1024 * 1024)
    if size_mb > 10:
        raise AssertionError(f"Expected file < 10MB but got {size_mb:.2f}MB")


@when('the file size should be larger than 10MB')
def step_validate_large_size(context):
    size = os.path.getsize(context.file_path)
    size_mb = size / (1024 * 1024)
    if size_mb <= 10:
        raise AssertionError(f"Expected file > 10MB but got {size_mb:.2f}MB")


@when('I press "Analyze" button')
def step_press_analyze(context):
    """Klik tombol Analyze - smart detection untuk sukses atau error case"""
    btn = find_element(context, "analyze-btn", "id")
    _scroll_into_view(context.driver, btn)
    time.sleep(0.3)
    
    # Cek apakah tombol disabled
    is_disabled = btn.get_attribute("disabled") is not None
    
    # Klik tombol (gunakan JS jika disabled)
    try:
        if is_disabled:
            context.driver.execute_script("arguments[0].click();", btn)
        else:
            btn.click()
    except Exception as e:
        print(f"Normal click failed: {e}, using JavaScript click")
        context.driver.execute_script("arguments[0].click();", btn)
    
    time.sleep(1)
    
    # Cek apakah ada error message yang muncul
    try:
        error_el = context.driver.find_element(By.ID, "form-message")
        error_classes = error_el.get_attribute("class") or ""
        has_error = "hidden" not in error_classes.lower() and error_el.is_displayed()
        
        if has_error:
            # Ada error, tidak perlu tunggu analisis
            print("DEBUG: Error message detected, skipping analysis wait")
            context.analysis_triggered = False
            return
    except Exception:
        pass
    
    # Tidak ada error, tunggu analisis selesai
    print("DEBUG: No error detected, waiting for analysis to complete")
    ok, reason = wait_for_analysis_complete(context, timeout=ANALYSIS_TIMEOUT)
    if not ok:
        ss, ps, logs = _save_debug_artifacts(context, prefix="analyze_timeout")
        raise AssertionError(
            f"Analyze did not finish within {ANALYSIS_TIMEOUT}s. Reason: {reason}. "
            f"Saved screenshot: {ss}, page snippet: {ps}, logs: {logs}"
        )
    context.analysis_finished_reason = reason
    context.analysis_triggered = True


@when('I attempt to press "Analyze" button')
def step_attempt_press_analyze(context):
    """Coba klik tombol Analyze (untuk kasus error/validation) - tidak tunggu analisis selesai"""
    btn = find_element(context, "analyze-btn", "id")
    _scroll_into_view(context.driver, btn)
    time.sleep(0.3)
    
    # Cek apakah tombol disabled atau tidak clickable
    is_disabled = btn.get_attribute("disabled") is not None
    is_clickable = btn.is_enabled()
    
    # Log untuk debugging
    print(f"DEBUG: Button disabled={is_disabled}, enabled={is_clickable}")
    
    try:
        if is_disabled or not is_clickable:
            # Jika disabled, gunakan JavaScript untuk klik (trigger validation/error)
            print("DEBUG: Using JavaScript click because button is disabled")
            context.driver.execute_script("arguments[0].click();", btn)
        else:
            # Jika enabled, klik normal
            print("DEBUG: Using normal click")
            btn.click()
    except Exception as e:
        print(f"DEBUG: Click failed with error: {e}, trying JavaScript click")
        context.driver.execute_script("arguments[0].click();", btn)
    
    time.sleep(1)  # Tunggu error message muncul


@when('I press "Cancel" button')
def step_press_cancel(context):
    btn = find_element(context, "close-modal", "id")
    _scroll_into_view(context.driver, btn)
    time.sleep(0.2)
    btn.click()  # FIXED: Changed from btn.press() to btn.click()
    time.sleep(0.5)


# ======================================================
# THEN Steps
# ======================================================

@then('I should see the modal "{modal_id}"')
def step_see_modal(context, modal_id):
    modal = find_element(context, modal_id, "id")
    # Check if modal is visible
    is_visible = modal.value_of_css_property("display") != "none" and modal.is_displayed()
    if not is_visible:
        raise AssertionError(f"Modal '{modal_id}' is not visible")


@then('the modal "{modal_id}" should be hidden')
def step_modal_hidden(context, modal_id):
    time.sleep(0.5)
    modal = find_element(context, modal_id, "id")
    is_hidden = modal.value_of_css_property("display") == "none" or (not modal.is_displayed())
    if not is_hidden:
        raise AssertionError(f"Modal '{modal_id}' should be hidden but is still visible")


@then('I should see the loading screen')
def step_see_loading_screen(context):
    loading = find_element(context, "loading-container", "id")
    # Check if loading container is visible
    classes = loading.get_attribute("class") or ""
    if "hidden" in classes.lower():
        raise AssertionError("Loading screen is not visible")


@then('the progress should reach 100%')
def step_progress_100(context):
    ok, why = wait_for_analysis_complete(context, timeout=ANALYSIS_TIMEOUT)
    if not ok or why != "progress_100":
        raise AssertionError(f"Progress did not reach 100% within {ANALYSIS_TIMEOUT}s. Last reason: {why}")


@then('I should be redirected to "{path}"')
def step_redirect_to(context, path):
    wait = WebDriverWait(context.driver, 60)
    try:
        wait.until(EC.url_contains(path))
    except TimeoutException:
        current_url = context.driver.current_url
        ss, ps, logs = _save_debug_artifacts(context, prefix="redirect_timeout")
        try:
            body_text = context.driver.find_element(By.TAG_NAME, "body").text[:2000]
        except Exception:
            body_text = "<could not retrieve body text>"
        raise AssertionError(
            f"Expected redirect to '{path}' but current URL is '{current_url}'. "
            f"Saved screenshot: {ss}, page snippet: {ps}, logs: {logs}. Body snippet: {body_text}"
        )


@then('I should remain on "{path}" page')
def step_remain_on_page(context, path):
    time.sleep(1)
    current_url = context.driver.current_url
    if path not in current_url:
        raise AssertionError(f"Expected to stay on '{path}', but at: {current_url}")


@then('I should see "{element_id}" element')
def step_see_element(context, element_id):
    element = find_element(context, element_id, "id")
    if not element.is_displayed():
        raise AssertionError(f"Element '{element_id}' exists but is not visible")


@then('I should see text "{text}"')
def step_see_text(context, text):
    wait = WebDriverWait(context.driver, 15)
    try:
        wait.until(EC.presence_of_element_located(
            (By.XPATH, f"//*[contains(text(), '{text}')]")
        ))
    except TimeoutException:
        body_text = context.driver.find_element(By.TAG_NAME, "body").text
        raise AssertionError(f"Text '{text}' not found on page. Page contains: {body_text[:1000]}")


@then('I should see error message "{message}"')
def step_see_error_message(context, message):
    time.sleep(0.5)
    error_el = find_element(context, "form-message", "id")
    
    # Check if error is visible
    classes = error_el.get_attribute("class") or ""
    if "hidden" in classes.lower():
        raise AssertionError(f"Error message element is hidden")
    
    actual_text = error_el.text.strip()
    if message not in actual_text:
        raise AssertionError(f"Expected error '{message}', got: '{actual_text}'")


@then('the displayed filename should be "{expected_text}"')
def step_check_displayed_filename(context, expected_text):
    time.sleep(0.5)
    filename_el = find_element(context, "display-filename", "id")
    actual_text = filename_el.text.strip()
    
    if actual_text != expected_text:
        raise AssertionError(f"Expected filename '{expected_text}', got: '{actual_text}'")


# ======================================================
# Cleanup
# ======================================================

def after_scenario(context, scenario):
    """Close browser after each scenario, tetapi simpan artifacts jika error."""
    if hasattr(context, 'driver'):
        # jika gagal simpan artifacts
        try:
            scenario_failed = getattr(scenario, "status", "").lower() == "failed"
        except Exception:
            scenario_failed = False

        if scenario_failed or getattr(context, "debug_keep_browser", False):
            ss, ps, logs = _save_debug_artifacts(context, prefix="after_scenario")
            print(f"Saved debug artifacts before quit: screenshot={ss}, page={ps}, logs={logs}")

        # akhirnya tutup driver kecuali sedang debug
        if not getattr(context, "debug_keep_browser", False):
            try:
                context.driver.quit()
            except Exception:
                pass