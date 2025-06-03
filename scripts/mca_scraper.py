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
    """Data class for MCA deal information - matches actual HTML structure"""
    deal_id: str                    # e.g., "MCA_19911" or "LOAN_19905"
    dba: str                        # DBA name from HTML
    owner: str                      # Business owner name
    deal_type: str                  # MCA, LOAN, MORTGAGE
    funding_type: str               # Funding Type from HTML
    funding_date: Optional[datetime] = None  # Funding Date
    purchase_price: float = 0.0     # Purchase Price (for MCAs)
    principal_amount: float = 0.0   # Principal Amount (for LOANs)
    receivables_purchased_amount: float = 0.0  # Receivables Purchased Amount
    current_balance: float = 0.0    # RTR Balance or Current Balance
    status: str = ""                # Performing, NSF, Canceled, etc.
    next_payment_due: Optional[datetime] = None  # Next Payment Due Date
    performance_ratio: str = ""     # Performance Ratio percentage
    mca_app_date: Optional[datetime] = None  # MCA App Date
    nature_of_business: str = ""    # Nature of Business
    monthly_cc_processing: float = 0.0  # Monthly CC Processing
    monthly_bank_deposits: float = 0.0   # Monthly Bank Deposits
    avg_daily_bank_bal: float = 0.0     # Avg Daily Bank Bal
    sales_rep: str = ""             # Sales Rep
    sos_status: str = ""            # SOS Status
    google_score: str = ""          # Google Score
    twitter_score: str = ""         # Twitter Score
    years_in_business: int = 0      # Years in business
    extracted_at: datetime = None   # When we extracted this
    last_updated: datetime = None   # When we last updated this

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
            
            # Navigate to deals page with ALL parameter
            self.logger.info("🔍 Navigating to deals page with ALL parameter...")
            self.driver.get("https://1workforce.com/n/cashadvance/list?listId=ListControl_Cashadvance&perPage=ALL")
            
            # Wait longer for all deals to load
            self.logger.info("⏳ Waiting for all deals to load...")
            time.sleep(10)  # Increased wait time for all deals
            
            # Wait for deal cards to load
            wait = WebDriverWait(self.driver, self.config.timeout)
            
            try:
                # Wait for the first deal card to appear
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "app-card")))
                self.logger.info("✅ Found deal cards")
            except TimeoutException:
                self.logger.warning("⚠️ No deal cards found")
                return deals
            
            # Check if we can find the paginator to see total count
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            paginator = soup.find('span', string=lambda text: text and '(' in text and 'of' in text)
            if paginator:
                self.logger.info(f"📋 Paginator info: {paginator.text.strip()}")
            
            # Find all deal cards
            deal_cards = soup.find_all('div', class_='app-card')
            self.logger.info(f"Found {len(deal_cards)} deal cards")
            
            # If we only got 25 cards, try clicking "All" button
            if len(deal_cards) == 25:
                self.logger.info("🔄 Only found 25 cards, looking for 'All' button...")
                try:
                    # Look for "All" button in paginator
                    all_button = self.driver.find_element(By.XPATH, "//span[contains(@class, 'pgn-btn') and contains(text(), 'All')]")
                    if all_button:
                        self.logger.info("🔘 Found 'All' button, clicking...")
                        all_button.click()
                        time.sleep(10)  # Wait for page to reload with all deals
                        
                        # Re-parse the page
                        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                        deal_cards = soup.find_all('div', class_='app-card')
                        self.logger.info(f"After clicking 'All': Found {len(deal_cards)} deal cards")
                except Exception as e:
                    self.logger.warning(f"Could not click 'All' button: {e}")
            
            for card in deal_cards:
                try:
                    # Extract deal ID and type from the customer link
                    customer_span = card.find('span', class_='customer')
                    if not customer_span:
                        continue
                        
                    customer_link = customer_span.find('a')
                    if not customer_link:
                        continue
                        
                    deal_text = customer_link.text.strip()
                    # Extract deal ID from text like "MCA # 19911" or "LOAN # 19905"
                    deal_parts = deal_text.split(' # ')
                    if len(deal_parts) != 2:
                        continue
                        
                    deal_type = deal_parts[0].strip()
                    deal_id = deal_parts[1].strip()
                    
                    # Extract business information from left column
                    left_col = card.find('div', class_='col-md-6')
                    if not left_col:
                        continue
                    
                    # Extract right column for status and other info
                    right_col = card.find('div', class_='col-md-6 right')
                    
                    # Extract DBA (business name)
                    dba_text = ""
                    for b_tag in left_col.find_all('b'):
                        if b_tag.text.strip() == "DBA:":
                            dba_text = b_tag.next_sibling
                            if dba_text:
                                dba_text = dba_text.strip()
                            break
                    
                    # Extract owner
                    owner_text = ""
                    for b_tag in left_col.find_all('b'):
                        if b_tag.text.strip() == "Owner:":
                            owner_text = b_tag.next_sibling
                            if owner_text:
                                owner_text = owner_text.strip()
                            break
                    
                    # Extract funding date
                    funding_date = None
                    for b_tag in left_col.find_all('b'):
                        if b_tag.text.strip() == "Funding Date:":
                            date_text = b_tag.next_sibling
                            if date_text:
                                try:
                                    funding_date = datetime.strptime(date_text.strip(), "%m/%d/%Y")
                                except ValueError:
                                    pass
                            break
                    
                    # Extract Purchase Price (for MCAs)
                    purchase_price = 0.0
                    for b_tag in left_col.find_all('b'):
                        if b_tag.text.strip() == "Purchase Price:":
                            amount_text = b_tag.next_sibling
                            if amount_text:
                                try:
                                    purchase_price = float(amount_text.strip().replace(',', ''))
                                except ValueError:
                                    pass
                            break
                    
                    # Extract Principal Amount (for LOANs)
                    principal_amount = 0.0
                    for b_tag in left_col.find_all('b'):
                        if b_tag.text.strip() == "Principal Amount:":
                            amount_text = b_tag.next_sibling
                            if amount_text:
                                try:
                                    principal_amount = float(amount_text.strip().replace(',', ''))
                                except ValueError:
                                    pass
                            break
                    
                    # Extract Receivables Purchased Amount
                    receivables_purchased_amount = 0.0
                    for b_tag in left_col.find_all('b'):
                        if b_tag.text.strip() == "Receivables Purchased Amount:":
                            amount_text = b_tag.next_sibling
                            if amount_text:
                                try:
                                    # Extract just the number part before parentheses
                                    amount_str = amount_text.strip().split('(')[0].replace(',', '')
                                    receivables_purchased_amount = float(amount_str)
                                except (ValueError, IndexError):
                                    pass
                            break
                    
                    # Extract status from right column
                    status = ""
                    if right_col:
                        status_div = right_col.find('div', class_='text-info')
                        if status_div:
                            status_b = status_div.find('b')
                            if status_b:
                                status = status_b.get_text(strip=True)
                    
                    # Extract current balance (RTR Balance or Current Balance)
                    current_balance = 0.0
                    balance_fields = ["Current Balance:", "RTR Balance:"]
                    for field in balance_fields:
                        for b_tag in left_col.find_all('b'):
                            if b_tag.text.strip() == field:
                                balance_text = b_tag.next_sibling
                                if balance_text:
                                    try:
                                        # Extract just the number part before parentheses
                                        balance_str = balance_text.strip().split('(')[0].replace(',', '')
                                        current_balance = float(balance_str)
                                    except (ValueError, IndexError):
                                        pass
                                break
                        if current_balance > 0:
                            break
                    
                    # Extract MCA App Date
                    mca_app_date = None
                    if right_col:
                        for b_tag in right_col.find_all('b'):
                            if "MCA App Date" in b_tag.get_text():
                                parent_row = b_tag.find_parent('div', class_='row')
                                if parent_row:
                                    date_col = parent_row.find('div', class_='col-md-7')
                                    if date_col and date_col.find('b'):
                                        date_text = date_col.find('b').text.strip()
                                        try:
                                            mca_app_date = datetime.strptime(date_text, "%Y-%m-%d %H:%M:%S")
                                        except ValueError:
                                            pass
                                break
                    
                    # Extract funding type
                    funding_type = ""
                    for b_tag in left_col.find_all('b'):
                        if b_tag.text.strip() == "Funding Type:":
                            funding_text = b_tag.next_sibling
                            if funding_text:
                                funding_type = funding_text.strip()
                            break
                    
                    # Extract sales rep from right column
                    sales_rep = ""
                    if right_col:
                        for b_tag in right_col.find_all('b'):
                            if b_tag.text.strip() == "Sales Rep:":
                                parent_row = b_tag.find_parent('div', class_='row')
                                if parent_row:
                                    rep_col = parent_row.find('div', class_='col-md-7')
                                    if rep_col and rep_col.find('b'):
                                        sales_rep = rep_col.find('b').text.strip()
                                break
                    
                    # Extract nature of business
                    nature_of_business = ""
                    if right_col:
                        for b_tag in right_col.find_all('b'):
                            if b_tag.text.strip() == "Nature of Business:":
                                parent_row = b_tag.find_parent('div', class_='row')
                                if parent_row:
                                    business_col = parent_row.find('div', class_='col-md-7')
                                    if business_col and business_col.find('b'):
                                        nature_of_business = business_col.find('b').text.strip()
                                break
                    
                    # Extract years in business
                    years_in_business = 0
                    if right_col:
                        for b_tag in right_col.find_all('b'):
                            if b_tag.text.strip() == "Years in business:":
                                parent_row = b_tag.find_parent('div', class_='row')
                                if parent_row:
                                    years_col = parent_row.find('div', class_='col-md-7')
                                    if years_col and years_col.find('b'):
                                        try:
                                            years_in_business = int(years_col.find('b').text.strip())
                                        except ValueError:
                                            pass
                                break
                    
                    # Extract performance ratio
                    performance_ratio = ""
                    for b_tag in left_col.find_all('b'):
                        if b_tag.text.strip() == "Performance Ratio:":
                            ratio_text = b_tag.next_sibling
                            if ratio_text:
                                performance_ratio = ratio_text.strip()
                            break
                    
                    # Extract next payment due date
                    next_payment_due = None
                    for b_tag in left_col.find_all('b'):
                        if b_tag.text.strip() == "Next Payment Due Date:":
                            date_text = b_tag.next_sibling
                            if date_text and date_text.strip():
                                try:
                                    next_payment_due = datetime.strptime(date_text.strip(), "%m/%d/%Y")
                                except ValueError:
                                    pass
                            break
                    
                    # Create Deal object with all extracted data
                    if deal_id and dba_text:  # Minimum required fields
                        deal = Deal(
                            deal_id=f"{deal_type}_{deal_id}",
                            dba=dba_text,
                            owner=owner_text,
                            deal_type=deal_type,
                            funding_type=funding_type,
                            funding_date=funding_date,
                            purchase_price=purchase_price,
                            principal_amount=principal_amount,
                            receivables_purchased_amount=receivables_purchased_amount,
                            current_balance=current_balance,
                            status=status,
                            next_payment_due=next_payment_due,
                            performance_ratio=performance_ratio,
                            mca_app_date=mca_app_date,
                            nature_of_business=nature_of_business,
                            sales_rep=sales_rep,
                            years_in_business=years_in_business,
                            extracted_at=datetime.now(timezone.utc),
                            last_updated=datetime.now(timezone.utc)
                        )
                        deals.append(deal)
                        
                        self.logger.debug(f"Extracted deal: {deal.deal_id} - {deal.business_name}")
                    
                except Exception as e:
                    self.logger.warning(f"Error parsing deal card: {e}")
                    continue
            
            self.logger.info(f"✅ Successfully extracted {len(deals)} deals")
            
        except Exception as e:
            self.logger.error(f"❌ Data extraction failed: {e}")
            self.save_debug_info("extraction_error")
            
        return deals

    def validate_deal_data(self, deal: Deal) -> bool:
        """Validate extracted deal data"""
        if not deal.deal_id or not deal.dba:
            return False
        if deal.purchase_price <= 0 and deal.principal_amount <= 0:
            return False
        return True

    def save_to_database(self, deals: List[Deal]):
        """Save deals to Supabase with error handling"""
        try:
            valid_deals = [deal for deal in deals if self.validate_deal_data(deal)]
            
            if not valid_deals:
                self.logger.warning("⚠️ No valid deals to save")
                return
            
            # Convert to dict format for Supabase - match exact schema
            deals_data = []
            for deal in valid_deals:
                deal_dict = {
                    'deal_id': deal.deal_id,
                    'dba': deal.dba,
                    'owner': deal.owner,
                    'deal_type': deal.deal_type,
                    'funding_type': deal.funding_type,
                    'funding_date': deal.funding_date.isoformat() if deal.funding_date else None,
                    'purchase_price': deal.purchase_price,
                    'principal_amount': deal.principal_amount,
                    'receivables_purchased_amount': deal.receivables_purchased_amount,
                    'current_balance': deal.current_balance,
                    'status': deal.status,
                    'next_payment_due': deal.next_payment_due.isoformat() if deal.next_payment_due else None,
                    'performance_ratio': deal.performance_ratio,
                    'mca_app_date': deal.mca_app_date.isoformat() if deal.mca_app_date else None,
                    'nature_of_business': deal.nature_of_business,
                    'monthly_cc_processing': deal.monthly_cc_processing,
                    'monthly_bank_deposits': deal.monthly_bank_deposits,
                    'avg_daily_bank_bal': deal.avg_daily_bank_bal,
                    'sales_rep': deal.sales_rep,
                    'sos_status': deal.sos_status,
                    'google_score': deal.google_score,
                    'twitter_score': deal.twitter_score,
                    'years_in_business': deal.years_in_business,
                    'extracted_at': datetime.now(timezone.utc).isoformat(),
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }
                deals_data.append(deal_dict)
            
            # Try to upsert to database
            try:
                result = self.supabase.table('mca_deals').upsert(
                    deals_data, 
                    on_conflict='deal_id'
                ).execute()
                
                if result.data:
                    self.logger.info(f"✅ Successfully saved {len(valid_deals)} deals to database")
                    
                    # Log summary by status
                    status_counts = {}
                    for deal in valid_deals:
                        status = deal.status or "Unknown"
                        status_counts[status] = status_counts.get(status, 0) + 1
                    
                    self.logger.info(f"📊 Status breakdown: {status_counts}")
                else:
                    self.logger.error("❌ Database save failed - no data returned")
            
            except Exception as db_error:
                self.logger.error(f"❌ Database upsert failed: {db_error}")
                self.logger.info("🔄 Trying simple insert instead...")
                
                # Try simple insert as fallback
                result = self.supabase.table('mca_deals').insert(deals_data).execute()
                if result.data:
                    self.logger.info(f"✅ Successfully inserted {len(valid_deals)} deals to database")
                else:
                    raise Exception("Both upsert and insert failed")
                
        except Exception as e:
            self.logger.error(f"❌ Database save failed: {e}")
            self.logger.info("💾 Saving deals data to local file as backup...")
            
            # Save to local file as backup
            backup_file = f"deals_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_file, 'w') as f:
                import json
                json.dump([{
                    'deal_id': deal.deal_id,
                    'business_name': deal.business_name,
                    'amount': deal.amount,
                    'status': deal.status,
                    'deal_type': deal.deal_type,
                    'owner': deal.owner
                } for deal in valid_deals], f, indent=2, default=str)
            self.logger.info(f"💾 Backup saved to {backup_file}")
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
