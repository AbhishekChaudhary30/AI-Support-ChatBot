# User Guide: AI Customer Support Chatbot
**Repository:** `ai-support-chatbot`  
**Audience:** End users, customer support administrators, and developers.  

---

## 1. Introduction

Welcome to the **AI Customer Support Chatbot**! This application is an intelligent assistant engineered to answer customer inquiries based on verified company policies, shipping guidelines, billing terms, and technical troubleshooting manuals.

By default, the application runs **completely locally and free of charge** using open-weight models via **Ollama**. You can also connect optional cloud providers (such as OpenAI, Anthropic, Google Gemini, Groq, or Mistral) using ephemeral, session-scoped credentials.

---

## 2. Quick Start: Launching the Application

### 2.1 Starting the Server
1. Open Windows PowerShell or your preferred terminal.
2. Navigate to the project directory:
   ```powershell
   cd "C:\Users\ABHISHEK CHAUDHARY\Desktop\ai-support-chatbot"
   ```
3. Activate the virtual environment:
   ```powershell
   .venv\Scripts\Activate.ps1
   ```
4. Start the Chainlit application:
   ```powershell
   chainlit run app.py -w
   ```
5. Your default web browser will automatically open to `http://localhost:8000`.

---

## 3. Selecting and Configuring Models

### 3.1 Using Local Ollama (Default & Zero-Cost)
1. Ensure your local Ollama daemon is running:
   ```powershell
   ollama serve
   ```
2. Pull the default recommended model:
   ```powershell
   ollama pull llama3.2:latest
   ```
3. In the application welcome screen, check the **Engine Status**:
   - `🟢 Local Ollama Active`: Ready for instant local inference.
   - `🟡 Local Ollama Not Running`: Start Ollama in your terminal using `ollama serve`.

### 3.2 Configuring an Optional Cloud Provider
If you wish to test or run cloud inference:
1. Open the **Settings Drawer** by clicking the **Sliders icon (⚙️)** in the sidebar.
2. Select your provider from the **Inference Provider** dropdown (e.g. `openai`, `anthropic`, `google`, `groq`, `mistral`).
3. Enter your target model identifier (e.g. `gpt-4o-mini`, `claude-3-5-haiku-latest`, `gemini-1.5-flash`).
4. Enter your provider API key in the **Session API Key (Ephemeral)** field. Characters are masked for your privacy.
5. Adjust sampling temperature (default `0.20` for factual customer support) or token limits if desired.
6. Click anywhere outside the drawer to apply. A status notification will confirm connection reachability.

### 3.3 Privacy & Session Secrets Guarantee
- **Never Persisted:** API keys are held strictly in server-side session memory for the duration of your browser session.
- **Never Logged:** Keys never enter chat transcripts, local storage, cookies, database tables, or server logs.
- **Zero Egress on Ollama:** When using Ollama, no prompt data or questions leave your machine.

### 3.4 Clearing Configuration and Secrets
To instantly wipe all credentials from runtime memory:
- Click the **🔒 Clear Session Secrets** action chip below the welcome banner.
- All session keys will be purged immediately, and provider configuration will reset to local Ollama defaults.

---

## 4. Interacting with the Chatbot

### 4.1 Asking Your First Question
You can ask any support-related question by typing in the chat composer at the bottom or clicking one of the sample prompt chips:
- 💳 *"What is your refund policy?"*
- 🔑 *"How do I reset my password?"*
- 🚚 *"What should I do if my order is delayed?"*
- 🛠️ *"How do I troubleshoot an unresponsive page?"*

### 4.2 Asking a Follow-Up Question
The chatbot maintains multi-turn conversation context within your active session. You can naturally refer to earlier topics using pronouns:
- **Turn 1:** *"What is your refund policy?"*
- **Turn 2:** *"Can I request it after delivery?"*

The retrieval engine automatically contextualizes your follow-up query with the prior turn to retrieve the exact relevant policy section.

### 4.3 Understanding Verified Source References
When an answer is grounded in documentation, the assistant displays a **Verified Knowledge Sources** card beneath the message:
```markdown
*Transparency: 🟢 Answered using support knowledge base (1 verified source)*

Verified Knowledge Sources:
> - 📄 Customer Support FAQ: Billing, Subscriptions & Refund Policies (Section: What is the refund policy? | Relevance: 0.453)
>   We offer a 14-day no-questions-asked money-back guarantee for all new subscription plans...
```
- **Title:** The authoritative support document name.
- **Section:** The exact H2/H3 heading containing the policy.
- **Relevance:** The cosine similarity score of the chunk.
- **Snippet:** The verified factual excerpt provided to the model.

### 4.4 Handling Unsupported or Unknown Questions
If you ask a question outside the ingested knowledge base (e.g. *"What is the stock price of Apple?"* or *"What is my live account balance?"*):
- The assistant refuses to invent or hallucinate policies or account data.
- A transparency notice informs you: `🟡 No matching support documentation found in knowledge base`.
- You are guided to consult your account portal or offered a connection to a human representative.

### 4.5 Requesting Human Support Escalation
If you need personal assistance:
- Type *"I want to speak with a human support agent."* or click the human support button.
- The chatbot generates a structured **Human Support Escalation Briefing**:
  - Summarizes your inquiry and recent conversation context.
  - Lists official contact channels and hours (Mon-Fri 8am-8pm EST).
  - Explicitly states: *"No external ticket has been automatically created,"* ensuring complete transparency.

### 4.6 Starting a New Conversation
- Click **New Chat (+)** in the sidebar.
- Message history is wiped clean, conversational context is reset, and stale retrieval references are removed.
- Your selected model configuration and preferences are preserved for convenience.

---

## 5. Troubleshooting Common Issues

| Symptom | Root Cause | Solution |
|---|---|---|
| `🟡 Local Ollama Not Running` | Ollama service is stopped or not installed. | Run `ollama serve` in a separate terminal. Ensure Ollama is installed from [ollama.com](https://ollama.com). |
| `Model 'llama3.2:latest' is not installed` | Target model has not been downloaded yet. | Run `ollama pull llama3.2:latest` in your terminal. |
| `Authentication failed for 'openai'` | Missing or invalid API key. | Open Model Settings (⚙️), check your key, and re-enter. |
| `The request to model provider timed out` | Endpoint is unreachable or model is too large for local hardware. | Switch to a smaller model (e.g. `llama3.2:1b`) or check network connectivity. |
| Blank page or CSS not loading | Browser cached older assets. | Perform a hard refresh (`Ctrl + F5` on Windows). |
