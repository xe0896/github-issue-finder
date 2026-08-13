import io
import warnings
import contextlib

from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from transformers import logging as hf_logging

# Keep model loading quiet so it doesn't clutter the rich UI.
hf_logging.set_verbosity_error()
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")

class Embedder:
    # Requires a task prefix for every input, corpus documents use "search_document: "
    # search queries use "search_query: ", model is trained using these prefixes
    MODEL_NAME = "nomic-ai/nomic-embed-text-v1.5"

    DOCUMENT = "search_document: "
    QUERY = "search_query: "

    def __init__(self):
        # The remote model code prints load chatter to stdout; swallow it so it
        # doesn't clutter the rich UI.
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.model = SentenceTransformer(self.MODEL_NAME, trust_remote_code=True)
    
    # Tells the model what we want, apply some truncuation to not give it irrelevant stuff, the embedder
    # needs that self.DOCUMENT, the DB body field wont store the self.DOCUMENT
    def _make_document_text(self, issue: dict, strip: bool = False) -> str:
        comments = issue["comments"] or ""
        body = issue["body"] or ""
        
        if strip:
            body = self.strip_templates(body)
        
        return self.DOCUMENT + issue["title"] + " " + body[:512] + comments[0][:128] + comments[1][:128]

    # Given a list of issues, returns vector embeddings for each one, uses _make_document_text
    # to apply preprocessing before giving it to the model
    def embed_documents(self, issues: list[dict]) -> list[list[float]]:
        preprocessedIssues = []
        for issue in issues:
            preprocessedIssues.append(self._make_document_text(issue))

        # normalize_embeddings makes the vector's magnitude=1, making cosine similarity = dot product
        # which is faster to compute, reduces bias on large documents to make it fair and faster comparisons
        return self.model.encode(preprocessedIssues, normalize_embeddings=True).tolist() # tolist() to make it not a numpy array

    # Given input by the user, we want to find the embedding for it so we call this which takes
    # in the query and outputs the embedding for it, called by SearchEngine class
    def embed_query(self, issue: str) -> list[float]:
        # Basically a singular call of embed_documents
        return self.model.encode(issue, normalize_embeddings=True).tolist()

