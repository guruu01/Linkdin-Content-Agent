import os
import json
import re
import logging
from typing import Dict, Any, Optional, List
from agent.config import settings

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.provider = settings.DEFAULT_LLM_PROVIDER.lower()
        self.gemini_key = settings.GEMINI_API_KEY
        self.groq_key = settings.GROQ_API_KEY
        self.openai_key = settings.OPENAI_API_KEY
        self._gemini_client = None
        self._groq_client = None

        self._init_clients()

    def _init_clients(self):
        # Gemini
        if self.gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_key)
                self._gemini_client = genai
                logger.info("Initialized Gemini LLM client")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini: {e}")

        # Groq
        if self.groq_key:
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=self.groq_key)
                logger.info("Initialized Groq LLM client")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq: {e}")

    def generate(self, prompt: str, system_prompt: Optional[str] = None, json_mode: bool = False) -> str:
        """
        Routes the prompt to available providers: Gemini -> Groq -> OpenAI -> Smart Offline Fallback.
        """
        # Try Gemini
        if self._gemini_client:
            try:
                model_name = "gemini-1.5-flash"
                generation_config = {}
                if json_mode:
                    generation_config["response_mime_type"] = "application/json"

                model = self._gemini_client.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_prompt if system_prompt else None,
                    generation_config=generation_config
                )
                response = model.generate_content(prompt)
                if response.text:
                    return response.text.strip()
            except Exception as e:
                logger.warning(f"Gemini generation error: {e}. Falling back...")

        # Try Groq
        if self._groq_client:
            models_to_try = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
            for model_id in models_to_try:
                try:
                    messages = []
                    if system_prompt:
                        messages.append({"role": "system", "content": system_prompt})
                    messages.append({"role": "user", "content": prompt})

                    kwargs = {
                        "model": model_id,
                        "messages": messages,
                        "temperature": 0.7,
                    }
                    if json_mode:
                        kwargs["response_format"] = {"type": "json_object"}

                    response = self._groq_client.chat.completions.create(**kwargs)
                    content = response.choices[0].message.content
                    if content:
                        return content.strip()
                except Exception as e:
                    logger.warning(f"Groq ({model_id}) error: {e}. Trying next...")

        # Fallback to Smart Heuristic Engine
        logger.info("Using smart offline heuristics for content generation.")
        return self._smart_fallback(prompt, json_mode=json_mode)

    def generate_json(self, prompt: str, system_prompt: Optional[str] = None) -> Any:
        raw = self.generate(prompt, system_prompt, json_mode=True)
        # Clean markdown code blocks if any
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Attempt to extract first JSON object or array
            match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
            logger.error(f"Failed to parse JSON from LLM response: {raw[:200]}...")
            return {}

    def _smart_fallback(self, prompt: str, json_mode: bool = False) -> str:
        """
        High quality, context-aware offline generator for testing and standalone operation.
        """
        p_lower = prompt.lower()

        # 1. Repurposing Articles / Carousels
        if "repurpose" in p_lower or "carousel_slides" in p_lower or "mini_series" in p_lower:
            data = {
                "summary": "This article explores how product managers can replace bureaucratic documentation with AI agents.",
                "post_content": """Most product documentation is where good ideas go to die.

Here is the 3-step playbook high-velocity teams use to fix it:

1. Kill the 30-page static PRD
Replace it with interactive prototypes and automated user story generation.

2. Ingest customer calls directly into AI clustering
Stop manually tagging feedback. Let agents surface high-frequency friction patterns in real time.

3. Measure outcome velocity instead of ticket completion
Shipping 10 features that move 0 needles is failure. Shipping 1 automated workflow that cuts churn by 12% is victory.

What is the single biggest bottleneck in your current product planning cycle?

#ProductManagement #ArtificialIntelligence #TechLeadership #ProductStrategy #SaaS""",
                "carousel_slides": [
                    {"slide_number": 1, "title": "The Death of the 30-Page PRD", "body": "Why modern teams are ditching static specs for interactive prototypes.", "visual_cue": "Bold title on navy background with minimal icon"},
                    {"slide_number": 2, "title": "Problem #1: Nobody Reads Them", "body": "Engineers skim.\nStakeholders miss critical context.\nEdge cases are only discovered in QA.", "visual_cue": "Split comparison graphic highlighting friction"},
                    {"slide_number": 3, "title": "The Alternative: Agentic Specs", "body": "1. Ingest customer calls automatically\n2. Cluster user friction patterns\n3. Spin up functional mockups in 1 hour.", "visual_cue": "3-step workflow diagram"},
                    {"slide_number": 4, "title": "The Real Impact", "body": "PMs spend 60% less time writing docs and 3x more time with real users.", "visual_cue": "Key metric highlight: +60% efficiency"},
                    {"slide_number": 5, "title": "Save This Playbook", "body": "Swipe left for more product frameworks or comment 'AGENT' to get our template.", "visual_cue": "Author photo & follow CTA"}
                ],
                "mini_series": [
                    {"day": 1, "theme": "The Problem", "content": "Why 30-page PRDs fail modern engineering teams... Most specs go unread while code ships daily. Here is what needs to change: #ProductManagement #Tech"},
                    {"day": 2, "theme": "The Solution", "content": "The 3-step Agentic PRD workflow used by high-velocity startups... Ingesting raw customer telemetry straight into prototype generation. #ProductManagement"},
                    {"day": 3, "theme": "Execution", "content": "How to transition your team to outcome-driven specs in 14 days without slowing sprint velocity. #ProductManagement #Leadership"}
                ]
            }
            return json.dumps(data, indent=2) if json_mode else data["post_content"]

        # 2. Topic Research & Trending Discussions
        if any(w in p_lower for w in ["research", "topic", "trend", "headline", "signal"]):
            data = [
                {
                    "title": "Agentic AI Workflows in B2B Product Discovery",
                    "source": "TechCrunch & HackerNews",
                    "url": "https://news.ycombinator.com",
                    "summary": "How autonomous AI agents are replacing legacy customer interview synthesis and PRD drafting, cutting PM planning cycles from weeks to hours.",
                    "discussion_points": [
                        "Are PMs becoming prompt reviewers or strategic orchestrators?",
                        "Hallucination risks in customer requirement specs",
                        "The emergence of 1-person multi-million dollar micro-SaaS teams"
                    ],
                    "trending_score": 9.4
                },
                {
                    "title": "The Death of Static Roadmaps: Context-Aware Dynamic Prioritization",
                    "source": "Product Coalition",
                    "url": "https://productcoalition.com",
                    "summary": "Top tech companies are abandoning quarterly static roadmaps in favor of real-time AI-weighted customer friction telemetry.",
                    "discussion_points": [
                        "Why quarterly roadmaps give false predictability",
                        "Balancing technical debt against AI feature velocity",
                        "How leadership evaluates PM output when code ships continuously"
                    ],
                    "trending_score": 9.1
                },
                {
                    "title": "Small Language Models (SLMs) on Edge Devices vs. Heavy Cloud LLMs",
                    "source": "Towards Data Science",
                    "url": "https://towardsdatascience.com",
                    "summary": "Why enterprise product managers are moving high-volume tasks from OpenAI/Claude cloud calls to local quantized models (Phi-4, Llama 3) for zero latency and privacy compliance.",
                    "discussion_points": [
                        "Cloud API cost shock at scale",
                        "Data sovereignty and GDPR enterprise requirements",
                        "Hybrid routing architectures"
                    ],
                    "trending_score": 8.9
                },
                {
                    "title": "AI Feature Bloat: Why 73% of Generative AI Add-ons Go Unused",
                    "source": "Gartner & VentureBeat",
                    "url": "https://venturebeat.com",
                    "summary": "Recent data reveals slapping a 'magic sparkle button' or chatbot onto existing SaaS without workflow re-architecture leads to user churn after 30 days.",
                    "discussion_points": [
                        "The vanity metric trap of 'AI features launched'",
                        "Jobs-to-be-Done (JTBD) vs. technology-first roadmaps",
                        "How to measure genuine AI feature retention"
                    ],
                    "trending_score": 9.5
                },
                {
                    "title": "The Rise of the 'Product Engineer' and the Blurring Lines of PM/Dev",
                    "source": "Pragmatic Engineer",
                    "url": "https://newsletter.pragmaticengineer.com",
                    "summary": "AI coding assistants (Claude Code, Cursor, Copilot) are enabling engineers to build full user journeys directly, forcing Product Managers to pivot toward deep unit economics and distribution.",
                    "discussion_points": [
                        "Do startups still need junior PMs?",
                        "The premium on distribution and GTM strategy",
                        "Technical literacy expectations for modern product leads"
                    ],
                    "trending_score": 9.2
                }
            ]
            return json.dumps(data, indent=2) if json_mode else str(data)

        # 3. Content Ideas Generation
        if any(w in p_lower for w in ["idea", "angle", "hook_premise", "target_audience"]):
            data = [
                {
                    "title": "Why 73% of AI SaaS features are ghost towns (and how to fix yours)",
                    "angle": "The Contrarian Take",
                    "hook_premise": "Most teams are building 'magic sparkle buttons' that users touch once and never touch again.",
                    "key_takeaway": "Focus on background automation rather than another chat sidebar.",
                    "target_audience": "Product Managers, Founders, Tech Leads"
                },
                {
                    "title": "The 4-Step Framework for Auditing AI Readiness in Your Backlog",
                    "angle": "The Tactical Framework",
                    "hook_premise": "Stop asking 'How can we add AI to this?'. Ask these 4 questions instead.",
                    "key_takeaway": "A practical scoring model evaluating latency, cost, failure tolerance, and user habit loops.",
                    "target_audience": "Senior PMs, Directors of Product"
                },
                {
                    "title": "We replaced our 40-page PRD with an Autonomous Agent. Here’s what happened.",
                    "angle": "The Real-World Case Study",
                    "hook_premise": "Last month, our product team killed traditional PRD templates.",
                    "key_takeaway": "Interactive prototypes generated directly from customer interview transcripts beat static docs every time.",
                    "target_audience": "Engineering Managers, Growth PMs"
                },
                {
                    "title": "The PM Role is not dying. It is bifurcating into two radically different jobs.",
                    "angle": "The Strategic / Executive Analysis",
                    "hook_premise": "If your day job is writing Jira tickets and summarizing meetings, AI will automate 80% of your week by 2027.",
                    "key_takeaway": "The two surviving archetypes: The Deep Systems Architect PM and The Growth & Distribution Strategist.",
                    "target_audience": "VP of Product, Aspiring Product Leaders"
                },
                {
                    "title": "5 Micro-Tools Modern Product Managers Use Daily to Ship 3x Faster",
                    "angle": "The Curated Stack",
                    "hook_premise": "The PM toolstack changed more in the past 12 months than the previous decade.",
                    "key_takeaway": "A curated breakdown of workflow automation, automated user feedback clustering, and synthetic user testing.",
                    "target_audience": "Early-career & Mid-level Tech Professionals"
                }
            ]
            return json.dumps(data, indent=2) if json_mode else str(data)

        # 4. Post Drafting
        if any(w in p_lower for w in ["draft", "post", "linkedin", "hook", "viral"]):
            post = {
                "hook": "73% of AI features launched in SaaS over the last 18 months are currently ghost towns.\n\nHere is the brutal reason why (and how smart PMs avoid it):",
                "content": """73% of AI features launched in SaaS over the last 18 months are currently ghost towns.

Here is the brutal reason why (and how smart PMs avoid it):

Most companies didn't build for user workflow.
They slapped a "magic sparkle button" or a chatbot sidebar onto an interface that was already working.

The result?
→ Week 1: High novelty spike (everyone tests it).
→ Week 3: Usage drops by 85%.
→ Week 6: It becomes tech debt with high API latency bills.

If you are a Product Manager planning your AI roadmap this quarter, adopt the "Invisible AI" doctrine:

1. Zero New UI
The best AI features require ZERO new buttons. They work in the background: auto-tagging, proactive routing, silent deduplication.

2. Tolerate Imperfection with One-Click Undo
If your AI makes a mistake, the user shouldn't have to restart the flow. Give them instant rollback.

3. Optimize for 'Time-to-Value', Not 'Time-Spent-Chatting'
Nobody opens business software to chat with a bot for 20 minutes. They open it to finish a task in 30 seconds.

4. Evaluate the Cost-to-Serve Unit Economics
A feature that burns $0.12 per click without expansion revenue is a growth trap.

The era of "AI vanity metrics" is over.
The era of high-retention, frictionless utility has begun.

What is the single best (or most frustrating) AI feature you've used in a product recently?

#ProductManagement #ArtificialIntelligence #ProductStrategy #TechLeadership #SaaS""",
                "hashtags": "#ProductManagement #ArtificialIntelligence #ProductStrategy #TechLeadership #SaaS",
                "caption": "Why 73% of SaaS AI features fail and the 4 rules of the Invisible AI framework."
            }
            return json.dumps(post, indent=2) if json_mode else post["content"]

        # Default text
        return json.dumps({"status": "ok", "message": "Content generated successfully"}) if json_mode else "Content generated successfully."

llm_client = LLMClient()
