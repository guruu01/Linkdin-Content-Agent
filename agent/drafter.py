import logging
from typing import List, Dict, Any, Optional
from agent.llm import llm_client
from agent.db import save_post_draft

logger = logging.getLogger(__name__)

LINKEDIN_TONES = {
    "thought_leader": "Visionary, authoritative, strategic, synthesizing macro patterns for executive minds.",
    "tactical_pm": "Pragmatic, execution-focused, full of actionable bullet points and day-to-day playbooks.",
    "contrarian": "Bold, questioning status quo, calling out popular industry bad habits with respectful nuance.",
    "storyteller": "Personal, narrative-driven, sharing behind-the-scenes struggles, pivots, and pivotal lessons.",
    "data_driven": "Metrics-oriented, citing benchmarks, unit economics, conversion lifts, and quantitative insights."
}

class LinkedInDrafter:
    def draft_post(self, idea: Dict[str, Any], tone: str = "tactical_pm") -> Dict[str, Any]:
        """
        Drafts a complete, high-converting LinkedIn post tailored to an idea.
        Enforces proper whitespace, hook optimization (before 'see more' cutoff),
        punchy body, engaging CTA, and curated hashtags.
        """
        tone_description = LINKEDIN_TONES.get(tone, LINKEDIN_TONES["tactical_pm"])

        system_prompt = (
            "You are an elite LinkedIn ghostwriter whose posts consistently generate 500k+ impressions and high-quality executive comments.\n"
            "LinkedIn Post Writing Rules:\n"
            "1. Hook: Lines 1 & 2 must be irresistible to stop the scroll before the 'see more' button (~140 chars). No boring greetings like 'Excited to share!'.\n"
            "2. Whitespace: Use 1-2 sentence paragraphs max. Generous spacing for mobile readability.\n"
            "3. Formatting: Use clean unicode bullets (→, •, ✓, ❌) or clean numbers.\n"
            "4. Value: Provide an actionable framework, specific examples, or non-obvious insight. No generic platitudes.\n"
            "5. CTA: End with one clear, thought-provoking question that invites peers to comment.\n"
            "6. Hashtags: End with exactly 3 to 5 highly relevant industry hashtags.\n"
            f"Tone style: {tone_description}"
        )

        user_prompt = f"""
Draft a viral, high-value LinkedIn post based on this idea:
- Topic: {idea.get('topic_title', 'AI & Product Management')}
- Idea Title: {idea.get('title', 'AI Workflow Optimization')}
- Angle: {idea.get('angle', 'Tactical Framework')}
- Hook Premise: {idea.get('hook_premise', '')}
- Key Takeaway: {idea.get('key_takeaway', '')}
- Target Audience: {idea.get('target_audience', 'Product Managers & Tech Leaders')}

Return a JSON object with:
- "hook": The first 1-2 lines before the fold (must be under 140 chars)
- "content": The entire full LinkedIn post (including hook, body, CTA, and hashtags at the end)
- "hashtags": String containing the 3-5 hashtags (e.g. "#ProductManagement #ArtificialIntelligence #TechLeadership")
- "caption": A concise 2-sentence caption suitable if this post is published alongside an infographic or carousel
"""

        result = llm_client.generate_json(user_prompt, system_prompt=system_prompt)

        if not isinstance(result, dict) or "content" not in result:
            raw_fallback = llm_client._smart_fallback("draft linkedin post", json_mode=True)
            try:
                import json
                result = json.loads(raw_fallback)
            except Exception:
                result = {
                    "hook": "73% of AI features launched in SaaS are ghost towns.",
                    "content": "73% of AI features launched in SaaS are ghost towns.\n\nHere is how to fix yours:\n\n1. Stop building chatbots.\n2. Start building background automations.\n\n#ProductManagement #AI",
                    "hashtags": "#ProductManagement #AI #TechLeadership"
                }

        # Build final post object
        content = result.get("content", "").strip()
        hook = result.get("hook", content.split("\n")[0][:140]).strip()
        hashtags = result.get("hashtags", "").strip()

        # Ensure hashtags are included in content if missing
        if hashtags and hashtags not in content:
            content = f"{content}\n\n{hashtags}"

        post_data = {
            "idea_id": idea.get("id"),
            "topic_id": idea.get("topic_id"),
            "source_url": idea.get("source_url", ""),
            "topic": idea.get("topic_title", idea.get("title", "Product Management")),
            "angle": idea.get("angle", "Tactical Framework"),
            "hook": hook,
            "content": content,
            "hashtags": hashtags,
            "character_count": len(content),
            "status": "needs_review",
            "caption": result.get("caption", hook)
        }

        # Save to database
        post_id = save_post_draft(post_data)
        post_data["id"] = post_id
        return post_data

    def draft_batch(self, ideas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Drafts posts for a list of ideas (e.g. 5 posts for the 5 selected weekly topics).
        """
        logger.info(f"Drafting batch of {len(ideas)} posts")
        tones = ["contrarian", "tactical_pm", "storyteller", "thought_leader", "data_driven"]
        drafts = []
        for i, idea in enumerate(ideas):
            tone = tones[i % len(tones)]
            draft = self.draft_post(idea, tone=tone)
            drafts.append(draft)
        return drafts

drafter = LinkedInDrafter()

