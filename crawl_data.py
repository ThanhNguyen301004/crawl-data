import json
import time
import random
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, WebDriverException

user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
]

categories = [
    "thoi-su", "kinh-doanh", "the-thao", "giai-tri", "phap-luat",
    "giao-duc", "suc-khoe", "doi-song", "du-lich", "khoa-hoc",
    "so-hoa", "xe", "y-kien", "tam-su"
]

proxies_list = [
]

os.makedirs("data", exist_ok=True)

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  
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
        print(f"Lỗi khi khởi tạo driver: {e}")
        return None

def crawl_article(driver, article_url, cnt, max_retries=3):
    for attempt in range(max_retries):
        try:
            driver.get(article_url)
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CLASS_NAME, "fck_detail"))
            )
            title = driver.find_element(By.CLASS_NAME, "title-detail").text.strip()
            category = driver.find_element(By.CLASS_NAME, "breadcrumb").find_element(By.TAG_NAME, "a").get_attribute("title").strip()
            print("title: ", title)
            date = driver.find_element(By.CLASS_NAME, "date").text
            description = driver.find_element(By.CLASS_NAME, "description").text.strip() if driver.find_elements(By.CLASS_NAME, "description") else ""
            content_elements = driver.find_elements(By.CSS_SELECTOR, "article.fck_detail p")
            content = " ".join(elem.text.strip() for elem in content_elements if elem.text.strip())
            cnt+=1
            print("cnt: ", cnt)
            return {
                "id": cnt,
                "title": title,
                "category": category,
                "date": date,
                "description": description,
                "content": content,
                "url": article_url
            }, cnt

        except Exception as e:
            print(f"Lỗi khi crawl bài viết {article_url} (lần {attempt+1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                return None, cnt
            time.sleep(10)
    return None, cnt

def crawl_category(category, driver, driver_sub, cnt, max_retries=3):
    base_url = f"https://vnexpress.net/{category}"
    articles = []
    page = 1
    has_next_page = True

    while has_next_page:
        url = f"{base_url}-p{page}" if page > 1 else base_url
        print(f"Đang crawl: {url}")

        for attempt in range(max_retries):
            try:
                driver.get(url)
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "article.item-news, article.article-item"))
                )

                driver.execute_script("window.scrollBy(0, 500);")
                time.sleep(2)  
                items = driver.find_elements(By.CSS_SELECTOR, "article.item-news, article.article-item")

                if not items:
                    has_next_page = False
                    print(f"Hết bài viết ở danh mục {category} tại trang {page}")
                    break

                for item in items:
                    try:
                        title_elem = item.find_elements(By.CLASS_NAME, "title-news")
                        if not title_elem:
                            continue
                        article_url = item.find_element(By.CLASS_NAME, "title-news").find_element(By.TAG_NAME, "a").get_attribute("href")

                        if article_url:
                            
                            article_data, cnt = crawl_article(driver_sub, article_url, cnt)
                            if article_data:
                                articles.append(article_data)
                            else:
                                print(f"Bỏ qua bài viết {article_url} do lỗi")

                    except Exception as e:
                        print(f"Lỗi khi xử lý bài viết: {e}")
                        continue
                    time.sleep(random.uniform(2, 4))

                page += 1
                if page > 2:
                    has_next_page = False
                print(f"Số bài viết tìm thấy ở trang {page-1}: {cnt}")
                break

            except Exception as e:
                print(f"Lỗi khi crawl trang {url} (lần {attempt+1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    has_next_page = False
                    print(f"Bỏ qua trang {url} sau {max_retries} lần thử")
                time.sleep(10)

        time.sleep(random.uniform(2, 4))
    return articles

def crawl_home(driver, sub_driver, max_retries=3):
    base_url = "https://vnexpress.net"
    articles = []

    for attempt in range(max_retries):
        try:
            driver.get(base_url)
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "article.item-news, article.article-item"))
            )

            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(2)
            items = driver.find_elements(By.CSS_SELECTOR, "article.item-news, article.article-item")
            cnt = 0

            for item in items:
                try:
                    title_elem = item.find_elements(By.CLASS_NAME, "title-news")
                    if not title_elem:
                        continue
                    article_url = title_elem[0].find_element(By.TAG_NAME, "a").get_attribute("href")
                    
                    print(f"Đang xử lý: {article_url}")
                    if article_url:
                        article_data, cnt = crawl_article(sub_driver, article_url, cnt)
                        if article_data:
                            articles.append(article_data)
                        else:
                            print(f"Bỏ qua bài viết {article_url} do lỗi")

                except Exception as e:
                    print(f"Lỗi khi xử lý bài viết: {e}")
                    continue
                time.sleep(random.uniform(2, 4))

            print(f"Số bài viết tìm thấy ở trang chủ: {cnt}")
            break

        except (TimeoutException, WebDriverException) as e:
            print(f"Lỗi khi crawl trang {base_url} (lần {attempt+1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                print(f"Bỏ qua trang chủ sau {max_retries} lần thử")
            time.sleep(10)

    return articles

def save_to_json(articles, category):
    file_path = f"data/vnexpress_articles_{category}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    print(f"Đã lưu {len(articles)} bài viết vào {file_path}")

def main():
    driver = setup_driver()
    driver_sub = setup_driver()
    try:
        all_articles = {}
        for category in categories:
            cnt = 0
            print(f"\nBắt đầu crawl danh mục: {category}")
            articles = crawl_category(category,driver,driver_sub, cnt)
            all_articles[category] = articles
            save_to_json(articles, category)

        total_articles = [article for articles in all_articles.values() for article in articles]
        save_to_json(total_articles, "all")
        # crawl page home
        # articles_page_home = crawl_home(driver, driver_sub)
        # save_to_json(articles_page_home, "home")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()