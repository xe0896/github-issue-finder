import sys
import os
import base64
import asyncio
import aiohttp

from pathlib import Path

from h11 import Data
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).resolve().parents[1] / "eval")) # Allows us to use eval folder
import runEval

from tqdm import tqdm
from setup import setup
from pprint import pprint

from classes.githubClient import GitHubClient
from classes.database import Database


BATCH_SIZE = 64

# Docker psql command: psql postgresql://dev:dev@localhost:5432/semantic_search

def ingest(): 
    load_dotenv()
    #database, embedder, client, hybrid = setup("strix", "usestrix")

    database = Database(os.getenv("DATABASE_URL"))
    client = GitHubClient(os.getenv("GITHUB_TOKEN"), "strix", "usestrix")

    issues = client.fetchIssues()

    insertion(issues, database)

    """
    content = client.get_file(".github/ISSUE_TEMPLATE")
    urls = []

    for x in content:
        url = x["url"]
        urls.append(url)

    res = asyncio.run(full_fetch(urls))

    for x in res:
        print(base64.standard_b64decode(x["content"]).decode("utf-8"))
        print("***********")

    

    storedBody = database.getIssue(206)["body"][0]
    #pprint(storedBody)
    """
    

    # feature_request = base64.standard_b64decode(content["content"]).decode("utf-8")

async def fetch_json(session, url):
    async with session.get(url) as response:
        return await response.json()

async def full_fetch(urls):
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(
            *(fetch_json(session, url) for url in urls)
        )
    return results

def insertion(issues: list[dict], database):
    print("Inserting issues in database")
    for issue in tqdm(issues):
        database.insertIssue(issue)

def embed(database, embedder):
    unembeddedIssues = database.getUnembedded()
        
    # For all the issues that do not have an embedding, we grab BATCH_SIZE amount of issues and 
    # calculate the embeddings for each issue and save each of them back into the database, we do this
    # to not load a lot of issues at once
    for i in tqdm(range(0, len(unembeddedIssues), BATCH_SIZE)):
        batch = unembeddedIssues[i: i + BATCH_SIZE]
        embeddings = embedder.embed_documents(batch)
        for j in range(len(batch)):
            database.saveEmbedding(batch[j]["id"], embeddings[j])

def evaluate(client, database, hybrid, embedder):
    duplicates, canonicals = client.fetch_duplicate_pairs()
    MRR = runEval.evaluate(duplicates, canonicals, database, hybrid, embedder)
    print("MRR:", MRR)

if __name__ == "__main__":
    ingest()
