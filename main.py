#!/usr/bin/env python3

import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def setup_chrome_driver():
    """Set up Chrome driver with options optimized for Mac ARM64"""
    chrome_options = Options()
    
    # Add options for better compatibility and performance
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    try:
        # Try to use webdriver-manager with specific OS configuration
        import platform
        os_type = platform.system().lower()
        arch = platform.machine().lower()
        
        print(f"Detected OS: {os_type}, Architecture: {arch}")
        
        # For ARM64 Macs, specify the correct driver version
        if os_type == "darwin" and "arm" in arch:
            print("Using ARM64-specific ChromeDriver configuration...")
            driver_path = ChromeDriverManager(version="latest").install()
        else:
            driver_path = ChromeDriverManager().install()
            
        print(f"ChromeDriver path: {driver_path}")
        service = Service(driver_path)
        
        return webdriver.Chrome(service=service, options=chrome_options)
        
    except Exception as e:
        print(f"WebDriver Manager failed: {e}")
        print("Trying to use system ChromeDriver...")
        
        # Fallback: try to use system-installed ChromeDriver
        try:
            return webdriver.Chrome(options=chrome_options)
        except Exception as e2:
            print(f"System ChromeDriver also failed: {e2}")
            raise Exception("Could not initialize ChromeDriver. Please ensure Chrome and ChromeDriver are installed.")

def scrape_truth_social_content():
    """Scrape content from the specified Truth Social URL with lazy loading support"""
    url = "https://rollcall.com/factbase-twitter/?platform=truth+social&sort=date&sort_order=desc"
    base_xpath = '//*[@id="app"]/div/div/div/div'
    
    driver = None
    
    try:
        print("Setting up Chrome driver...")
        driver = setup_chrome_driver()
        
        print(f"Navigating to: {url}")
        driver.get(url)
        
        # Quick initial check
        print("Page loaded! Quick check...")
        print("Page title:", driver.title)
        print("Current URL:", driver.current_url)
        
        # Short wait for content to render
        print("Waiting 3 seconds for content to render...")
        time.sleep(3)
        
        print("Starting content extraction with lazy loading support...")
        
        all_content = []
        previous_content_length = 0
        scroll_attempts = 0
        max_scroll_attempts = 10
        
        while scroll_attempts < max_scroll_attempts:
            print(f"\n--- Scroll attempt {scroll_attempts + 1} ---")
            
            # First, check if the base element exists
            print("Checking if base element exists...")
            try:
                base_elements = driver.find_elements(By.XPATH, base_xpath)
                print(f"Found {len(base_elements)} base elements")
                
                if len(base_elements) == 0:
                    print("Base element not found! Let's check the page structure...")
                    print("Page title:", driver.title)
                    print("Current URL:", driver.current_url)
                    
                    # Try to find the app element
                    app_elements = driver.find_elements(By.ID, "app")
                    print(f"Found {len(app_elements)} #app elements")
                    
                    if len(app_elements) > 0:
                        print("App element found, checking its structure...")
                        app_html = app_elements[0].get_attribute('outerHTML')[:500]
                        print("First 500 chars of app element:", app_html)
                    
                    # Try alternative selectors
                    print("Trying alternative selectors...")
                    alt_selectors = [
                        "//div[@id='app']//div",
                        "//div[contains(@class, 'posts')]",
                        "//div[contains(@class, 'tweet')]", 
                        "//div[contains(@class, 'post')]",
                        "//div[contains(@class, 'item')]"
                    ]
                    
                    for selector in alt_selectors:
                        try:
                            alt_elements = driver.find_elements(By.XPATH, selector)
                            print(f"Selector '{selector}' found {len(alt_elements)} elements")
                            if len(alt_elements) > 0:
                                base_xpath = selector
                                print(f"Using alternative selector: {selector}")
                                break
                        except Exception as e:
                            print(f"Selector '{selector}' failed: {e}")
                
                # Find all div elements under the base xpath
                print("Locating all div elements...")
                div_elements = driver.find_elements(By.XPATH, f"{base_xpath}/div")
                print(f"Found {len(div_elements)} div elements")
                
            except Exception as e:
                print(f"Error finding elements: {e}")
                div_elements = []
            
            # Extract content from each div
            current_batch_content = []
            for i, div_element in enumerate(div_elements):
                try:
                    div_text = div_element.text.strip()
                    if div_text:
                        current_batch_content.append(f"--- Div {i+1} Content ---\n{div_text}\n")
                    else:
                        # If no text, try to get HTML
                        div_html = div_element.get_attribute('innerHTML')
                        if div_html and div_html.strip():
                            current_batch_content.append(f"--- Div {i+1} HTML ---\n{div_html}\n")
                except Exception as e:
                    print(f"Error extracting content from div {i+1}: {e}")
                    continue
            
            # Check if we got new content
            current_content_length = len(''.join(current_batch_content))
            
            if current_content_length > previous_content_length:
                print(f"New content found! Length: {current_content_length} characters")
                all_content = current_batch_content
                previous_content_length = current_content_length
                
                # Scroll down to trigger lazy loading
                print("Scrolling down to load more content...")
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                # Wait for lazy loading
                time.sleep(3)
                
                scroll_attempts += 1
            else:
                print("No new content found. Stopping scroll attempts.")
                break
        
        # Print all collected content
        if all_content:
            print("\n" + "=" * 80)
            print("ALL SCRAPED CONTENT:")
            print("=" * 80)
            
            for content_piece in all_content:
                print(content_piece)
            
            print("=" * 80)
            print(f"Total content pieces: {len(all_content)}")
            print(f"Total content length: {len(''.join(all_content))} characters")
            print("=" * 80)
        else:
            print("No content found!")
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        print("Trying to get page source for debugging...")
        if driver:
            print("Page title:", driver.title)
            print("Current URL:", driver.current_url)
        
    finally:
        if driver:
            print("Closing browser...")
            driver.quit()

if __name__ == "__main__":
    print("Starting Truth Social scraper...")
    scrape_truth_social_content()
    print("Scraping completed!")
