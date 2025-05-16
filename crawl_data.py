import os
import json
import time
import random
import config
import sqlite3
import logging
import requests
from queue import Queue
from threading import Lock
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, WebDriverException
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_db_connection(db_path="data/seen_urls.db"):
    conn = sqlite3.connect(db_path)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS crawled_urls (
            url TEXT PRIMARY KEY
        )
    ''')
    return conn

def is_url_crawled(conn, url):
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM crawled_urls WHERE url = ?", (url,))
    return cursor.fetchone() is not None

def mark_url_as_crawled(conn, url):
    try:
        conn.execute("INSERT OR IGNORE INTO crawled_urls (url) VALUES (?)", (url,))
        conn.commit()
    except Exception as e:
        logging.error(f"Failed to insert crawled URL: {url} — {e}")

user_agents = config.user_agents

proxy = config.proxy

max_retries = config.max_retries

valid_proxy = None


os.makedirs("data", exist_ok=True)

def check_proxy(proxy):
    try:
        response = requests.get("http://httpbin.org/ip", proxies={"http": f"http://{proxy}", "https": f"http://{proxy}"}, timeout=5)
        return response.status_code == 200
    except:
        return False


def setup_driver():
    """
    Sets up a headless Chrome driver with a random user agent and optional proxy.

    Returns:
        webdriver.Chrome: The set up Chrome driver.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  
    if valid_proxy:
        chrome_options.add_argument(f'--proxy-server=http://{valid_proxy}')
    chrome_options.add_argument(f"user-agent={random.choice(user_agents)}")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--enable-unsafe-swiftshader")
    chrome_options.add_argument("--ignore-certificate-errors") 
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        logging.error(f"Error initializing driver: {e}")
        return None
    
def get_categories(driver):
    base_url = "https://vnexpress.net"
    categories = []
    base_delay = 2  
    jitter = 3  
    
    for attempt in range(max_retries):
        try:
            driver.get(base_url)
            
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "nav.main-nav"))
            )
            
            menu_items = driver.find_elements(By.CSS_SELECTOR, "nav.main-nav > ul > li > a")
            
            for item in menu_items:
                category_name = item.text.strip()
                category_url = item.get_attribute("href")
                
                if category_name and category_url and category_url.startswith(base_url):
                    categories.append({
                        "name": category_name,
                        "url": category_url
                    })
            
            unique_categories = []
            seen_urls = set()
            for category in categories:
                if category["url"] not in seen_urls:
                    unique_categories.append(category)
                    seen_urls.add(category["url"])
            
            return unique_categories
            
        except (TimeoutException, WebDriverException) as e:
            logging.warning(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                logging.error("Max retries reached. Returning empty list.")
                return []
            delay = base_delay * (2 ** attempt) + random.uniform(0, jitter)
            time.sleep(delay)
            
        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}")
            return []
            
    return categories

def get_article_url(driver, base_url):
    article_urls = []
    page = 1
    ok = True
    base_delay = 2  
    jitter = 3  


    while ok:
        url = f"{base_url}-p{page}" if page > 1 else base_url
        logging.info(f"Processing page {page}: {url}")
        
        for attempt in range(max_retries):
            try:
                driver.get(url)
                
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "article.item-news"))
                )
                
                articles = driver.find_elements(By.CSS_SELECTOR, "article.item-news h3.title-news a")
                
                for article in articles:
                    article_url = article.get_attribute("href")
                    if article_url and article_url.startswith("https://vnexpress.net/") and article_url not in article_urls:
                        article_urls.append(article_url)
                
                page += 1

                if page > 20:
                    ok = False

                break
                
            except (TimeoutException, WebDriverException) as e:
                logging.warning(f"Attempt {attempt + 1} failed for page {page}: {str(e)}")
                if attempt == max_retries - 1:
                    logging.error(f"Max retries reached for page {page}. Skipping.")
                    return article_urls
                delay = base_delay * (2 ** attempt) + random.uniform(0, jitter)
                time.sleep(delay)
                
            except Exception as e:
                logging.error(f"Unexpected error on page {page}: {str(e)}")
                return article_urls
    
    return article_urls
    
def get_all_article_url(driver, categories):
    article_url_map = {}
    cnt = 0

    for category in categories:
        cnt += 1
        if cnt > 1:
            break
        urls = get_article_url(driver, category["url"])
        for url in urls:
            if url not in article_url_map:
                article_url_map[url] = category["name"]

    return list(article_url_map.items())



def crawl_article(driver, article_url, category_name):
    base_delay = 2
    jitter = 3

    for attempt in range(max_retries):
        try:
            logging.info(f"Crawling article: {article_url} (attempt {attempt + 1})")
            driver.get(article_url)

            article_root = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CLASS_NAME, "fck_detail"))
            )

            if driver.find_elements(By.CLASS_NAME, "title-detail"):
                title = driver.find_element(By.CLASS_NAME, "title-detail").text.strip()
                date = driver.find_element(By.CLASS_NAME, "date").text.strip()
                description = driver.find_element(By.CLASS_NAME, "description").text.strip() if article_root.find_elements(By.CLASS_NAME, "description") else ""
                content = " ".join(elem.text.strip() for elem in article_root.find_elements(By.CSS_SELECTOR, "p") if elem.text.strip())
                if content == "":
                    break
                logging.info(f"Successfully crawled article: {title}")
                return {
                    "title": title,
                    "category": category_name,
                    "date": date,
                    "description": description,
                    "content": content,
                    "url": article_url
                }

        except Exception as e:
            delay = base_delay * (2 ** attempt) + random.uniform(0, jitter)
            logging.warning(f"Error crawling {article_url} (attempt {attempt + 1}): {e} — Retrying after {delay:.1f}s")
            time.sleep(delay)

    logging.error(f"Failed to crawl article after {max_retries} attempts: {article_url}")
    return None


def crawl_all_articles_with_pool(article_url_tuples, max_workers=3, db_path="data/seen_urls.db"):
    articles = []
    driver_pool = Queue()
    lock = Lock()
    conn = get_db_connection(db_path)

    new_urls = [(url, cat) for url, cat in article_url_tuples if not is_url_crawled(conn, url)]
    logging.info(f"{len(new_urls)} new URLs to crawl (filtered from {len(article_url_tuples)})")

    for _ in range(max_workers):
        driver = setup_driver()
        if driver:
            driver_pool.put(driver)

    def worker(url, category_name):
        driver = driver_pool.get()
        try:
            article_data = crawl_article(driver, url, category_name)
            if article_data:
                with lock:
                    articles.append(article_data)
                    mark_url_as_crawled(conn, url)
        finally:
            driver_pool.put(driver)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(worker, url, cat) for url, cat in new_urls]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logging.error(f"Error in crawling task: {e}")
            time.sleep(random.uniform(1, 2))

    while not driver_pool.empty():
        driver = driver_pool.get()
        driver.quit()

    conn.close()
    return articles

def save_to_json(articles, category):
    file_path = f"data/vnexpress_articles_{category}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    logging.info(f"Saved {len(articles)} articles to {file_path}")

def main():
    global valid_proxy
    if check_proxy(proxy):
        valid_proxy = proxy
        logging.info(f"Using proxy: {proxy}")
    else:
        valid_proxy = None
        logging.warning("Proxy is not working. Proceeding without proxy.")

    driver = setup_driver()
    if not driver:
        logging.error("Driver setup failed. Exiting.")
        return
    
    categories = []
    try:
        categories = get_categories(driver)
        article_url_tuples = []
        for category in categories:
            urls = get_article_url(driver, category["url"])
            for url in urls:
                article_url_tuples.append((url, category["name"]))

        articles = crawl_all_articles_with_pool(article_url_tuples, max_workers=5)

        logging.info(f"Total articles crawled: {len(articles)}")
        articles_by_category = {}
        for article in articles:
            cat = article["category"]
            articles_by_category.setdefault(cat, []).append(article)

        for cat, arts in articles_by_category.items():
            save_to_json(arts, cat)
        
        save_to_json(articles, "all")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()