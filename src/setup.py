import os
from dotenv import load_dotenv

from classes.githubClient import GitHubClient as GitHubClient
from classes.embedder import Embedder as Embedder
from classes.database import Database as Database
from classes.search import SearchEngine as SearchEngine
from classes.hybrid import HybridSearch
from classes.search import SearchEngine

def setup(repo: str, name: str) -> tuple[Database, Embedder, GitHubClient, HybridSearch]:
    load_dotenv()

    client = GitHubClient(os.getenv("GITHUB_TOKEN"), repo, name)
    database = Database(os.getenv("DATABASE_URL"))
    embedder = Embedder()
    engine = SearchEngine(database, embedder)
    hybrid = HybridSearch(database, engine)    

    return database, embedder, client, hybrid

    