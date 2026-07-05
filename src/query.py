import os
from dotenv import load_dotenv
from database import Database
from embedder import Embedder
from search import SearchEngine
from hybrid import HybridSearch
from pprint import pprint

import ingest

def main():
    load_dotenv()

    #ingest.ingest()

    #query = input("Enter query: ")
    query = "stalls"
    print(f"Query: {query}")
    if not query:
        print("Usage: python3 query.py <query>")
        return
    
    db = Database(os.getenv("DATABASE_URL"))
    embedder = Embedder()
    engine = SearchEngine(db, embedder)

    hybrid = HybridSearch(db, engine)    

    similar = hybrid.search(query, k=10)
    pprint(similar)

    db.close()

if __name__ == "__main__":
    main()