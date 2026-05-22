"""Campaign Brief Parser Agent — extracts structured data from natural language briefs."""

import logging
import re
from typing import Any, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator

from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# ── Schemas ───────────────────────────────────────────────────────────────────

_ALLOWED_GOALS = {"awareness", "conversion", "retention", "engagement"}
_ALLOWED_TONES = {"professional", "casual", "friendly", "urgent"}

_BUDGET_RE = re.compile(r"\$?\s*([\d,]+(?:\.\d{1,2})?)\s*[kK]?")


class BriefInput(BaseModel):
    """Input schema for the brief parser agent."""

    brief_text: str = Field(..., min_length=1, description="Natural language campaign brief")

    @field_validator("brief_text")
    @classmethod
    def strip_and_require(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("brief_text must not be empty")
        return v


class ParsedBrief(BaseModel):
    """Structured output produced by the brief parser agent."""

    product_name: str
    product_description: str = "Not specified"
    target_audience: str
    campaign_goal: str
    cta_link: str = ""
    budget: Optional[float] = None
    preferred_tone: str = "professional"
    key_messages: list[str] = Field(default_factory=list)
    constraints: Optional[str] = None

    @field_validator("campaign_goal")
    @classmethod
    def validate_goal(cls, v: str) -> str:
        normalised = v.lower().strip()
        if normalised not in _ALLOWED_GOALS:
            raise ValueError(
                f"campaign_goal must be one of {sorted(_ALLOWED_GOALS)}, got '{v}'"
            )
        return normalised

    @field_validator("preferred_tone")
    @classmethod
    def validate_tone(cls, v: str) -> str:
        normalised = v.lower().strip()
        if normalised not in _ALLOWED_TONES:
            return "professional"
        return normalised

    @field_validator("cta_link")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v or v.lower() in {"unknown", "not specified", "none", "n/a", ""}:
            return ""
        parsed = urlparse(v)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"cta_link must be a valid URL, got '{v}'")
        return v

    @field_validator("key_messages")
    @classmethod
    def ensure_messages(cls, v: list[str]) -> list[str]:
        return [m.strip() for m in v if m and m.strip()]

    @model_validator(mode="after")
    def validate_required_fields(self) -> "ParsedBrief":
        missing = []
        if not self.product_name or self.product_name.lower() in {"unknown", "not specified"}:
            missing.append("product_name")
        if not self.target_audience or self.target_audience.lower() in {"unknown", "not specified"}:
            missing.append("target_audience")
        if missing:
            raise ValueError(
                f"Critically required fields could not be extracted: {missing}. "
                "Please provide a more detailed campaign brief."
            )
        return self


# ── Prompt ────────────────────────────────────────────────────────────────────

_BRIEF_PARSER_TEMPLATE = """\
You are a marketing analyst AI. Extract structured campaign information from the brief below \
and respond with ONLY a valid JSON object — no markdown fences, no extra text.

## Required JSON schema
{{
  "product_name":        "<string>  — name of the product or service being promoted",
  "product_description": "<string>  — short description of the product/service",
  "target_audience":     "<string>  — who the campaign targets (demographics, interests, etc.)",
  "campaign_goal":       "<string>  — MUST be one of: awareness | conversion | retention | engagement",
  "cta_link":            "<string>  — CTA URL if present, otherwise empty string",
  "budget":              <number|null> — numeric budget in USD (e.g. 5000.0), null if absent",
  "preferred_tone":      "<string>  — MUST be one of: professional | casual | friendly | urgent",
  "key_messages":        ["<string>", ...]  — 3-5 key selling points or messages",
  "constraints":         "<string|null> — any stated restrictions, timing, or compliance notes"
}}

## Rules
- If a field cannot be inferred, use the safest default (empty string / null / "professional").
- campaign_goal: map "sales"→conversion, "brand"→awareness, "loyal"→retention, "interact"→engagement.
- budget: strip currency symbols and "k" multipliers (e.g. "$5k" → 5000.0).
- cta_link: return empty string if no valid URL is present.
- key_messages: even if written as prose, split into 3–5 individual bullet-style strings.
- Do NOT invent facts not present in the brief.

## Examples

Brief: "Launch our new CloudStorage Pro plan targeting SMB owners. Goal is to get sign-ups at \
https://cloudstorage.io/pro. Budget $8,000. Keep it professional. Key points: 500 GB storage, \
team collaboration, 99.9 % uptime."

Response:
{{
  "product_name": "CloudStorage Pro",
  "product_description": "Cloud storage plan for small and medium businesses",
  "target_audience": "SMB owners",
  "campaign_goal": "conversion",
  "cta_link": "https://cloudstorage.io/pro",
  "budget": 8000.0,
  "preferred_tone": "professional",
  "key_messages": ["500 GB storage", "Team collaboration tools", "99.9% uptime guarantee"],
  "constraints": null
}}

---

Brief: "Remind existing subscribers about renewal. Friendly reminder tone. No fixed budget."

Response:
{{
  "product_name": "Subscription Service",
  "product_description": "Existing subscription product",
  "target_audience": "Existing subscribers approaching renewal",
  "campaign_goal": "retention",
  "cta_link": "",
  "budget": null,
  "preferred_tone": "friendly",
  "key_messages": [
    "Your subscription is coming up for renewal",
    "Continue enjoying uninterrupted access",
    "Renew now to keep your benefits"
  ],
  "constraints": null
}}

---

## Campaign Brief to parse

{brief_text}

Respond with ONLY the JSON object. No explanation.
"""


# ── Agent ─────────────────────────────────────────────────────────────────────

class CampaignBriefParserAgent(BaseAgent):
    """Parses natural language marketing briefs into structured ``ParsedBrief`` objects."""

    def __init__(self, **kwargs: Any) -> None:
        # Low temperature for deterministic, factual extraction
        kwargs.setdefault("temperature", 0.1)
        kwargs.setdefault("max_tokens", 1024)
        super().__init__(**kwargs)
        self._prompt = self.create_prompt_template(
            template=_BRIEF_PARSER_TEMPLATE,
            input_variables=["brief_text"],
        )

    # ── Public interface ──────────────────────────────────────────────────────

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Parse a campaign brief and return a validated ``ParsedBrief`` dict.

        Args:
            input_data: Must contain ``brief_text`` (natural language campaign brief).

        Returns:
            A dict representation of the validated ``ParsedBrief``.

        Raises:
            ValueError: If ``brief_text`` is missing/empty or required fields cannot
                        be extracted (product_name, target_audience, campaign_goal).
        """
        validated: BriefInput = self._validate_input(input_data, BriefInput)
        self._log_action("execute_start", {"brief_length": len(validated.brief_text)})

        raw_output: str = await self._retry_with_backoff(
            self._call_llm, validated.brief_text
        )

        parsed_dict = self._parse_llm_output(raw_output)
        parsed_dict = self._post_process(parsed_dict, validated.brief_text)
        parsed_brief = self._validate_input(parsed_dict, ParsedBrief)

        self._log_action(
            "execute_complete",
            {
                "product_name": parsed_brief.product_name,  # type: ignore[union-attr]
                "campaign_goal": parsed_brief.campaign_goal,  # type: ignore[union-attr]
                "budget": parsed_brief.budget,  # type: ignore[union-attr]
                "key_messages_count": len(parsed_brief.key_messages),  # type: ignore[union-attr]
            },
        )
        return parsed_brief.model_dump()  # type: ignore[union-attr]

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _call_llm(self, brief_text: str) -> str:
        """Format the prompt and invoke the LLM, returning the raw response string."""
        prompt_text = self._prompt.format(brief_text=brief_text)
        response = await self.llm.ainvoke(prompt_text)
        return response.content if hasattr(response, "content") else str(response)

    def _post_process(self, data: dict[str, Any], original_brief: str) -> dict[str, Any]:
        """Apply heuristic fixes to the raw LLM-extracted dict before Pydantic validation.

        Handles:
        - Budget string normalisation ("$5k" → 5000.0)
        - Removing placeholder sentinel values
        - Ensuring key_messages is always a list
        - Defaulting missing keys so Pydantic receives the full schema
        """
        # -- budget normalisation -------------------------------------------------
        raw_budget = data.get("budget")
        if isinstance(raw_budget, str):
            data["budget"] = self._parse_budget(raw_budget)
        elif raw_budget is not None:
            try:
                data["budget"] = float(raw_budget)
            except (TypeError, ValueError):
                data["budget"] = None

        # -- cta_link sentinel clean-up -------------------------------------------
        cta = data.get("cta_link", "")
        if isinstance(cta, str) and cta.lower() in {"unknown", "n/a", "none", "not specified"}:
            data["cta_link"] = ""

        # -- key_messages: tolerate comma-separated strings / single strings -------
        km = data.get("key_messages")
        if isinstance(km, str):
            data["key_messages"] = [m.strip() for m in km.split(",") if m.strip()]
        elif not isinstance(km, list):
            data["key_messages"] = []

        # -- fill missing optional keys -------------------------------------------
        data.setdefault("product_description", "Not specified")
        data.setdefault("preferred_tone", "professional")
        data.setdefault("constraints", None)
        data.setdefault("cta_link", "")
        data.setdefault("budget", None)

        return data

    @staticmethod
    def _parse_budget(raw: str) -> Optional[float]:
        """Convert a textual budget string to a float (USD).

        Handles formats like "$5,000", "5k", "$8K", "10000.00".
        Returns ``None`` if the string cannot be parsed.
        """
        raw = raw.strip().replace(",", "")
        multiplier = 1000.0 if raw.lower().endswith("k") else 1.0
        raw = raw.lstrip("$").rstrip("kK").strip()
        match = _BUDGET_RE.match(raw)
        if match:
            try:
                return float(match.group(1).replace(",", "")) * multiplier
            except ValueError:
                return None
        return None
