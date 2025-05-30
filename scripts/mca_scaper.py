import os
import logging
from datetime import datetime, timezone
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from supabase import create_client, Client
from supabase_client import get_supabase_client

class CSLMCAScraper:
    def __init__(self):
        self.setup_logging()
        self.supabase = get_supabase_client()
        self.driver = None
        
    def setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def run_daily_extraction(self):
        """Main function for daily GitHub Actions run"""
        try:
            self.logger.info("🚀 Starting CSL Capital MCA extraction...")
            
            # Your scraping logic here
            deals = self.scrape_portfolio()
            
            if deals:
                self.save_to_supabase(deals)
                self.logger.info(f"✅ Successfully extracted {len(deals)} deals")
            else:
                self.logger.warning("⚠️ No deals extracted")
                
        except Exception as e:
            self.logger.error(f"❌ Extraction failed: {str(e)}")
            raise

if __name__ == "__main__":
    scraper = CSLMCAScraper()
    scraper.run_daily_extraction()
