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


class AudienceGroup(BaseModel):
    """Structured demographic/behavioural profile for one target audience segment."""

    min_age: Optional[int] = None
    max_age: Optional[int] = None
    Marital_Status: Optional[str] = None        # Single | Married | Divorced
    Family_Size: Optional[int] = None
    Dependent_count: Optional[int] = None
    Occupation: Optional[str] = None
    Occupation_type: Optional[str] = None       # Full-time | Part-time | Self-employed
    Monthly_Income: Optional[int] = None        # absolute integer e.g. 30000
    KYC_status: Optional[str] = None            # Y | N
    City: Optional[str] = None
    Kids_in_Household: Optional[int] = None
    App_Installed: Optional[str] = None         # Y | N
    Existing_Customer: Optional[str] = None     # Y | N
    Credit_score: Optional[int] = None
    Social_Media_Active: Optional[str] = None   # Y | N


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
    target_audience: dict[str, AudienceGroup] = Field(default_factory=dict)
    campaign_goal: str
    campaign_objective: str = ""
    campaign_name: str = ""
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
        if not self.product_name or self.product_name.lower() in {"unknown", "not specified"}:
            raise ValueError(
                "Critically required fields could not be extracted: ['product_name']. "
                "Please provide a more detailed campaign brief."
            )
        if not self.target_audience:
            self.target_audience = {"Group 1": AudienceGroup()}
        return self


# ── Prompt ────────────────────────────────────────────────────────────────────

_BRIEF_PARSER_TEMPLATE = """\
You are a marketing analyst AI. Extract structured campaign information from the brief below \
and respond with ONLY a valid JSON object — no markdown fences, no extra text.

## Required JSON schema
{{
  "product_name":        "<string>  — name of the product or service being promoted",
  "product_description": "<string>  — short description of the product/service",
  "target_audience": {{
    "Group 1": {{
      "min_age":           <int|null>,
      "max_age":           <int|null>,
      "Marital_Status":    <"Single"|"Married"|"Divorced"|null>,
      "Family_Size":       <int|null>,
      "Dependent_count":   <int|null>,
      "Occupation":        <string|null>,
      "Occupation_type":   <"Full-time"|"Part-time"|"Self-employed"|null>,
      "Monthly_Income":    <int|null>,
      "KYC_status":        <"Y"|"N"|null>,
      "City":              <string|null>,
      "Kids_in_Household": <int|null>,
      "App_Installed":     <"Y"|"N"|null>,
      "Existing_Customer": <"Y"|"N"|null>,
      "Credit_score":      <int|null>,
      "Social_Media_Active": <"Y"|"N"|null>
    }},
    "Group 2": {{ ... }}
  }},
  "campaign_goal":       "<string>  — MUST be one of: awareness | conversion | retention | engagement",
  "campaign_objective":  "<string>  — a full, descriptive sentence combining the primary objective, secondary objective, and success metrics; empty string if none stated",
  "campaign_name":       "<string>  — a short, memorable campaign label of 15-20 characters; ALWAYS generate one",
  "cta_link":            "<string>  — CTA URL if present, otherwise empty string",
  "budget":              <number|null>,
  "preferred_tone":      "<string>  — MUST be one of: professional | casual | friendly | urgent",
  "key_messages":        ["<string>", ...],
  "constraints":         "<string|null>"
}}

## Rules
- target_audience: create one group per DISTINCT audience segment described. If only one segment, produce only "Group 1".
- Each group field must be null if NOT explicitly stated in the brief. Do NOT infer or predict.
- Monthly_Income must be an absolute integer (e.g. 30000, not "30L" or "30k").
- campaign_goal: map "sales"→conversion, "brand"→awareness, "loyal"→retention, "interact"→engagement.
- budget: strip currency symbols and "k" multipliers (e.g. "$5k" → 5000.0).
- cta_link: return empty string if no valid URL is present.
- key_messages: split into 3–5 individual bullet-style strings.
- campaign_name: ALWAYS generate a short label (15–20 characters). Use the brief's name if one is given.
- Do NOT invent facts not present in the brief.

## Examples

Brief: "Launch our new CloudStorage Pro plan targeting SMB owners. Goal is to get sign-ups at \
https://cloudstorage.io/pro. Budget $8,000. Keep it professional. Key points: 500 GB storage, \
team collaboration, 99.9 % uptime."

Response:
{{
  "product_name": "CloudStorage Pro",
  "product_description": "Cloud storage plan for small and medium businesses",
  "target_audience": {{
    "Group 1": {{
      "min_age": null, "max_age": null, "Marital_Status": null, "Family_Size": null,
      "Dependent_count": null, "Occupation": "SMB owner", "Occupation_type": null,
      "Monthly_Income": null, "KYC_status": null, "City": null,
      "Kids_in_Household": null, "App_Installed": null, "Existing_Customer": null,
      "Credit_score": null, "Social_Media_Active": null
    }}
  }},
  "campaign_goal": "conversion",
  "campaign_objective": "Drive new sign-ups for the CloudStorage Pro plan.",
  "campaign_name": "CloudStorage Launch",
  "cta_link": "https://cloudstorage.io/pro",
  "budget": 8000.0,
  "preferred_tone": "professional",
  "key_messages": ["500 GB storage", "Team collaboration tools", "99.9% uptime guarantee"],
  "constraints": null
}}

---

Brief: "Target married salaried professionals aged 25-45 in metro cities (monthly income > 50k, \
app installed, KYC verified, credit score above 700, family size 3+) AND single students aged \
18-24 without the app. Goal: drive sign-ups for XDeposit at https://example.com/xdeposit."

Response:
{{
  "product_name": "XDeposit",
  "product_description": "Investment / deposit product",
  "target_audience": {{
    "Group 1": {{
      "min_age": 25, "max_age": 45, "Marital_Status": "Married", "Family_Size": 3,
      "Dependent_count": null, "Occupation": null, "Occupation_type": "Full-time",
      "Monthly_Income": 50000, "KYC_status": "Y", "City": "Metro cities",
      "Kids_in_Household": null, "App_Installed": "Y", "Existing_Customer": null,
      "Credit_score": 700, "Social_Media_Active": null
    }},
    "Group 2": {{
      "min_age": 18, "max_age": 24, "Marital_Status": "Single", "Family_Size": null,
      "Dependent_count": null, "Occupation": "Student", "Occupation_type": null,
      "Monthly_Income": null, "KYC_status": null, "City": null,
      "Kids_in_Household": null, "App_Installed": "N", "Existing_Customer": null,
      "Credit_score": null, "Social_Media_Active": null
    }}
  }},
  "campaign_goal": "conversion",
  "campaign_objective": "Drive sign-ups for XDeposit among married high-income professionals and young students.",
  "campaign_name": "XDeposit Metro Push",
  "cta_link": "https://example.com/xdeposit",
  "budget": null,
  "preferred_tone": "professional",
  "key_messages": ["Safe investment option", "Higher returns than FD", "Easy sign-up in minutes"],
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
        kwargs.setdefault("max_tokens", 2048)
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

        parsed_dict = await self._retry_with_backoff(
            self._call_and_parse, validated.brief_text
        )

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

    async def _call_and_parse(self, brief_text: str) -> dict[str, Any]:
        """Call the LLM and extract JSON; raises ValueError if non-JSON is returned.

        Raising here lets _retry_with_backoff retry the full LLM call rather than
        silently accepting a plain-text fallback that will fail Pydantic validation.
        """
        raw = await self._call_llm(brief_text)
        parsed = self._parse_llm_output(raw)
        if set(parsed.keys()) == {"content"}:
            raise ValueError(
                f"LLM returned non-JSON output (will retry). Preview: {raw[:120]!r}"
            )
        return parsed

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
        data.setdefault("campaign_objective", "")
        data.setdefault("campaign_name", "")

        # -- target_audience: normalise to structured group dict ------------------
        ta = data.get("target_audience")
        if not isinstance(ta, dict) or not ta:
            data["target_audience"] = {"Group 1": {}}
        else:
            data["target_audience"] = {
                k: v if isinstance(v, dict) else {}
                for k, v in ta.items()
            }

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
