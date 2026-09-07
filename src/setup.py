import os
from dotenv import load_dotenv

from classes.githubClient import GitHubClient as GitHubClient
from classes.embedder import Embedder as Embedder
from classes.database import Database as Database
from classes.search import SearchEngine
from classes.hybrid import HybridSearch
from rich.console import Console

def setup(repo: str, name: str, console : Console) -> tuple[Database, Embedder, GitHubClient, HybridSearch]:
    load_dotenv()
    database = Database(os.getenv("DATABASE_URL"), console)
    client = GitHubClient(os.getenv("GITHUB_TOKEN"), repo, name, console, database)
    embedder = Embedder(console)
    engine = SearchEngine(database, embedder)
    hybrid = HybridSearch(database, engine)    

    return database, embedder, client, hybrid

    