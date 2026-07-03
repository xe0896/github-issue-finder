from database import Database
from embedder import Embedder

class SearchEngine:
    def __init__(self, db: Database, embedder: Embedder):
        self.db = db
        self.embedder = embedder

    def search(self, query: str, k: int = 10) -> list[dict]:
        embedding = self.embedder.embed_query(query)
        return self.db.search(embedding, k)