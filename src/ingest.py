import sys
import os
import base64
import asyncio
import aiohttp

from pathlib import Path

# Ensure src/ (this file's directory) is importable so bare
# `classes.*` / `eval.*` / `setup` imports resolve regardless of cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import typer
from dotenv import load_dotenv
from setup import setup
from pprint import pprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    MofNCompleteColumn,
    TimeElapsedColumn,
)

from eval import runEval
from classes.githubClient import GitHubClient
from classes.database import Database
from classes.embedder import Embedder


BATCH_SIZE = 64

app = typer.Typer()
console = Console()

# Docker psql command: psql postgresql://dev:dev@localhost:5432/semantic_search

@app.command()
def ingest(
    repo: str = typer.Option("strix", "--repo", "-r", help="Repository name"),
    owner: str = typer.Option("usestrix", "--owner", "-o", help="Repository owner"),
):
    """Fetch issues from a GitHub repo and store them in the database."""
    console.print(
        Panel.fit(
            f"[bold cyan]GitHub Issue Ingest[/]\n[dim]{owner}/{repo}[/]",
            border_style="cyan",
        )
    )

    load_dotenv()

    with console.status("[bold green]Connecting to database & GitHub…", spinner="dots"):
        database = Database(os.getenv("DATABASE_URL"))
        client = GitHubClient(os.getenv("GITHUB_TOKEN"), repo, owner)
    console.print("[green]✓[/] Connected to database & GitHub")

    issues = client.fetchIssues()

    inserted = insertion(issues, database)

    summary = Table(box=None, show_header=False, padding=(0, 2))
    summary.add_column(style="dim")
    summary.add_column(style="bold")
    summary.add_row("Issues fetched", str(len(issues)))
    summary.add_row("Issues processed", str(inserted))
    console.print(Panel(summary, title="[bold green]Done[/]", border_style="green", expand=False))

    """
    content = client.get_file(".github/ISSUE_TEMPLATE")
    urls = []

    for x in content:
        url = x["url"]
        urls.append(url)

    res = asyncio.run(full_fetch(urls))

    for x in res:
        print(base64.standard_b64decode(x["content"]).decode("utf-8"))
        print("***********")

    

    storedBody = database.getIssue(206)["body"][0]
    #pprint(storedBody)
    """
    

    # feature_request = base64.standard_b64decode(content["content"]).decode("utf-8")

async def fetch_json(session, url):
    async with session.get(url) as response:
        return await response.json()

async def full_fetch(urls):
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(
            *(fetch_json(session, url) for url in urls)
        )
    return results

def _progress() -> Progress:
    """A consistent progress bar style used across the ingest pipeline."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    )

def insertion(issues: list[dict], database) -> int:
    inserted = 0
    with _progress() as progress:
        task = progress.add_task("[cyan]Inserting issues", total=len(issues))
        for issue in issues:
            database.insertIssue(issue)
            inserted += 1
            progress.advance(task)
    return inserted

def embed(database, embedder):
    unembeddedIssues = database.getUnembedded()

    # For all the issues that do not have an embedding, we grab BATCH_SIZE amount of issues and
    # calculate the embeddings for each issue and save each of them back into the database, we do this
    # to not load a lot of issues at once
    with _progress() as progress:
        task = progress.add_task("[magenta]Embedding issues", total=len(unembeddedIssues))
        for i in range(0, len(unembeddedIssues), BATCH_SIZE):
            batch = unembeddedIssues[i: i + BATCH_SIZE]
            embeddings = embedder.embed_documents(batch)
            for j in range(len(batch)):
                database.saveEmbedding(batch[j]["id"], embeddings[j])
            progress.advance(task, len(batch))

def evaluate(client, database, hybrid, embedder):
    duplicates, canonicals = client.fetch_duplicate_pairs()
    MRR = runEval.evaluate(duplicates, canonicals, database, hybrid, embedder)  # noqa
    print("MRR:", MRR)

if __name__ == "__main__":
    app()
