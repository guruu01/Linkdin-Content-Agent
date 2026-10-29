import logging
import re
import requests
from typing import Dict, Any, List
from agent.config import settings

logger = logging.getLogger(__name__)

class NotionIntegration:
    def __init__(self):
        self.api_key = settings.NOTION_API_KEY
        raw_db_id = settings.NOTION_DATABASE_ID.strip()
        # Clean URL if user pasted full Notion link
        match = re.search(r"([0-9a-f]{32})", raw_db_id.replace("-", ""))
        self.database_id = match.group(1) if match else raw_db_id

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.database_id)

    def sync_post(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a page in the user's Notion Content Database.
        Automatically maps to existing database properties (e.g. 'Name')
        and formats full content into page blocks.
        """
        if not self.is_configured:
            logger.info("Notion not configured in .env. Simulating Notion sync.")
            return {
                "success": True,
                "mode": "simulated",
                "message": "Notion API key or database ID not provided in .env."
            }

        url = "https://api.notion.com/v1/pages"
        title_text = post.get("topic", post.get("hook", "Untitled LinkedIn Post"))[:100]

        # Break content into paragraphs <= 1900 chars each for Notion block limit
        raw_content = post.get("content", "")
        paragraphs = [p.strip() for p in raw_content.split("\n\n") if p.strip()]
        children_blocks = []

        # Hook callout block
        children_blocks.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": f"🎣 Hook: {post.get('hook', '')[:1800]}"}}],
                "icon": {"emoji": "💡"}
            }
        })

        # Body paragraphs
        for p in paragraphs:
            # Chunk if longer than 1800 chars
            for i in range(0, len(p), 1800):
                children_blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": p[i:i+1800]}}]
                    }
                })

        # Hashtags block
        if post.get("hashtags"):
            children_blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": f"🏷️ {post.get('hashtags')[:1800]}"}}]
                }
            })

        payload = {
            "parent": {"database_id": self.database_id},
            "properties": {
                "Name": {
                    "title": [{"text": {"content": title_text}}]
                }
            },
            "children": children_blocks[:50]  # Notion max 100 children per request
        }

        try:
            resp = requests.post(url, headers=self.headers, json=payload, timeout=12)
            if resp.status_code in (200, 201):
                page_id = resp.json().get("id")
                return {"success": True, "mode": "live", "page_id": page_id}
            else:
                logger.error(f"Notion API error: {resp.status_code} - {resp.text}")
                return {"success": False, "mode": "live", "error": resp.text}
        except Exception as e:
            logger.error(f"Exception during Notion sync: {e}")
            return {"success": False, "mode": "live", "error": str(e)}
            logger.error(f"Exception during Notion sync: {e}")
            return {"success": False, "mode": "live", "error": str(e)}

    def sync_batch(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for post in posts:
            res = self.sync_post(post)
            results.append(res)
        return results

notion_client = NotionIntegration()

