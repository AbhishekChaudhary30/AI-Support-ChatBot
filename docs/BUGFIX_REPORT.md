# Bugfix & Root-Cause Engineering Report

**Project:** AI Customer Support Chatbot  
**Date:** October 2026  
**Auditor / Engineer:** Senior Python Engineer, LLM Integration Engineer, Chainlit Specialist & AppSec Specialist  
**Status:** ✅ Both Root Causes Identified, Fixed, Regression-Tested, and Verified (91/91 Tests Passing)

---

## 1. Executive Summary

This report documents the investigation, root-cause analysis, engineering remediation, and end-to-end verification of two critical runtime defects observed in the application:

1. **Error A (Incorrect Provider Endpoint / Configuration):**  
   Selecting a cloud provider such as `groq` resulted in a backend configuration pointing to Ollama's loopback endpoint (`http://localhost:11434`) with model `groq`, causing immediate connection failure and misleading error prompts (*"Could not communicate with the model provider. Is the local Ollama daemon running?"*).
2. **Error B (Chainlit Action Payload Validation Failure):**  
   Clicking suggestion action chips or interaction buttons failed with:
   `pydantic_core._pydantic_core.ValidationError: 1 validation error for Action payload. Field required [type=missing, input_value=ArgsKwargs((), {'name': 'ask_example', 'value': ...})]`.

Both issues have been remediated at their architectural root causes. Zero cosmetic workarounds or suppression hacks were used. Full session isolation and ephemeral secret handling have been preserved. 29 new automated regression tests were authored, bringing the test suite to **91 passing tests with 0 failures**.

---

## 2. Root Cause Analysis

### 2.1 Root Cause of Error A: Provider Endpoint & Model Contamination

#### Observed Defect
```text
Provider: groq
Model: groq
Endpoint: http://localhost:11434
Credentials: Configured (Session-only)
Health Status: Connection error: Could not contact endpoint
```
Followed by:
*"An unexpected error occurred while communicating with the model provider. Please verify your model settings or ensure your local Ollama daemon is running."*

#### Deep Trace & Mechanism
1. **Frontend State Retention:** In Chainlit, switching a `Select` dropdown in `ChatSettings` does not automatically update or clear the values of adjacent `TextInput` fields (`endpoint_url`, `model_name`) in the browser DOM. The endpoint input retains `http://localhost:11434` (Ollama's initial default), and the model input retains `llama3.2:latest` (or the user types `groq`).
2. **Naive Backend Ingestion:** In `app.py:on_settings_update`, the backend previously assigned incoming raw form strings directly to `session_config`:
   ```python
   provider_name = raw_settings.get("provider", session_config.provider_name)
   model_name = raw_settings.get("model_name", session_config.model_name)
   endpoint_url = raw_settings.get("endpoint_url", session_config.endpoint_url)
   ```
   No validation was performed to check whether the incoming endpoint was Ollama's local URL while a cloud provider was selected, nor whether the model was a generic provider placeholder.
3. **Hardcoded Fallback in Workflow Coordinator:** In `src/support_bot/workflows/support_workflow.py`, lines 276-281 caught generic `Exception` and emitted a hardcoded string blaming Ollama:
   ```python
   except Exception as ex:
       err_msg = "An unexpected error occurred while communicating with the model provider. Please verify your model settings or ensure your local Ollama daemon is running."
   ```
   This error message was emitted even when the active provider was Groq, OpenAI, Anthropic, or Google.

---

### 2.2 Root Cause of Error B: Chainlit 2.12.0 Action Payload Validation Failure

#### Observed Defect
```text
pydantic_core._pydantic_core.ValidationError: 1 validation error for Action payload
Field required [type=missing, input_value=ArgsKwargs((), {'name': 'ask_example', 'value': 'What is your refund policy?', 'label': '💳 What is your refund policy?'})]
```

#### Deep Trace & Mechanism
1. **Pydantic Dataclass Schema in Chainlit 2.x:** In Chainlit 2.12.0, `chainlit.action.Action` is defined with the following dataclass annotations:
   ```python
   {'name': str, 'payload': Dict, 'label': str, 'tooltip': str, 'icon': Optional[str], 'forId': Optional[str], 'id': str}
   ```
   Notice that `payload: Dict` is a **mandatory, required field** without a default value. Furthermore, `Action` does not have an attribute named `value`.
2. **Incorrect Instantiation:** `app.py` previously constructed actions as:
   ```python
   cl.Action(name="ask_example", value="What is your refund policy?", label="💳 What is your refund policy?")
   ```
   Because `payload` was not provided, Pydantic's schema validator rejected the object with `Field required [type=missing, field='payload']`.
3. **Attribute Access in Callback:** In `on_ask_example(action: cl.Action)`, the handler executed:
   ```python
   question = action.value
   ```
   Because `Action` has no `value` attribute, this raised `AttributeError: 'Action' object has no attribute 'value'`.

---

## 3. Implemented Fixes

### 3.1 Dedicated GroqProvider Adapter (`src/support_bot/providers/groq_provider.py`)
- Created an explicit `GroqProvider` implementing `BaseModelProvider`.
- Default endpoint: `https://api.groq.com/openai/v1`
- Canonical default model: `llama-3.3-70b-versatile`
- Curated models list: `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, `llama3-70b-8192`, `llama3-8b-8192`, `mixtral-8x7b-32768`, `gemma2-9b-it`.
- Truthful health checks validating reachability (`/models`), API key authorization (401), rate limits (429), and model existence.
- Explicitly rejects loopback addresses (`localhost:11434`, `127.0.0.1`) to prevent endpoint contamination.

### 3.2 Endpoint Anti-Contamination & Normalization (`src/support_bot/security/input_validation.py`)
- Implemented `normalize_endpoint_url(url, provider_name)`:
  - Safely normalizes whitespace and trailing slashes (`.rstrip('/')`).
  - Prohibits loopback/private/link-local addresses (`localhost`, `127.0.0.1`, `::1`, `169.254.169.254`, port `11434`) when selecting cloud providers (`groq`, `openai`, `anthropic`, `google`, `mistral`).
  - Explicitly permits `localhost:11434` for local `ollama` mode.
- Enhanced `validate_model_identifier(model_name)`:
  - Rejects generic provider names (`groq`, `ollama`, `openai`, `default`) with actionable instructions.

### 3.3 Provider Configuration Switch Flow (`app.py:on_settings_update`)
- Automatically detects provider transitions (`submitted_provider != session_config.provider_name`).
- Auto-resolves canonical endpoints when switching providers or when an Ollama endpoint was submitted for a cloud provider.
- Auto-resolves canonical default models when switching providers or when generic placeholder names are entered.
- Preserves genuine user-specified custom remote endpoints for `openai_compatible` gateways.
- Displays helpful informational notes explaining automatic normalizations.

### 3.4 Runtime Error Categorization (`src/support_bot/workflows/support_workflow.py`)
- Implemented `format_provider_runtime_error(ex, session_config)`:
  - **Local Ollama Daemon Unreachable:** Explains daemon status and outputs exact `ollama serve` and `ollama list` commands.
  - **Cloud Provider Connection Error:** Reports endpoint reachability failure without mentioning Ollama.
  - **Authentication Failed (401/403):** Directs user to Model Configuration to enter a valid session key.
  - **Model Not Found (404):** Distinguishes Ollama missing model (`ollama pull <model>`) from cloud model misconfiguration.
  - **Rate Limit / Quota Exceeded (429):** Clearly states provider quota limits.
  - **Credential Safety:** Never leaks authorization headers, bearer tokens, or internal tracebacks.

### 3.5 Action Schema & Callback Normalization (`app.py`)
- Updated all 11 `cl.Action` instances to provide valid `payload: Dict[str, Any]` arguments:
  ```python
  cl.Action(name="ask_example", payload={"value": "What is your refund policy?"}, label="💳 What is your refund policy?")
  ```
- Updated `on_ask_example` to safely extract query text:
  ```python
  payload = action.payload if isinstance(getattr(action, "payload", None), dict) else {}
  question = payload.get("value") or getattr(action, "value", None)
  ```
- Wrapped all action callback handlers in try-except guards so unexpected payload errors gracefully inform the user without crashing the session.

---

## 4. Verification & Automated Test Results

The entire test suite was executed in `.venv` (Python 3.13.7) with pytest:

```powershell
.venv\Scripts\pytest -v
```

### Test Summary
```text
============================= test session starts =============================
platform win32 -- Python 3.13.7, pytest-9.1.1, pluggy-1.7.0
rootdir: C:\Users\ABHISHEK CHAUDHARY\Desktop\ai-support-chatbot
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.15.1, langsmith-0.14.11, asyncio-1.4.0
collected 91 items

tests\integration\test_retrieval_interface.py ...                        [  3%]
tests\unit\test_chainlit_actions.py .....                                [  8%]
tests\unit\test_chunking.py ..                                           [ 10%]
tests\unit\test_compatible_provider.py ...                               [ 14%]
tests\unit\test_config.py ...                                            [ 17%]
tests\unit\test_e2e_scenarios.py ............                            [ 30%]
tests\unit\test_error_normalization.py ......                            [ 37%]
tests\unit\test_escalation.py .                                          [ 38%]
tests\unit\test_groq_provider.py ...........                             [ 50%]
tests\unit\test_input_validation.py .......                              [ 58%]
tests\unit\test_intent.py .......                                        [ 65%]
tests\unit\test_loader.py ...                                            [ 69%]
tests\unit\test_ollama_provider.py ....                                  [ 73%]
tests\unit\test_provider_configuration_switch.py .......                 [ 81%]
tests\unit\test_provider_registry.py ....                                [ 85%]
tests\unit\test_security.py .....                                        [ 91%]
tests\unit\test_session_isolation.py .....                               [ 96%]
tests\unit\test_workflow.py ...                                          [100%]

============================= 91 passed in 27.49s =============================
```

### Dedicated Regression Tests Added
| Test Module | Tests | Scenarios Covered |
| :--- | :--- | :--- |
| `tests/unit/test_groq_provider.py` | 11 | Groq capabilities, missing key auth failure, rejection of Ollama localhost, rejection of generic 'groq' model name, 200 health check, 401 auth check, 429 rate limit check. |
| `tests/unit/test_provider_configuration_switch.py` | 7 | Switching from Ollama to Groq endpoint normalization, model normalization, trailing slash trimming, cloud loopback rejection, local Ollama loopback permission. |
| `tests/unit/test_chainlit_actions.py` | 5 | Chainlit Action creation with payload, reproduction of missing payload ValidationError, welcome actions schema validation, callback payload extraction. |
| `tests/unit/test_error_normalization.py` | 6 | Ollama connection error with `ollama serve`, Groq connection error without Ollama mentions, 401 auth error guidance, 404 missing model distinctions, 429 quota error. |

---

## 5. Instructions for Running and Testing

### 5.1 Application Startup
```powershell
# Activate virtual environment
.venv\Scripts\Activate.ps1

# Run Chainlit application in watch mode
chainlit run app.py -w
```
Open your browser at `http://localhost:8000`.

### 5.2 Steps to Verify Local Ollama
1. Verify Ollama is installed:
   ```powershell
   ollama --version
   ```
2. Start the local daemon:
   ```powershell
   ollama serve
   ```
3. List installed models:
   ```powershell
   ollama list
   ```
4. If `llama3.2:latest` is not listed, pull it:
   ```powershell
   ollama pull llama3.2:latest
   ```
5. In the chatbot, click the **"🔍 Test Provider Connection"** action button. The status should report `🟢 Ollama is active and running`.

### 5.3 Steps to Configure a Cloud Provider (e.g. Groq)
1. In the chatbot UI, open the **Model Configuration** sidebar drawer (sliders icon).
2. Select **Inference Provider:** `groq`.
3. The endpoint will automatically resolve to `https://api.groq.com/openai/v1` and model to `llama-3.3-70b-versatile`.
4. In **Session API Key (Ephemeral)**, paste your Groq API key (`gsk_...`).
5. Click **Confirm**. The status card will show:
   ```text
   - Provider: groq (Groq Cloud LPU Ultra-Fast Inference)
   - Model: llama-3.3-70b-versatile
   - Endpoint: https://api.groq.com/openai/v1
   - Credentials: Configured (Session-only)
   - Health Status: 🟢 Groq LPU active and authenticated.
   ```
6. Ask a question (e.g. *"What is your refund policy?"*). The response will stream in real-time with grounded citations.
7. Click **"🔒 Clear Session Secrets"** at any time to purge credentials from server runtime memory.

---

## 6. Remaining Limitations

1. **Active Internet for Cloud Providers:** Live execution of Groq, OpenAI, Anthropic, Google, or Mistral requires an active internet connection and a valid API key with available quota. In offline environments, the local Ollama engine or deterministic test mocks must be used.
2. **Local Hardware Constraints for Ollama:** Running large local models (e.g. 70B parameters) requires substantial GPU VRAM. For standard developer workstations, 3B parameter models (`llama3.2:latest`) or 1B models (`llama3.2:1b`) are recommended.
