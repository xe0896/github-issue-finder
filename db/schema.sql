CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS issues (
    id BIGINT PRIMARY KEY, -- GitHub's internal unique ID
    number INT NOT NULL, -- issue number shown in the URL e.g. #4821
    title TEXT NOT NULL, -- issue title
    body TEXT, -- full description written by the author
    state TEXT NOT NULL, -- 'open' or 'closed'
    labels TEXT[], -- array of label names e.g. ['bug', 'help wanted']
    created_at TIMESTAMPTZ, -- when the issue was opened
    closed_at TIMESTAMPTZ, -- when it was closed, NULL if still open
    url TEXT, -- link to the issue on GitHub
    embedding vector(768) -- 768-dim meaning vector, filled in by the embedder
);