"""
Hybrid News Aggregator (V2-Inspired)
Combines direct RSS feeds with Google News RSS proxy for blocked sources.
"""
import asyncio
import os
from datetime import datetime, timedelta
import time
from typing import List, Dict

import feedparser
import aiohttp
import news_rss_aggregator

# --- Configuration ---
# --- Configuration ---
def load_sources_from_file():
    domains = ["lexpress.mu", "defimedia.info", "lemauricien.com", "ionnews.mu"] # Default fallbacks
    try:
        if os.path.exists("news_sources.txt"):
            with open("news_sources.txt", "r") as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                for line in lines:
                    # Extract domain from URL
                    domain = line.split("//")[-1].split("/")[0]
                    if domain and domain not in domains:
                        domains.append(domain)
    except Exception as e:
        print(f"Error loading news_sources.txt: {e}")
    return list(set(domains))

PROXY_RSS_DOMAINS = load_sources_from_file()

# --- Cache ---
_news_cache = {
    "data": None,
    "expiry": 0
}
CACHE_TTL = 900  # 15 minutes to reduce API calls and memory churn

class NewsAggregator:
    async def fetch_headlines(self, limit: int = 15, topic: str = None) -> List[Dict]:
        """Fetch headlines from Google Proxy (Source of Truth)."""
        headlines = []
        
        # Proxy RSS Sources (Google News)
        print(f"🔍 Fetching {len(PROXY_RSS_DOMAINS)} sources via Google News RSS (+when:1d) Topic: {topic}...")
        try:
            proxy_headlines = await news_rss_aggregator.get_google_proxy_news(PROXY_RSS_DOMAINS, topic=topic)
            headlines.extend(proxy_headlines)
        except Exception as e:
            print(f"Proxy RSS error: {e}")

        return headlines[:limit]
        
_aggregator = NewsAggregator()

async def get_daily_news(topic: str = None):
    """Get news from today with caching."""
    global _news_cache
    
    # Simple cache key including topic
    cache_key = f"data_{topic}" if topic else "data"
    
    current_time = time.time()
    # Check cache (simplified for demo - ideally per-topic cache dict)
    # For now, we only cache general news. If topic is present, bypass cache (or simpler: no cache for topics)
    if not topic and _news_cache["data"] and current_time < _news_cache["expiry"]:
        print("♻️ Serving news from cache")
        return _news_cache["data"]

    today = datetime.now().strftime("%Y-%m-%d")
    headlines = await _aggregator.fetch_headlines(limit=15, topic=topic)
    
    header = f"**📅 Daily News ({today})**"
    if topic:
        header = f"**📅 News on '{topic}' ({today})**"
    
    if not headlines:
        return f"No fresh news found for '{topic}'." if topic else "No fresh news found at the moment."

    txt = f"{header}\n"
    for h in headlines:
        txt += f"- [{h['source']}] {h['headline']}\n"
    
    # Only cache general news to update the global 'data' key
    if not topic:
        _news_cache["data"] = txt
        _news_cache["expiry"] = current_time + CACHE_TTL
    
    return txt

async def get_weekly_news():
    """Get news summary for the week."""
    headlines = await _aggregator.fetch_headlines(limit=30)
    txt = "**🗓️ Weekly Round-up**\n"
    for h in headlines:
        txt += f"- [{h.get('source', 'News')}] {h['headline']}\n"
    return txt
