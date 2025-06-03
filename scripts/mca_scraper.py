#!/usr/bin/env python3
"""
CSL Capital MCA Portfolio Scraper - 1Workforce Specific Version
"""
import os
import time
import re
import logging
import pickle
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from supabase_client import get_supabase_client


class CSLMCAScraper:
    def __init__(self):
        self.setup_logging()
        self.supabase = get_supabase_client()
        self.driver = None
        self.deals = []

    def setup_logging(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

def setup_driver(self):
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.notifications": 2,
        "profile.managed_default_content_settings.images": 2
    })

    self.driver = webdriver.Chrome(options=options)
    self.driver.execute_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        window.chrome = {runtime: {}};
    """)
    self.logger.info("Chrome driver initialized")

    # ✅ Load cookies if present
    cookie_path = "scripts/cookies.pkl"
    if os.path.exists(cookie_path):
        self.driver.get("https://1workforce.com/")
        with open(cookie_path, "rb") as f:
            cookies = pickle.load(f)
        for cookie in cookies:
            self.driver.add_cookie(cookie)
        self.driver.get("https://1workforce.com/n/cashadvance/list")
        self.logger.info("✅ Loaded session cookies and navigated directly")

    def login(self, username, password):
        try:
            self.driver.get("https://1workforce.com/n/login")
            time.sleep(3)
            self.logger.info("Waiting for username field...")
    
            wait = WebDriverWait(self.driver, 15)
            user_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']")))
            user_field.click()
    
            pass_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            user_field.send_keys(username)
            pass_field.send_keys(password)
            pass_field.send_keys(Keys.RETURN)
            time.sleep(5)
    
            if any(x in self.driver.current_url for x in ["/dashboard", "/portfolio", "/cashadvance"]):
                with open("cookies.pkl", "wb") as f:
                    pickle.dump(self.driver.get_cookies(), f)
                return True
    
            return False
    
        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            try:
                with open("login_fail_dump.html", "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source or "Page source unavailable")
                self.driver.save_screenshot("login_fail.png")
                self.logger.info("Saved login_fail_dump.html and login_fail.png for debugging")
            except Exception as write_error:
                self.logger.warning(f"Could not save debug files: {write_error}")
            return False

    def accept_terms_if_prompted(self):
        try:
            wait = WebDriverWait(self.driver, 5)
            checkbox = wait.until(EC.element_to_be_clickable((By.XPATH, "//label[contains(text(), 'agree')]/preceding-sibling::input[@type='checkbox']")))
            checkbox.click()
            btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'Continue')]")))
            btn.click()
            self.logger.info("✅ Accepted terms of service")
        except TimeoutException:
            self.logger.info("No terms prompt found")

    def run_daily_extraction(self):
        username = os.getenv('WORKFORCE_USERNAME')
        password = os.getenv('WORKFORCE_PASSWORD')
        if not username or not password:
            raise ValueError("Missing credentials")

        try:
            self.logger.info("🚀 Starting CSL Capital MCA portfolio extraction...")
            self.setup_driver()

            if not self.login(username, password):
                raise Exception("Login failed")

            self.accept_terms_if_prompted()
            self.logger.info("✅ Ready to scrape after login and TOS")
            # TODO: Call scraping logic here once login is stable

        except Exception as e:
            self.logger.error(f"❌ MCA extraction failed: {e}")
            raise
        finally:
            if self.driver:
                self.driver.quit()
                self.logger.info("🔐 Browser closed")


def main():
    scraper = CSLMCAScraper()
    try:
        scraper.run_daily_extraction()
    except Exception as e:
        print(f"❌ MCA extraction failed: {e}")
        exit(1)


if __name__ == "__main__":
    main()
