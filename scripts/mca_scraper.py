#!/usr/bin/env python3
"""
CSL Capital MCA Portfolio Scraper - Production Version
Works with separate capture_cookies.py script for cookie extraction
"""
import os
import time
import re
import logging
import pickle
import base64
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from contextlib import contextmanager
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    WebDriverException, 
    NoSuchElementException,
    StaleElementReferenceException
)
from supabase_client import get_supabase_client

@dataclass
class ScrapingConfig:
    """Configuration class for scraper settings"""
    headless: bool = True
    timeout: int = 15
    max_retries: int = 3
    retry_delay: int = 2
    page_load_timeout: int = 30
    implicit_wait: int = 10
    screenshot_on_error: bool = True
    save_html_on_error: bool = True

@dataclass
class Deal:
    """Data class for MCA deal information"""
    deal_id: str
    business_name: str
    amount: float
    status: str
    date_created: datetime
    last_updated: datetime
    # Add more fields as needed based on actual data structure

class CSLMCAScraper:
    def __init__(self, config: Optional[ScrapingConfig] = None):
        self.config = config or ScrapingConfig()
        self.setup_logging()
        self.supabase = get_supabase_client()
        self.driver = None
        self.deals: List[Deal] = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create necessary directories
        self.debug_dir = Path("debug")
        self.debug_dir.mkdir(exist_ok=True)

    def setup_logging(self):
        """Enhanced logging setup with file output"""
        Path("logs").mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(f'logs/mca_scraper_{datetime.now().strftime("%Y%m%d")}.log')
            ]
        )
        self.logger = logging.getLogger(__name__)

    @contextmanager
    def driver_context(self):
        """Context manager for proper driver lifecycle management"""
        try:
            self.setup_driver()
            yield self.driver
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    self.logger.info("🔐 Browser closed successfully")
                except Exception as e:
                    self.logger.warning(f"Error closing browser: {e}")

    def setup_driver(self):
        """Enhanced driver setup with better options"""
        options = Options()
        
        if self.config.headless:
            options.add_argument('--headless=new')
        
        # Enhanced Chrome options for better stability
        chrome_args = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor',
            '--window-size=1920,1080',
            '--disable-blink-features=AutomationControlled',
            '--disable-extensions',
            '--disable-plugins',
            '--disable-images',  # Faster loading
            '--disable-javascript-harmony-shipping',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        for arg in chrome_args:
            options.add_argument(arg)
        
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.notifications": 2,
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_settings.popups": 0
        })

        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(self.config.page_load_timeout)
            self.driver.implicitly_wait(self.config.implicit_wait)
            
            # Anti-detection script
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                window.chrome = {runtime: {}};
                Object.defineProperty(navigator, 'permissions', {
                    get: () => ({
                        query: () => Promise.resolve({state: 'granted'})
                    })
                });
            """)
            
            self.logger.info("✅ Chrome driver initialized successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Chrome driver: {e}")
            raise

    def load_cookies_from_secret(self) -> bool:
        """
        Load cookies from WORKFORCE_COOKIES_B64 environment variable
        This is the base64 encoded version of cookies.pkl from capture_cookies.py
        """
        try:
            # Get the base64 encoded cookies from GitHub Secret
            encoded_cookies = os.getenv('WORKFORCE_COOKIES_B64')
            if not encoded_cookies:
                self.logger.error("❌ WORKFORCE_COOKIES_B64 environment variable not found")
                return False
            
            # Decode and load cookies
            cookies_data = base64.b64decode(encoded_cookies.encode('utf-8'))
            cookies = pickle.loads(cookies_data)
            
            self.logger.info(f"✅ Loaded {len(cookies)} cookies from WORKFORCE_COOKIES_B64")
            
            # Navigate to domain first
            self.driver.get("https://1workforce.com/")
            time.sleep(2)
            
            # Apply cookies
            cookies_applied = 0
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                    cookies_applied += 1
                except Exception as e:
                    self.logger.warning(f"Could not apply cookie {cookie.get('name', 'unknown')}: {e}")
            
            self.logger.info(f"✅ Applied {cookies_applied}/{len(cookies)} cookies to browser")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to load cookies from secret: {e}")
            return False

    def verify_authentication(self) -> bool:
        """Verify that cookies provide valid authentication"""
        try:
            # Navigate to protected area
            self.logger.info("🔍 Verifying authentication by accessing protected page...")
            self.driver.get("https://1workforce.com/n/cashadvance/list")
            time.sleep(5)
            
            current_url = self.driver.current_url
            page_source = self.driver.page_source.lower()
            
            # Check authentication indicators
            auth_indicators = ['dashboard', 'portfolio', 'cashadvance', 'logout']
            is_authenticated = any(
                indicator in current_url.lower() or indicator in page_source 
                for indicator in auth_indicators
            )
            
            if is_authenticated:
                self.logger.info("✅ Authentication verified - cookies are working!")
                return True
            else:
                self.logger.error("❌ Authentication failed - cookies may have expired")
                self.logger.info(f"Current URL: {current_url}")
                
                # Save debug info
                self.save_debug_info("auth_failure")
                
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Authentication verification failed: {e}")
            self.save_debug_info("auth_error")
            return False

    def save_debug_info(self, prefix: str):
        """Save debug information for troubleshooting"""
        if not self.config.save_html_on_error and not self.config.screenshot_on_error:
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            if self.config.save_html_on_error:
                html_file = self.debug_dir / f"{prefix}_{self.session_id}_{timestamp}.html"
                with open(html_file, "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source or "Page source unavailable")
                self.logger.info(f"💾 Debug HTML saved: {html_file}")
            
            if self.config.screenshot_on_error:
                screenshot_file = self.debug_dir / f"{prefix}_{self.session_id}_{timestamp}.png"
                self.driver.save_screenshot(str(screenshot_file))
                self.logger.info(f"📷 Debug screenshot saved: {screenshot_file}")
                
        except Exception as e:
            self.logger.warning(f"Could not save debug info: {e}")

    def retry_on_failure(self, func, *args, **kwargs):
        """Retry decorator for failed operations"""
        for attempt in range(self.config.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    raise

    def accept_terms_if_prompted(self):
        """Accept terms of service if prompted"""
        try:
            wait = WebDriverWait(self.driver, 5)
            
            # Multiple selector strategies for terms checkbox
            checkbox_selectors = [
                "//label[contains(text(), 'agree')]/preceding-sibling::input[@type='checkbox']",
                "//input[@type='checkbox'][following-sibling::*[contains(text(), 'agree')]]",
                "//input[@type='checkbox'][contains(@class, 'terms')]"
            ]
            
            for selector in checkbox_selectors:
                try:
                    checkbox = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    if not checkbox.is_selected():
                        checkbox.click()
                        self.logger.info("✅ Terms checkbox clicked")
                    break
                except TimeoutException:
                    continue
            
            # Multiple selector strategies for submit button
            button_selectors = [
                "//button[contains(text(), 'Accept') or contains(text(), 'Continue') or contains(text(), 'Proceed')]",
                "//input[@type='submit'][contains(@value, 'Accept')]"
            ]
            
            for selector in button_selectors:
                try:
                    btn = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    btn.click()
                    self.logger.info("✅ Terms accepted successfully")
                    time.sleep(2)
                    return
                except TimeoutException:
                    continue
                    
        except Exception as e:
            self.logger.info(f"No terms prompt found or error accepting: {e}")

    def extract_deals_data(self) -> List[Deal]:
        """Extract MCA deals data from the portfolio page"""
        deals = []
        try:
            self.logger.info("📊 Starting data extraction...")
            
            # Navigate to deals page if not already there
            current_url = self.driver.current_url
            if "cashadvance/list" not in current_url:
                self.driver.get("https://1workforce.com/n/cashadvance/list")
                time.sleep(5)
            
            # Wait for table to load
            wait = WebDriverWait(self.driver, self.config.timeout)
            
            # Try to find the data table
            try:
                table = wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
                self.logger.info("✅ Found data table")
            except TimeoutException:
                self.logger.warning("⚠️ No table found - checking for alternative data structure")
                # You might need to adjust selectors based on actual page structure
            
            # Parse table data using BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # TODO: Implement actual data extraction based on table structure
            # This is a placeholder - you'll need to customize based on actual HTML structure
            """
            Example structure might be:
            table_rows = soup.find('table').find_all('tr')[1:]  # Skip header
            for row in table_rows:
                cells = row.find_all('td')
                if len(cells) >= 5:  # Adjust based on actual columns
                    deal = Deal(
                        deal_id=cells[0].text.strip(),
                        business_name=cells[1].text.strip(),
                        amount=float(cells[2].text.strip().replace('$', '').replace(',', '')),
                        status=cells[3].text.strip(),
                        date_created=datetime.fromisoformat(cells[4].text.strip()),
                        last_updated=datetime.now(timezone.utc)
                    )
                    deals.append(deal)
            """
            
            self.logger.info(f"✅ Extracted {len(deals)} deals")
            
        except Exception as e:
            self.logger.error(f"❌ Data extraction failed: {e}")
            self.save_debug_info("extraction_error")
            
        return deals

    def validate_deal_data(self, deal: Deal) -> bool:
        """Validate extracted deal data"""
        if not deal.deal_id or not deal.business_name:
            return False
        if deal.amount <= 0:
            return False
        return True

    def save_to_database(self, deals: List[Deal]):
        """Save deals to Supabase with error handling"""
        try:
            valid_deals = [deal for deal in deals if self.validate_deal_data(deal)]
            
            if not valid_deals:
                self.logger.warning("⚠️ No valid deals to save")
                return
            
            # Convert to dict format for Supabase
            deals_data = [
                {
                    'deal_id': deal.deal_id,
                    'business_name': deal.business_name,
                    'amount': deal.amount,
                    'status': deal.status,
                    'date_created': deal.date_created.isoformat(),
                    'last_updated': deal.last_updated.isoformat(),
                    'extracted_at': datetime.now(timezone.utc).isoformat()
                }
                for deal in valid_deals
            ]
            
            # Upsert to database
            result = self.supabase.table('mca_deals').upsert(deals_data).execute()
            
            if result.data:
                self.logger.info(f"✅ Successfully saved {len(valid_deals)} deals to database")
            else:
                self.logger.error("❌ Database save failed - no data returned")
                
        except Exception as e:
            self.logger.error(f"❌ Database save failed: {e}")
            raise

    def run_daily_extraction(self):
        """Main extraction workflow using cookies from capture_cookies.py"""
        try:
            self.logger.info("🚀 Starting CSL Capital MCA portfolio extraction...")
            
            with self.driver_context():
                # Load cookies from GitHub Secret
                if not self.load_cookies_from_secret():
                    raise Exception("❌ Failed to load cookies from WORKFORCE_COOKIES_B64")

                # Verify authentication works
                if not self.verify_authentication():
                    raise Exception("❌ Cookie authentication failed - cookies may have expired")

                # Accept terms if prompted
                self.accept_terms_if_prompted()
                
                # Extract deals data
                deals = self.extract_deals_data()
                
                if deals:
                    # Save to database
                    self.save_to_database(deals)
                    self.logger.info(f"✅ Successfully processed {len(deals)} deals")
                else:
                    self.logger.warning("⚠️ No deals extracted - check if data structure has changed")

        except Exception as e:
            self.logger.error(f"❌ MCA extraction failed: {e}")
            raise

def main():
    """Main entry point with configuration options"""
    # Allow configuration via environment variables
    config = ScrapingConfig(
        headless=os.getenv('SCRAPER_HEADLESS', 'true').lower() == 'true',
        timeout=int(os.getenv('SCRAPER_TIMEOUT', '15')),
        max_retries=int(os.getenv('SCRAPER_MAX_RETRIES', '3')),
        screenshot_on_error=os.getenv('SCRAPER_SCREENSHOT_ON_ERROR', 'true').lower() == 'true'
    )
    
    scraper = CSLMCAScraper(config)
    try:
        scraper.run_daily_extraction()
        print("✅ MCA extraction completed successfully")
    except Exception as e:
        print(f"❌ MCA extraction failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
