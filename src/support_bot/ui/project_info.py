"""Educational documentation and architectural metadata for UI presentation.

Provides clear, authoritative, and professionally phrased content for:
1. About This Project
2. Technology Stack Architecture & Component Cards
3. RAG Explanation & Lifecycle Transparency
4. Privacy & Credential Security Model
"""

from typing import Any, Dict, List

ABOUT_PROJECT_TEXT = """### What is this project?
The **AI Customer Support Chatbot** is a production-grade conversational application engineered to deliver accurate, reliable, and contextual customer assistance. Rather than relying solely on the general internal weights of an LLM—which can produce out-of-date or hallucinated answers—this system implements **Retrieval-Augmented Generation (RAG)**. It searches verified support documentation, policies, and FAQs to ground every generated response.

### How does it work? (Request Lifecycle)
1. **User Inquiry:** A customer submits a question in the conversational interface.
2. **UI Reception:** Chainlit receives the event and initiates real-time UI state tracking.
3. **Input Validation:** The backend validates length, sanitizes input, and screens for adversarial prompt injection.
4. **Context Preparation:** The Conversation Manager loads the session's conversational turns.
5. **Knowledge Retrieval:** The retrieval subsystem queries indexed FAQ chunks using vector similarity.
6. **Prompt Assembly:** LangChain fuses system instructions, relevant FAQ context, conversation history, and the user question.
7. **Model Inference:** The configured provider adapter (local Ollama or optional cloud API) executes inference.
8. **Response Processing:** The output is validated, formatted, and paired with verifiable source citations.
9. **Presentation:** Chainlit renders the grounded response and source references.
10. **Error & Escalation:** In case of missing information or service unavailability, clear guidance or human escalation options are offered.

### What is RAG?
**Retrieval-Augmented Generation (RAG)** bridges private domain knowledge with natural language models. When a user asks a question, the application first retrieves relevant factual excerpts from the local knowledge base, then supplies those excerpts directly into the prompt context for the model. This significantly reduces hallucinations, enables immediate documentation updates without model retraining, and provides verifiable citations.

### Modular Provider Architecture
Language model providers differ drastically in API contracts, cost, latency, token limits, and privacy guarantees. This application implements a **Provider Adapter Pattern**:
- **Local Ollama:** Default zero-cost, private inference running completely on your device.
- **OpenAI-Compatible:** Dynamic support for cloud providers (OpenAI, Groq, Mistral, Together AI) using session-scoped credentials.
Switching providers requires no rewrites of application logic or conversation managers.

### Known Limitations
- **Local Hardware Requirements:** Running local models via Ollama requires sufficient RAM/VRAM depending on model quantization (e.g. 8GB+ for 3B models, 16GB+ for 8B models).
- **Knowledge Base Scope:** The system cannot answer questions beyond the coverage of its ingested documentation.
- **Cloud Privacy:** If a user chooses to enter a cloud API key, prompt data is processed according to that cloud provider's data policy.
"""

TECHNOLOGY_CARDS: List[Dict[str, str]] = [
    {
        "name": "Python 3.10+",
        "role": "Application Backend & Core Logic",
        "why_needed": "Provides robust orchestration, type validation, structured logging, and integration across all modules.",
        "communicates_with": "Chainlit UI, LangChain, Pydantic, and HTTP Provider Adapters",
    },
    {
        "name": "Chainlit",
        "role": "Conversational UI & Interaction Layer",
        "why_needed": "Delivers an accessible, modern chat interface with streaming, loading indicators, and session tracking.",
        "communicates_with": "End User Browser & Python Application Backend",
    },
    {
        "name": "LangChain",
        "role": "LLM Orchestration & Prompt Engineering",
        "why_needed": "Standardizes chat model interfaces, message structures (System, Human, AI), and retrieval chains.",
        "communicates_with": "Conversation Manager & Model Provider Adapters",
    },
    {
        "name": "Ollama (Default)",
        "role": "Local Inference Engine",
        "why_needed": "Runs open-weight models (Llama 3.2, Mistral, Qwen) completely locally with zero cost and maximum privacy.",
        "communicates_with": "OllamaProvider Adapter via local HTTP daemon (port 11434)",
    },
    {
        "name": "Vector Store & Embeddings",
        "role": "Semantic FAQ Indexing & Retrieval",
        "why_needed": "Converts support documents into numerical vectors to find the most relevant context for any customer query.",
        "communicates_with": "Retrieval Subsystem & Knowledge Base Markdown Files",
    },
    {
        "name": "Pydantic & Settings",
        "role": "Data Validation & Configuration",
        "why_needed": "Validates structured runtime configurations, input bounds, and prevents malformed payload crashes.",
        "communicates_with": "Application Core & Security Layer",
    },
    {
        "name": "Pytest",
        "role": "Automated Testing & Quality Assurance",
        "why_needed": "Validates unit components, configuration boundaries, secret redaction, and provider adapters.",
        "communicates_with": "Development Environment & CI Pipelines",
    },
]

ARCHITECTURE_FLOW_DIAGRAM = """```mermaid
flowchart TD
    User([Customer / User]) <-->|Ask Question / Receive Answer| UI[Chainlit Conversational UI]
    UI <--> Core[Python Backend Orchestration]
    Core --> Sec[Input Validation & Safety Screening]
    Sec --> Conv[Conversation Context Manager]
    Conv --> Ret[FAQ Vector Retrieval Subsystem]
    Ret --> KB[(Knowledge Base FAQs)]
    Ret --> Prompt[LangChain Prompt Fusion]
    Prompt --> Reg[Model Provider Registry]
    Reg -->|Default / Local| Local[Ollama Local Engine]
    Reg -->|Optional / Cloud| Cloud[OpenAI / Groq / Cloud API]
    Local --> Stream[Response Processing & Citation Formatting]
    Cloud --> Stream
    Stream --> UI
```"""

PRIVACY_EXPLANATION = """### Privacy & Credential Security
- **Session-Only Lifetime:** When you enter a cloud provider API key, it is held strictly in volatile, server-side memory for the current session.
- **Zero Persistence:** Keys are **never** written to disk, database, local storage, cookies, logs, or Git.
- **Complete Erasure:** Clicking **"Clear Configuration"** or refreshing the session removes the active reference immediately.
- **Local Inference Guarantee:** When using Ollama, no prompt data or queries leave your local machine.
- **Deployment Warning:** Do not submit personal API keys on untrusted public deployments.
"""
