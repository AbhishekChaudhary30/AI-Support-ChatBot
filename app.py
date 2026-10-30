"""AI Customer Support Chatbot - Main Application Entrypoint.

Powered by Chainlit, LangChain, and Ollama with multi-provider cloud adapters (OpenAI, Groq, Mistral, Google, Anthropic).
Features:
- Genuine token streaming with real-time UI updates.
- FAQ vector retrieval with heading-aware chunking and score thresholding.
- Support intent routing and human escalation workflow.
- Session-only ephemeral credential handling.
- Atomic knowledge base rebuild and health diagnostics.
"""

from typing import Any, Dict, List, Optional
import chainlit as cl
from chainlit.input_widget import Select, Slider, TextInput

from support_bot.conversation.context import MessageRole
from support_bot.conversation.manager import ConversationManager
from support_bot.core.config import AppSettings, SessionModelConfig, get_settings
from support_bot.core.exceptions import SupportBotException
from support_bot.core.logging_config import setup_logging
from support_bot.providers.base import BaseModelProvider
from support_bot.providers.registry import registry
from support_bot.retrieval.chunking import TextChunker
from support_bot.retrieval.embeddings import DeterministicFallbackEmbeddingProvider
from support_bot.retrieval.loader import KnowledgeBaseLoader
from support_bot.retrieval.manifest import ManifestManager
from support_bot.retrieval.retriever import InMemoryVectorRetriever
from support_bot.security.input_validation import normalize_endpoint_url, SecurityValidationError
from support_bot.security.secrets import SessionSecret, mask_secret
from support_bot.ui.components import (
    get_brand_badge,
    render_about_section_markdown,
    render_footer_markdown,
    render_technology_stack_markdown,
)
from support_bot.workflows.escalation import SupportEscalationManager
from support_bot.workflows.intent import IntentClassifier, SupportIntentCategory
from support_bot.workflows.support_workflow import SupportWorkflowCoordinator, WorkflowExecutionResult

logger = setup_logging()
settings: AppSettings = get_settings()


async def initialize_default_retriever() -> InMemoryVectorRetriever:
    """Pre-index knowledge base documents into in-memory retriever with manifest tracking."""
    manifest_mgr = ManifestManager()
    retriever = InMemoryVectorRetriever(
        embedding_provider=DeterministicFallbackEmbeddingProvider(),
        manifest_manager=manifest_mgr,
        default_min_score=0.20,
    )
    try:
        loader = KnowledgeBaseLoader(directory_path=settings.knowledge_base_dir)
        chunker = TextChunker(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
        report = await retriever.rebuild_from_knowledge_base(loader=loader, chunker=chunker)
        logger.info(
            "Knowledge base indexed: %d docs, %d chunks. Skipped: %d",
            report.get("documents_indexed", 0),
            report.get("chunks_indexed", 0),
            len(report.get("skipped_files", [])),
        )
    except Exception as e:
        logger.warning("Could not pre-index knowledge base: %s", str(e))
    return retriever


@cl.on_chat_start
async def on_chat_start():
    """Initialize session runtime state, settings drawer, and interactive welcome banner."""
    session_id = cl.user_session.get("id", "default_session")
    logger.info("Initializing chat session %s", session_id)

    # 1. Initialize session-only runtime models and secrets (preserving configuration if set)
    existing_config: Optional[SessionModelConfig] = cl.user_session.get("session_config")
    existing_secret: Optional[SessionSecret] = cl.user_session.get("session_secret")

    session_config = existing_config if existing_config else SessionModelConfig(
        provider_name=settings.default_provider,
        model_name=settings.default_ollama_model,
        endpoint_url=settings.ollama_base_url,
        temperature=0.2,
        max_tokens=1024,
        top_p=0.9,
    )
    session_secret = existing_secret if existing_secret else SessionSecret(None)

    # 2. Build fresh session-scoped retriever & workflow coordinator for clean conversation
    retriever = await initialize_default_retriever()
    workflow = SupportWorkflowCoordinator(
        session_id=session_id,
        retriever=retriever,
        settings=settings,
    )

    cl.user_session.set("session_config", session_config)
    cl.user_session.set("session_secret", session_secret)
    cl.user_session.set("retriever", retriever)
    cl.user_session.set("workflow", workflow)

    # 3. Configure Model Settings in Sidebar
    providers_list = registry.list_providers()
    default_idx = providers_list.index("ollama") if "ollama" in providers_list else 0
    await cl.ChatSettings(
        [
            Select(
                id="provider",
                label="Inference Provider",
                values=providers_list,
                initial_index=default_idx,
                description="Choose Ollama (free/local) or an optional cloud provider.",
            ),
            TextInput(
                id="model_name",
                label="Model Identifier",
                initial=settings.default_ollama_model,
                description="e.g. 'llama3.2:latest', 'mistral', 'gpt-4o-mini', 'gemini-1.5-flash', 'claude-3-5-haiku-latest'",
            ),
            TextInput(
                id="endpoint_url",
                label="Provider Endpoint URL",
                initial=settings.ollama_base_url,
                description="Default: http://localhost:11434 (Ollama) or official cloud API base URL",
            ),
            TextInput(
                id="api_key",
                label="Session API Key (Ephemeral)",
                initial="",
                description="Optional for cloud. Never written to disk, database, logs, or Git. Cleared on session end.",
            ),
            Slider(
                id="temperature",
                label="Sampling Temperature",
                initial=0.2,
                min=0.0,
                max=1.0,
                step=0.05,
                description="Lower values generate more factual, deterministic answers.",
            ),
            Slider(
                id="max_tokens",
                label="Max Response Tokens",
                initial=1024,
                min=128,
                max=4096,
                step=128,
                description="Maximum token budget for generated answers.",
            ),
        ]
    ).send()

    # 4. Check initial local Ollama reachability
    ollama_provider: BaseModelProvider = registry.get_provider("ollama")
    health = await ollama_provider.check_health(
        endpoint_url=settings.ollama_base_url,
        model_name=settings.default_ollama_model,
    )
    health_badge = (
        f"🟢 **Local Ollama Active** ({health.get('latency_ms', 0)}ms)"
        if health.get("is_healthy")
        else "🟡 **Local Ollama Not Running** (Start via `ollama serve` or select a cloud provider in Settings)"
    )

    # 5. Send Welcome Banner with interactive questions
    welcome_text = (
        f"{get_brand_badge()}\n\n"
        "Welcome to the **AI Customer Support Assistant**! I am here to help answer questions grounded in our "
        "verified knowledge base, guide you through policies, troubleshoot technical issues, or connect you with human representatives.\n\n"
        f"**Engine Status:** {health_badge}\n"
        f"**Active Model:** `{session_config.model_name}` via `{session_config.provider_name}`\n\n"
        "### Frequently Asked Questions (Click to Ask):"
    )

    example_actions = [
        cl.Action(name="ask_example", payload={"value": "What is your refund policy?"}, label="💳 What is your refund policy?"),
        cl.Action(name="ask_example", payload={"value": "How do I reset my password?"}, label="🔑 How do I reset my password?"),
        cl.Action(name="ask_example", payload={"value": "What should I do if my order is delayed?"}, label="🚚 What if my order is delayed?"),
        cl.Action(name="ask_example", payload={"value": "How do I troubleshoot an unresponsive page?"}, label="🛠️ Troubleshooting tips"),
        cl.Action(name="ask_example", payload={"value": "I want to speak with a human support agent."}, label="👤 Speak to human support"),
    ]

    await cl.Message(content=welcome_text, actions=example_actions).send()

    # Send Secondary System Controls message
    system_controls_text = (
        "> [!NOTE]\n"
        "> **Privacy & Session Isolation:** Any API key you enter is stored exclusively in server-side session memory "
        "> and is **never** written to disk, database, chat logs, or Git. Click **'Clear Session Secrets'** below at any time."
    )
    system_actions = [
        cl.Action(name="check_kb_status", payload={"value": "kb_status"}, label="📚 Knowledge Base Status"),
        cl.Action(name="rebuild_kb", payload={"value": "rebuild_kb"}, label="🔄 Rebuild Knowledge Index"),
        cl.Action(name="check_status", payload={"value": "status"}, label="🔍 Test Provider Connection"),
        cl.Action(name="clear_config", payload={"value": "clear"}, label="🔒 Clear Session Secrets"),
        cl.Action(name="about_project", payload={"value": "about"}, label="📖 About Project"),
        cl.Action(name="tech_stack", payload={"value": "tech"}, label="⚡ Technology Stack"),
    ]
    await cl.Message(content=system_controls_text, actions=system_actions).send()


async def _execute_streaming_query(user_query: str):
    """Execute query through workflow coordinator and stream tokens to Chainlit UI."""
    workflow: SupportWorkflowCoordinator = cl.user_session.get("workflow")
    session_config: SessionModelConfig = cl.user_session.get("session_config")
    session_secret: SessionSecret = cl.user_session.get("session_secret")

    # Initialize streaming message
    stream_msg = cl.Message(content="")
    await stream_msg.send()

    final_result: Optional[WorkflowExecutionResult] = None

    async for event in workflow.process_user_query_stream(
        raw_message=user_query,
        session_config=session_config,
        session_secret=session_secret,
    ):
        event_type = event.get("type")
        if event_type == "token":
            await stream_msg.stream_token(event["content"])
        elif event_type == "done":
            final_result = event.get("result")

    # Format retrieval transparency tag and verified sources
    citations_block = ""
    transparency_tag = ""

    if final_result:
        if final_result.is_escalation:
            transparency_tag = "\n\n*Transparency: 👤 Human Support Escalation Request*"
        elif final_result.retrieval_status == "grounded" and final_result.citations:
            source_count = len(final_result.citations)
            transparency_tag = f"\n\n*Transparency: 🟢 Answered using support knowledge base ({source_count} verified source{'s' if source_count > 1 else ''})*"
            
            citation_items = []
            for cit in final_result.citations:
                citation_items.append(
                    f"> - 📄 **{cit['title']}** (Section: *{cit['section']}* | Relevance: `{cit['score']}`)\n"
                    f">   *{cit['snippet']}*"
                )
            citations_block = "\n\n**Verified Knowledge Sources:**\n" + "\n".join(citation_items)
        elif final_result.retrieval_status == "insufficient_evidence":
            transparency_tag = "\n\n*Transparency: 🟡 No matching support documentation found in knowledge base*"
        else:
            transparency_tag = "\n\n*Transparency: 💬 General conversational response*"

    footer = render_footer_markdown(settings)
    final_content = f"{stream_msg.content}{citations_block}{transparency_tag}\n\n{footer}"
    stream_msg.content = final_content
    await stream_msg.update()


@cl.action_callback("ask_example")
async def on_ask_example(action: cl.Action):
    """Handle click on an example FAQ question with safe payload validation."""
    try:
        payload = action.payload if isinstance(getattr(action, "payload", None), dict) else {}
        question = payload.get("value") or getattr(action, "value", None)
        if not question or not str(question).strip():
            await cl.Message(content="⚠️ Could not process action: question payload was missing or empty.").send()
            return
        clean_question = str(question).strip()
        # Render user prompt message
        await cl.Message(content=clean_question, author="User").send()
        await _execute_streaming_query(clean_question)
    except Exception as e:
        logger.error("Error in on_ask_example callback: %s", str(e), exc_info=True)
        await cl.Message(content=f"⚠️ Action failed: {type(e).__name__}. Please type your question directly.").send()


@cl.on_settings_update
async def on_settings_update(raw_settings: Dict[str, Any]):
    """Handle user updates in the Model Configuration drawer with endpoint/model normalization."""
    session_config: SessionModelConfig = cl.user_session.get("session_config")
    session_secret: SessionSecret = cl.user_session.get("session_secret")

    previous_provider = session_config.provider_name
    submitted_provider = str(raw_settings.get("provider", session_config.provider_name)).strip().lower()

    # 1. Resolve Provider
    if not registry.is_registered(submitted_provider):
        await cl.Message(
            content=f"⚠️ **Unknown Provider:** `{submitted_provider}` is not registered. Keeping `{session_config.provider_name}`."
        ).send()
        return

    provider_changed = (submitted_provider != previous_provider)
    target_provider: BaseModelProvider = registry.get_provider(submitted_provider)
    canonical_endpoint = target_provider.capabilities.default_endpoint or ""
    canonical_model = getattr(target_provider.capabilities, "default_model", "") or "default"

    # 2. Endpoint normalization & anti-contamination
    raw_endpoint = str(raw_settings.get("endpoint_url", "")).strip()
    prev_default_endpoint = (
        registry.get_provider(previous_provider).capabilities.default_endpoint
        if registry.is_registered(previous_provider)
        else ""
    )
    is_ollama_endpoint = any(h in raw_endpoint for h in ("localhost:11434", "127.0.0.1:11434", "::1:11434")) or (raw_endpoint == settings.ollama_base_url)
    is_cloud_provider = not target_provider.capabilities.is_local

    endpoint_normalized_notice = False
    if (
        provider_changed
        or not raw_endpoint
        or (is_cloud_provider and is_ollama_endpoint)
        or (raw_endpoint == prev_default_endpoint and provider_changed)
    ):
        endpoint_url = canonical_endpoint
        if is_cloud_provider and is_ollama_endpoint:
            endpoint_normalized_notice = True
    else:
        # Validate custom endpoint
        try:
            endpoint_url = normalize_endpoint_url(raw_endpoint, provider_name=submitted_provider)
        except SecurityValidationError as sve:
            await cl.Message(
                content=f"⚠️ **Endpoint Notice:** {sve.user_friendly_message} Using default `{canonical_endpoint}`."
            ).send()
            endpoint_url = canonical_endpoint

    # 3. Model identifier normalization & anti-contamination
    raw_model = str(raw_settings.get("model_name", "")).strip()
    prev_default_model = (
        getattr(registry.get_provider(previous_provider).capabilities, "default_model", "")
        if registry.is_registered(previous_provider)
        else ""
    )
    is_generic_placeholder = raw_model.lower() in (
        "groq",
        "ollama",
        "openai",
        "anthropic",
        "google",
        "mistral",
        "provider",
        "model",
        "default",
        "",
    )

    model_normalized_notice = False
    if (
        provider_changed
        or not raw_model
        or is_generic_placeholder
        or (raw_model == prev_default_model and provider_changed)
    ):
        model_name = canonical_model
        if is_generic_placeholder and raw_model:
            model_normalized_notice = True
    else:
        model_name = raw_model

    # 4. API Key Handling (session-only ephemeral storage)
    api_key_input = str(raw_settings.get("api_key", "")).strip()
    if api_key_input:
        session_secret = SessionSecret(api_key_input)
        cl.user_session.set("session_secret", session_secret)
        logger.info(
            "Session API key updated for provider '%s' (masked: %s)",
            submitted_provider,
            mask_secret(api_key_input),
        )

    # 5. Update session configuration
    session_config.provider_name = submitted_provider
    session_config.model_name = model_name
    session_config.endpoint_url = endpoint_url
    try:
        session_config.temperature = float(raw_settings.get("temperature", 0.2))
    except (ValueError, TypeError):
        pass
    try:
        session_config.max_tokens = int(raw_settings.get("max_tokens", 1024))
    except (ValueError, TypeError):
        pass

    # 6. Perform health & reachability check
    health = await target_provider.check_health(
        endpoint_url=endpoint_url,
        session_secret=session_secret,
        model_name=model_name,
    )

    # 7. Format clean, truthful configuration status
    is_healthy = health.get("is_healthy", False)
    if is_healthy:
        status_icon = "🟢"
    elif health.get("details", {}).get("key_missing"):
        status_icon = "🟡"
    elif health.get("details", {}).get("model_missing"):
        status_icon = "🟡"
    else:
        status_icon = "🔴"

    correction_notes = []
    if endpoint_normalized_notice:
        correction_notes.append(
            f"> ℹ️ *Endpoint automatically set to official `{submitted_provider}` API (`{canonical_endpoint}`) instead of local Ollama.*"
        )
    if model_normalized_notice:
        correction_notes.append(
            f"> ℹ️ *Model name normalized to `{canonical_model}` (`{raw_model}` was recognized as a provider name).* "
        )
    correction_text = ("\n" + "\n".join(correction_notes) + "\n") if correction_notes else ""

    credentials_text = (
        "Configured (Session-only)"
        if session_secret.is_configured()
        else ("Not Required (Local)" if target_provider.capabilities.is_local else "Missing (API Key Required)")
    )

    status_msg = (
        f"### ⚙️ Provider Configuration Updated\n\n"
        f"- **Provider:** `{submitted_provider}` ({target_provider.capabilities.display_name})\n"
        f"- **Model:** `{model_name}`\n"
        f"- **Endpoint:** `{endpoint_url}`\n"
        f"- **Credentials:** `{credentials_text}`\n"
        f"- **Health Status:** {status_icon} {health.get('message', 'Active')}\n"
        f"{correction_text}"
    )
    await cl.Message(content=status_msg).send()


@cl.action_callback("check_kb_status")
async def on_check_kb_status(action: cl.Action):
    """Render knowledge base index status, document count, and manifest metadata."""
    retriever: InMemoryVectorRetriever = cl.user_session.get("retriever")
    if not retriever:
        await cl.Message(content="⚠️ Knowledge base retriever is not initialized.").send()
        return

    manifest = retriever.manifest_manager.manifest
    report = (
        f"### 📚 Knowledge Base Index Status\n\n"
        f"- **Index State:** `{retriever.status.value.upper()}`\n"
        f"- **Documents Indexed:** `{manifest.document_count}`\n"
        f"- **Semantic Chunks:** `{retriever.chunk_count}`\n"
        f"- **Embedding Model:** `{retriever.embedding_provider.model_name}`\n"
        f"- **Last Indexed At:** `{manifest.last_indexed_at or 'Never'}`\n"
        f"- **Indexed FAQ Files:**\n"
    )
    for path in manifest.file_hashes.keys():
        report += f"  - `📄 {path}`\n"

    await cl.Message(content=report).send()


@cl.action_callback("rebuild_kb")
async def on_rebuild_kb(action: cl.Action):
    """Perform atomic knowledge base re-indexing."""
    retriever: InMemoryVectorRetriever = cl.user_session.get("retriever")
    status_msg = await cl.Message(content="⏳ **Rebuilding Knowledge Base Index...** Loading and chunking files...").send()

    try:
        loader = KnowledgeBaseLoader(directory_path=settings.knowledge_base_dir)
        chunker = TextChunker(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
        result = await retriever.rebuild_from_knowledge_base(loader=loader, chunker=chunker)

        status_msg.content = (
            f"✅ **Knowledge Base Index Rebuilt Successfully!**\n\n"
            f"- **Documents Indexed:** `{result.get('documents_indexed', 0)}`\n"
            f"- **Semantic Chunks:** `{result.get('chunks_indexed', 0)}`\n"
            f"- **Skipped Files:** `{len(result.get('skipped_files', []))}`\n"
            "- **Embedding Model:** `deterministic-fallback-128` (Ready for local queries)"
        )
        await status_msg.update()
    except Exception as e:
        status_msg.content = f"🔴 **Knowledge Base Rebuild Failed:** {str(e)}"
        await status_msg.update()


@cl.action_callback("check_status")
async def on_check_status(action: cl.Action):
    """Check connection status of active model provider."""
    session_config: SessionModelConfig = cl.user_session.get("session_config")
    session_secret: SessionSecret = cl.user_session.get("session_secret")

    try:
        provider: BaseModelProvider = registry.get_provider(session_config.provider_name)
        health = await provider.check_health(
            endpoint_url=session_config.endpoint_url,
            session_secret=session_secret,
            model_name=session_config.model_name,
        )
        status_icon = "🟢" if health.get("is_healthy") else "🔴"
        report = (
            f"### Provider Connection Report\n\n"
            f"- **Provider:** `{session_config.provider_name}`\n"
            f"- **Endpoint:** `{session_config.endpoint_url}`\n"
            f"- **Model:** `{session_config.model_name}`\n"
            f"- **Status:** {status_icon} {health.get('message')}\n"
            f"- **Latency:** {health.get('latency_ms', 'N/A')} ms\n"
            f"- **API Key Loaded:** {'Yes (Ephemeral Session)' if session_secret.is_configured() else 'No / Not Required'}"
        )
    except Exception as e:
        report = f"🔴 **Health Check Failed:** {str(e)}"

    await cl.Message(content=report).send()


@cl.action_callback("clear_config")
async def on_clear_config(action: cl.Action):
    """Erase ephemeral session credentials and reset model configuration."""
    session_secret: SessionSecret = cl.user_session.get("session_secret")
    if session_secret:
        session_secret.clear()

    session_config = SessionModelConfig(
        provider_name="ollama",
        model_name=settings.default_ollama_model,
        endpoint_url=settings.ollama_base_url,
    )
    cl.user_session.set("session_config", session_config)

    logger.info("Session credentials cleared by user.")
    await cl.Message(
        content=(
            "🔒 **Session Credentials Cleared!**\n\n"
            "All session API keys have been completely erased from runtime memory. "
            "Provider configuration has been reset to local Ollama defaults."
        )
    ).send()


@cl.action_callback("about_project")
async def on_about_project(action: cl.Action):
    """Render About This Project educational documentation."""
    await cl.Message(content=render_about_section_markdown()).send()


@cl.action_callback("tech_stack")
async def on_tech_stack(action: cl.Action):
    """Render Technology Stack visualization and cards."""
    await cl.Message(content=render_technology_stack_markdown()).send()


@cl.on_message
async def on_message(message: cl.Message):
    """Process incoming customer support questions with token streaming."""
    await _execute_streaming_query(message.content)
