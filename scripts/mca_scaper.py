#!/usr/bin/env python3
"""
CSL Capital MCA Portfolio Scraper
Scrapes 1Workforce portfolio data and saves to Supabase
"""

import os
import time
import logging
import re
from datetime import datetime, timezone
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
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
        """Setup Chrome driver for GitHub Actions"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.logger.info("Chrome driver initialized")

    def login(self, username, password):
        """Login to 1Workforce platform"""
        try:
            self.logger.info("Attempting to login to 1Workforce...")
            self.driver.get("https://1workforce.com/n/login")
            
            wait = WebDriverWait(self.driver, 20)
            
            # Wait for login form
            username_field = wait.until(EC.presence_of_element_located((By.NAME, "username")))
            password_field = self.driver.find_element(By.NAME, "password")
            
            username_field.clear()
            username_field.send_keys(username)
            password_field.clear()
            password_field.send_keys(password)
            
            # Submit form
            login_button = self.driver.find_element(By.CSS_SELECTOR, "input[type='submit'], button[type='submit']")
            login_button.click()
            
            # Wait for successful login redirect
            wait.until(EC.url_contains('/home'))
            self.logger.info("✅ Login successful!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Login failed: {str(e)}")
            return False

    def navigate_to_portfolio(self):
        """Navigate to portfolio page"""
        try:
            self.logger.info("Navigating to portfolio page...")
            self.driver.get("https://1workforce.com/n/cashadvance/list")
            
            wait = WebDriverWait(self.driver, 20)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "app-card")))
            
            self.logger.info("✅ Portfolio page loaded")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to navigate to portfolio: {str(e)}")
            return False

    def get_total_pages(self):
        """Get total number of pages to scrape"""
        try:
            pagination_elements = self.driver.find_elements(By.CLASS_NAME, "pgn-btn")
            for element in pagination_elements:
                text = element.text
                if "of" in text:
                    match = re.search(r'\(1 - \d+ of (\d+)\)', text)
                    if match:
                        total_deals = int(match.group(1))
                        deals_per_page = 53  # Adjust based on site settings
                        total_pages = (total_deals + deals_per_page - 1) // deals_per_page
                        self.logger.info(f"Found {total_deals} total deals across {total_pages} pages")
                        return total_pages
            return 1
        except Exception as e:
            self.logger.warning(f"Could not determine total pages: {str(e)}")
            return 1

    def extract_deals_from_page(self):
        """Extract deals from current page"""
        deals = []
        try:
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            deal_cards = soup.find_all('div', class_='app-card')
            
            for card in deal_cards:
                deal = self.extract_deal_from_card(card)
                if deal and deal.get('deal_id'):
                    deals.append(deal)
            
            self.logger.info(f"Extracted {len(deals)} deals from current page")
            return deals
            
        except Exception as e:
            self.logger.error(f"Error extracting deals: {str(e)}")
            return []

    def extract_deal_from_card(self, card):
        """Extract deal data from HTML card"""
        deal = {
            'extracted_at': datetime.now(timezone.utc).isoformat(),
            'page_url': self.driver.current_url
        }
        
        try:
            # Extract deal ID and type
            customer_link = card.find('span', class_='customer')
            if customer_link:
                link_element = customer_link.find('a')
                if link_element:
                    deal_text = link_element.get_text().strip()
                    deal['deal_id'] = deal_text
                    deal['detail_url'] = link_element.get('href', '')
                    
                    match = re.match(r'(MCA|LOAN|MORTGAGE)\s*#\s*(\d+)', deal_text)
                    if match:
                        deal['deal_type'] = match.group(1)
                        deal['deal_number'] = int(match.group(2))

            # Extract all fields from the card
            rows = card.find_all('div', class_='row')
            for row in rows:
                cells = row.find_all('div', class_=lambda x: x and 'col-md' in x)
                for cell in cells:
                    bold_elements = cell.find_all('b')
                    for bold in bold_elements:
                        label = bold.get_text().replace(':', '').strip()
                        value = self.extract_field_value(bold)
                        if label and value:
                            deal[self.normalize_field_name(label)] = value

            # Standardize fields for database
            self.standardize_deal_fields(deal)
            return deal
            
        except Exception as e:
            self.logger.warning(f"Error extracting deal: {str(e)}")
            return {}

    def extract_field_value(self, bold_element):
        """Extract value text following a bold label"""
        value = ''
        if bold_element.next_sibling:
            value = bold_element.next_sibling.strip() if isinstance(bold_element.next_sibling, str) else ''
        
        if not value and bold_element.parent:
            parent_text = bold_element.parent.get_text()
            value = parent_text.replace(bold_element.get_text(), '').strip()
        
        return value

    def normalize_field_name(self, name):
        """Normalize field names for database"""
        return re.sub(r'[^a-zA-Z0-9]', '_', name.lower())

    def standardize_deal_fields(self, deal):
        """Standardize and clean deal fields for database"""
        # Core text fields
        deal['dba'] = deal.get('dba', '')
        deal['owner'] = deal.get('owner', '')
        deal['funding_type'] = deal.get('funding_type', '')
        deal['funding_date'] = self.parse_date(deal.get('funding_date', ''))
        deal['status'] = deal.get('status', '')
        deal['sales_rep'] = deal.get('sales_rep', '')
        deal['nature_of_business'] = deal.get('nature_of_business', '')
        deal['performance_ratio'] = deal.get('performance_ratio', '')
        deal['next_payment_due_date'] = self.parse_date(deal.get('next_payment_due_date', ''))
        
        # Financial fields
        deal['purchase_price'] = self.parse_amount(deal.get('purchase_price') or deal.get('principal_amount'))
        deal['receivables_amount'] = self.parse_amount(deal.get('receivables_purchased_amount') or deal.get('repayment_amount'))
        deal['current_balance'] = self.parse_amount(deal.get('rtr_balance') or deal.get('current_balance'))
        deal['past_due_amount'] = self.parse_amount(deal.get('payment_amount_past_due'))
        
        # Numeric fields
        deal['years_in_business'] = self.parse_int(deal.get('years_in_business'))
        
        # Performance metrics - extract from performance text
        performance_text = deal.get('performance', '')
        if performance_text:
            payments_match = re.search(r'(\d+(?:\.\d+)?)\s*\(.*?\)\s*of\s*(\d+)', performance_text)
            if payments_match:
                deal['payments_made'] = float(payments_match.group(1))
                deal['total_payments_expected'] = int(payments_match.group(2))

    def parse_amount(self, amount_str):
        """Parse monetary amounts"""
        if not amount_str:
            return 0.0
        try:
            # Handle formats like "400,000.00", "$400,000.00", "400000 (1.30)"
            cleaned = re.sub(r'[^\d.]', '', str(amount_str))
            return float(cleaned) if cleaned else 0.0
        except:
            return 0.0

    def parse_int(self, int_str):
        """Parse integer values"""
        if not int_str:
            return 0
        try:
            return int(re.sub(r'[^\d]', '', str(int_str)))
        except:
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
        """Navigate to next page"""
        try:
            next_buttons = self.driver.find_elements(By.PARTIAL_LINK_TEXT, "Next")
            if next_buttons:
                next_button = next_buttons[0]
                if 'disabled' not in (next_button.get_attribute('class') or ''):
                    next_button.click()
                    time.sleep(3)  # Wait for page load
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Error navigating to next page: {str(e)}")
            return False

    def scrape_all_pages(self, max_pages=None):
        """Scrape all pages of portfolio"""
        all_deals = []
        total_pages = self.get_total_pages()
        
        if max_pages:
            total_pages = min(total_pages, max_pages)
        
        current_page = 1
        
        while current_page <= total_pages:
            self.logger.info(f"Scraping page {current_page} of {total_pages}")
            
            page_deals = self.extract_deals_from_page()
            all_deals.extend(page_deals)
            
            if current_page >= total_pages:
                break
                
            if not self.navigate_to_next_page():
                self.logger.warning("Could not navigate to next page, stopping")
                break
                
            current_page += 1
            time.sleep(2)  # Be respectful to the server
        
        self.deals = all_deals
        self.logger.info(f"Total deals extracted: {len(all_deals)}")
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
            self.logger.info(f"Created extraction run {run_id}")

            # Prepare deals for batch insert
            for deal in deals:
                deal['extraction_run_id'] = run_id
                # Remove any None values and ensure proper data types
                deal = {k: v for k, v in deal.items() if v is not None and v != ''}

            # Batch insert deals (Supabase handles this efficiently)
            batch_size = 100  # Insert in batches to avoid timeouts
            total_saved = 0
            
            for i in range(0, len(deals), batch_size):
                batch = deals[i:i + batch_size]
                result = self.supabase.table('mca_deals').insert(batch).execute()
                total_saved += len(result.data)
                self.logger.info(f"Saved batch {i//batch_size + 1}: {len(result.data)} deals")
            
            # Update run status to success
            self.supabase.table('mca_extraction_runs').update({
                'deals_saved': total_saved,
                'status': 'success'
            }).eq('id', run_id).execute()
            
            self.logger.info(f"✅ Successfully saved {total_saved} deals to Supabase")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error saving to Supabase: {str(e)}")
            
            # Update run status to failed
            if 'run_id' in locals():
                self.supabase.table('mca_extraction_runs').update({
                    'status': 'failed',
                    'error_message': str(e)
                }).eq('id', run_id).execute()
            
            return False

    def run_daily_extraction(self):
        """Main extraction process for GitHub Actions"""
        username = os.getenv('WORKFORCE_USERNAME')
        password = os.getenv('WORKFORCE_PASSWORD')
        
        if not username or not password:
            raise ValueError("WORKFORCE_USERNAME and WORKFORCE_PASSWORD environment variables are required")
        
        try:
            self.logger.info("🚀 Starting CSL Capital MCA portfolio extraction...")
            
            # Setup and login
            self.setup_driver()
            
            if not self.login(username, password):
                raise Exception("Login failed")
            
            if not self.navigate_to_portfolio():
                raise Exception("Failed to navigate to portfolio")
            
            # Extract all deals
            deals = self.scrape_all_pages()
            
            if not deals:
                raise Exception("No deals extracted")
            
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
                self.logger.info("Browser closed")

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
