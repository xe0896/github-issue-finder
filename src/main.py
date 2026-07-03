import os
from dotenv import load_dotenv
from githubClient import GitHubClient as gc
from embedder import Embedder as emb
from database import Database as db
from search import SearchEngine as engine
from pprint import pprint

load_dotenv()

def main():

    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    #client = gc(token=GITHUB_TOKEN,repo="usestrix/strix")
    #issues = client.fetchIssues()

    embedder = emb()
    database = db(os.getenv("DATABASE_URL"))

    #embedder.embed_documents(issues)
    searchEngine = engine(database, embedder)
    print(searchEngine.search(" [FEATURE] Add support for OS/Arch: linux/arm64", 10))

main()