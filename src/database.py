import psycopg2 # Execute SQL queries and enable connection
from psycopg2.extras import DictCursor # Adds cursor types
from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv

class Database:
    def __init__(self, url: str):
        # Connection accepts host, dbname, user and password but it can also except a connection string
        self.conn =  psycopg2.connect(url)
        # Allows psycopg2 to handle the vector embedding type
        register_vector(self.conn)

    def insertIssue(self, issue: dict) -> None:
        cursor = self.conn.cursor()
        insertIssues = """
        INSERT INTO issues (id, number, title, body, state, labels, created_at, closed_at, url, embedding)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NULL);
        """
        labelNames = []
        for label in issue.get("labels", []):
            # label is a list of dictionaries, so index to get one dictionary and get the name for it
            labelNames.append(label["name"]) # We just care about the label name

        data = (issue["id"], issue["number"], issue["title"], issue["body"], issue["state"],
                labelNames, issue["created_at"], issue["closed_at"], issue["url"])

        cursor.execute(insertIssues, data)

        self.conn.commit()
        cursor.close()

    def getUnembedded(self) -> list[dict]:
        cursor = self.conn.cursor(cursor_factory=DictCursor) # We want a dict
        selectUnembeddedRows = """
        SELECT id, number, title, body FROM issues WHERE embedding is NULL;
        """

        cursor.execute(selectUnembeddedRows)

        # Returns a list of al rows in the result set
        rows = cursor.fetchall()
        
        cursor.close()

        return rows

    def saveEmbedding(self, issue_id: int, embedding: list[float]) -> None:
        cursor = self.conn.cursor()

        updateEmbedding = """
        UPDATE issues SET embedding = %s WHERE id = %s;
        """

        cursor.execute(updateEmbedding, (embedding, issue_id))
        self.conn.commit()
        cursor.close()

    def get_query(self, id: list[int]) -> list[dict]:
        cursor = self.conn.cursor(cursor_factory=DictCursor)

        getQuery = """
        SELECT number, body, title FROM issues WHERE number = ANY(%s)
        """

        data = (id,) # psycopg wants a tuple so trailing , makes it

        cursor.execute(getQuery, data)
        rows = cursor.fetchall()
        cursor.close()

        return rows

    def search(self, query_embedding: list[float], k: int = 10, exclude: int = None) -> list[dict]:
        cursor = self.conn.cursor(cursor_factory=DictCursor)

        excludeStr = ""
        data = (query_embedding, query_embedding, k)

        if exclude is not None:
            excludeStr = " AND number != %s"
            data = (query_embedding, exclude, query_embedding, k)

        # embedding <=> %s returns the embedding of the vector in that row
        # This is considered a dense search, since an embedding represented by a 768 length vector
        # is mainly non-zero whereas the keyword_search() would be very sparse since a whole document
        # is basically the bodies of the issues combined into a large document and we are comparing
        # the use query with each body, causing the vector being very sparse 

        cosineNeighbourQuery = f"""
        SELECT number, title, state, url, 1 - (embedding <=> %s::vector) AS similarity
        FROM issues WHERE embedding IS NOT NULL{excludeStr}
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """

        cursor.execute(cosineNeighbourQuery, data)
        
        rows = cursor.fetchall()

        cursor.close()

        return rows
    
    def keyword_search(self, query: str, k: int = 10, exclude: int = None) -> list[dict]:
        # The idea is that given a user query, we want to find matching textsearch values existing in the table
        # so given a query we can do an inline calculation of websearch_to_tsquery('english', %s) to get the value
        # then find the matching using a WHERE clause, but we want the top k and we find the rank by doing
        # ts_rank(tsquery), to find the matches we use @@ between search_vector (the stored tsquery) and query 
        # (the inline tsquery calclation of the user query) which would take the user query boolean expression
        # and make it go against the search_vector to find candidates and 

        # To compare this inline tsquery user calculation, we can do a CROSS JOIN with each row (N x 1 = N) 
        # then do the @@ syntax to compare 
        cursor = self.conn.cursor(cursor_factory=DictCursor)

        # websearch_to_tsquery() would take in the user query and each space would be replaced with & and 
        # we can also do some preprocessing to get 'failing or builds' to become 'fail' | 'build'

        excludeStr = ""
        data = (query, k)

        if exclude is not None:
            excludeStr = " AND number != %s"
            data = (query, exclude, k)

        keywordSearchQuery = f"""
        SELECT number, title, state, url, ts_rank(search_vector, query) AS score
        FROM issues, websearch_to_tsquery('english', %s) AS query
        WHERE search_vector @@ query{excludeStr}
        ORDER BY score DESC
        LIMIT %s
        """

        cursor.execute(keywordSearchQuery, data)
        rows = cursor.fetchall()

        cursor.close()

        return rows

    def close(self) -> None:
        self.conn.commit()
        self.conn.close()
