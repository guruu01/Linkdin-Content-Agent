import logging
from typing import Dict, Any, Optional, List
from agent.llm import llm_client
from agent.researcher import researcher
from agent.db import save_repurposed, save_post_draft

logger = logging.getLogger(__name__)

class ArticleRepurposer:
    def repurpose(self, input_text: Optional[str] = None, url: Optional[str] = None) -> Dict[str, Any]:
        """
        Takes an article URL or raw long text and converts it into:
        1. Single high-converting LinkedIn post.
        2. 5-7 Slide PDF Carousel Outline (perfect for LinkedIn document posts).
        3. 3-Part Sequential Mini-Series.
        """
        source_title = "Repurposed Industry Article"
        article_text = ""

        if url:
            logger.info(f"Fetching article from URL: {url}")
            fetched = researcher.fetch_article_text(url)
            source_title = fetched.get("title", "Article from Web")
            article_text = fetched.get("content", "")

        if not article_text and input_text:
            article_text = input_text
            lines = [l.strip() for l in input_text.split("\n") if l.strip()]
            if lines:
                source_title = lines[0][:80]

        if not article_text:
            article_text = "Modern product managers are transitioning from writing extensive static PRDs to orchestrating agentic workflows and dynamic customer feedback telemetry."

        # Truncate if excessively long
        article_snippet = article_text[:4000]

        system_prompt = (
            "You are a master LinkedIn content repurposer. You take long-form articles, whitepapers, or transcripts "
            "and distill them into magnetic LinkedIn formats: single punchy posts, multi-slide PDF carousels, and mini-series."
        )

        user_prompt = f"""
Article Title: {source_title}
Article Content:
{article_snippet}

Repurpose this article into 3 high-impact LinkedIn content formats:

1. "summary": A concise 2-sentence executive summary of the article's core thesis.
2. "post_content": A standalone viral LinkedIn post (Hook, formatted body with whitespace, bullet points, question CTA, and 3-5 hashtags).
3. "carousel_slides": An array of 5 to 6 slide objects for a LinkedIn PDF document carousel:
   - "slide_number": int
   - "title": punchy slide headline
   - "body": 1-2 bullet points or short text for the slide
   - "visual_cue": design instruction (e.g. "Minimal dark slide with bold white text", "Diagram comparing A vs B")
4. "mini_series": An array of 3 distinct posts meant to be published over 3 days (Day 1: The Problem/Data, Day 2: The Solution Framework, Day 3: Practical Implementation). Each object has "day": 1..3, "theme": str, "content": str.

Return ONLY a valid JSON object matching this structure.
"""

        result = llm_client.generate_json(user_prompt, system_prompt=system_prompt)

        # Fallback handling
        if not isinstance(result, dict) or "post_content" not in result:
            result = {
                "summary": "This article explores how product managers can replace bureaucratic documentation with AI agents.",
                "post_content": f"Most product documentation is where good ideas go to die.\n\nHere are 3 rules to modernize your workflow:\n\n1. Replace 30-page PRDs with interactive prototypes.\n2. Ingest customer call transcripts with AI clustering.\n3. Measure outcome velocity instead of ticket completion.\n\nWhat is your biggest bottleneck in product planning?\n\n#ProductManagement #AI #Strategy",
                "carousel_slides": [
                    {"slide_number": 1, "title": "The Death of the 30-Page PRD", "body": "Why modern teams are ditching static specs for interactive prototypes.", "visual_cue": "Bold title on navy background"},
                    {"slide_number": 2, "title": "Problem #1: Nobody Reads Them", "body": "Engineers skim. Stakeholders miss context. Edge cases are discovered in QA.", "visual_cue": "Split comparison graphic"},
                    {"slide_number": 3, "title": "The Alternative: Agentic Specs", "body": "1. Ingest customer calls\n2. Auto-generate user journey maps\n3. Spin up functional mockups in 1 hour.", "visual_cue": "Step-by-step flowchart"},
                    {"slide_number": 4, "title": "The Real Impact", "body": "PMs spend 60% less time writing docs and 3x more time with users.", "visual_cue": "Key metric callout: 60% time saved"},
                    {"slide_number": 5, "title": "Save This Cheat Sheet", "body": "Swipe left for more product frameworks or comment 'PRD' for the template.", "visual_cue": "Author photo & follow CTA"}
                ],
                "mini_series": [
                    {"day": 1, "theme": "The Problem", "content": "Why 30-page PRDs fail modern engineering teams... #ProductManagement"},
                    {"day": 2, "theme": "The Solution", "content": "The 3-step Agentic PRD workflow used by high-velocity startups... #ProductManagement"},
                    {"day": 3, "theme": "Execution", "content": "How to transition your team to outcome-driven specs in 14 days... #ProductManagement"}
                ]
            }

        result["source_url"] = url or ""
        result["source_title"] = source_title

        # Save to database
        rep_id = save_repurposed(result)
        result["id"] = rep_id

        # Also create a draft post in the posts queue from post_content
        post_draft_id = save_post_draft({
            "topic": source_title,
            "angle": "Repurposed Article",
            "hook": result["post_content"].split("\n")[0][:140],
            "content": result["post_content"],
            "hashtags": "#ProductManagement #RepurposedContent #ThoughtLeadership",
            "status": "needs_review"
        })
        result["draft_post_id"] = post_draft_id

        return result

repurposer = ArticleRepurposer()

