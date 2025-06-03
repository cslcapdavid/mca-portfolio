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
    """Extract and prepare cookies for GitHub Secrets"""
    
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
        print("🔑 STEP 1: Manual Login Process")
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
            
            # Get additional session info
            session_info = {
                'cookies': cookies,
                'user_agent': self.driver.execute_script("return navigator.userAgent;"),
                'current_url': current_url,
                'extracted_at': datetime.now().isoformat(),
                'expires_estimate': (datetime.now() + timedelta(days=14)).isoformat()  # Conservative estimate
            }
            
            return session_info
            
        except Exception as e:
            print(f"❌ Error during manual login: {e}")
            return None
    
    def save_cookies_locally(self, session_info):
        """
        Step 2: Save cookies locally for testing
        """
        print("\n💾 STEP 2: Saving Cookies Locally")
        print("=" * 50)
        
        try:
            # Create output directory
            output_dir = Path("extracted_cookies")
            output_dir.mkdir(exist_ok=True)
            
            # Save as pickle (for local testing)
            pickle_file = output_dir / "session_cookies.pkl"
            with open(pickle_file, 'wb') as f:
                pickle.dump(session_info, f)
            print(f"✅ Saved pickle file: {pickle_file}")
            
            # Save as JSON (human readable)
            json_file = output_dir / "session_info.json"
            with open(json_file, 'w') as f:
                json.dump(session_info, f, indent=2, default=str)
            print(f"✅ Saved JSON file: {json_file}")
            
            # Prepare for GitHub Secrets (base64 encoded)
            github_secret = base64.b64encode(pickle.dumps(session_info)).decode('utf-8')
            
            secret_file = output_dir / "github_secret.txt"
            with open(secret_file, 'w') as f:
                f.write(github_secret)
            print(f"✅ Saved GitHub secret: {secret_file}")
            
            print(f"\n📋 GitHub Secret Value (copy this):")
            print("-" * 50)
            print(github_secret)
            print("-" * 50)
            
            return github_secret
            
        except Exception as e:
            print(f"❌ Error saving cookies: {e}")
            return None
    
    def test_cookies_locally(self, session_info):
        """
        Step 3: Test cookies work locally
        """
        print("\n🧪 STEP 3: Testing Cookies Locally")
        print("=" * 50)
        
        try:
            # Open new browser instance
            test_driver = webdriver.Chrome(options=Options())
            
            # Navigate to site
            test_driver.get("https://1workforce.com/")
            time.sleep(2)
            
            # Load cookies
            for cookie in session_info['cookies']:
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
            session_info = self.manual_login_and_extract()
            if not session_info:
                print("❌ Failed to extract session info")
                return False
            
            # Step 2: Save cookies
            github_secret = self.save_cookies_locally(session_info)
            if not github_secret:
                print("❌ Failed to save cookies")
                return False
            
            # Step 3: Test cookies
            if self.test_cookies_locally(session_info):
                print("\n🎉 SUCCESS! Cookies extracted and tested successfully")
                print("\n📋 NEXT STEPS:")
                print("1. Copy the GitHub secret value above")
                print("2. Go to your GitHub repository")
                print("3. Settings → Secrets and variables → Actions")
                print("4. Add new secret: WORKFORCE_COOKIES_B64")
                print("5. Paste the value from github_secret.txt")
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
    Modified scraper that uses GitHub Secrets cookies
    This is what runs in GitHub Actions
    """
    
    def __init__(self):
        self.driver = None
        self.session_info = None
    
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
        Load session info from GitHub Secret
        """
        try:
            # Get the base64 encoded session from environment
            encoded_session = os.getenv('WORKFORCE_COOKIES_B64')
            if not encoded_session:
                raise ValueError("WORKFORCE_COOKIES_B64 secret not found")
            
            # Decode and load session info
            session_data = base64.b64decode(encoded_session.encode('utf-8'))
            self.session_info = pickle.loads(session_data)
            
            print(f"✅ Loaded session info from secret")
            print(f"   - Extracted at: {self.session_info.get('extracted_at')}")
            print(f"   - Estimated expiry: {self.session_info.get('expires_estimate')}")
            print(f"   - Cookies count: {len(self.session_info.get('cookies', []))}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to load session from secret: {e}")
            return False
    
    def apply_session_to_driver(self):
        """
        Apply loaded session to driver
        """
        try:
            if not self.session_info:
                return False
            
            # Navigate to domain first
            self.driver.get("https://1workforce.com/")
            time.sleep(2)
            
            # Apply cookies
            cookies_applied = 0
            for cookie in self.session_info['cookies']:
                try:
                    self.driver.add_cookie(cookie)
                    cookies_applied += 1
                except Exception as e:
                    print(f"⚠️ Could not apply cookie {cookie.get('name')}: {e}")
            
            print(f"✅ Applied {cookies_applied} cookies")
            
            # Set user agent to match
            user_agent = self.session_info.get('user_agent')
            if user_agent:
                self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                    "userAgent": user_agent
                })
                print("✅ User agent set to match original session")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to apply session: {e}")
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
            
            # Load session from GitHub Secret
            if not self.load_session_from_secret():
                raise Exception("Failed to load session cookies")
            
            # Apply session to driver
            if not self.apply_session_to_driver():
                raise Exception("Failed to apply session cookies")
            
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
