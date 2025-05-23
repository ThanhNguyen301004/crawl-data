import logging
from config.settings import *
from src.utils import *
from src.database import *
from src.crawler import *
from selenium.webdriver.support import expected_conditions as EC


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/crawler.log'),
        logging.StreamHandler()
    ]
)

user_agents = user_agents
proxy = proxy
max_retries = max_retries
valid_proxy = None
subcategory_urls = subcategory_urls

def main():
    global valid_proxy
    if check_proxy(proxy):
        valid_proxy = proxy
        logging.info(f"Using proxy: {proxy}")
    else:
        valid_proxy = None
        logging.warning("Proxy is not working. Proceeding without proxy.")

    driver = setup_driver(valid_proxy, user_agents)
    if not driver:
        logging.error("Driver setup failed. Exiting.")
        return
    
    categories = []
    try:
        categories = get_categories(driver)
        article_url_tuples = []
        cnt = 0
        for category in categories:
            cnt += 1
            if cnt >1:
                break
            urls = get_article_url(driver, category["url"], subcategory_urls)
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