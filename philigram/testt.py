from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

def setup_driver():
    options = Options()
    options.add_argument("--start-maximized")


    # ChromeDriver installé dans /usr/local/bin/
    service = Service("/usr/local/bin/chromedriver")

    driver = webdriver.Chrome(service=service, options=options)
    return driver
setup_driver()