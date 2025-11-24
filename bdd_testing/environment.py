"""
Behave environment configuration
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import os
import sys

# Path to chromedriver (adjust based on your structure)
CHROMEDRIVER_PATH = os.path.join(os.path.dirname(__file__), "..", "chromedriver.exe")

def before_all(context):
    """Setup browser before all tests"""
    try:
        print(f"\n{'='*60}")
        print("🚀 INITIALIZING BROWSER...")
        print(f"{'='*60}")
        
        # Verify chromedriver exists
        if not os.path.exists(CHROMEDRIVER_PATH):
            raise FileNotFoundError(
                f"❌ ChromeDriver not found at: {CHROMEDRIVER_PATH}\n"
                f"Current working directory: {os.getcwd()}\n"
                f"Please ensure chromedriver.exe is in the correct location."
            )
        
        print(f"✅ ChromeDriver found: {CHROMEDRIVER_PATH}")
        
        # Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # Uncomment for headless mode (faster but can't see browser)
        # chrome_options.add_argument('--headless')
        
        # Initialize driver
        service = Service(CHROMEDRIVER_PATH)
        context.driver = webdriver.Chrome(service=service, options=chrome_options)
        context.driver.implicitly_wait(10)
        context.driver.maximize_window()
        
        print(f"✅ Browser initialized successfully")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"❌ BROWSER INITIALIZATION FAILED!")
        print(f"{'='*60}")
        print(f"Error: {str(e)}")
        print(f"Error Type: {type(e).__name__}")
        print(f"\nTraceback:")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")
        
        # Fail fast - don't continue tests without browser
        sys.exit(1)


def after_scenario(context, scenario):
    """Cleanup after each scenario"""
    try:
        if hasattr(context, 'driver') and context.driver:
            # Take screenshot on failure
            if scenario.status == 'failed':
                screenshot_dir = os.path.join(os.getcwd(), 'screenshots')
                os.makedirs(screenshot_dir, exist_ok=True)
                
                screenshot_name = f"{scenario.name.replace(' ', '_')}.png"
                screenshot_path = os.path.join(screenshot_dir, screenshot_name)
                
                context.driver.save_screenshot(screenshot_path)
                print(f"\n📸 Screenshot saved: {screenshot_path}")
    except Exception as e:
        print(f"⚠️ Warning during scenario cleanup: {e}")


def after_all(context):
    """Cleanup after all tests"""
    try:
        if hasattr(context, 'driver') and context.driver:
            print(f"\n{'='*60}")
            print("🧹 CLOSING BROWSER...")
            print(f"{'='*60}\n")
            context.driver.quit()
            print("✅ Browser closed successfully\n")
    except Exception as e:
        print(f"⚠️ Warning during browser cleanup: {e}")