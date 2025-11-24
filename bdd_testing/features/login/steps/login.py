# features/login/steps/login.py
from behave import given, when, then
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from urllib.parse import urljoin
import os

# --- Konfigurasi ---
CHROMEDRIVER_PATH = os.path.join(os.getcwd(), "chromedriver.exe")
BASE_URL = "http://127.0.0.1:8000/"

# Mapping label -> data-testid di template
LABEL_TO_TESTID = {
    "Email": "email-input",
    "Password": "password-input",
}

def build_url(path: str) -> str:
    """Gabungkan BASE_URL dan path dengan rapi."""
    return urljoin(BASE_URL, path.lstrip("/"))

def find_element_by_locator_name(context, name):
    """Cari elemen dengan prioritas: data-testid -> id -> className."""
    wait = WebDriverWait(context.driver, 6)

    # 1) data-testid
    try:
        selector = f"[data-testid='{name}']"
        return wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
    except TimeoutException:
        pass

    # 2) id
    try:
        return wait.until(EC.visibility_of_element_located((By.ID, name)))
    except TimeoutException:
        pass

    # 3) className
    try:
        selector = f".{name}"
        return wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
    except TimeoutException:
        raise AssertionError(f"Failed to find element '{name}' by data-testid, id, or class")

def _scroll_into_view(driver, el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)

def _hover(driver, el):
    ActionChains(driver).move_to_element(el).pause(0.2).perform()

# =========================
# Step Definitions
# =========================

@given('I am on the "{path}" page')
def step_go_to_page(context, path):
    # Start 1 browser per scenario
    service = Service(CHROMEDRIVER_PATH)
    context.driver = webdriver.Chrome(service=service)
    context.driver.get(build_url(path))

@given('I am on "{path}"')
def step_go_to_page_alt(context, path):
    service = Service(CHROMEDRIVER_PATH)
    context.driver = webdriver.Chrome(service=service)
    context.driver.get(build_url(path))

@given('I fill in "{label}" with "{value}"')
def step_fill_input_by_label(context, label, value):
    testid = LABEL_TO_TESTID.get(label.strip())
    if not testid:
        raise AssertionError(f'No testid mapping for label "{label}". Add it to LABEL_TO_TESTID.')
    el = find_element_by_locator_name(context, testid)
    el.clear()
    if value is not None:
        el.send_keys(value)

# Handler khusus untuk literal kosong "" (mengatasi Undefined)
@given('I fill in "{label}" with ""')
def step_fill_input_empty(context, label):
    return step_fill_input_by_label(context, label, "")

@when('I press "Login"')
def step_press_login(context):
    wait = WebDriverWait(context.driver, 10)
    try:
        el = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='login-button']")))
    except TimeoutException:
        # fallback by visible text "Login"
        xpath = (
            "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'login') or "
            "self::a[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'login')]]"
        )
        el = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
    _scroll_into_view(context.driver, el)
    try:
        el.click()
    except Exception:
        context.driver.execute_script("arguments[0].click();", el)

@when('I press "{button_text}"')
def step_press_generic(context, button_text):
    lowered = button_text.strip().lower()
    if lowered == "login":
        return step_press_login(context)

    wait = WebDriverWait(context.driver, 10)
    xpath = (
        "//*[(self::button or self::a or self::input or self::span or self::div)"
        f" and contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{lowered}')]"
    )
    try:
        el = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
    except TimeoutException:
        raise AssertionError(f"Button or link with text '{button_text}' was not found or could not be clicked.")
    _scroll_into_view(context.driver, el)
    try:
        el.click()
    except Exception:
        context.driver.execute_script("arguments[0].click();", el)

@then('I should be redirected to "{path}"')
def step_redirected_to(context, path):
    expected = build_url(path)
    WebDriverWait(context.driver, 8).until(EC.url_to_be(expected))

@then('I should be on "{path}"')
def step_url_contains(context, path):
    wait = WebDriverWait(context.driver, 6)
    try:
        wait.until(EC.url_contains(path))
    except TimeoutException:
        current = context.driver.current_url
        raise AssertionError(f"Expected URL to contain '{path}', but was '{current}'.")

@then('I should remain on the "{path}" page')
def step_remain_on(context, path):
    # Lebih toleran (menghindari timeout saat ada trailing slash/prefix berbeda)
    wait = WebDriverWait(context.driver, 6)
    try:
        wait.until(EC.url_contains(path))
    except TimeoutException:
        current = context.driver.current_url
        raise AssertionError(f"Expected URL to contain '{path}', but was '{current}'.")

@then('I should see the message "{msg}"')
def step_see_message(context, msg):
    wait = WebDriverWait(context.driver, 8)

    # Pastikan kontainer flash ada di DOM (sebaiknya dipasang global di base.html)
    # Coba by ID lebih dulu:
    try:
        wait.until(EC.presence_of_element_located((By.ID, "flash-messages")))
    except TimeoutException:
        # Fallback ke data-testid (kalau di-include dengan data-testid)
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='flash-messages']")))
        except TimeoutException:
            raise AssertionError(
                "Flash messages container not found. "
                "Pastikan blok #flash-messages dirender global (mis. di base.html)."
            )

    # Ambil semua teks pesan
    texts = [el.text.strip()
             for el in context.driver.find_elements(By.CSS_SELECTOR, "#flash-messages .flash-message-text")]
    if not texts:
        # Bisa jadi pesan hanya berupa toast JS; tapi untuk BDD kita butuh fallback DOM
        raise AssertionError("No flash messages found in DOM under #flash-messages. Ensure messages are rendered to HTML.")

    if not any(msg in t for t in texts):
        raise AssertionError(f'Expected message "{msg}" not found. Got: {texts}')
