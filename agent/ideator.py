import logging
from typing import List, Dict, Any, Optional
from agent.llm import llm_client
from agent.db import save_ideas

logger = logging.getLogger(__name__)

ANGLES = [
    "The Contrarian Take (Debunking a popular industry myth)",
    "The Tactical Framework (Step-by-step how-to with actionable bullets)",
    "The Real-World Case Study (Story-driven failure-to-win breakdown)",
    "The Strategic Analysis (Executive-level ROI, org design & macro shift)",
    "The Curated Stack / Cheat Sheet (High-utility tools and resources)"
]

class ContentIdeator:
    def generate_ideas_for_topics(self, topics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Takes researched topics and creates 5 distinct, high-performing LinkedIn content angles.
        """
        logger.info(f"Generating content ideas for {len(topics)} topics")

        topics_summary = "\n".join([
            f"- Topic #{i+1}: {t.get('title')} | Summary: {t.get('summary')} | Key Points: {', '.join(t.get('discussion_points', []) if isinstance(t.get('discussion_points'), list) else [str(t.get('discussion_points'))])}"
            for i, t in enumerate(topics)
        ])

        system_prompt = (
            "You are a top 0.1% LinkedIn ghostwriter and content strategist for Fortune 500 executives, "
            "tech founders, and Senior Product Leaders. You craft ideas designed for maximum dwell time, "
            "genuine discussion, and bookmark-worthy value—avoiding generic AI fluff."
        )

        user_prompt = f"""
Here are the recent researched industry topics:
{topics_summary}

Generate 5 distinct LinkedIn post ideas, each mapped to one of these proven viral formats:
1. The Contrarian Take (call out a flawed trend or myth)
2. The Tactical Framework (practical 4-step framework)
3. The Real-World Case Study (before & after transformation story)
4. The Strategic / Executive Analysis (implications on headcount, budgets, org design)
5. The Curated Stack / Cheat Sheet (actionable checklist)

For each idea, return:
- "topic_title": The corresponding research topic title
- "title": Working headline for the post
- "angle": The format archetype name
- "hook_premise": The compelling first 1-2 sentence hook designed to stop the scroll
- "key_takeaway": The core value or insight the reader walks away with
- "target_audience": E.g. "Product Managers, AI Engineers, Founders, VPs"

Return ONLY a valid JSON array of 5 objects matching this structure.
"""

        result = llm_client.generate_json(user_prompt, system_prompt=system_prompt)

        ideas_to_save = []
        if isinstance(result, list) and len(result) > 0:
            for i, item in enumerate(result[:5]):
                # Map back topic_id if available
                topic_id = topics[i].get("id") if i < len(topics) else None
                item["topic_id"] = topic_id
                ideas_to_save.append(item)
        else:
            # Fallback
            raw = llm_client._smart_fallback("generate ideas for linkedin", json_mode=True)
            try:
                import json
                ideas_to_save = json.loads(raw)[:5]
                for i, it in enumerate(ideas_to_save):
                    it["topic_title"] = topics[i].get("title") if i < len(topics) else "AI & Product Strategy"
                    it["topic_id"] = topics[i].get("id") if i < len(topics) else None
            except Exception:
                ideas_to_save = []

        if ideas_to_save:
            save_ideas(ideas_to_save)

        return ideas_to_save

ideator = ContentIdeator()

