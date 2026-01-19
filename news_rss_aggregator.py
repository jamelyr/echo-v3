"""
Google News RSS Aggregator
Acts as a proxy fetcher for sources that block direct RSS scrapers.
Enhanced with optional webctl support for deep content extraction.
"""
import aiohttp
import feedparser
import asyncio
from typing import List, Dict, Optional
import subprocess

def _extract_article_body_webctl(url: str, timeout: int = 15) -> Optional[str]:
    """
    Use webctl to navigate to URL and extract article body from main content area.
    Returns: article body (first 50 lines max) or None on failure
    """
    try:
        # Navigate and snapshot main content only
        cmd = [
            "webctl", "-q",
            "navigate", url,
            "-w", "load"
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        
        # Take snapshot of main content area only
        cmd = [
            "webctl", "-q",
            "snapshot",
            "-v", "md",  # Markdown view for readability
            "-w", "role=main",  # Focus on main article area
            "-i",  # Interactive only
            "-l", "30"  # Limit nodes
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        
        if result.returncode == 0:
            lines = result.stdout.split("\n")[:50]  # Limit to 50 lines
            return "\n".join(lines)
    except Exception as e:
        print(f"⚠️ webctl extraction failed for {url}: {e}")
    
    return None


class GoogleNewsRSSAggregator:
    def __init__(self, use_webctl: bool = False):
        # Added +when:1d to enforce 24h freshness
        self.base_url = "https://news.google.com/rss/search?q=site:{domain}+when:1d&hl=fr&gl=MU&ceid=MU:fr"
        self.use_webctl = use_webctl  # Enable deep extraction via webctl

    async def fetch_for_domain(self, domain: str, limit: int = 5, topic: str = None) -> List[Dict]:
        """Fetch news for a specific domain via Google News RSS."""
        # Construct query: topic OR site query depending on input
        if topic:
            # Query: "topic site:domain when:1d"
            base = "https://news.google.com/rss/search?q={topic}+site:{domain}+when:1d&hl=fr&gl=MU&ceid=MU:fr"
            url = base.format(topic=topic, domain=domain)
        else:
            url = self.base_url.format(domain=domain)
        headlines = []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        content = await resp.text()
                        feed = feedparser.parse(content)
                        for entry in feed.entries[:limit]:
                            # Clean up headline (Google News often adds " - Source" at the end)
                            headline = entry.title
                            if " - " in headline:
                                headline = " - ".join(headline.split(" - ")[:-1])
                            
                            article_data = {
                                'headline': headline,
                                'source': domain.split('.')[0].capitalize(),
                                'url': entry.link
                            }
                            
                            # Optionally extract article body via webctl (expensive, use sparingly)
                            if self.use_webctl and entry.link:
                                body = _extract_article_body_webctl(entry.link)
                                if body:
                                    article_data['body'] = body
                            
                            headlines.append(article_data)
        except Exception as e:
            print(f"Error fetching Google RSS for {domain}: {e}")
            
        return headlines

    async def aggregate_all(self, domains: List[str], limit_per_source: int = 3, topic: str = None) -> List[Dict]:
        """Aggregate news from multiple domains concurrently."""
        tasks = [self.fetch_for_domain(domain, limit_per_source, topic) for domain in domains]
        results = await asyncio.gather(*tasks)
        
        # Flatten results
        all_headlines = []
        for res in results:
            all_headlines.extend(res)
            
        return all_headlines

_google_aggregator = GoogleNewsRSSAggregator()

async def get_google_proxy_news(domains: List[str], limit_per_source: int = 3, topic: str = None) -> List[Dict]:
    """Helper function to get news from blocked sources."""
    return await _google_aggregator.aggregate_all(domains, limit_per_source, topic)
