# Troubleshooting Guide

This guide covers common development, setup, and runtime issues encountered when running the **AI Customer Support Chatbot**.

---

## 1. Environment & Setup Issues

### Issue 1.1: PowerShell Execution Policy Blocks Virtual Environment Activation
**Symptom:**
```powershell
.venv\Scripts\Activate.ps1 : File cannot be loaded because running scripts is disabled on this system.
```
**Solution:**
Allow signed scripts for your current user session by running in PowerShell:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Then re-activate:
```powershell
.venv\Scripts\Activate.ps1
```

---

### Issue 1.2: `chainlit` is Not Recognized as a Command
**Symptom:**
```powershell
chainlit : The term 'chainlit' is not recognized as the name of a cmdlet...
```
**Solution:**
Ensure you have activated your virtual environment or invoke it directly using python module syntax:
```powershell
.venv\Scripts\python -m chainlit run app.py -w
```

---

### Issue 1.3: Import Error: `ModuleNotFoundError: No module named 'support_bot'`
**Symptom:**
The application or test suite fails to import internal packages.
**Solution:**
Install the package in editable mode within your virtual environment:
```powershell
.venv\Scripts\python -m pip install -e .
```

---

## 2. Local Ollama Issues

### Issue 2.1: Ollama Service is Not Reachable
**Symptom:**
The application UI displays:
`🟡 Local Ollama Not Running (Start via ollama serve...)`
**Solution:**
1. Check if Ollama is installed:
   ```powershell
   ollama --version
   ```
   If not installed, download it from [ollama.com](https://ollama.com).
2. Start the daemon in a separate terminal:
   ```powershell
   ollama serve
   ```
3. Verify reachability by visiting `http://localhost:11434` in your browser. It should display *"Ollama is running"*.

---

### Issue 2.2: Model Not Found: `Model 'llama3.2:latest' not found`
**Symptom:**
Error message indicating the requested model identifier is unavailable locally.
**Solution:**
Download the model weights using Ollama CLI:
```powershell
ollama pull llama3.2
```
Alternatively, pull another lightweight model:
```powershell
ollama pull mistral
```
Then update the **Model Identifier** in the sidebar settings.

---

### Issue 2.3: Embedding Model Missing
**Symptom:**
Local embeddings fail because `nomic-embed-text` is not installed.
**Solution:**
Pull the recommended embedding model:
```powershell
ollama pull nomic-embed-text
```
*Note: If Ollama is offline or the embedding model is not present, the system automatically falls back to a deterministic offline hashing embedding provider, so retrieval continues to work seamlessly without crashing.*

---

## 3. Cloud Provider & API Key Issues

### Issue 3.1: Authentication Failed / Missing API Key
**Symptom:**
`Authentication failed for the selected provider. Check the API key and your account's model access.`
**Solution:**
1. Open the **Model Configuration** sidebar in the UI.
2. Enter your valid API key in the **Session API Key** field.
3. Verify your key hasn't expired and has sufficient credit on the provider's billing dashboard.

---

### Issue 3.2: Rate Limit / Quota Exceeded
**Symptom:**
`Rate limit reached for 'groq' (or 'openai')`
**Solution:**
1. Free tiers on cloud providers have rate limits (e.g. 30 requests/min). Wait a moment and retry.
2. Switch to local inference (**Ollama**) in the Model Configuration drawer for unlimited, free local queries.

---

### Issue 3.3: Request Timeout (`The request to model provider timed out after 60 seconds`)
**Symptom:**
Inference halts after 60 seconds and returns a clean timeout notice.
**Solution:**
1. If using Ollama, ensure your computer has sufficient RAM/VRAM to run the model without excessive CPU swapping.
2. Consider switching to a smaller quantized model (e.g. `llama3.2:1b` or `qwen2.5:1.5b`).
3. If using a remote cloud provider, verify your internet connection or proxy settings.
4. You can increase `REQUEST_TIMEOUT_SECONDS` in your `.env` file (e.g. `REQUEST_TIMEOUT_SECONDS=120`).

---

### Issue 3.4: Incorrect Provider Endpoint Mismatch (e.g. Groq pointing to `localhost:11434`)
**Symptom:**
Selecting a cloud provider like `groq` displays:
```text
Provider: groq
Endpoint: http://localhost:11434
Health Status: Connection error: Could not contact endpoint
```
Or chat replies with:
*"Could not communicate with the model provider. Is the local Ollama daemon running?"*

**Root Cause:**
In Chainlit, switching a dropdown widget does not dynamically update other text input fields in the browser DOM. The endpoint input retains `http://localhost:11434` from Ollama's initial default.

**Resolution & Behavior:**
The application automatically detects provider switches and normalizes the endpoint URL to that provider's official canonical base URL:
- **Groq:** `https://api.groq.com/openai/v1`
- **OpenAI:** `https://api.openai.com/v1`
- **Anthropic:** `https://api.anthropic.com/v1`
- **Google Gemini:** `https://generativelanguage.googleapis.com`
- **Mistral:** `https://api.mistral.ai/v1`
- **Local Ollama:** `http://localhost:11434`

If you enter a custom endpoint, ensure it does not point to a loopback address (`localhost`, `127.0.0.1`, port `11434`) when selecting a cloud provider.

---

### Issue 3.5: Generic Provider Name Used as Model Identifier (e.g. `groq`)
**Symptom:**
Setting model name to `groq` fails with model not found.

**Root Cause:**
`groq` is a provider name, not a valid model ID. Cloud endpoints require specific supported model identifiers (e.g., `llama-3.3-70b-versatile` or `llama-3.1-8b-instant`).

**Resolution & Behavior:**
The configuration handler automatically normalizes generic placeholders (`groq`, `ollama`, `openai`, `default`) to that provider's canonical default model:
- **Groq default:** `llama-3.3-70b-versatile`
- **Ollama default:** `llama3.2:latest`
- **OpenAI default:** `gpt-4o-mini`
- **Anthropic default:** `claude-3-5-haiku-latest`
- **Google default:** `gemini-1.5-flash`
- **Mistral default:** `mistral-small-latest`

---

## 4. Knowledge Base & Retrieval Issues

### Issue 4.1: "Support Knowledge Base Not Initialized"
**Symptom:**
Queries return fallback answers or a status badge indicates the knowledge base is not ready.
**Solution:**
1. In the chat interface, click the **"🔄 Rebuild Knowledge Index"** action button.
2. Verify that Markdown FAQ files exist in `knowledge_base/faqs/`.
3. Check that the document loader can parse them without exceeding the 2MB per-file safety limit.

---

### Issue 4.2: Safe Atomic Rebuild Recovery on Corrupted Files
**Symptom:**
Adding an invalid or unreadable file causes the index rebuild to fail.
**Behavior & Recovery:**
The system automatically applies **atomic rollback**:
- The error is logged to `IndexManifest`.
- The previously working index is restored immediately.
- Active customer conversations continue to be served using the verified prior index.
- Correct or remove the problematic file, then click **"🔄 Rebuild Knowledge Index"**.

---

### Issue 4.3: "No Matching Support Source Found"
**Symptom:**
The bot responds with general assistance and displays:
`*Transparency: 🟡 No matching support documentation found in knowledge base*`
**Solution:**
1. Verify that your query relates to a topic covered in `knowledge_base/faqs/` (e.g. refunds, shipping, 2FA, troubleshooting).
2. The retrieval similarity threshold is set to `min_score=0.20` to prevent irrelevant context matches. If needed, rephrase your query with more specific keywords.

---

## 5. Support Workflows & Escalation

### Issue 5.1: Why Did the Bot Generate an Escalation Card Instead of Answering?
**Symptom:**
The bot produces a structured card titled `CUSTOMER SUPPORT ESCALATION BRIEFING` when asking to speak to a person.
**Design Rationale:**
The system includes deterministic intent routing. When a customer explicitly requests human support (e.g. *"I want to talk to a human agent"*), it provides an escalation briefing containing conversation summaries and support email links (`support@example.com`).
In accordance with ethical AI design, it **never** invents fake ticket numbers or claims an external agent was alerted unless a real external ticketing API has been integrated.

---

## 6. Streaming, Actions & Frontend Rendering

### Issue 6.1: Streaming Output Appears Frozen or Token Duplication
**Symptom:**
The chat loading indicator spins without output.
**Solution:**
1. Chainlit v2 uses WebSockets for real-time streaming. Ensure no aggressive corporate firewall or browser ad-blocker is terminating WebSocket connections to `ws://localhost:8000/ws/socket.io`.
2. Check the server console log for provider connection exceptions.
3. Refresh the browser page or click **New Chat (+)** in the sidebar.

---

### Issue 6.2: Chainlit Action Payload Validation Failure (`1 validation error for Action payload`)
**Symptom:**
Clicking an action button (e.g. FAQ starter question) crashes with:
```text
pydantic_core._pydantic_core.ValidationError: 1 validation error for Action payload
Field required [type=missing, input_value=ArgsKwargs((), {'name': 'ask_example', ...})]
```

**Root Cause:**
In Chainlit 2.12.0+, `cl.Action` is a Pydantic dataclass that strictly requires a `payload: Dict[str, Any]` argument. Passing `value="xyz"` instead of `payload={"value": "xyz"}` causes Pydantic schema validation to reject the object.

**Resolution:**
All action buttons are constructed with explicit payload dictionaries:
```python
cl.Action(name="ask_example", payload={"value": "What is your refund policy?"}, label="💳 What is your refund policy?")
```
And callback handlers extract data safely:
```python
payload = action.payload if isinstance(getattr(action, "payload", None), dict) else {}
question = payload.get("value") or getattr(action, "value", None)
```
