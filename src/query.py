import os
from dotenv import load_dotenv
from database import Database
from embedder import Embedder
from search import SearchEngine


def main():
    load_dotenv()

    query = input("Enter query: ")
    print(f"Query: {query}")
    if not query:
        print("Usage: python3 query.py <query>")
        return
    
    db = Database(os.getenv("DATABASE_URL"))
    embedder = Embedder()
    engine = SearchEngine(db, embedder)

    results = engine.search(query,k=10)

    for r in results:
        print(embedder.embed_query(query))

    db.close()

if __name__ == "__main__":
    main()