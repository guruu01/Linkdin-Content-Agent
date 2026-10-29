import logging
from datetime import datetime
from typing import Dict, Any, Callable, Optional, List

from agent.config import settings
from agent.researcher import researcher
from agent.ideator import ideator
from agent.drafter import drafter
from agent.integrations.sheets import sheets_client
from agent.integrations.notion import notion_client
from agent.integrations.whatsapp import whatsapp_notifier
from agent.integrations.linkedin import linkedin_publisher
from agent.db import record_workflow_run, get_posts

logger = logging.getLogger(__name__)

class ContentWorkflow:
    def run_weekly_workflow(
        self,
        topic_query: Optional[str] = None,
        host_url: str = "http://localhost:8000",
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes the complete Monday morning workflow:
        1. Research AI & product management developments
        2. Select 5 relevant topics
        3. Generate 5 LinkedIn post drafts
        4. Save drafts to Google Sheets / Excel and Notion
        5. Send WhatsApp message for review
        6. Publish approved content (if auto-publish enabled)
        """
        query = topic_query or settings.DEFAULT_TOPIC
        logger.info(f"Starting Weekly LinkedIn Content Workflow for: '{query}'")

        def emit(msg: str, step_num: int):
            logger.info(f"[Step {step_num}/6] {msg}")
            if progress_callback:
                progress_callback(msg, step_num)

        summary = {
            "run_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "topic_query": query,
            "steps": [],
            "topics": [],
            "drafts": [],
            "sheets_result": {},
            "notion_result": {},
            "whatsapp_result": {},
            "published_posts": []
        }

        try:
            # 1. Research
            emit(f"Step 1: Researching latest developments in '{query}'...", 1)
            topics = researcher.research_topic_trends(query, count=5)
            summary["topics"] = topics
            summary["steps"].append({"step": 1, "name": "Topic Research", "status": "completed", "count": len(topics)})

            # 2. Select 5 topics & generate ideas
            emit("Step 2: Selecting 5 relevant topics and formulating viral content angles...", 2)
            ideas = ideator.generate_ideas_for_topics(topics)
            summary["ideas"] = ideas
            summary["steps"].append({"step": 2, "name": "Idea Generation", "status": "completed", "count": len(ideas)})

            # 3. Generate 5 post drafts
            emit("Step 3: Drafting 5 full LinkedIn posts with scroll-stopping hooks & hashtags...", 3)
            drafts = drafter.draft_batch(ideas)
            summary["drafts"] = drafts
            summary["steps"].append({"step": 3, "name": "Post Drafting", "status": "completed", "count": len(drafts)})

            # 4. Save to Sheets & Notion
            emit("Step 4: Syncing drafts to Google Sheets / Content Calendar and Notion...", 4)
            sheets_res = sheets_client.sync_batch(drafts)
            notion_res = notion_client.sync_batch(drafts)
            summary["sheets_result"] = sheets_res
            summary["notion_result"] = notion_res
            summary["steps"].append({"step": 4, "name": "Storage & Sync", "status": "completed"})

            # 5. WhatsApp review notification
            emit("Step 5: Sending WhatsApp message with review digest & approval links...", 5)
            wa_res = whatsapp_notifier.send_review_digest(drafts, host=host_url)
            summary["whatsapp_result"] = wa_res
            summary["steps"].append({"step": 5, "name": "WhatsApp Review", "status": "completed", "wa_link": wa_res.get("wa_me_link")})

            # 6. Publish approved content
            emit("Step 6: Checking and publishing approved content through LinkedIn integration...", 6)
            published = []
            if settings.AUTO_PUBLISH_APPROVED:
                # If auto-publish enabled, check for any posts marked 'approved'
                approved_posts = get_posts(status="approved")
                for post in approved_posts:
                    pub_res = linkedin_publisher.publish_post(post)
                    published.append({"post_id": post["id"], "result": pub_res})
            summary["published_posts"] = published
            summary["steps"].append({"step": 6, "name": "Publishing Integration", "status": "completed", "published_count": len(published)})

            # Record run
            record_workflow_run({
                "run_date": summary["run_date"],
                "topic_query": query,
                "topics_count": len(topics),
                "posts_count": len(drafts),
                "sheets_synced": True,
                "notion_synced": notion_client.is_configured,
                "whatsapp_sent": True,
                "status": "success",
                "details": f"Generated {len(drafts)} posts for '{query}'"
            })

            emit("[SUCCESS] Weekly Content Workflow completed successfully!", 6)
            return summary

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}", exc_info=True)
            record_workflow_run({
                "run_date": summary["run_date"],
                "topic_query": query,
                "topics_count": len(summary["topics"]),
                "posts_count": len(summary["drafts"]),
                "sheets_synced": False,
                "notion_synced": False,
                "whatsapp_sent": False,
                "status": "failed",
                "details": str(e)
            })
            raise e

workflow_manager = ContentWorkflow()
