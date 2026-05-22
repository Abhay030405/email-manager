"""Base agent providing shared LLM, memory, prompting, retry, and validation infrastructure."""

import asyncio
import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel, ValidationError

try:
    from langchain_openai import ChatOpenAI
except ImportError:  # pragma: no cover – fallback for environments without langchain-openai
    from langchain.chat_models import ChatOpenAI  # type: ignore[no-redef]

from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all CampaignX AI agents.

    Provides:
    - OpenAI GPT-4 LLM initialisation (reads OPENAI_API_KEY from settings)
    - Conversation buffer memory
    - PromptTemplate factory
    - Exponential back-off retry wrapper (async-aware)
    - Structured logging helper
    - Pydantic input validation
    - LLM output parsing (JSON-first with plain-text fallback)
    - Per-call timeout enforcement
    """

    DEFAULT_MODEL: str = "gpt-4"
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
        self.llm: ChatOpenAI = self.setup_llm()
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

    def setup_llm(self) -> ChatOpenAI:
        """Initialise the OpenAI ChatOpenAI client from application settings."""
        api_key = self._settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is not configured. "
                "Set the variable in your environment or .env file."
            )
        return ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            openai_api_key=api_key,
            request_timeout=self.timeout,
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

        Strips Markdown code fences (\\`\\`\\`json ... \\`\\`\\`) before attempting
        JSON decoding. Falls back to ``{"content": raw_output}`` when the
        response cannot be decoded as JSON, ensuring callers always receive
        a ``dict``.

        Args:
            raw_output: The raw string returned by the LLM.

        Returns:
            A dictionary representation of the LLM's output.
        """
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_output.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip())

        try:
            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            self._log_action(
                "parse_llm_output",
                {"warning": "LLM response is not valid JSON; wrapping as plain text."},
            )
            return {"content": raw_output}
