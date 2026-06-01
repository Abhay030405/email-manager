"""Base agent providing shared LLM, memory, prompting, retry, and validation infrastructure."""

import asyncio
import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel, ValidationError

try:
    from langchain.memory import ConversationBufferMemory
except ImportError:
    try:
        from langchain_community.memory import ConversationBufferMemory  # type: ignore[no-redef]
    except ImportError:
        class ConversationBufferMemory:  # type: ignore[no-redef]
            """Minimal stub when langchain memory packages are unavailable."""
            def __init__(self, **kwargs: Any) -> None:
                self.chat_history: list = []

try:
    from langchain.prompts import PromptTemplate
except ImportError:
    from langchain_core.prompts import PromptTemplate  # type: ignore[no-redef]

import openai
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class _LLMClient:
    """Thin async wrapper around the OpenAI SDK pointed at OpenRouter.

    OpenRouter exposes an OpenAI-compatible Chat Completions API, so we
    configure `base_url` to route all calls through OpenRouter instead of
    OpenAI directly. This lets any model available on OpenRouter (Gemini,
    Claude, Mistral, etc.) be swapped in via the LLM_MODEL env variable.
    """

    def __init__(
        self,
        model: str,
        temperature: float,
        max_tokens: int,
        api_key: str,
        base_url: str,
        timeout: int,
    ) -> None:
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )

    async def ainvoke(self, prompt: str) -> Any:
        """Call the model via OpenRouter and return an object with a `.content` attribute."""
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=self._max_tokens,
            temperature=self._temperature,
        )
        content = resp.choices[0].message.content or ""
        return type("_Msg", (), {"content": content})()


class BaseAgent(ABC):
    """Abstract base class for all CampaignX AI agents.

    Provides:
    - LLM initialisation via OpenRouter (reads OPENROUTER_API_KEY / LLM_MODEL from settings)
    - Conversation buffer memory
    - PromptTemplate factory
    - Exponential back-off retry wrapper (async-aware)
    - Structured logging helper
    - Pydantic input validation
    - LLM output parsing (JSON-first with plain-text fallback)
    - Per-call timeout enforcement
    """

    DEFAULT_MODEL: str = get_settings().LLM_MODEL
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_MAX_TOKENS: int = 2000
    DEFAULT_TIMEOUT: int = 30  # seconds
    MAX_RETRIES: int = 3

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self._settings = get_settings()
        self.llm: _LLMClient = self.setup_llm()
        self.memory: ConversationBufferMemory = self.setup_memory()
        logger.info(
            "Agent '%s' initialised | model='%s' temperature=%.2f max_tokens=%d timeout=%ds",
            self.__class__.__name__,
            model_name,
            temperature,
            max_tokens,
            timeout,
        )

    # ── Setup ──────────────────────────────────────────────────────────────

    def setup_llm(self) -> "_LLMClient":
        """Initialise the OpenRouter LLM client from application settings."""
        api_key = self._settings.OPENROUTER_API_KEY
        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY is not configured. "
                "Set the variable in your environment or .env file."
            )
        return _LLMClient(
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            api_key=api_key,
            base_url=self._settings.OPENROUTER_BASE_URL,
            timeout=self.timeout,
        )

    def setup_memory(self) -> ConversationBufferMemory:
        """Initialise a fresh conversation buffer memory instance."""
        return ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
        )

    def create_prompt_template(
        self, template: str, input_variables: list[str]
    ) -> PromptTemplate:
        """Create a LangChain ``PromptTemplate`` from a raw template string.

        Args:
            template: The prompt template string with ``{variable}`` placeholders.
            input_variables: Ordered list of variable names used in *template*.

        Returns:
            A configured ``PromptTemplate`` instance ready for formatting.
        """
        return PromptTemplate(template=template, input_variables=input_variables)

    # ── Core execution ─────────────────────────────────────────────────────

    @abstractmethod
    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent's primary task.

        Must be implemented by every concrete subclass.

        Args:
            input_data: Arbitrary key/value payload specific to the agent's domain.

        Returns:
            A dictionary containing the agent's result payload.
        """

    # ── Retry / back-off ───────────────────────────────────────────────────

    async def _retry_with_backoff(
        self,
        func,
        *args: Any,
        max_retries: int = MAX_RETRIES,
        **kwargs: Any,
    ) -> Any:
        """Invoke *func* up to *max_retries* times with exponential back-off.

        Supports both async coroutines and regular callables. Each call is
        wrapped with ``self.timeout`` via ``asyncio.wait_for``.

        Back-off schedule: 1 s → 2 s → 4 s between successive attempts.

        Args:
            func: The callable (sync or async) to invoke.
            *args: Positional arguments forwarded to *func*.
            max_retries: Maximum number of attempts (default ``MAX_RETRIES = 3``).
            **kwargs: Keyword arguments forwarded to *func*.

        Returns:
            The return value of *func* on the first successful attempt.

        Raises:
            The last exception raised after all retries are exhausted.
        """
        last_exc: Optional[Exception] = None

        for attempt in range(1, max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await asyncio.wait_for(
                        func(*args, **kwargs), timeout=float(self.timeout)
                    )
                loop = asyncio.get_event_loop()
                return await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: func(*args, **kwargs)),
                    timeout=float(self.timeout),
                )
            except asyncio.TimeoutError as exc:
                last_exc = exc
                self._log_action(
                    "timeout",
                    {
                        "attempt": attempt,
                        "max_retries": max_retries,
                        "timeout_seconds": self.timeout,
                    },
                )
            except Exception as exc:
                last_exc = exc
                self._log_action(
                    "retry",
                    {
                        "attempt": attempt,
                        "max_retries": max_retries,
                        "error": str(exc),
                    },
                )

            if attempt < max_retries:
                backoff = 2 ** (attempt - 1)  # 1 s, 2 s, 4 s
                logger.debug(
                    "Agent '%s' — waiting %.0fs before attempt %d/%d",
                    self.__class__.__name__,
                    backoff,
                    attempt + 1,
                    max_retries,
                )
                await asyncio.sleep(backoff)

        raise last_exc  # type: ignore[misc]

    # ── Logging ────────────────────────────────────────────────────────────

    def _log_action(self, action: str, data: dict[str, Any]) -> None:
        """Emit a structured INFO log entry for an agent action.

        Args:
            action: Short label describing the action (e.g. ``"retry"``, ``"validation_error"``).
            data:   Arbitrary contextual metadata to include in the log record.
        """
        logger.info(
            "Agent='%s' action='%s' data=%s",
            self.__class__.__name__,
            action,
            data,
        )

    # ── Validation ─────────────────────────────────────────────────────────

    def _validate_input(
        self, data: dict[str, Any], schema: type[BaseModel]
    ) -> BaseModel:
        """Validate *data* against a Pydantic *schema*.

        Args:
            data:   Raw dictionary of input values to validate.
            schema: A Pydantic ``BaseModel`` subclass to validate against.

        Returns:
            The validated and coerced Pydantic model instance.

        Raises:
            ValueError: Wraps ``ValidationError`` with a human-readable message.
        """
        try:
            return schema.model_validate(data)
        except ValidationError as exc:
            self._log_action("validation_error", {"errors": exc.errors()})
            raise ValueError(f"Input validation failed: {exc}") from exc

    # ── Output parsing ─────────────────────────────────────────────────────

    def _parse_llm_output(self, raw_output: str) -> dict[str, Any]:
        """Parse an LLM response string into a structured dictionary.

        Strategy (in order):
        1. Strip all markdown code fences and try direct JSON parse.
        2. Extract the first {...} block from anywhere in the text (handles
           preamble like "Here is the JSON:" added by some models).
        3. Extract the first [...] array block.
        4. Fall back to {"content": raw_output} so callers always get a dict.
        """
        # Remove all ``` fences (not just start/end)
        cleaned = re.sub(r"```(?:json)?\s*", "", raw_output.strip(), flags=re.IGNORECASE)
        cleaned = cleaned.replace("```", "").strip()

        # 1. Direct parse
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # 2. Extract first {...} object (handles preamble text)
        obj_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if obj_match:
            try:
                return json.loads(obj_match.group())
            except json.JSONDecodeError:
                pass

        # 3. Extract first [...] array
        arr_match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if arr_match:
            try:
                return json.loads(arr_match.group())
            except json.JSONDecodeError:
                pass

        self._log_action(
            "parse_llm_output",
            {"warning": "LLM response is not valid JSON; wrapping as plain text."},
        )
        return {"content": raw_output}
