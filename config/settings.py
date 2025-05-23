import os

user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
]

proxy = ["47.245.117.43"]

max_retries = 3

subcategory_urls = {
        "https://www.bbc.com/business/": [
            "executive-lounge",
            "technology-of-business",
            "future-of-business",
        ],
        "https://www.bbc.com/innovation/": [
            "technology",
            "science",
            "artificial-intelligence",
            "ai-v-the-mind"
        ],
        "https://www.bbc.com/culture/": [
            "film-tv",
            "music",
            "books",
            "art",
            "style",
            "entertainment-news"
        ],
        "https://www.bbc.com/travel/": [
            "destinations",
            "worlds-table",
            "cultural-experiences",
            "adventures",
            "specialist"
        ],
        "https://www.bbc.com/future-planet/": [
            "natural-wonders",
            "weather-science",
            "solutions",
            "sustainable-business",
            "green-living"
        ]
    }