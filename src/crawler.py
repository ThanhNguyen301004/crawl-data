import time
import random
import logging
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

from src.database import get_db_connection, is_url_crawled, mark_url_as_crawled
from config.settings import user_agents



def setup_driver(valid_proxy, user_agents):
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
    

def get_categories(driver, max_retries=3):
    base_url = "https://www.bbc.com"
    categories = []
    base_delay = 2  
    jitter = 3  
    
    for attempt in range(max_retries):
        try:
            driver.get(base_url)
            
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "nav#main-navigation-container"))
            )

            menu_items = driver.find_elements(By.CSS_SELECTOR, "nav#main-navigation-container ul li a")

            for item in menu_items:
                category_name = item.get_attribute("innerHTML")
                category_url = item.get_attribute("href")
                if category_name != "Home" and category_name != "News" and category_name != "Sport" and category_name != "Audio" and category_name != "Video" and category_name != "Live" and category_url and category_url.startswith(base_url):
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

def get_urls_each_page(driver, article_urls):    
    while True:
        print("get_urls_each_page", driver.current_url)
        next_buttons = driver.find_elements(By.CSS_SELECTOR, "button[data-testid='pagination-next-button']")
        if not next_buttons or not next_buttons[0].is_enabled():
            break

        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", next_buttons[0])
            time.sleep(1)

            driver.execute_script("arguments[0].click();", next_buttons[0])
            
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "main#main-content"))
            )
            time.sleep(2)
            articles = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='liverpool-card']")
            for article in articles:
                article_url = article.find_element(By.CSS_SELECTOR, "a[data-testid='internal-link']").get_attribute("href")
                if article_url and article_url.startswith("https://www.bbc.com/") and article_url not in article_urls:
                    article_urls.append(article_url)
                print("article_url: ", article_url)
            print("articles: ", len(articles))
        except Exception as e:
            logging.warning(f"Click failed: {e}")
            break  


def get_article_url(driver, base_url, subcategory_urls, max_retries=3):
    article_urls = []  
    base_delay = 2
    jitter = 3

    for attempt in range(max_retries):
        try:
            driver.get(base_url)
            logging.info(f"Loading page: {base_url}")

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "main#main-content"))
            )

            sub_urls = []
            
            for a, b in subcategory_urls.items():
                if a.startswith(base_url):
                    for n in b:
                        sub_urls.append(f"{a}{n}")
            logging.info(f"Subcategory URLs: {sub_urls}")

            for url in sub_urls:
                print("url: ", url)

            article_elements = driver.find_elements(By.CSS_SELECTOR, "a[data-testid='internal-link']")
            for article in article_elements:
                url = article.get_attribute("href")
                if url and url.startswith("https://www.bbc.com/news/"):
                    article_urls.append(url)

            break

        except (TimeoutException, WebDriverException) as e:
            logging.warning(f"Attempt {attempt + 1} failed for page: {base_url}. Error: {e}")
            if attempt == max_retries - 1:
                logging.error(f"Max retries reached for {base_url}. Skipping.")
                break
            delay = base_delay * (2 ** attempt) + random.uniform(0, jitter)
            time.sleep(delay)

        except Exception as e:
            logging.error(f"Unexpected error on {base_url}: {e}")
            break
            
    get_urls_each_page(driver, article_urls)
    print("Ok")

    for url in sub_urls:
        print("url: ", url)

        for attempt in range(max_retries):
                try:
                    driver.get(url)
                    logging.info(f"Loading page: {url}")
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)  

                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "main#main-content"))
                    )

                    articles = driver.find_elements(By.CSS_SELECTOR, "a[data-testid='internal-link']")


                    for article in articles:
                        article_url = article.get_attribute("href")
                        if article_url and article_url.startswith("https://www.bbc.com/news/") and article_url not in article_urls:
                            print(article_url)
                            article_urls.append(article_url)
                    
                    break

                except (TimeoutException, WebDriverException) as e:
                    logging.warning(f"Attempt {attempt + 1} failed for pag: {str(url)}")
                    if attempt == max_retries - 1:
                        logging.error(f"Max retries reached for page. Skipping.")
                        return article_urls
                    delay = base_delay * (2 ** attempt) + random.uniform(0, jitter)
                    time.sleep(delay)
                    
                except Exception as e:
                    logging.error(f"Unexpected error on page : {str(base_url)}")
                    return article_urls
            
        get_urls_each_page(driver, article_urls)
        print("Okla")

    return article_urls


def crawl_article(driver, article_url, category_name, max_retries=3):
    base_delay = 2
    jitter = 3

    for attempt in range(max_retries):
        try:
            logging.info(f"Crawling article: {article_url} (attempt {attempt + 1})")
            driver.get(article_url)

            article_root = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "article"))
            )

            if article_root.find_elements(By.CSS_SELECTOR, "div[data-component='headline-block']"):
                title = article_root.find_element(By.CSS_SELECTOR, "div[data-component='headline-block']").text.strip()
                date = article_root.find_element(By.TAG_NAME, "time").get_attribute("datetime") if article_root.find_elements(By.TAG_NAME, "time") else ""
                description = article_root.find_element(By.CSS_SELECTOR, "div[data-component='caption-block']").text.strip() if article_root.find_elements(By.CSS_SELECTOR, "div[data-component='caption-block']") else ""
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

def crawl_all_articles_with_pool(article_url_tuples, max_workers=3, db_path="data/seen_urls.db", valid_proxy= None):
    articles = []
    driver_pool = Queue()
    lock = Lock()
    conn = get_db_connection(db_path)

    new_urls = [(url, cat) for url, cat in article_url_tuples if not is_url_crawled(conn, url)]
    logging.info(f"{len(new_urls)} new URLs to crawl (filtered from {len(article_url_tuples)})")

    for _ in range(max_workers):
        driver = setup_driver(valid_proxy, user_agents)
        if driver:
            driver_pool.put(driver)

    def worker(url, category_name):
        driver = driver_pool.get()
        try:
            article_data = crawl_article(driver, url, category_name)
            if article_data:
                with lock:
                    articles.append(article_data)
                    mark_url_as_crawled(db_path, url)  # Pass db_path instead of conn
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