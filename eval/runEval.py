import os

from database import Database
from hybrid import HybridSearch
from embedder import Embedder

from pprint import pprint

def evaluate(duplicates: list[int], canonicals: list[int], db: Database, hybridSearch: HybridSearch, embedder: Embedder, k: int = 10) -> int:
    queries = db.get_query(duplicates)

    """
    for i in range(0, len(queries)):
        preprocessedQuery = embedder._make_document_text(queries[i])
        queries[i] = hybridSearch.search(preprocessedQuery)
    """

    MRR = 0
    j = 0

    for duplicate, canonical in zip(duplicates, canonicals):
        i = 0
        query = queries[j]
        preprocessedQuery = embedder._make_document_text(query)
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

        
        
        


        