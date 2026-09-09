import os
import sys
from pathlib import Path

from rich.control import Control

# Ensure src/ (this file's directory) is importable regardless of cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
from classes.database import Database
from classes.embedder import Embedder
from classes.search import SearchEngine
from classes.hybrid import HybridSearch

import typer
from rich.console import Console
from rich.panel import Panel
from rich.control import Control
from rich.table import Table
from rich.prompt import Prompt

app = typer.Typer()
console = Console()

def _results_table(results: list, db: Database) -> Table:
    table = Table(title="Issues", header_style="bold cyan", expand=True)
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Issue", style="bold", width=8)
    table.add_column("Score", justify="right", width=8)
    table.add_column("Title", overflow="fold")

    for rank, (number, score) in enumerate(results, start=1):
        issue = db.getIssue(number) or {}
        title = issue.get("title", "[dim]—[/]")
        table.add_row(str(rank), f"#{number}", f"{score:.4f}", title)

    return table


@app.command()
def query(
    text: str = typer.Argument(None, help="Search query. Omit to be prompted."),
    k: int = typer.Option(10, "--k", "-k", help="Number of results to return."),
):
    """Semantically search stored GitHub issues."""
    load_dotenv()

    if not text:
        text = Prompt.ask("[bold cyan]Describe an issue[/]")
        print("\033[F\033[K", end="")
    if not text.strip():
        console.print("[red]✗ Empty query.[/]")
        raise typer.Exit(1)

    console.print(Panel.fit(f"{text}", border_style="cyan"))

    with console.status("[bold green]Loading models & searching…", spinner="dots"):
        db = Database(os.getenv("DATABASE_URL"), console)
        embedder = Embedder(console)
        engine = SearchEngine(db, embedder)
        hybrid = HybridSearch(db, engine)
        results = hybrid.search(text, k=k)

    if not results:
        console.print("[yellow]No matching issues found.[/]")
    else:
        console.print(_results_table(results, db))

    db.close()


if __name__ == "__main__":
    app()
