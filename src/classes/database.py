from datetime import datetime, timezone

import psycopg2 # Execute SQL queries and enable connection
from psycopg2.extras import DictCursor # Adds cursor types
from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
import sys
class Database:
    def __init__(self, url: str, console : Console):
        # Connection accepts host, dbname, user and password but it can also except a connection string
        self.conn = None
        self.console = console
        try:
            self.conn =  psycopg2.connect(url)
        except psycopg2.OperationalError:
            console.print(
                Panel.fit(
                    f"[bold red]Docker database is not running.",
                    border_style="red",
                )
            )
            sys.exit(0) # Failure

        # Allows psycopg2 to handle the vector embedding type
        register_vector(self.conn)

    def insertIssue(self, issue: dict, repoId : int) -> None:
        cursor = self.conn.cursor()
        insertIssues = """
        INSERT INTO issues (id, number, title, body, state, labels, created_at, closed_at, url, comments, embedding, repoId)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s)
        ON CONFLICT (id) DO NOTHING;
        """

        existenceCheck = """
        SELECT COUNT(*) FROM issues WHERE id = %s
        """

        labelNames = []
        for label in issue.get("labels", []):
            # label is a list of dictionaries, so index to get one dictionary and get the name for it
            labelNames.append(label["name"]) # We just care about the label name

        comments = []
        for comment in issue.get("comments", []):
            comments.append(comment)

        cursor.execute(existenceCheck, (issue["id"], ))
        
        rows = cursor.fetchone()
        
        if(rows[0] > 0):
            updateIssue = """
            UPDATE issues
            SET body = %s, state = %s, comments = %s
            WHERE id = %s
            """
            cursor.execute(updateIssue, (issue["body"], issue["state"], comments, issue["id"]))
        else:
            data = (issue["id"], issue["number"], issue["title"], issue["body"], issue["state"],
                            labelNames, issue["created_at"], issue["closed_at"], issue["url"], comments, repoId)
            
            cursor.execute(insertIssues, data)

        self.conn.commit()
        cursor.close()

    def getIssue(self, issue_num: int) -> dict:
        cursor = self.conn.cursor(cursor_factory=DictCursor)
        getIssue = """
        SELECT * FROM issues WHERE number = %s
        """

        data = (issue_num, )
        cursor.execute(getIssue, data)

        rows = cursor.fetchone()
        cursor.close()

        return rows

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

        # The array given may return out of order w.r.t to the array provided order, so we use
        # array_position to make it so that it is in order
        getQuery = """
        SELECT number, body, title FROM issues WHERE number = ANY(%s)
        ORDER BY array_position(%s, number)
        """

        data = (id, id) # psycopg wants a tuple so trailing , makes it

        cursor.execute(getQuery, data)
        rows = cursor.fetchall()
        cursor.close()

        return rows

    def incomingRepo(self, id: int) -> datetime:
        cursor = self.conn.cursor(cursor_factory=DictCursor)

        existenceCheck = """
        SELECT lastFetched FROM repos WHERE id = %s
        """
        cursor.execute(existenceCheck, (id, ))
        dt = datetime.now(timezone.utc)
        rows = cursor.fetchone()
        timestamp = None
        count = None
        if rows is not None:
            timestamp = rows[0]

        if(timestamp == None):
            # Does not exist yet
            
            newRepo = """
            INSERT INTO repos (id, lastFetched)
            VALUES (%s, %s)
            ON CONFLICT (id) DO NOTHING;
            """

            data = (id, dt)

            cursor.execute(newRepo, data)
        else:
            # Does exist
            updateLastFetched = """
            UPDATE repos
            SET lastFetched = %s
            WHERE id = %s
            """

            data = (dt, id)

            cursor.execute(updateLastFetched, data)

            getIssueCount = """
            SELECT COUNT(*) FROM issues WHERE repoId = %s
            """

            data = (id,)

            cursor.execute(getIssueCount, data)
            count = cursor.fetchone()

        self.conn.commit()
        cursor.close()

        return timestamp, count[0] if count else None

    def getBodies(self, repoId : int, issueId : int):
        cursor = self.conn.cursor(cursor_factory=DictCursor)

        getBody = """
        SELECT body FROM issues WHERE repoId = %s AND number = %s
        """

        data = (repoId, issueId)

        cursor.execute(getBody, data)

        return cursor.fetchall()


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
