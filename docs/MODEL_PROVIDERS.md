# Model Provider Architecture & Configuration Guide

## 1. Local vs. Cloud Inference Overview

This application implements a modular **Provider Adapter Pattern**, enabling flexible switching between local models and cloud APIs:

| Attribute | Local Inference (Ollama) | Cloud APIs (OpenAI, Gemini, Anthropic, Groq, Mistral) |
| :--- | :--- | :--- |
| **Cost** | 100% Free (Zero API usage cost) | Pay-per-token / Subscription quota |
| **Privacy** | 100% Private (No data leaves local machine) | Data processed according to vendor privacy terms |
| **Internet Dependency** | Works completely offline once weights are pulled | Requires constant outbound internet connectivity |
| **Hardware Required** | Moderate to high (RAM/VRAM depending on model size) | Minimal (runs on standard clients/servers) |
| **Latency** | Depends on local GPU/CPU hardware | Very fast with specialized LPUs (e.g. Groq) |

---

## 2. Supported Provider Adapters

### 2.1 Ollama (Default Local Engine)
- **Adapter Name:** `ollama`
- **Default Endpoint:** `http://localhost:11434`
- **Default Model:** `llama3.2:latest` (or `mistral:latest`, `qwen2.5:latest`)
- **Credentials Required:** None (runs 100% offline).
- **Streaming:** Supported out-of-the-box (`langchain-ollama`).
- **Model Discovery:** Supported via Ollama `/api/tags` endpoint.
- **Setup:**
  1. Install Ollama from [ollama.com](https://ollama.com).
  2. Start the daemon: `ollama serve`
  3. Pull your preferred model: `ollama pull llama3.2`

### 2.2 OpenAI (Official Cloud API)
- **Adapter Name:** `openai`
- **Default Endpoint:** `https://api.openai.com/v1`
- **Supported Models:** `gpt-4o`, `gpt-4o-mini`, `gpt-3.5-turbo`
- **Credentials Required:** Valid OpenAI API key (`sk-...`).
- **Streaming:** Supported via SSE token streams.

### 2.3 Google Gemini (Official Google GenAI)
- **Adapter Name:** `google`
- **Default Endpoint:** Google Generative AI Cloud
- **Supported Models:** `gemini-2.0-flash`, `gemini-1.5-pro`, `gemini-1.5-flash`
- **Credentials Required:** Valid Google AI Studio API key (`AIza...`).
- **Integration Package:** `langchain-google-genai` (`ChatGoogleGenerativeAI`).
- **Streaming:** Supported.

### 2.4 Anthropic Claude (Official Anthropic API)
- **Adapter Name:** `anthropic`
- **Default Endpoint:** `https://api.anthropic.com`
- **Supported Models:** `claude-3-5-sonnet-20241022`, `claude-3-5-haiku-20241022`, `claude-3-opus-20240229`
- **Credentials Required:** Valid Anthropic API key (`sk-ant-...`).
- **Integration Package:** `langchain-anthropic` (`ChatAnthropic`).
- **Streaming:** Supported.

### 2.5 Groq Cloud (Ultra-Fast Inference)
- **Adapter Name:** `groq`
- **Default Endpoint:** `https://api.groq.com/openai/v1`
- **Supported Models:** `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, `mixtral-8x7b-32768`
- **Credentials Required:** Valid Groq API key (`gsk_...`).
- **Streaming:** Supported.

### 2.6 Mistral AI (European Cloud LLM)
- **Adapter Name:** `mistral`
- **Default Endpoint:** `https://api.mistral.ai/v1`
- **Supported Models:** `mistral-large-latest`, `mistral-small-latest`, `codestral-latest`
- **Credentials Required:** Valid Mistral API key.
- **Streaming:** Supported.

### 2.7 Custom OpenAI-Compatible Endpoints
- **Adapter Name:** `openai_compatible`
- **Endpoint:** Configurable (e.g. `http://localhost:8080/v1` for LocalAI, vLLM, LM Studio, or custom enterprise gateway).
- **Credentials Required:** Provider-dependent.
- **Streaming:** Supported if the gateway supports standard OpenAI SSE streaming format.

---

## 3. How to Add a New Provider Adapter

Extending the system to support an additional LLM provider requires three steps:

1. **Subclass `BaseModelProvider`:**
   ```python
   from support_bot.providers.base import BaseModelProvider, ProviderCapabilities

   class CustomProvider(BaseModelProvider):
       def __init__(self):
           super().__init__(ProviderCapabilities(
               provider_name="custom_provider",
               display_name="Custom Provider",
               is_local=False,
               requires_api_key=True,
               supports_streaming=True,
           ))

       def validate_configuration(self, session_config, session_secret=None):
           # Verify key and model format
           pass

       def get_chat_model(self, session_config, session_secret=None):
           # Return initialized LangChain BaseChatModel
           pass
   ```

2. **Implement Async Streaming:**
   Override `astream` or leverage standard LangChain model streaming (`chat_model.astream()`).

3. **Register in `ProviderRegistry`:**
   In `src/support_bot/providers/registry.py`:
   ```python
   from support_bot.providers.custom_provider import CustomProvider
   registry.register_provider(CustomProvider())
   ```
