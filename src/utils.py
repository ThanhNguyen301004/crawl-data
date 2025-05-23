import os
import json
import time
import random
import config.settings as settings
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
from bs4 import BeautifulSoup

from main import valid_proxy, user_agents, max_retries, subcategory_urls
from src.database import get_db_connection


def check_proxy(proxy):
    try:
        response = requests.get("http://httpbin.org/ip", proxies={"http": f"http://{proxy}", "https": f"http://{proxy}"}, timeout=5)
        return response.status_code == 200
    except:
        return False

def save_to_json(articles, category):
    file_path = f"data/bbc_articles_{category}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    logging.info(f"Saved {len(articles)} articles to {file_path}")