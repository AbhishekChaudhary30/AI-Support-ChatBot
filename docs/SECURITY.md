# Application Security and Privacy Architecture

## 1. Threat Model & Security Posture
The **AI Customer Support Chatbot** handles customer inquiries, sensitive configuration credentials, and external model interactions. This document outlines the security controls implemented to protect credentials, validate untrusted inputs, isolate multi-user sessions, and safeguard application runtime state.

---

## 2. Session-Only Credential Lifetime

### 2.1 The Zero-Persistence Rule
When a user enters a cloud provider API key in the Model Configuration drawer:
- **Server-Side Session Memory Only:** The key is wrapped in a `SessionSecret` object and stored strictly in volatile server runtime memory bound to that specific session ID.
- **No Disk Persistence:** Keys are **never** written to `.env`, configuration files, SQLite, or disk cache.
- **No Database Storage:** No database tables store or replicate credentials.
- **No Browser Local Storage:** Keys are not placed in `localStorage`, `sessionStorage`, or cookies.
- **No URL Leakage:** Credentials are never passed via URL query strings or path parameters.
- **No Prompt Leakage:** Secrets are isolated and never inserted into prompts or messages.
- **Explicit Teardown:** Clicking **"Clear Session Secrets"** or terminating the user session immediately erases the secret from runtime memory.

### 2.2 In-Memory Protection (`SessionSecret`)
The `SessionSecret` class overrides `__repr__` and `__str__` methods to output `[REDACTED]` and `<SessionSecret: [Configured]>`, preventing accidental string conversions or print statement leaks in debug environments.

---

## 3. Multi-User Session Isolation

The application enforces strict boundaries between simultaneous user sessions:
- **Independent Contexts:** Each user session operates with a dedicated `ConversationContext` and `ConversationManager`. Chat history from Session A cannot bleed into Session B.
- **Isolated Credentials:** Cloud API keys configured in Session A are completely inaccessible to Session B.
- **Isolated Workflows:** Each user session creates an isolated `SupportWorkflowCoordinator` instance.
- **Automated Isolation Testing:** Verified via `tests/unit/test_session_isolation.py` and `tests/unit/test_e2e_scenarios.py` (Scenario I).

---

## 4. Structured Logging & Secret Redaction

Application logging is filtered through `RedactingFilter`:
- **Pattern Matching:** Detects and scrubs OpenAI keys (`sk-...`), Anthropic keys (`sk-ant-...`), Google API keys (`AIza...`), Bearer tokens, and password query parameters.
- **Automatic Scrubbing:** Any log statement attempting to log a message or dictionary argument containing sensitive keys automatically has those values replaced with masked placeholders (e.g. `sk-...xyz (len: 51)`).
- **Conversational Privacy:** Complete conversation transcripts are not dumped to log files by default.

---

## 5. Input Validation & Prompt-Injection Mitigation

All user input is passed through `support_bot.security.input_validation`:
1. **Length Boundaries:** Rejects messages exceeding `MAX_MESSAGE_LENGTH` (default: 3,000 characters).
2. **Empty Input Defense:** Prevents blank or whitespace-only submissions.
3. **Adversarial Pattern Scanning:** Detects common jailbreak and prompt extraction signatures (e.g. *"ignore all previous instructions"*, *"reveal system prompt"*, *"you are now in developer mode"*).
4. **Untrusted Knowledge Base Context:** Retrieved documents are framed inside explicit delimiter boundaries (`---`) in system prompts. System prompts explicitly instruct the model that retrieved text is passive reference material and cannot override core system instructions.
5. **No Code Execution / Shell Access:** The LLM is never granted arbitrary code execution, file modification permissions, or shell execution capabilities.

---

## 6. Document Ingestion Security & Path Confinement

1. **Approved Directories Only:** `KnowledgeBaseLoader` restricts document discovery strictly to approved directories under `knowledge_base/faqs`.
2. **Path Traversal Defense:** Verifies canonical paths with `resolve()`. Any path attempting directory traversal (e.g. `../../etc/passwd`) is rejected immediately.
3. **File Size Enforcement:** Imposes a strict 2MB cap per document file to prevent memory exhaustion / denial of service.
4. **File Type Whitelisting:** Accepts only plain text (`.txt`) and Markdown (`.md`) files. Executable files (`.py`, `.sh`, `.exe`, `.bat`) are ignored.

---

## 7. Git Exclusions & Repository Hygiene

The project `.gitignore` explicitly prevents accidental leakage of:
- Virtual environments (`.venv/`, `venv/`).
- Real environment files (`.env`, `.env.*`), while explicitly whitelisting the safe `.env.example` template.
- Local databases (`*.db`, `*.sqlite3`).
- Vector store indices containing embedded private text (`chroma_db/`, `faiss_index/`).
- Logs and test cache artifacts (`logs/`, `.pytest_cache/`, `htmlcov/`).

An automated test (`test_no_real_secrets_in_tracked_code`) runs during test execution to verify that no actual API keys exist in tracked repository files.

---

## 8. Safe Production Deployment Guidelines

If deploying this application in production:
1. **Enforce HTTPS / TLS:** Ensure all traffic between clients and the server is encrypted in transit.
2. **Reverse Proxy:** Deploy behind an enterprise reverse proxy (e.g. Nginx, Caddy, or Cloudflare) with rate limiting.
3. **Public Deployment Trust Warning:** On public deployments, users entering personal API keys must understand that credentials reside in host memory. For public multi-tenant environments, configure backend enterprise keys or use local Ollama inference.
