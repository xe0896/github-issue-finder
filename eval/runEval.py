import os

from classes.database import Database
from classes.hybrid import HybridSearch
from classes.embedder import Embedder

from pprint import pprint

def evaluate(duplicates: list[int], canonicals: list[int], db: Database, hybridSearch: HybridSearch, embedder: Embedder, k: int = 10) -> int:
    queries = db.get_query(duplicates)
    pprint(duplicates)

    pprint(queries) 

    MRR = 0
    j = 0

    # MRR: 0.5111111111111111
    
    for duplicate, canonical in zip(duplicates, canonicals):
        i = 0
        query = queries[j]
        pprint(query)
        
        preprocessedQuery = f"{query["title"]} {query["body"] or ''}"
        print(preprocessedQuery)
        result = hybridSearch.search(query=preprocessedQuery, exclude=duplicate)

        for pair in result:
            recievedCanonical = pair[0]
            print("i:", i, "canonical:", canonical, "duplicate", duplicate)
            if recievedCanonical == canonical:
                MRR += 1/(i +1)
            
                break
            i = i + 1

        j = j + 1

        pprint(result)
    

    return MRR/len(duplicates)