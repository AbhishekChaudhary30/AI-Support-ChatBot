# Changelog
All notable changes to the **AI Customer Support Chatbot** project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] - 2026-10-23
### Final Engineering, Security Hardening, RAG Optimization & Release Preparation

#### Added
- **Multi-Turn Contextual Follow-Up Query Resolution:** Automated query reformulation in `SupportWorkflowCoordinator` that combines prior turn context with pronouns/short inquiries (*"Can I request it after delivery?"*), achieving 100% Top-1 recall on conversational follow-ups.
- **Provider Streaming Timeout Guard:** Integrated `asyncio.wait_for` timeout protection respecting `REQUEST_TIMEOUT_SECONDS`, preventing application hangs on stalled network streams.
- **Safe Atomic Index Rollback:** `InMemoryVectorRetriever.rebuild_from_knowledge_base` now snapshots verified indexes, automatically restoring the working index if document loading or embedding throws an exception.
- **Token Filtering & Punctuation Stripping in Fallback Embeddings:** Enhanced `DeterministicFallbackEmbeddingProvider` with regex tokenization and high-frequency stop-word down-weighting to avoid punctuation mismatches and reduce hash collisions.
- **Session Model Configuration Persistence:** In `app.py:on_chat_start`, user-selected provider and model configurations are preserved across new chat resets within the same browser session.
- **Premium Graphite UI Theme:** Bespoke custom CSS stylesheet (`public/custom.css`) introducing dark graphite surfaces, subtle glassmorphic cards, muted slate captions, and restrained cyan/violet accents.
- **Masked Password Field:** Added `-webkit-text-security: disc;` to prevent shoulder-surfing when entering ephemeral API keys.
- **Static Assets Mount:** Created `public/` folder with `public/logo.png` and configured `.chainlit/config.toml` to serve brand logo in the upper-left sidebar and welcome banner.
- **Acceptance Regression Test Suite:** Created explicit unit test cases validating Scenarios J (New conversation reset), K (Provider timeout recovery), and L (Atomic index rebuild rollback).
- **Comprehensive Documentation Suite:**
  - `docs/FINAL_AUDIT.md`: 32-point engineering evaluation matrix.
  - `docs/RAG_EVALUATION.md`: Measured benchmark metrics (Recall@1, Recall@3, MRR, Rejection rate).
  - `docs/SECURITY_REVIEW.md`: Threat model, credential lifecycle audit, and OWASP Top 10 alignment.
  - `docs/TECHNOLOGY_STACK.md`: Deep dive into every core technology and its role.
  - `docs/USER_GUIDE.md`: Step-by-step user guide for local and cloud workflows.
  - `docs/FINAL_RELEASE_REPORT.md`: Comprehensive release handoff report.

#### Fixed
- **OpenAICompatibleProvider Keyword Argument Error:** Fixed `TypeError` in `compatible_provider.py` by accepting `model_name` and `**kwargs` in `check_health`.
- **List-Based Stream Token Unpacking:** Updated `BaseModelProvider.astream` to safely handle both plain string chunks and LangChain list-based content blocks.
- **Clean Footer Formatting:** Verified strict `"Follow and Connect only on LinkedIn and GitHub"` footer line with configurable profile links.

---

## [0.1.0] - 2026-10-22
### Initial Architecture & Retrieval Implementation
- Initialized project structure with `src/support_bot/` package layout.
- Implemented `InMemoryVectorRetriever` with heading-aware `TextChunker` and `KnowledgeBaseLoader`.
- Built modular provider adapters for Ollama, OpenAI, Groq, Mistral, Google Gemini, and Anthropic Claude.
- Created `SessionSecret` ephemeral in-memory vault and scrubbed structured logging filter.
- Implemented deterministic intent classifier with 8 support categories and human escalation manager.
- Authored initial unit and integration test suite with 57 passing tests.
