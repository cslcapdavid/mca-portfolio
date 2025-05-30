#!/usr/bin/env python3
"""
CSL Capital MCA Portfolio Scraper - 1Workforce Specific Version
Optimized for the exact 1Workforce login form structure
"""

import os
import time
import logging
import re
from datetime import datetime, timezone
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, ElementNotInteractableException
from bs4 import BeautifulSoup
from supabase_client import get_supabase_client

class CSLMCAScraper:
    def __init__(self):
        self.setup_logging()
        self.supabase = get_supabase_client()
        self.driver = None
        self.deals = []
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def setup_driver(self):
        """Setup Chrome driver optimized for 1Workforce"""
        options = Options()
        
        # Basic headless options
        options.add_argument('--headless=new')  # Use new headless mode
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # Anti-detection options
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-extensions')
        options.add_argument('--no-first-run')
        options.add_argument('--disable-default-apps')
        options.add_argument('--disable-infobars')
        
        # Realistic user agent
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Remove automation indicators
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Preferences to avoid detection
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,
                "media_stream": 2,
            },
            "profile.managed_default_content_settings": {
                "images": 2  # Don't load images for faster loading
            }
        }
        options.add_experimental_option("prefs", prefs)
        
        self.driver = webdriver.Chrome(options=options)
        
        # Execute stealth scripts after driver creation
        self.driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            window.chrome = {runtime: {}};
        """)
        
        self.logger.info("Chrome driver initialized for 1Workforce")

    def login(self, username, password):
        """Login specifically optimized for 1Workforce form structure"""
        try:
            self.logger.info("Attempting to login to 1Workforce...")
            
            # Navigate to login page
            self.driver.get("https://1workforce.com/n/login")
            
            # Wait for page to fully load
            time.sleep(5)
            
            self.logger.info(f"Page loaded. Current URL: {self.driver.current_url}")
            self.logger.info(f"Page title: {self.driver.title}")
            
            # Wait for the login form to be present
            wait = WebDriverWait(self.driver, 20)
            
            # Look for the username field - based on the screenshot, it's likely an input field
            username_field = None
            username_selectors = [
                "input[placeholder*='User Name']",
                "input[placeholder*='Email']", 
                "input[type='text']",
                "input[name*='username']",
                "input[name*='email']",
                "input[id*='username']",
                "input[id*='email']"
            ]
            
            for selector in username_selectors:
                try:
                    username_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    self.logger.info(f"✅ Found username field with selector: {selector}")
                    break
                except TimeoutException:
                    self.logger.debug(f"❌ Username selector failed: {selector}")
                    continue
            
            if not username_field:
                # Try more generic approach
                try:
                    text_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
                    if text_inputs:
                        username_field = text_inputs[0]  # Take first text input
                        self.logger.info("✅ Found username field as first text input")
                except:
                    pass
            
            if not username_field:
                raise Exception("Could not locate username field")
            
            # Look for password field
            password_field = None
            password_selectors = [
                "input[type='password']",
                "input[name*='password']",
                "input[id*='password']"
            ]
            
            for selector in password_selectors:
                try:
                    password_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    self.logger.info(f"✅ Found password field with selector: {selector}")
                    break
                except:
                    self.logger.debug(f"❌ Password selector failed: {selector}")
                    continue
            
            if not password_field:
                raise Exception("Could not locate password field")
            
            # Clear and fill the fields with human-like typing
            self.logger.info("Filling in credentials...")
            
            # Clear and type username
            username_field.click()
            username_field.clear()
            time.sleep(0.5)
            
            # Type username character by character to simulate human typing
            for char in username:
                username_field.send_keys(char)
                time.sleep(0.1)
            
            time.sleep(1)
            
            # Clear and type password
            password_field.click()
            password_field.clear()
            time.sleep(0.5)
            
            # Type password character by character
            for char in password:
                password_field.send_keys(char)
                time.sleep(0.1)
            
            time.sleep(1)
            
            # Look for login button - from screenshot it appears to be a blue button with "Login" text
            login_button = None
            login_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:contains('Login')",
                ".btn:contains('Login')",
                "button.btn",
                "*[onclick*='login']",
                "*[onclick*='submit']"
            ]
            
            for selector in login_selectors:
                try:
                    if ":contains(" in selector:
                        # Use XPath for text-based selectors
                        xpath_selector = f"//button[contains(text(), 'Login')] | //input[@value='Login']"
                        login_button = self.driver.find_element(By.XPATH, xpath_selector)
                    else:
                        login_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    self.logger.info(f"✅ Found login button with selector: {selector}")
                    break
                except:
                    self.logger.debug(f"❌ Login button selector failed: {selector}")
                    continue
            
            # Submit the form
            if login_button:
                self.logger.info("Clicking login button...")
                login_button.click()
            else:
                self.logger.info("No login button found, trying Enter key...")
                password_field.send_keys(Keys.RETURN)
            
            # Wait for login to process
            time.sleep(5)
            
            # Check for successful login
            current_url = self.driver.current_url
            self.logger.info(f"After login attempt - URL: {current_url}")
            
            # Success indicators for 1Workforce
            if any(indicator in current_url.lower() for indicator in ['/home', '/dashboard', '/portfolio', '/cashadvance']):
                self.logger.info("✅ Login successful - redirected to authenticated page!")
                return True
            
            # Check if we're still on login page
            if '/login' in current_url.lower():
                # Look for error messages
                error_messages = []
                error_selectors = [
                    ".alert",
                    ".error",
                    ".alert-danger",
                    "*[class*='error']",
                    "*[class*='alert']"
                ]
                
                for selector in error_selectors:
                    try:
                        error_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in error_elements:
                            if element.text.strip():
                                error_messages.append(element.text.strip())
                    except:
                        continue
                
                error_msg = "; ".join(error_messages) if error_messages else "Still on login page"
                raise Exception(f"Login failed: {error_msg}")
            
            # Try waiting a bit more and check again
            time.sleep(3)
            current_url = self.driver.current_url
            if '/login' not in current_url.lower():
                self.logger.info("✅ Login successful after additional wait!")
                return True
            
            raise Exception("Login failed - remained on login page")
            
        except Exception as e:
            self.logger.error(f"❌ Login failed: {str(e)}")
            
            # Enhanced debugging
            try:
                self.logger.info(f"Final URL: {self.driver.current_url}")
                self.logger.info(f"Page title: {self.driver.title}")
                
                # Check for any visible text that might indicate the issue
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                if len(page_text) < 500:
                    self.logger.info(f"Page body text: {page_text}")
                else:
                    self.logger.info(f"Page body text (first 500 chars): {page_text[:500]}...")
                    
            except:
                self.logger.info("Could not get additional debug info")
            
            return False

    def navigate_to_portfolio(self):
        """Navigate to portfolio page"""
        try:
            self.logger.info("Navigating to portfolio page...")
            self.driver.get("https://1workforce.com/n/cashadvance/list")
            
            # Wait for portfolio page to load
            wait = WebDriverWait(self.driver, 20)
            
            # Check for portfolio page indicators
            portfolio_indicators = [
                ".app-card",
                ".panel-heading",
                "*[class*='portfolio']",
                "*[class*='cashadvance']"
            ]
            
            page_loaded = False
            for selector in portfolio_indicators:
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    page_loaded = True
                    self.logger.info(f"✅ Portfolio page loaded - found: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not page_loaded:
                # Check if we got redirected back to login
                if '/login' in self.driver.current_url:
                    raise Exception("Redirected to login page - session may have expired")
                else:
                    self.logger.warning("Portfolio indicators not found, but proceeding...")
            
            self.logger.info("✅ Portfolio page navigation completed")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to navigate to portfolio: {str(e)}")
            self.logger.info(f"Current URL: {self.driver.current_url}")
            return False

    def get_total_pages(self):
        """Get total number of pages to scrape"""
        try:
            # Look for pagination info - based on your HTML sample: "(1 - 53 of 53)"
            pagination_text = ""
            pagination_selectors = [
                ".pgn-btn",
                "*[class*='pagination']",
                "*[class*='pgn']"
            ]
            
            for selector in pagination_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip()
                        if "of" in text and "(" in text:
                            pagination_text = text
                            break
                    if pagination_text:
                        break
                except:
                    continue
            
            if pagination_text:
                # Extract total from "(1 - 53 of 53)" format
                match = re.search(r'\(1 - \d+ of (\d+)\)', pagination_text)
                if match:
                    total_deals = int(match.group(1))
                    deals_per_page = 53  # Based on your sample
                    total_pages = (total_deals + deals_per_page - 1) // deals_per_page
                    self.logger.info(f"Found {total_deals} total deals across {total_pages} pages")
                    return total_pages
            
            self.logger.info("Could not determine pagination, assuming single page")
            return 1
            
        except Exception as e:
            self.logger.warning(f"Error determining total pages: {str(e)}")
            return 1

    def extract_deals_from_page(self):
        """Extract deals from current page"""
        deals = []
        try:
            # Wait a moment for page to fully load
            time.sleep(2)
            
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Look for deal cards - based on your HTML: class="app-card"
            deal_cards = soup.find_all('div', class_='app-card')
            
            if not deal_cards:
                # Try alternative selectors
                deal_cards = soup.find_all('div', class_=lambda x: x and 'card' in x)
            
            self.logger.info(f"Found {len(deal_cards)} deal cards on page")
            
            for i, card in enumerate(deal_cards):
                try:
                    deal = self.extract_deal_from_card(card)
                    if deal and deal.get('deal_id'):
                        deals.append(deal)
                        self.logger.debug(f"Extracted deal {i+1}: {deal.get('deal_id')}")
                    else:
                        self.logger.debug(f"Skipped deal card {i+1} - no valid deal_id")
                except Exception as e:
                    self.logger.warning(f"Error extracting deal card {i+1}: {str(e)}")
                    continue
            
            self.logger.info(f"✅ Successfully extracted {len(deals)} deals from current page")
            return deals
            
        except Exception as e:
            self.logger.error(f"❌ Error extracting deals from page: {str(e)}")
            return []

    def extract_deal_from_card(self, card):
        """Extract deal data from HTML card - optimized for 1Workforce structure"""
        deal = {
            'extracted_at': datetime.now(timezone.utc).isoformat(),
            'page_url': self.driver.current_url
        }
        
        try:
            # Extract deal ID and type from customer link
            customer_link = card.find('span', class_='customer')
            if customer_link:
                link_element = customer_link.find('a')
                if link_element:
                    deal_text = link_element.get_text().strip()
                    deal['deal_id'] = deal_text
                    
                    # Extract deal type and number
                    match = re.match(r'(MCA|LOAN|MORTGAGE)\s*#\s*(\d+)', deal_text)
                    if match:
                        deal['deal_type'] = match.group(1)
                        deal['deal_number'] = int(match.group(2))
                    
                    # Get detail URL
                    href = link_element.get('href', '')
                    if href:
                        deal['detail_url'] = href if href.startswith('http') else f"https://1workforce.com{href}"

            # Extract all labeled fields from the card
            rows = card.find_all('div', class_='row')
            for row in rows:
                # Find all column divs
                cells = row.find_all('div', class_=lambda x: x and 'col-md' in x)
                for cell in cells:
                    # Look for bold labels followed by values
                    bold_elements = cell.find_all('b')
                    for bold in bold_elements:
                        label = bold.get_text().replace(':', '').strip()
                        value = self.extract_field_value(bold)
                        
                        if label and value:
                            # Normalize field name for database
                            field_name = self.normalize_field_name(label)
                            deal[field_name] = value

            # Standardize the extracted fields
            self.standardize_deal_fields(deal)
            
            return deal
            
        except Exception as e:
            self.logger.warning(f"Error extracting individual deal: {str(e)}")
            return {}

    def extract_field_value(self, bold_element):
        """Extract the value that follows a bold label"""
        value = ''
        
        # Try to get the next sibling text
        if bold_element.next_sibling:
            if isinstance(bold_element.next_sibling, str):
                value = bold_element.next_sibling.strip()
            else:
                value = bold_element.next_sibling.get_text().strip() if hasattr(bold_element.next_sibling, 'get_text') else ''
        
        # If no direct sibling, try parent text minus the label
        if not value and bold_element.parent:
            parent_text = bold_element.parent.get_text()
            label_text = bold_element.get_text()
            value = parent_text.replace(label_text, '').strip()
        
        return value

    def normalize_field_name(self, name):
        """Convert field names to database-friendly format"""
        # Convert to lowercase and replace non-alphanumeric with underscores
        normalized = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
        # Remove multiple consecutive underscores
        normalized = re.sub(r'_+', '_', normalized)
        # Remove leading/trailing underscores
        return normalized.strip('_')

    def standardize_deal_fields(self, deal):
        """Standardize field names and formats for database storage"""
        # Core text fields
        deal['dba'] = deal.get('dba', '')
        deal['owner'] = deal.get('owner', '')
        deal['funding_type'] = deal.get('funding_type', '')
        deal['status'] = deal.get('status', '')
        deal['sales_rep'] = deal.get('sales_rep', '')
        deal['nature_of_business'] = deal.get('nature_of_business', '')
        deal['performance_ratio'] = deal.get('performance_ratio', '')
        
        # Date fields
        deal['funding_date'] = self.parse_date(deal.get('funding_date', ''))
        deal['next_payment_due_date'] = self.parse_date(deal.get('next_payment_due_date', ''))
        
        # Financial fields - handle multiple possible field names
        deal['purchase_price'] = self.parse_amount(
            deal.get('purchase_price') or 
            deal.get('principal_amount') or
            deal.get('loan_amount')
        )
        
        deal['receivables_amount'] = self.parse_amount(
            deal.get('receivables_purchased_amount') or 
            deal.get('repayment_amount') or
            deal.get('total_amount')
        )
        
        deal['current_balance'] = self.parse_amount(
            deal.get('rtr_balance') or 
            deal.get('current_balance') or
            deal.get('remaining_balance')
        )
        
        deal['past_due_amount'] = self.parse_amount(
            deal.get('payment_amount_past_due') or
            deal.get('past_due_amount') or
            deal.get('overdue_amount')
        )
        
        # Numeric fields
        deal['years_in_business'] = self.parse_int(deal.get('years_in_business'))

    def parse_amount(self, amount_str):
        """Parse monetary amounts from various formats"""
        if not amount_str:
            return 0.0
        
        try:
            # Remove all non-digit characters except decimal points
            cleaned = re.sub(r'[^\d.]', '', str(amount_str))
            return float(cleaned) if cleaned else 0.0
        except (ValueError, TypeError):
            return 0.0

    def parse_int(self, int_str):
        """Parse integer values"""
        if not int_str:
            return 0
        
        try:
            # Extract only digits
            digits_only = re.sub(r'[^\d]', '', str(int_str))
            return int(digits_only) if digits_only else 0
        except (ValueError, TypeError):
            return 0

    def parse_date(self, date_str):
        """Parse date strings to ISO format"""
        if not date_str or date_str.strip() == '':
            return None
        
        try:
            from dateutil import parser
            parsed_date = parser.parse(date_str)
            return parsed_date.date().isoformat()
        except:
            return None

    def navigate_to_next_page(self):
        """Navigate to next page if available"""
        try:
            # Look for "Next" button or link
            next_selectors = [
                "a:contains('Next')",
                "*[class*='next']",
                "*[onclick*='next']"
            ]
            
            for selector in next_selectors:
                try:
                    if ":contains(" in selector:
                        next_button = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Next')]")
                    else:
                        next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    # Check if button is enabled
                    if 'disabled' not in (next_button.get_attribute('class') or ''):
                        self.logger.info("Navigating to next page...")
                        next_button.click()
                        time.sleep(3)  # Wait for page load
                        return True
                except:
                    continue
            
            self.logger.info("No next page available")
            return False
            
        except Exception as e:
            self.logger.error(f"Error navigating to next page: {str(e)}")
            return False

    def scrape_all_pages(self, max_pages=None):
        """Scrape all pages of the portfolio"""
        all_deals = []
        total_pages = self.get_total_pages()
        
        if max_pages:
            total_pages = min(total_pages, max_pages)
        
        current_page = 1
        
        while current_page <= total_pages:
            self.logger.info(f"📄 Scraping page {current_page} of {total_pages}")
            
            page_deals = self.extract_deals_from_page()
            all_deals.extend(page_deals)
            
            self.logger.info(f"Page {current_page}: Found {len(page_deals)} deals (Total: {len(all_deals)})")
            
            # Break if this is the last page
            if current_page >= total_pages:
                break
                
            # Try to navigate to next page
            if not self.navigate_to_next_page():
                self.logger.warning("Could not navigate to next page, stopping pagination")
                break
                
            current_page += 1
            time.sleep(2)  # Be respectful to the server
        
        self.deals = all_deals
        self.logger.info(f"🎉 Scraping completed! Total deals extracted: {len(all_deals)}")
        return all_deals

    def save_to_supabase(self, deals):
        """Save deals to Supabase database"""
        if not deals:
            self.logger.warning("No deals to save")
            return False

        try:
            # Create extraction run record
            run_data = {
                'extracted_at': datetime.now(timezone.utc).isoformat(),
                'total_deals': len(deals),
                'status': 'running'
            }
            
            run_result = self.supabase.table('mca_extraction_runs').insert(run_data).execute()
            run_id = run_result.data[0]['id']
            self.logger.info(f"📝 Created extraction run {run_id}")

            # Prepare deals for batch insert
            prepared_deals = []
            for deal in deals:
                deal['extraction_run_id'] = run_id
                # Remove any None values and ensure proper data types
                cleaned_deal = {k: v for k, v in deal.items() if v is not None and v != ''}
                prepared_deals.append(cleaned_deal)

            # Batch insert deals
            batch_size = 50  # Smaller batches for reliability
            total_saved = 0
            
            for i in range(0, len(prepared_deals), batch_size):
                batch = prepared_deals[i:i + batch_size]
                try:
                    result = self.supabase.table('mca_deals').insert(batch).execute()
                    total_saved += len(result.data)
                    self.logger.info(f"💾 Saved batch {i//batch_size + 1}: {len(result.data)} deals")
                except Exception as batch_error:
                    self.logger.error(f"❌ Error saving batch {i//batch_size + 1}: {str(batch_error)}")
                    # Continue with next batch
                    continue
            
            # Update run status
            self.supabase.table('mca_extraction_runs').update({
                'deals_saved': total_saved,
                'status': 'success' if total_saved > 0 else 'partial_success'
            }).eq('id', run_id).execute()
            
            self.logger.info(f"✅ Successfully saved {total_saved} deals to Supabase")
            return total_saved > 0
            
        except Exception as e:
            self.logger.error(f"❌ Error saving to Supabase: {str(e)}")
            
            # Update run status to failed
            if 'run_id' in locals():
                try:
                    self.supabase.table('mca_extraction_runs').update({
                        'status': 'failed',
                        'error_message': str(e)
                    }).eq('id', run_id).execute()
                except:
                    pass  # Don't let logging failure stop the process
            
            return False

    def run_daily_extraction(self):
        """Main extraction process for GitHub Actions"""
        username = os.getenv('WORKFORCE_USERNAME')
        password = os.getenv('WORKFORCE_PASSWORD')
        
        if not username or not password:
            raise ValueError("WORKFORCE_USERNAME and WORKFORCE_PASSWORD environment variables are required")
        
        try:
            self.logger.info("🚀 Starting CSL Capital MCA portfolio extraction...")
            
            # Setup driver
            self.setup_driver()
            
            # Login
            if not self.login(username, password):
                raise Exception("Login failed")
            
            # Navigate to portfolio
            if not self.navigate_to_portfolio():
                raise Exception("Failed to navigate to portfolio")
            
            # Extract all deals
            deals = self.scrape_all_pages()
            
            if not deals:
                self.logger.warning("⚠️  No deals extracted - this might indicate an issue")
                # Don't fail completely, as this might be expected sometimes
                return True
            
            # Save to Supabase
            if self.save_to_supabase(deals):
                self.logger.info("✅ MCA portfolio extraction completed successfully")
                return True
            else:
                raise Exception("Failed to save data to Supabase")
                
        except Exception as e:
            self.logger.error(f"❌ MCA extraction failed: {str(e)}")
            raise
        finally:
            if self.driver:
                self.driver.quit()
                self.logger.info("🔐 Browser closed")

    def close(self):
        """Cleanup resources"""
        if self.driver:
            self.driver.quit()


def main():
    """Main function for GitHub Actions"""
    scraper = CSLMCAScraper()
    
    try:
        scraper.run_daily_extraction()
        print("✅ CSL Capital MCA data extraction completed successfully")
    except Exception as e:
        print(f"❌ MCA extraction failed: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()
