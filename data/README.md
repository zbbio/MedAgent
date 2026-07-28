# Knowledge data

The public repository and Docker image intentionally contain no medical
textbooks, chunks, embeddings, or Chroma databases.

Without local data, MedAgent starts in `pubmed_only` mode and uses the selected
LLM plus PubMed retrieval. Local BM25 retrieval becomes available only when an
authorized JSONL corpus is mounted at:

```text
/app/data/index/medrag/MedCorp/chunk/*.jsonl
```

Each JSONL line must contain at least:

```json
{"id":"source_1","title":"Source title","content":"Authorized text"}
```

Before distributing a corpus or an image containing it, verify the source
license permits copying, indexing, retrieval, excerpt display, and
redistribution. The private textbook corpus used during local development is
not part of this project.
