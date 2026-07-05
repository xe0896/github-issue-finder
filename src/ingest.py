import os
from dotenv import load_dotenv
from githubClient import GitHubClient as GitHubClient
from embedder import Embedder as Embedder
from database import Database as Database
from search import SearchEngine as SearchEngine
from tqdm import tqdm
from pprint import pprint

BATCH_SIZE = 64

def ingest() -> Database | Embedder:
    load_dotenv()
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

    client = GitHubClient(token=GITHUB_TOKEN,repo="usestrix/strix")
    embedder = Embedder()
    db = Database(os.getenv("DATABASE_URL"))

    duplicates = client.fetch_duplicate_pairs()
    print(duplicates)

    """
    print("Inserting issues in database")
    for issue in tqdm(issues):
        db.insertIssue(issue)

    unembeddedIssues = db.getUnembedded()
    
    # For all the issues that do not have an embedding, we grab BATCH_SIZE amount of issues and 
    # calculate the embeddings for each issue and save each of them back into the database, we do this
    # to not load a lot of issues at once
    for i in tqdm(range(0, len(unembeddedIssues), BATCH_SIZE)):
        batch = unembeddedIssues[i: i + BATCH_SIZE]
        embeddings = embedder.embed_documents(batch)
        for j in range(len(batch)):
            db.saveEmbedding(batch[j]["id"], embeddings[j])

    """

if __name__ == "__main__":
    ingest()
