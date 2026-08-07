#!/usr/bin/env python3
"""
Reddit Engagement OS - Interactive CLI
A memory-based system for building karma and backlinks through authentic engagement.
Uses Laguna S 2.1 Free for response generation.
"""

import asyncio
import os
import sys
import json
import textwrap
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.markdown import Markdown

# Initialize Rich console
console = Console()

async def main():
    from lib.indexer import MemoryIndexer
    
    indexer = MemoryIndexer(os.getenv("DATABASE_URL", "sqlite:///./reddit_os.db"))
    
    console.print(Panel.fit(
        "[bold cyan]Reddit Engagement OS[/bold cyan]\n[dim]Memory-based engagement assistant[/dim]",
        border_style="cyan"
    ))
    
    while True:
        console.print("\n[bold]Menu:[/bold]")
        console.print("1. Index a Reddit post for analysis")
        console.print("2. Generate response suggestions")
        console.print("3. Search similar past responses")
        console.print("4. View dashboard metrics")
        console.print("5. Index a response")
        console.print("6. Submit feedback on a response")
        console.print("7. Run topic clustering")
        console.print("0. Exit")
        
        choice = Prompt.ask("\n[bold]Select option[/bold]", default="0")
        
        if choice == "1":
            await index_post(indexer)
        elif choice == "2":
            await generate_response_cli(indexer)
        elif choice == "3":
            await search_similar(indexer)
        elif choice == "4":
            await show_dashboard(indexer)
        elif choice == "5":
            await index_response_cli(indexer)
        elif choice == "6":
            await submit_feedback_cli(indexer)
        elif choice == "7":
            console.print("[yellow]Running topic clustering...[/yellow]")
            indexer.cluster_topics()
            console.print("[green]Topic clustering complete![/green]")
        elif choice == "0":
            console.print("[yellow]Goodbye![/yellow]")
            break

async def index_post(indexer):
    console.print("\n[bold]Index Reddit Post[/bold]")
    reddit_id = Prompt.ask("Reddit ID/Post hash")
    subreddit = Prompt.ask("Subreddit name")
    title = Prompt.ask("Post title")
    content = Prompt.ask("Post content (or URL)")
    author = Prompt.ask("Author", default="unknown")
    score = Prompt.ask("Score (karma)", default="0")
    num_comments = Prompt.ask("Number of comments", default="0")
    
    try:
        conv_id = await indexer.index_conversation({
            'reddit_id': reddit_id,
            'subreddit': subreddit,
            'title': title,
            'content': content,
            'author': author,
            'score': int(score),
            'num_comments': int(num_comments),
            'created_utc': '',
            'permalink': f'/r/{subreddit}/comments/{reddit_id}'
        })
        console.print(f"[green]Indexed successfully! Conversation ID: {conv_id}[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

async def generate_response_cli(indexer):
    console.print("\n[bold]Generate Response Suggestions[/bold]")
    post_content = Prompt.ask("Paste the post content")
    subreddit = Prompt.ask("Subreddit name")
    model = Prompt.ask("Model to use", default="laguna-s-2.1-free")
    
    console.print(f"[yellow]Generating suggestions using {model}...[/yellow]")
    result = await indexer.generate_response_suggestion(post_content, subreddit, model)
    
    console.print(f"\n[bold]Similar Context Found:[/bold]")
    for i, sim in enumerate(result.get('similar_context', [])):
        console.print(f"  [dim]#{i+1}[/dim] Score: {sim['score']} | Similarity: {sim['similarity']}")
    
    console.print(f"\n[bold cyan]Response Suggestions:[/bold cyan]")
    for i, suggestion in enumerate(result.get('suggestions', [])):
        console.print(f"\n[suggest]#{i+1}[/suggest]")
        if 'tone' in suggestion:
            console.print(f"  [yellow]Tone:[/yellow] {suggestion['tone']}")
        if 'content' in suggestion:
            console.print(f"  [bold]Content:[/bold]")
            console.print(textwrap.fill(suggestion['content'], width=80, initial_indent="    ", subsequent_indent="    "))
        if 'expected_karma' in suggestion:
            console.print(f"  [green]Expected karma:[/green] ~{suggestion['expected_karma']}")
        if 'reason' in suggestion:
            console.print(f"  [dim]Why:[/dim] {suggestion['reason']}")
        console.print("    [dim]---[/dim]")

async def search_similar(indexer):
    console.print("\n[bold]Search Similar Responses[/bold]")
    query = Prompt.ask("Enter search query")
    limit = int(Prompt.ask("Results limit", default="5"))
    
    results = indexer.find_similar_responses(query, limit)
    
    if not results:
        console.print("[yellow]No similar responses found. Start indexing some posts![/yellow]")
        return
    
    table = Table(title=f"Similar Responses to: {query[:50]}...")
    table.add_column("#", style="dim", width=4)
    table.add_column("Content", overflow="fold")
    table.add_column("Score", justify="right", style="cyan")
    table.add_column("Similarity", justify="right", style="green")
    table.add_column("Topic", style="magenta")
    
    for i, r in enumerate(results):
        table.add_row(
            str(i+1),
            r['content'][:100] + "...",
            str(r.get('score', 0)),
            f"{r['similarity']:.3f}",
            r.get('topic') or "N/A"
        )
    
    console.print(table)

async def show_dashboard(indexer):
    console.print("\n[bold]Dashboard Metrics[/bold]")
    metrics = await indexer.get_dashboard_metrics()
    
    table = Table(title="Reddit Engagement OS Dashboard")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Conversations", str(metrics.get('total_conversations', 0)))
    table.add_row("Total Responses", str(metrics.get('total_responses', 0)))
    table.add_row("Karma Events", str(metrics.get('total_karma_events', 0)))
    table.add_row("Total Karma Gain", f"{metrics.get('total_karma_gain', 0):.1f}")
    
    console.print(table)

async def index_response_cli(indexer):
    console.print("\n[bold]Index a Response[/bold]")
    conv_id = Prompt.ask("Conversation ID (optional)")
    content = Prompt.ask("Response content")
    score = Prompt.ask("Score (karma) (optional)", default="")
    
    resp_data = {
        'content': content,
        'score': int(score) if score else None,
        'ai_generated': False,
        'model_used': 'manual:laguna-s-2.1-free',
        'created_at': '',
        'embeddings': None
    }
    if conv_id:
        resp_data['conversation_id'] = int(conv_id)
    
    resp_id = await indexer.index_response(resp_data)
    console.print(f"[green]Response indexed! ID: {resp_id}[/green]")

async def submit_feedback_cli(indexer):
    console.print("\n[bold]Submit Feedback[/bold]")
    resp_id = int(Prompt.ask("Response ID"))
    rating = int(Prompt.ask("Rating (1-5)", default="4"))
    feedback = Prompt.ask("Feedback text (optional)", default="")
    
    feedback_id = await indexer.submit_feedback(resp_id, rating, feedback if feedback else None)
    console.print(f"[green]Feedback recorded (ID: {feedback_id})[/green]")

if __name__ == "__main__":
    console.print("[bold cyan]Starting Reddit Engagement OS...[/bold cyan]")
    console.print("[dim]Loading AI brain (Laguna S 2.1 Free)...[/dim]")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")
