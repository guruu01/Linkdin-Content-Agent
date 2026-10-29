import sys
import os

# Fix Windows console UTF-8 encoding
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import uvicorn
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

from agent.config import settings
from agent.workflow import workflow_manager
from agent.researcher import researcher
from agent.repurposer import repurposer
from agent.integrations.sheets import sheets_client
from agent.integrations.whatsapp import whatsapp_notifier
from agent.integrations.linkedin import linkedin_publisher
from agent.db import get_posts, get_post_by_id, update_post_status, get_recent_topics
from agent.scheduler import init_scheduler

console = Console()

def cmd_run_workflow(args):
    topic = args.topic or settings.DEFAULT_TOPIC
    console.print(Panel(f"[bold blue]Executing Monday Morning Content Workflow[/bold blue]\nTarget Topic: [bold green]{topic}[/bold green]", border_style="blue"))
    
    summary = workflow_manager.run_weekly_workflow(
        topic_query=topic,
        progress_callback=lambda msg, step: console.print(f"[cyan]Step {step}:[/cyan] {msg}")
    )

    console.print("\n[bold green]Workflow Complete! Summary of Generated LinkedIn Posts:[/bold green]")
    table = Table(title="Generated 5-Post Batch", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim", width=6)
    table.add_column("Angle", width=22)
    table.add_column("Hook Preview", width=40)
    table.add_column("Chars", width=8)
    table.add_column("Status", width=14)

    for p in summary.get("drafts", []):
        table.add_row(
            str(p.get("id")),
            p.get("angle", ""),
            p.get("hook", "")[:38] + "...",
            str(p.get("character_count", 0)),
            f"[yellow]{p.get('status')}[/yellow]"
        )
    console.print(table)

    wa_res = summary.get("whatsapp_result", {})
    if wa_res.get("wa_me_link"):
        console.print(Panel(f"[bold green]WhatsApp Review Ready![/bold green]\nDirect Review Link:\n[link={wa_res['wa_me_link']}]{wa_res['wa_me_link']}[/link]", border_style="green"))

def cmd_research(args):
    query = args.query or settings.DEFAULT_TOPIC
    console.print(f"[bold]Searching trends for:[/bold] [cyan]{query}[/cyan]")
    topics = researcher.research_topic_trends(query, count=args.count or 5)

    table = Table(title=f"Trending Topics for '{query}'", show_header=True, header_style="bold blue")
    table.add_column("#", width=4)
    table.add_column("Title", width=35)
    table.add_column("Source", width=18)
    table.add_column("Score", width=8)
    table.add_column("Core Debate Points", width=45)

    for i, t in enumerate(topics, 1):
        points = "\n• ".join(t.get("discussion_points", [])) if isinstance(t.get("discussion_points"), list) else str(t.get("discussion_points"))
        table.add_row(
            str(i),
            t.get("title", ""),
            t.get("source", ""),
            f"[bold yellow]{t.get('trending_score')}[/bold yellow]",
            f"• {points}"
        )
    console.print(table)

def cmd_repurpose(args):
    console.print(Panel("[bold magenta]Repurposing Long Article into LinkedIn Formats[/bold magenta]", border_style="magenta"))
    text = args.text
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()

    res = repurposer.repurpose(input_text=text, url=args.url)
    
    console.print("\n[bold green]1. Standalone LinkedIn Post:[/bold green]")
    console.print(Panel(res.get("post_content", ""), border_style="blue"))

    console.print("\n[bold yellow]2. PDF Carousel Slide Outline (5-7 Slides):[/bold yellow]")
    for s in res.get("carousel_slides", []):
        console.print(f"[bold cyan]Slide #{s.get('slide_number')}: {s.get('title')}[/bold cyan]")
        console.print(f"  Copy: {s.get('body')}")
        console.print(f"  [dim]Visual Note: {s.get('visual_cue')}[/dim]\n")

    console.print("[bold purple]3. 3-Day Mini-Series:[/bold purple]")
    for part in res.get("mini_series", []):
        console.print(f"[bold]Day {part.get('day')} ({part.get('theme')}):[/bold]\n{part.get('content')}\n")

def cmd_posts(args):
    posts = get_posts(status=args.status)
    table = Table(title="LinkedIn Content Queue", show_header=True, header_style="bold blue")
    table.add_column("ID", width=6)
    table.add_column("Topic", width=30)
    table.add_column("Angle", width=20)
    table.add_column("Status", width=14)
    table.add_column("Chars", width=8)

    for p in posts:
        st_color = "yellow" if p["status"] == "needs_review" else ("green" if p["status"] == "approved" else "purple")
        table.add_row(
            str(p["id"]),
            p["topic"][:28],
            p["angle"][:18],
            f"[{st_color}]{p['status']}[/{st_color}]",
            str(p["character_count"])
        )
    console.print(table)

def cmd_approve(args):
    success = update_post_status(args.post_id, "approved", notes="Approved via CLI")
    if success:
        console.print(f"[bold green]Post #{args.post_id} marked as APPROVED.[/bold green]")
    else:
        console.print(f"[bold red]Could not find or approve Post #{args.post_id}.[/bold red]")

def cmd_publish(args):
    post = get_post_by_id(args.post_id)
    if not post:
        console.print(f"[bold red]Post #{args.post_id} not found.[/bold red]")
        return
    res = linkedin_publisher.publish_post(post)
    if res.get("success"):
        console.print(f"[bold green]{res.get('message')}[/bold green]")
        if res.get("share_url"):
            console.print(f"Open composer link:\n[link={res['share_url']}]{res['share_url']}[/link]")
    else:
        console.print(f"[bold red]Publishing failed: {res.get('error')}[/bold red]")

def cmd_export_sheets(args):
    path = sheets_client.export_to_excel()
    console.print(f"[bold green]Excel Content Calendar updated at:[/bold green] [cyan]{path}[/cyan]")

def cmd_send_whatsapp(args):
    posts = get_posts(status="needs_review", limit=5)
    if not posts:
        posts = get_posts(limit=5)
    res = whatsapp_notifier.send_review_digest(posts)
    console.print(f"[bold green]WhatsApp review digest generated:[/bold green]")
    console.print(f"Mode: [cyan]{res.get('mode')}[/cyan]")
    if res.get("wa_me_link"):
        console.print(f"Direct WhatsApp Click-to-Chat Link:\n[link={res['wa_me_link']}]{res['wa_me_link']}[/link]")

def cmd_start_server(args):
    port = args.port or settings.APP_PORT
    host = args.host or settings.APP_HOST
    console.print(Panel(
        f"[bold blue]Starting LinkedIn Content Agent Web Server[/bold blue]\n"
        f"URL: [bold green]http://{host}:{port}[/bold green]\n"
        f"Scheduler: [cyan]Active (Every {settings.WORKFLOW_SCHEDULE_DAY.upper()} at {settings.WORKFLOW_SCHEDULE_TIME})[/cyan]",
        border_style="blue"
    ))
    uvicorn.run("web.app:app", host=host, port=port, reload=False)

def main():
    parser = argparse.ArgumentParser(description="AI Social Media Content Agent for LinkedIn")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # run-workflow
    p_run = subparsers.add_parser("run-workflow", help="Run the full 6-step Monday morning workflow")
    p_run.add_argument("--topic", help="Custom topic query (default: AI and product management)")
    p_run.set_defaults(func=cmd_run_workflow)

    # research
    p_res = subparsers.add_parser("research", help="Research trending topics & discussions")
    p_res.add_argument("--query", help="Topic query to search")
    p_res.add_argument("--count", type=int, default=5, help="Number of topics to retrieve")
    p_res.set_defaults(func=cmd_research)

    # repurpose
    p_rep = subparsers.add_parser("repurpose", help="Repurpose an article/URL into LinkedIn post & carousel")
    p_rep.add_argument("--url", help="Article URL to fetch and repurpose")
    p_rep.add_argument("--file", help="Path to text file to repurpose")
    p_rep.add_argument("--text", help="Raw text string to repurpose")
    p_rep.set_defaults(func=cmd_repurpose)

    # posts
    p_posts = subparsers.add_parser("posts", help="List all drafts in the content queue")
    p_posts.add_argument("--status", choices=["needs_review", "approved", "published"], help="Filter by status")
    p_posts.set_defaults(func=cmd_posts)

    # approve
    p_app = subparsers.add_parser("approve", help="Approve a post draft")
    p_app.add_argument("post_id", type=int, help="Post ID to approve")
    p_app.set_defaults(func=cmd_approve)

    # publish
    p_pub = subparsers.add_parser("publish", help="Publish a post via LinkedIn API or share link")
    p_pub.add_argument("post_id", type=int, help="Post ID to publish")
    p_pub.set_defaults(func=cmd_publish)

    # export-sheets
    p_exp = subparsers.add_parser("export-sheets", help="Export posts to Excel content calendar")
    p_exp.set_defaults(func=cmd_export_sheets)

    # send-whatsapp
    p_wa = subparsers.add_parser("send-whatsapp", help="Send WhatsApp review digest")
    p_wa.set_defaults(func=cmd_send_whatsapp)

    # start-server
    p_serv = subparsers.add_parser("start-server", help="Start the interactive Web Dashboard & API")
    p_serv.add_argument("--host", default=settings.APP_HOST, help="Host address")
    p_serv.add_argument("--port", type=int, default=settings.APP_PORT, help="Port")
    p_serv.set_defaults(func=cmd_start_server)

    args = parser.parse_args()
    if not args.command:
        # Default to starting the server
        console.print("[yellow]No command specified. Starting Web Dashboard by default...[/yellow]")
        parser.parse_args(["start-server"]).func(args)
    else:
        args.func(args)

if __name__ == "__main__":
    main()
