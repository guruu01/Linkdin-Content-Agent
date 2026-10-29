import logging
import urllib.parse
from typing import List, Dict, Any, Optional
from agent.config import settings
from agent.db import update_post_status

logger = logging.getLogger(__name__)

class WhatsAppNotifier:
    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_WHATSAPP_FROM
        self.to_number = settings.RECIPIENT_WHATSAPP_NUMBER
        self._twilio_client = None

        if self.account_sid and self.auth_token:
            try:
                from twilio.rest import Client
                self._twilio_client = Client(self.account_sid, self.auth_token)
            except Exception as e:
                logger.warning(f"Could not initialize Twilio client: {e}")

    @property
    def is_twilio_configured(self) -> bool:
        return bool(self._twilio_client and self.to_number)

    def format_review_message(self, posts: List[Dict[str, Any]], host: str = "http://localhost:8000") -> str:
        """
        Creates an engaging, easy-to-read WhatsApp review digest.
        """
        lines = [
            "👋 *Good morning!*",
            "🚀 *Your Monday LinkedIn Content Batch is ready for review:*\n"
        ]

        for i, post in enumerate(posts, 1):
            topic = post.get("topic", "Industry Insight")
            angle = post.get("angle", "Framework")
            hook = post.get("hook", "").replace("\n", " ")[:90]
            post_id = post.get("id")
            lines.append(f"*{i}. {topic}*")
            lines.append(f"📌 _Angle:_ {angle}")
            lines.append(f"🎣 _Hook:_ \"{hook}...\"")
            lines.append(f"🔗 Review & Edit: {host}/#post-{post_id}\n")

        lines.append("────────────────")
        lines.append("📲 *Quick Actions:*")
        lines.append("• Open dashboard to approve/edit: " + host)
        lines.append("• Or reply: *APPROVE 1* or *APPROVE ALL*")

        return "\n".join(lines)

    def generate_wa_me_link(self, message: str, phone: Optional[str] = None) -> str:
        """
        Generates a 1-click wa.me link that opens WhatsApp directly with the pre-filled message.
        """
        target = phone or self.to_number or ""
        # Clean phone: remove 'whatsapp:', '+', spaces, dashes
        clean_num = target.replace("whatsapp:", "").replace("+", "").replace(" ", "").replace("-", "")
        encoded = urllib.parse.quote(message)
        if clean_num:
            return f"https://wa.me/{clean_num}?text={encoded}"
        return f"https://wa.me/?text={encoded}"

    def send_review_digest(self, posts: List[Dict[str, Any]], host: str = "http://localhost:8000") -> Dict[str, Any]:
        """
        Sends the review digest via Twilio WhatsApp if configured,
        and always generates the direct 1-click wa.me review link.
        """
        message = self.format_review_message(posts, host)
        wa_link = self.generate_wa_me_link(message)

        result = {
            "success": True,
            "mode": "wa_link",
            "message_text": message,
            "wa_me_link": wa_link,
            "recipient": self.to_number or "Direct Web/App Link"
        }

        if self.is_twilio_configured:
            try:
                msg = self._twilio_client.messages.create(
                    body=message,
                    from_=self.from_number,
                    to=self.to_number
                )
                result["mode"] = "twilio_live"
                result["twilio_sid"] = msg.sid
                logger.info(f"Sent live WhatsApp message via Twilio SID: {msg.sid}")
            except Exception as e:
                logger.error(f"Failed to send Twilio WhatsApp message: {e}")
                result["twilio_error"] = str(e)

        return result

    def handle_incoming_reply(self, text: str) -> str:
        """
        Processes replies received from WhatsApp (e.g. 'APPROVE 1', 'APPROVE ALL').
        """
        t = text.strip().upper()
        if "APPROVE ALL" in t:
            # We can approve all pending posts
            from agent.db import get_posts
            pending = get_posts(status="needs_review")
            for p in pending:
                update_post_status(p["id"], "approved", notes="Approved via WhatsApp")
            return f"✅ Approved all {len(pending)} pending LinkedIn posts! Ready to publish."
        
        elif "APPROVE" in t:
            parts = t.split()
            if len(parts) >= 2 and parts[1].isdigit():
                post_num = int(parts[1])
                # Find post by ID or index
                from agent.db import get_post_by_id, get_posts
                post = get_post_by_id(post_num)
                if not post:
                    pending = get_posts(status="needs_review")
                    if 0 < post_num <= len(pending):
                        post = pending[post_num - 1]
                
                if post:
                    update_post_status(post["id"], "approved", notes="Approved via WhatsApp")
                    return f"✅ Post #{post['id']} (\"{post['topic']}\") has been approved for publication!"

        return "Received your message! Open your dashboard at http://localhost:8000 to manage your posts."

whatsapp_notifier = WhatsAppNotifier()

