import sys
import base64

from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "eval")) # Allows us to use eval folder
import runEval

from tqdm import tqdm
from setup import setup
from pprint import pprint

BATCH_SIZE = 64

def ingest(): 

    database, embedder, client, hybrid = setup("strix", "usestrix")

    issues = client.fetchIssues()

    print("Inserting issues in database")
    for issue in tqdm(issues):
        database.insertIssue(issue)

    unembeddedIssues = database.getUnembedded()
    
    # For all the issues that do not have an embedding, we grab BATCH_SIZE amount of issues and 
    # calculate the embeddings for each issue and save each of them back into the database, we do this
    # to not load a lot of issues at once
    for i in tqdm(range(0, len(unembeddedIssues), BATCH_SIZE)):
        batch = unembeddedIssues[i: i + BATCH_SIZE]
        embeddings = embedder.embed_documents(batch)
        for j in range(len(batch)):
            database.saveEmbedding(batch[j]["id"], embeddings[j])

    """ Evaluation:
    content = client.get_file(".github/ISSUE_TEMPLATE/feature_request.md")
    feature_request = base64.standard_b64decode(content["content"]).decode("utf-8")

    issue = client.TEMP_get_issue_content("206")
    issue_body = issue["body"]
    

    duplicates, canonicals = client.fetch_duplicate_pairs()
    MRR = runEval.evaluate(duplicates, canonicals, database, hybrid, embedder)
    print("MRR:", MRR)
    """

if __name__ == "__main__":
    ingest()
