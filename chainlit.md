# AI Customer Support Chatbot ⚡

Welcome to the **AI Customer Support Assistant**, an intelligent customer support application engineered with **Retrieval-Augmented Generation (RAG)**, local open-weight LLMs via **Ollama**, and modular cloud provider adapters.

---

### Key Capabilities

- **FAQ Knowledge Grounding:** Uses vector search to retrieve verified company policies, billing rules, and troubleshooting manuals.
- **Zero-Cost Local Inference:** Default execution runs locally with **Ollama** (`llama3.2:latest`, `mistral`), keeping data completely on your machine.
- **Session-Only Ephemeral Credentials:** Cloud API keys (OpenAI, Groq, Mistral) are held exclusively in server-side session memory—never saved to disk, database, chat logs, or Git.
- **Safety Boundaries:** Built-in message bounds, parameter sanitization, and adversarial prompt-injection screening.

---

### Quick Start Guide

1. **Ask a Support Question:** Type your question in the chat input below (e.g., *"What is the refund policy?"* or *"How do I reset my password?"*).
2. **Configure Model & Provider:** Open the **Settings (slider icon)** in the sidebar to switch between local Ollama or cloud providers, adjust sampling temperature, or enter a temporary API key.
3. **Inspect Architecture:** Click the action buttons below to view the full request lifecycle and technology breakdown.
