import os
import json
import time
import _random
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

def mark_url_as_crawled(db_path, url):
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("INSERT OR IGNORE INTO crawled_urls (url) VALUES (?)", (url,))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Failed to insert crawled URL: {url} — {e}")