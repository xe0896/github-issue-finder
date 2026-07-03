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

    def search(self, query_embedding: list[float], k: int = 10) -> list[dict]:
        cursor = self.conn.cursor()

        # embedding <=> %s returns the embedding of the vector in that row
        cosineNeighbourQuery = """
        SELECT number, title, state, url, 1 - (embedding <=> %s::vector) AS similarity
        FROM issues WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """

        data = (query_embedding, query_embedding, k)
        cursor.execute(cosineNeighbourQuery, data)
        
        rows = cursor.fetchall()

        cursor.close()

        return rows

    def close(self) -> None:
        self.conn.commit()
        self.conn.close()
