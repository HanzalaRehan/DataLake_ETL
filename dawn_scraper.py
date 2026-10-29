# =========================
# 1️⃣ Install & Imports
# =========================

# You need to install these packages if you haven't already:
# pip install selenium webdriver-manager beautifulsoup4 tqdm pandas python-dateutil

import time
import datetime
import random
import csv
import logging

from dateutil import parser as dateparser
from tqdm import tqdm
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from webdriver_manager.chrome import ChromeDriverManager

# Logging config for clean output
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# Create Selenium Driver

def make_driver(headless=True, user_agent=None):
    """
    Creates and returns a Selenium Chrome WebDriver.
    headless: True = browser runs in background, False = visible browser
    user_agent: optional custom user agent string
    """
    options = Options()

    if headless:
        options.add_argument("--headless=new")  # Headless mode

    # Common flags for stability
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    # Optional: set custom user-agent
    if user_agent:
        options.add_argument(f"user-agent={user_agent}")

    # Create driver service using webdriver-manager (auto-downloads ChromeDriver)
    service = ChromeService(ChromeDriverManager().install())

    # Initialize the Chrome WebDriver
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# Safe GET function

def safe_get(driver, url, timeout=15):
    """
    Selenium-safe GET request with wait.
    Returns True if page loaded successfully, else False
    """
    try:
        driver.get(url)
        # Wait until body tag is present (page fully loaded)
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        return True
    except TimeoutException:
        logging.warning(f"Timeout on {url}")
        return False
    except WebDriverException as e:
        logging.error(f"WebDriver error on {url}: {e}")
        return False


# Helper Functions

def get_daily_url(date):
    """Return Dawn archive URL for a given date"""
    return f"https://www.dawn.com/archive/{date.strftime('%Y-%m-%d')}"

def get_article_links(driver, daily_url):
    """
    Returns list of article links for a given date page.
    Uses Selenium to load JS-rendered content if needed.
    """
    ok = safe_get(driver, daily_url)
    if not ok:
        return []

    soup = BeautifulSoup(driver.page_source, "html.parser")
    links = []

    for a_tag in soup.find_all("a", href=True):
        href = a_tag['href']
        if "/news/" in href:
            links.append(href)

    # Remove duplicates
    return list(set(links))


def get_article_text_and_time(driver, url):
    """
    Given an article URL, returns (title, body text, timestamp)
    """
    ok = safe_get(driver, url)
    if not ok:
        return "", "", ""

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Title
    title_tag = soup.find("h2", class_="story__title") or soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Timestamp
    time_tag = soup.find("span", class_="timestamp--time") or soup.find("span", class_="story__time")
    timestamp = time_tag.get_text(strip=True) if time_tag else ""

    # Body text
    body_div = soup.find("div", class_="story__content")
    if body_div:
        paragraphs = [p.get_text(strip=True) for p in body_div.find_all("p")]
        text = " ".join(paragraphs)
    else:
        text = ""

    return title, text, timestamp


# Main Scraper

def scrape_dates(start_date, end_date, output_csv="dawn_news.csv", headless=True):
    """
    Scrapes Dawn.com articles between start_date and end_date.
    Saves results to CSV.
    """
    delta = datetime.timedelta(days=1)

    # Open CSV file
    with open(output_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "time", "url", "title", "text"])

        current_date = start_date
        while current_date <= end_date:
            daily_url = get_daily_url(current_date)
            logging.info(f"Processing date: {current_date} -> {daily_url}")

            driver = make_driver(headless=headless)
            try:
                article_links = get_article_links(driver, daily_url)
                logging.info(f"Found {len(article_links)} articles")

                for link in tqdm(article_links, desc=f"Scraping {current_date}"):
                    try:
                        title, text, timestamp = get_article_text_and_time(driver, link)
                        writer.writerow([current_date, timestamp, link, title, text])
                        time.sleep(random.uniform(0.5, 1.5))  # polite delay
                    except Exception as e:
                        logging.error(f"Error scraping {link}: {e}")

            finally:
                driver.quit()

            # Move to next day
            current_date += delta


# Run the Scraper

if __name__ == "__main__":
    # Example: small test range
    TEST_START = datetime.date(2015, 1, 1)
    TEST_END = datetime.date(2015, 12, 31)

    scrape_dates(TEST_START, TEST_END, output_csv="dawn_test.csv", headless=False)
