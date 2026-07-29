# Knowledge data

The public repository and Docker image intentionally contain no textbook
content, embeddings, or Chroma databases.

When explicitly enabled, the `corpus-init` Compose service downloads the pinned
`MedRAG/textbooks` snapshot, verifies all 18 files and 125,847 rows, and stores
it in the `medagent-data` volume at:

```text
/app/data/index/medrag/textbooks/chunk/*.jsonl
```

Set `TEXTBOOKS_ENABLED=false` to skip the third-party corpus and run in
`pubmed_only` mode. Setting only `TEXTBOOKS_AUTO_DOWNLOAD=false` prevents
network downloads while preserving support for an existing or mounted corpus.

Each JSONL line must contain at least:

```json
{"id":"source_1","title":"Source title","content":"Authorized text"}
```

The upstream dataset card does not declare a license. Setting
`MEDRAG_TEXTBOOKS_ACCEPT_TERMS=true` records the deployer's acknowledgement of
that fact; it does not grant rights. Do not redistribute the downloaded corpus
or an image containing it without verifying that the applicable permissions
allow copying, indexing, retrieval, excerpt display, and redistribution.
