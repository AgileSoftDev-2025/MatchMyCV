from behave import given, when, then
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
import os

CHROMEDRIVER_PATH = os.path.join(os.getcwd(), "chromedriver.exe")
BASE_URL = "https://buildwithangga.com"  

def find_element_by_locator_name(context, name):
    wait = WebDriverWait(context.driver, 3) 
    
    try:
        selector = f"[data-testid='{name}']"
        return wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
    
    except TimeoutException:
        try:
            return wait.until(EC.visibility_of_element_located((By.ID, name)))
        
        except TimeoutException:
            try:
                selector = f".{name}" 
                return wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
            
            except TimeoutException:
                raise AssertionError(
                    f"Failed to find element '{name}'"
                )

def _scroll_into_view(driver, el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)

def _hover(driver, el):
    ActionChains(driver).move_to_element(el).pause(0.2).perform()


@given('I am on "{path}"')
def step_impl_visit_page(context, path):
    service = Service(CHROMEDRIVER_PATH)
    context.driver = webdriver.Chrome(service=service)
    url = BASE_URL + path
    context.driver.get(url)

@when('I press "{button_text}"')
def step_impl_press_button(context, button_text):
    wait = WebDriverWait(context.driver, 10)
    lowered = button_text.lower()

    # 1) Coba cari anchor dropdown “Alur Belajar” by ID (paling pasti)
    id_xpath = "//a[@id='listAlurBelajarDropdown' and contains(@class,'dropdown-toggle')]"

    # 2) Generic fallback: cari teks di button/a/input/span/div (case-insensitive)
    text_xpath = (
        "//*[(self::button or self::a or self::input or self::span or self::div)"
        f" and contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{lowered}')]"
    )

    try:
        try:
            el = wait.until(EC.visibility_of_element_located((By.XPATH, id_xpath)))
        except TimeoutException:
            el = wait.until(EC.visibility_of_element_located((By.XPATH, text_xpath)))

        _scroll_into_view(context.driver, el)

        # Navbar dropdown biasanya perlu hover dulu
        try:
            _hover(context.driver, el)
        except Exception:
            pass

        # Klik normal; kalau gagal, pakai JS click
        try:
            wait.until(EC.element_to_be_clickable((By.XPATH, "."))).click()
        except Exception:
            context.driver.execute_script("arguments[0].click();", el)

    except TimeoutException:
        raise AssertionError(f"Button or link with text '{button_text}' was not found or could not be clicked.")

@when('I follow "{link_text}"')
def step_impl_follow_link(context, link_text):
    wait = WebDriverWait(context.driver, 10)
    lowered = link_text.lower()
    xpath = (
        "//a[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),"
        f" '{lowered}')]"
    )
    el = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
    _scroll_into_view(context.driver, el)
    before = context.driver.current_window_handle
    try:
        el.click()
    except Exception:
        context.driver.execute_script("arguments[0].click();", el)

    WebDriverWait(context.driver, 10).until(lambda d: len(d.window_handles) >= 1)
    if len(context.driver.window_handles) > 1:
        for h in context.driver.window_handles:
            if h != before:
                context.driver.switch_to.window(h)
                break

@then('I should be on "{path}"')
def step_impl_check_url(context, path):
    wait = WebDriverWait(context.driver, 3)

    try:
        wait.until(EC.url_contains(path))
    except TimeoutException:
        current_url = context.driver.current_url
        raise AssertionError(f"Expected URL to contain '{path}', but was '{current_url}'.")

@then('I should see an "{element_name}" element')
def step_impl_see_element(context, element_name):
    try:
        element = find_element_by_locator_name(context, element_name)
        assert element.is_displayed(), f"Element '{element_name}' was found in the HTML but is not visible."
    except AssertionError as e:
        raise e