from sentence_transformers import SentenceTransformer

class Embedder:
    # Requires a task prefix for every input, corpus documents use "search_document: "
    # search queries use "search_query: ", model is trained using these prefixes
    MODEL_NAME = "nomic-ai/nomic-embed-text-v1.5"

    DOCUMENT = "search_document: "
    QUERY = "search_query: "

    def __init__(self):
        self.model = SentenceTransformer(self.MODEL_NAME, trust_remote_code=True)
    
    # Tells the model what we want, apply some truncuation to not give it irrelevant stuff
    def _make_document_text(self, issue: dict) -> str:
        if(issue["body"] is None):
            return self.DOCUMENT + issue["title"]
        return self.DOCUMENT + issue["title"] + issue["body"][:512]

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

