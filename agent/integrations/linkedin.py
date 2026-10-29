import logging
import urllib.parse
import requests
from typing import Dict, Any, Optional
from agent.config import settings
from agent.db import update_post_status

logger = logging.getLogger(__name__)

class LinkedInPublisher:
    def __init__(self):
        self.access_token = settings.LINKEDIN_ACCESS_TOKEN
        self.author_urn = settings.LINKEDIN_AUTHOR_URN
        self.api_url = "https://api.linkedin.com/v2/ugcPosts"

    @property
    def is_api_configured(self) -> bool:
        return bool(self.access_token and self.author_urn)

    def generate_share_url(self, post_content: str) -> str:
        """
        Creates a 1-click direct browser share URL for LinkedIn.
        Opens LinkedIn feed composer with text pre-loaded!
        """
        encoded = urllib.parse.quote(post_content)
        return f"https://www.linkedin.com/feed/?shareActive=true&text={encoded}"

    def publish_post(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """
        Publishes the post via LinkedIn API (if configured) or generates direct share intent.
        """
        post_id = post.get("id")
        content = post.get("content", "").strip()

        # Validation
        if len(content) > 3000:
            return {
                "success": False,
                "error": f"Content exceeds LinkedIn limit of 3000 characters (current: {len(content)})"
            }

        share_url = self.generate_share_url(content)

        if self.is_api_configured:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            }
            payload = {
                "author": self.author_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": content
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }

            try:
                resp = requests.post(self.api_url, headers=headers, json=payload, timeout=12)
                if resp.status_code in (200, 201):
                    data = resp.json()
                    ugc_id = data.get("id", "")
                    if post_id:
                        update_post_status(post_id, "published", notes=f"Published via LinkedIn API (UGC ID: {ugc_id})")
                    return {
                        "success": True,
                        "mode": "api_live",
                        "ugc_id": ugc_id,
                        "message": "Published to LinkedIn successfully!",
                        "share_url": share_url
                    }
                else:
                    logger.error(f"LinkedIn API error {resp.status_code}: {resp.text}")
                    return {
                        "success": False,
                        "mode": "api_live",
                        "error": resp.text,
                        "share_url": share_url
                    }
            except Exception as e:
                logger.error(f"Exception publishing to LinkedIn API: {e}")
                return {
                    "success": False,
                    "mode": "api_live",
                    "error": str(e),
                    "share_url": share_url
                }

        # If API not configured, mark approved/published and return 1-click share intent
        if post_id:
            update_post_status(post_id, "published", notes="Published via 1-click LinkedIn Share Intent")

        return {
            "success": True,
            "mode": "share_intent",
            "message": "Ready to publish! Click the direct LinkedIn share link to open in LinkedIn.",
            "share_url": share_url
        }

linkedin_publisher = LinkedInPublisher()

