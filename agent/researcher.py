import urllib.parse
import logging
import feedparser
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from agent.llm import llm_client
from agent.db import save_topics

logger = logging.getLogger(__name__)

# Curated high-signal RSS feeds
RSS_FEEDS = {
    "Hacker News": "https://news.ycombinator.com/rss",
    "TechCrunch": "https://techcrunch.com/feed/",
    "ArXiv AI": "http://export.arxiv.org/rss/cs.AI",
    "VentureBeat AI": "https://venturebeat.com/category/ai/feed/"
}

class TopicResearcher:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def fetch_google_news(self, query: str, limit: int = 8) -> List[Dict[str, Any]]:
        """
        Fetches live news headlines and summaries from Google News RSS for any given topic query.
        """
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
        items = []
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:limit]:
                # Extract clean summary
                summary = ""
                if hasattr(entry, "summary"):
                    soup = BeautifulSoup(entry.summary, "html.parser")
                    summary = soup.get_text()

                items.append({
                    "title": entry.title,
                    "url": entry.link if hasattr(entry, "link") else "",
                    "source": entry.source.title if hasattr(entry, "source") and hasattr(entry.source, "title") else "Google News",
                    "published": entry.published if hasattr(entry, "published") else "",
                    "raw_summary": summary
                })
        except Exception as e:
            logger.warning(f"Error fetching Google News for '{query}': {e}")
        return items

    def fetch_curated_rss(self, feed_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        url = RSS_FEEDS.get(feed_name)
        if not url:
            return []
        items = []
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:limit]:
                summary = ""
                if hasattr(entry, "summary"):
                    soup = BeautifulSoup(entry.summary, "html.parser")
                    summary = soup.get_text()[:300]
                items.append({
                    "title": entry.title,
                    "url": entry.link if hasattr(entry, "link") else "",
                    "source": feed_name,
                    "published": entry.published if hasattr(entry, "published") else "",
                    "raw_summary": summary
                })
        except Exception as e:
            logger.warning(f"Error fetching RSS for {feed_name}: {e}")
        return items

    def fetch_article_text(self, url: str) -> Dict[str, str]:
        """
        Scrapes and cleans text from an article URL.
        """
        try:
            resp = requests.get(url, headers=self.headers, timeout=8)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                title = soup.title.string.strip() if soup.title else "Article"
                paragraphs = [p.get_text().strip() for p in soup.find_all("p") if len(p.get_text().strip()) > 40]
                body = "\n\n".join(paragraphs[:10])  # First 10 paragraphs
                return {"title": title, "content": body}
        except Exception as e:
            logger.warning(f"Failed to fetch article text from {url}: {e}")
        return {"title": "Web Article", "content": ""}

    def research_topic_trends(self, topic_query: str = "AI and product management developments", count: int = 5) -> List[Dict[str, Any]]:
        """
        Full research workflow:
        1. Queries Google News + Hacker News / TechCrunch for raw items.
        2. Synthesizes findings using LLM into top `count` trending discussions.
        3. Identifies debates, friction points, and LinkedIn engagement hooks.
        4. Saves to database and returns structured results.
        """
        logger.info(f"Researching topic: {topic_query}")
        raw_items = self.fetch_google_news(topic_query, limit=10)
        
        # If live items are few, supplement with Hacker News & TechCrunch
        if len(raw_items) < 5:
            raw_items.extend(self.fetch_curated_rss("Hacker News", limit=3))
            raw_items.extend(self.fetch_curated_rss("TechCrunch", limit=3))

        raw_context = "\n".join([
            f"[{i+1}] Title: {it['title']} | Source: {it['source']} | Real URL: {it.get('url', '')}"
            for i, it in enumerate(raw_items)
        ])

        system_prompt = (
            "You are a Principal Product & AI Industry Research Analyst. "
            "Your job is to identify high-signal, trending industry discussions and debates that will resonate strongly with professionals on LinkedIn."
        )

        user_prompt = f"""
Given the following raw industry news headlines and signals regarding '{topic_query}':
{raw_context if raw_context.strip() else f"General industry developments in {topic_query}"}

Select or synthesize exactly {count} distinct, high-impact topics/discussions.
CRITICAL INSTRUCTION FOR URL:
- You MUST copy the exact "Real URL" provided in the items above for your topic.
- Do NOT fabricate or guess fake URLs. If no URL matches, use empty string "".

For each topic, provide:
- "title": Compelling industry theme or event title
- "source": Primary publication or community source
- "url": The exact Real URL from above
- "summary": 2-sentence executive summary of the shift or announcement
- "discussion_points": 3 provocative questions or debate angles dividing experts
- "trending_score": Number between 8.0 and 9.9 indicating virality/relevance potential

Return ONLY a valid JSON array of {count} objects matching this structure.
"""

        result = llm_client.generate_json(user_prompt, system_prompt=system_prompt)

        # Fallback or validate format
        topics_to_save = []
        if isinstance(result, list) and len(result) > 0:
            for i, item in enumerate(result[:count]):
                item["query"] = topic_query
                u = item.get("url", "").strip()
                
                # Check if URL is valid or needs mapping to live feed URL / Google Search
                if not u or not u.startswith("http") or any(fake in u for fake in ["example.com", "hbr.org/2024", "sloanreview.mit.edu/article", "mckinsey.com/insights/agentic"]):
                    if i < len(raw_items) and raw_items[i].get("url"):
                        item["url"] = raw_items[i]["url"]
                    else:
                        title_clean = item.get("title", topic_query)
                        item["url"] = f"https://www.google.com/search?q={urllib.parse.quote_plus(title_clean + ' ' + item.get('source', ''))}"
                
                topics_to_save.append(item)
        else:
            # Smart fallback
            raw_fallback = llm_client._smart_fallback("research topic " + topic_query, json_mode=True)
            try:
                import json
                topics_to_save = json.loads(raw_fallback)[:count]
                for i, item in enumerate(topics_to_save):
                    item["query"] = topic_query
                    if i < len(raw_items) and raw_items[i].get("url"):
                        item["url"] = raw_items[i]["url"]
                    else:
                        title_clean = item.get("title", topic_query)
                        item["url"] = f"https://www.google.com/search?q={urllib.parse.quote_plus(title_clean)}"
            except Exception:
                topics_to_save = []

        if topics_to_save:
            ids = save_topics(topics_to_save)
            for i, tid in enumerate(ids):
                if i < len(topics_to_save):
                    topics_to_save[i]["id"] = tid

        return topics_to_save

researcher = TopicResearcher()

