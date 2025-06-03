from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import pickle
import time

# Setup headful Chrome (visible browser)
options = Options()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(options=options)

# Step 1: Navigate to login page
driver.get("https://1workforce.com/n/login")

# Step 2: Manually log in (including 2FA)
print("Please log in manually and complete 2FA...")

# Step 3: Pause script to wait for login
input("Press Enter AFTER you have logged in and landed on dashboard...")

# Step 4: Save cookies
with open("cookies.pkl", "wb") as f:
    pickle.dump(driver.get_cookies(), f)

print("✅ Cookies saved to cookies.pkl")

driver.quit()
