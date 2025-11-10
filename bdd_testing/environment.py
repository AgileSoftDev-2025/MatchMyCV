from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import os

CHROMEDRIVER_PATH = os.path.join(os.getcwd(), "chromedriver.exe")

def before_all(context):

    service = Service(CHROMEDRIVER_PATH)
    context.driver = webdriver.Chrome(service=service)
    context.driver.implicitly_wait(10) 
    context.driver.maximize_window()

def after_all(context):
    context.driver.quit()


def after_scenario(context, scenario):
    try:
        context.driver.quit()
    except Exception:
        pass
