import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from agent.config import DB_PATH

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT,
        title TEXT,
        source TEXT,
        url TEXT,
        summary TEXT,
        discussion_points TEXT,
        trending_score REAL DEFAULT 8.5,
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ideas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id INTEGER,
        topic_title TEXT,
        title TEXT,
        angle TEXT,
        hook_premise TEXT,
        key_takeaway TEXT,
        target_audience TEXT,
        status TEXT DEFAULT 'idea',
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        idea_id INTEGER,
        topic_id INTEGER,
        topic TEXT,
        angle TEXT,
        hook TEXT,
        content TEXT,
        hashtags TEXT,
        character_count INTEGER,
        status TEXT DEFAULT 'needs_review',
        scheduled_for TEXT,
        published_at TEXT,
        notion_page_id TEXT,
        sheets_synced INTEGER DEFAULT 0,
        whatsapp_sent INTEGER DEFAULT 0,
        review_notes TEXT,
        source_url TEXT,
        created_at TEXT
    )
    """)
    # Migrations for existing DBs
    try:
        cursor.execute("ALTER TABLE posts ADD COLUMN source_url TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE posts ADD COLUMN topic_id INTEGER")
    except Exception:
        pass

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS repurposed_articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_url TEXT,
        source_title TEXT,
        summary TEXT,
        post_content TEXT,
        carousel_slides TEXT,
        mini_series TEXT,
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS workflow_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_date TEXT,
        topic_query TEXT,
        topics_count INTEGER DEFAULT 0,
        posts_count INTEGER DEFAULT 0,
        sheets_synced INTEGER DEFAULT 0,
        notion_synced INTEGER DEFAULT 0,
        whatsapp_sent INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        details TEXT,
        created_at TEXT
    )
    """)

    # Seed default topics if fresh database (e.g. serverless instance)
    try:
        cursor.execute("SELECT COUNT(*) FROM topics")
        if cursor.fetchone()[0] == 0:
            now = datetime.now().isoformat()
            sample_topics = [
                ("AI and product management developments", "Agentic AI in Product Management: The Autonomous Roadmap", "MIT Sloan Management Review", "https://www.google.com/search?q=Agentic+AI+in+Product+Management", "Explores how autonomous agents are shifting product managers from feature managers to systems architects.", json.dumps(["Will agents replace sprint planning?", "How does product intuition translate to system prompts?", "The shift from output metrics to system reliability"]), 9.6, now),
                ("AI and product management developments", "AI Feature Bloat: Why 73% of Generative Add-ons Go Unused", "VentureBeat", "https://www.google.com/search?q=AI+Feature+Bloat+SaaS", "Examines customer fatigue with superficial AI wrappers and the demand for embedded, outcome-based automation.", json.dumps(["Chatbots vs Background automations", "The ROI of generative features in B2B SaaS", "How users actually interact with AI tools"]), 9.4, now),
                ("AI and product management developments", "The Rise of the 'Product Engineer' and the Blurring of PM/Dev Lines", "Andreessen Horowitz", "https://www.google.com/search?q=Product+Engineer+PM+Developer+Lines", "AI code assistants like Cursor are enabling engineers to build full user experiences without heavy PM specifications.", json.dumps(["Does the PM role become more technical or more business-oriented?", "The collapse of the spec-writing loop", "Rapid prototyping replacing user research decks"]), 9.2, now)
            ]
            cursor.executemany("""
                INSERT INTO topics (query, title, source, url, summary, discussion_points, trending_score, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, sample_topics)
    except Exception:
        pass

    conn.commit()
    conn.close()

# Helper queries
def save_topics(topics: List[Dict[str, Any]]) -> List[int]:
    conn = get_connection()
    cursor = conn.cursor()
    ids = []
    now = datetime.now().isoformat()
    for t in topics:
        points = json.dumps(t.get("discussion_points", [])) if isinstance(t.get("discussion_points"), list) else str(t.get("discussion_points", ""))
        cursor.execute("""
            INSERT INTO topics (query, title, source, url, summary, discussion_points, trending_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            t.get("query", ""),
            t.get("title", ""),
            t.get("source", ""),
            t.get("url", ""),
            t.get("summary", ""),
            points,
            float(t.get("trending_score", 8.5)),
            now
        ))
        ids.append(cursor.lastrowid)
    conn.commit()
    conn.close()
    return ids

def get_topic_by_id(topic_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM topics WHERE id = ?", (topic_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    try:
        d["discussion_points"] = json.loads(d["discussion_points"])
    except Exception:
        pass
    return d

def get_recent_topics(limit: int = 15) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM topics ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    for r in rows:
        try:
            r["discussion_points"] = json.loads(r["discussion_points"])
        except Exception:
            pass
    return rows

def save_ideas(ideas: List[Dict[str, Any]]) -> List[int]:
    conn = get_connection()
    cursor = conn.cursor()
    ids = []
    now = datetime.now().isoformat()
    for item in ideas:
        cursor.execute("""
            INSERT INTO ideas (topic_id, topic_title, title, angle, hook_premise, key_takeaway, target_audience, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item.get("topic_id"),
            item.get("topic_title", ""),
            item.get("title", ""),
            item.get("angle", "Thought Leadership"),
            item.get("hook_premise", ""),
            item.get("key_takeaway", ""),
            item.get("target_audience", "Tech & Product Professionals"),
            item.get("status", "idea"),
            now
        ))
        ids.append(cursor.lastrowid)
    conn.commit()
    conn.close()
    return ids

def get_ideas(limit: int = 20) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ideas ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def save_post_draft(post: Dict[str, Any]) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    content = post.get("content", "")
    cursor.execute("""
        INSERT INTO posts (idea_id, topic_id, topic, angle, hook, content, hashtags, character_count, status, scheduled_for, source_url, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        post.get("idea_id"),
        post.get("topic_id"),
        post.get("topic", "General"),
        post.get("angle", "Insight"),
        post.get("hook", content[:120]),
        content,
        post.get("hashtags", ""),
        len(content),
        post.get("status", "needs_review"),
        post.get("scheduled_for", ""),
        post.get("source_url", ""),
        now
    ))
    post_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return post_id

def update_post_status(post_id: int, status: str, notes: Optional[str] = None) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    if status == "published":
        cursor.execute("UPDATE posts SET status = ?, published_at = ?, review_notes = COALESCE(?, review_notes) WHERE id = ?", (status, now, notes, post_id))
    else:
        cursor.execute("UPDATE posts SET status = ?, review_notes = COALESCE(?, review_notes) WHERE id = ?", (status, notes, post_id))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success

def update_post_content(post_id: int, content: str, hashtags: str, hook: Optional[str] = None) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    hook_val = hook or content.split("\n")[0][:140]
    cursor.execute("""
        UPDATE posts
        SET content = ?, hashtags = ?, hook = ?, character_count = ?
        WHERE id = ?
    """, (content, hashtags, hook_val, len(content), post_id))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success

def get_posts(status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    if status:
        cursor.execute("SELECT * FROM posts WHERE status = ? ORDER BY id DESC LIMIT ?", (status, limit))
    else:
        cursor.execute("SELECT * FROM posts ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_post_by_id(post_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def record_workflow_run(run_data: Dict[str, Any]) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO workflow_runs (run_date, topic_query, topics_count, posts_count, sheets_synced, notion_synced, whatsapp_sent, status, details, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_data.get("run_date", now),
        run_data.get("topic_query", ""),
        run_data.get("topics_count", 0),
        run_data.get("posts_count", 0),
        1 if run_data.get("sheets_synced") else 0,
        1 if run_data.get("notion_synced") else 0,
        1 if run_data.get("whatsapp_sent") else 0,
        run_data.get("status", "success"),
        run_data.get("details", ""),
        now
    ))
    run_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return run_id

def get_recent_workflow_runs(limit: int = 10) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM workflow_runs ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def save_repurposed(data: Dict[str, Any]) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO repurposed_articles (source_url, source_title, summary, post_content, carousel_slides, mini_series, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("source_url", ""),
        data.get("source_title", "Untitled Article"),
        data.get("summary", ""),
        data.get("post_content", ""),
        json.dumps(data.get("carousel_slides", [])),
        json.dumps(data.get("mini_series", [])),
        now
    ))
    rep_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return rep_id

def get_repurposed_articles(limit: int = 10) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM repurposed_articles ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    for r in rows:
        try:
            r["carousel_slides"] = json.loads(r["carousel_slides"])
            r["mini_series"] = json.loads(r["mini_series"])
        except Exception:
            pass
    return rows

# Initialize on import
init_db()

