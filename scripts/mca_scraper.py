#!/usr/bin/env python3
"""
Step-by-Step Cookie Extraction System for GitHub Actions
Run this locally to extract cookies, then upload to GitHub Secrets
"""

import os
import time
import json
import base64
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class CookieExtractor:
    """Extract and save cookies as cookies.pkl for manual base64 encoding"""
    
    def __init__(self):
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """Setup Chrome driver for manual login"""
        options = Options()
        # DON'T use headless for manual login
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        self.driver = webdriver.Chrome(options=options)
        print("✅ Chrome browser opened")
    
    def manual_login_and_extract(self):
        """
        Step 1: Manual login with 2FA, then extract cookies
        """
        print("🔑 Manual Login Process")
        print("=" * 50)
        
        try:
            # Navigate to login page
            self.driver.get("https://1workforce.com/n/login")
            print("📍 Navigated to login page")
            
            # Wait for user to manually complete login
            print("\n🚨 MANUAL ACTION REQUIRED:")
            print("1. Complete login in the browser window")
            print("2. Complete 2FA if prompted")
            print("3. Navigate to any authenticated page")
            print("4. Press ENTER here when you see the dashboard/portfolio")
            
            input("Press ENTER when you're fully logged in...")
            
            # Verify login success
            current_url = self.driver.current_url
            if any(indicator in current_url.lower() for indicator in ['dashboard', 'portfolio', 'cashadvance']):
                print(f"✅ Login verified! Current URL: {current_url}")
            else:
                print(f"⚠️ Warning: URL doesn't look authenticated: {current_url}")
                proceed = input("Continue anyway? (y/n): ")
                if proceed.lower() != 'y':
                    return None
            
            # Extract cookies
            cookies = self.driver.get_cookies()
            print(f"📥 Extracted {len(cookies)} cookies")
            
            return cookies
            
        except Exception as e:
            print(f"❌ Error during manual login: {e}")
            return None
    
    def save_cookies_as_pkl(self, cookies):
        """
        Step 2: Save cookies as cookies.pkl for manual base64 encoding
        """
        print("\n💾 Saving Cookies as cookies.pkl")
        print("=" * 50)
        
        try:
            # Save cookies as pickle file
            with open("cookies.pkl", 'wb') as f:
                pickle.dump(cookies, f)
            print(f"✅ Saved cookies.pkl with {len(cookies)} cookies")
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving cookies: {e}")
            return False
    
    def test_cookies_locally(self, cookies):
        """
        Step 3: Test cookies work locally
        """
        print("\n🧪 Testing Cookies Locally")
        print("=" * 50)
        
        try:
            # Open new browser instance
            test_driver = webdriver.Chrome(options=Options())
            
            # Navigate to site
            test_driver.get("https://1workforce.com/")
            time.sleep(2)
            
            # Load cookies
            for cookie in cookies:
                try:
                    test_driver.add_cookie(cookie)
                except Exception as e:
                    print(f"⚠️ Could not add cookie {cookie.get('name')}: {e}")
            
            # Navigate to protected page
            test_driver.get("https://1workforce.com/n/cashadvance/list")
            time.sleep(5)
            
            # Check if we're logged in
            current_url = test_driver.current_url
            page_source = test_driver.page_source.lower()
            
            if any(indicator in current_url.lower() or indicator in page_source for indicator in ['dashboard', 'portfolio', 'cashadvance', 'logout']):
                print("✅ Cookie test PASSED - Successfully logged in!")
                success = True
            else:
                print("❌ Cookie test FAILED - Not authenticated")
                print(f"Current URL: {current_url}")
                success = False
            
            test_driver.quit()
            return success
            
        except Exception as e:
            print(f"❌ Error testing cookies: {e}")
            return False
    
    def run_extraction_process(self):
        """
        Complete extraction workflow
        """
        print("🚀 STARTING COOKIE EXTRACTION PROCESS")
        print("=" * 60)
        
        try:
            # Step 1: Manual login and extract
            cookies = self.manual_login_and_extract()
            if not cookies:
                print("❌ Failed to extract cookies")
                return False
            
            # Step 2: Save cookies as pkl
            if not self.save_cookies_as_pkl(cookies):
                print("❌ Failed to save cookies")
                return False
            
            # Step 3: Test cookies
            if self.test_cookies_locally(cookies):
                print("\n🎉 SUCCESS! Cookies extracted and tested successfully")
                print("\n📋 NEXT STEPS:")
                print("1. Run in terminal: base64 -i cookies.pkl -o cookies.b64")
                print("2. Copy contents of cookies.b64")
                print("3. Go to your GitHub repository")
                print("4. Settings → Secrets and variables → Actions")
                print("5. Add new secret: WORKFORCE_COOKIES_B64")
                print("6. Paste the base64 content")
                return True
            else:
                print("\n❌ Cookie test failed - extraction may not have worked")
                return False
                
        except Exception as e:
            print(f"❌ Extraction process failed: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
                print("🔐 Browser closed")


class ProductionScraper:
    """
    Modified scraper that uses WORKFORCE_COOKIES_B64 secret
    This is what runs in GitHub Actions
    """
    
    def __init__(self):
        self.driver = None
        self.cookies = None
    
    def setup_driver(self):
        """Setup headless driver for production"""
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        self.driver = webdriver.Chrome(options=options)
        print("✅ Production driver initialized")
    
    def load_session_from_secret(self):
        """
        Load cookies from WORKFORCE_COOKIES_B64 GitHub Secret
        """
        try:
            # Get the base64 encoded cookies from environment
            encoded_cookies = os.getenv('WORKFORCE_COOKIES_B64')
            if not encoded_cookies:
                raise ValueError("WORKFORCE_COOKIES_B64 secret not found")
            
            # Decode and load cookies
            cookies_data = base64.b64decode(encoded_cookies.encode('utf-8'))
            self.cookies = pickle.loads(cookies_data)
            
            print(f"✅ Loaded cookies from WORKFORCE_COOKIES_B64 secret")
            print(f"   - Cookies count: {len(self.cookies)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to load cookies from secret: {e}")
            return False
    
    def apply_session_to_driver(self):
        """
        Apply loaded cookies to driver
        """
        try:
            if not self.cookies:
                return False
            
            # Navigate to domain first
            self.driver.get("https://1workforce.com/")
            time.sleep(2)
            
            # Apply cookies
            cookies_applied = 0
            for cookie in self.cookies:
                try:
                    self.driver.add_cookie(cookie)
                    cookies_applied += 1
                except Exception as e:
                    print(f"⚠️ Could not apply cookie {cookie.get('name')}: {e}")
            
            print(f"✅ Applied {cookies_applied} cookies")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to apply cookies: {e}")
            return False
    
    def verify_authentication(self):
        """
        Verify that cookies provide authentication
        """
        try:
            # Navigate to protected area
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
                print("✅ Authentication verified - cookies are working!")
                return True
            else:
                print("❌ Authentication failed - cookies may have expired")
                print(f"Current URL: {current_url}")
                
                # Save debug info
                with open("debug_auth_failure.html", "w") as f:
                    f.write(self.driver.page_source)
                print("💾 Saved debug_auth_failure.html")
                
                return False
                
        except Exception as e:
            print(f"❌ Authentication verification failed: {e}")
            return False
    
    def run_with_cookies(self):
        """
        Main production workflow using cookies
        """
        try:
            print("🚀 Starting production scraper with cookies...")
            
            # Setup driver
            self.setup_driver()
            
            # Load cookies from GitHub Secret
            if not self.load_session_from_secret():
                raise Exception("Failed to load cookies from WORKFORCE_COOKIES_B64")
            
            # Apply cookies to driver
            if not self.apply_session_to_driver():
                raise Exception("Failed to apply cookies")
            
            # Verify authentication
            if not self.verify_authentication():
                raise Exception("Cookie authentication failed")
            
            print("✅ Ready to scrape with authenticated session!")
            
            # TODO: Add your actual scraping logic here
            # self.extract_deals_data()
            # self.save_to_database(deals)
            
        except Exception as e:
            print(f"❌ Production scraper failed: {e}")
            raise
        finally:
            if self.driver:
                self.driver.quit()


def main():
    """
    Main entry point - choose extraction or production mode
    """
    mode = os.getenv('SCRAPER_MODE', 'production')
    
    if mode == 'extract':
        # Local cookie extraction mode
        print("🔧 Running in EXTRACTION mode")
        extractor = CookieExtractor()
        extractor.run_extraction_process()
    else:
        # Production mode (GitHub Actions)
        print("🏭 Running in PRODUCTION mode")
        scraper = ProductionScraper()
        scraper.run_with_cookies()


if __name__ == "__main__":
    main()
