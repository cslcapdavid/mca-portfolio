📋 UPDATED STEP-BY-STEP INSTRUCTIONS:
git clone https://github.com/github/mca-portfolio.git
cd mca-portfolio/scripts
═══════════════════════════════════════════════════════════════════════════════
PHASE 1: LOCAL COOKIE EXTRACTION  
═══════════════════════════════════════════════════════════════════════════════



1. 🖥️ RUN LOCALLY (on your machine):
   ```bash
   ```# Save the script as capture_cookies.py```
   python capture_cookies.py
   ```
   

2. 🔑 MANUAL LOGIN:
   - Browser window will open
   - Login to 1workforce.com manually
   - Complete 2FA (enter code from your phone)
   - Navigate to dashboard/portfolio
   - Press ENTER in terminal when done

3. 💾 ENCODE COOKIES:
   ```bash
   # Run this in terminal after step 2
   base64 -i cookies.pkl -o cookies.b64

cat cookies.b64
   ```

4. 📋 COPY BASE64 CONTENT:
   ```bash
   # Copy the contents of the base64 file
   cat cookies.b64
   # Copy this output to clipboard
   ```

# Just run this single command
./run_scraper.sh
═══════════════════════════════════════════════════════════════════════════════
PHASE 2: GITHUB REPOSITORY SETUP
═══════════════════════════════════════════════════════════════════════════════

5. 🔧 ADD GITHUB SECRET:
   - Go to your GitHub repository
   - Click Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: WORKFORCE_COOKIES_B64
   - Value: [paste the base64 content from step 4]
   - Click "Add secret"

6. 📝 ADD OTHER SECRETS (if needed):
   - WORKFORCE_USERNAME (your username)
   - WORKFORCE_PASSWORD (your password)

═══════════════════════════════════════════════════════════════════════════════
PHASE 3: GITHUB ACTIONS WORKFLOW
═══════════════════════════════════════════════════════════════════════════════

7. 📄 CREATE .github/workflows/scraper.yml:
   ```yaml
   name: MCA Scraper
   on:
     schedule:
       - cron: '0 9 * * 1-5'  # Weekdays 9 AM
     workflow_dispatch:  # Manual trigger
   
   jobs:
     scrape:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         
         - name: Setup Python
           uses: actions/setup-python@v4
           with:
             python-version: '3.9'
             
         - name: Install Chrome
           uses: browser-actions/setup-chrome@latest
           
         - name: Install dependencies
           run: |
             pip install selenium beautifulsoup4
             
         - name: Run scraper
           env:
             WORKFORCE_COOKIES_B64: ${{ secrets.WORKFORCE_COOKIES_B64 }}
             WORKFORCE_USERNAME: ${{ secrets.WORKFORCE_USERNAME }}
             WORKFORCE_PASSWORD: ${{ secrets.WORKFORCE_PASSWORD }}
             SCRAPER_MODE: production
           run: python capture_cookies.py
   ```

═══════════════════════════════════════════════════════════════════════════════
PHASE 4: TESTING & MAINTENANCE
═══════════════════════════════════════════════════════════════════════════════

8. 🧪 TEST THE WORKFLOW:
   - Go to Actions tab in GitHub
   - Click "MCA Scraper"
   - Click "Run workflow"
   - Monitor the logs

9. 🔄 COOKIE REFRESH (when they expire):
   - Run steps 1-5 again to get fresh cookies
   - Update the WORKFORCE_COOKIES_B64 secret
   - Typical refresh needed every 1-2 weeks

═══════════════════════════════════════════════════════════════════════════════
TROUBLESHOOTING
═══════════════════════════════════════════════════════════════════════════════

❌ If authentication fails:
   - Cookies may have expired
   - Re-run local extraction (steps 1-5)
   - Check GitHub Actions logs for specific errors

❌ If base64 command not found (Windows):
   ```powershell
   # Use PowerShell instead
   [System.Convert]::ToBase64String([System.IO.File]::ReadAllBytes("cookies.pkl")) | Out-File cookies.b64
   ```

🔍 Debug files are saved automatically:
   - debug_auth_failure.html (when auth fails)
   - Check GitHub Actions artifacts
"""
