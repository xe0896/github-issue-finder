from database import Database
from search import SearchEngine
from pprint import pprint

class HybridSearch:

    RRF_K = 60

    def __init__(self, db: Database, engine: SearchEngine):
        self.database = db
        self.engine = engine

    def rrf(self, dense: list[dict], sparse: list[dict], k: int = 10) -> list[dict]:
        scores = {}

        for i in range(len(sparse)):
            number = sparse[i]["number"]
            scores[number] = scores.get(number, 0) + 1/(self.RRF_K + i + 1)

        for i in range(len(dense)):
            number = dense[i]["number"]
            scores[number] = scores.get(number, 0) + 1/(self.RRF_K + i + 1)
        
        # first k, v is making the dict; second one is unpacking the tuple
        #topK = {k: v for k, v in sorted(scores.items(), key=lambda item: item[1])}
        # Sorts the given dictionary based on score into a list, the top one would make it back to a dict
        # which is not what we want since it would remove the order

        topK = sorted(scores.items(), key=lambda item: item[1],reverse=True)
        return topK[0:10]
    
    def search(self, query: str, k: int = 10) -> list[dict]:
        dense = self.engine.search(query, k)
        sparse = self.database.keyword_search(query, k)

        return self.rrf(dense, sparse, k)

