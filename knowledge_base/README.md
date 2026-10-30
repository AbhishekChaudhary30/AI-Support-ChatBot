# Knowledge Base Directory

This directory stores the customer support knowledge base documents.

## Directory Structure
- `faqs/`: Contains structured markdown documents representing Frequently Asked Questions, policies, refund rules, and technical troubleshooting guides.
- `docs/`: Optional folder for extended customer support manuals and product guides.

## Ingestion Architecture (Prepared for Phase 2)
In Phase 2, documents placed in this directory will be:
1. Validated and scanned for malicious prompt injection attempts.
2. Chunked using semantic chunking boundaries (default chunk size ~500 chars with 50 chars overlap).
3. Converted into vector embeddings using a local embedding model (e.g. `nomic-embed-text` via Ollama) or compatible cloud embeddings.
4. Indexed in a vector store for fast similarity retrieval.
