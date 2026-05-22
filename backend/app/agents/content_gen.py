"""Content Generation Agent — produces personalised HTML email content for each campaign variant.

Example usage::

    agent = ContentGenerationAgent()
    result = await agent.execute({
        "parsed_brief": { ... },   # ParsedBrief dict
        "segment":      { ... },   # SegmentOut dict
        "variant_id":   "variant_A",
        "strategy":     { ... },   # CampaignStrategy dict
    })
    # result is an EmailContent dict
"""

import logging
import re
import time
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.agents.base_agent import BaseAgent
from app.agents.brief_parser import ParsedBrief
from app.agents.segmentation import SegmentOut
from app.agents.strategy import CampaignStrategy

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

# Maps variant suffix to its content archetype
_VARIANT_ARCHETYPES: dict[str, dict[str, str]] = {
    "A": {
        "label": "Benefit-focused / Emotional appeal",
        "guidance": (
            "Lead with the transformation and lifestyle benefit the customer will experience. "
            "Use emotive, aspirational language. Show the 'after' picture. "
            "CTA should feel like an invitation, not a command."
        ),
    },
    "B": {
        "label": "Feature-focused / Logical appeal",
        "guidance": (
            "Lead with concrete product specifications and data points. "
            "Use factual, confident language. Include a comparison or stats where relevant. "
            "CTA should be direct and action-oriented."
        ),
    },
    "C": {
        "label": "Urgency-driven / FOMO",
        "guidance": (
            "Create a sense of scarcity or time-limit. Use countdown language and loss-aversion framing. "
            "Keep the copy short and punchy. The CTA should convey immediacy."
        ),
    },
    "D": {
        "label": "Social proof / Testimonial-style",
        "guidance": (
            "Open with a relatable customer quote or success story. "
            "Use 'others like you' framing. Include community or ratings signals. "
            "CTA should feel like joining a group."
        ),
    },
}

_DEFAULT_ARCHETYPE = {
    "label": "General",
    "guidance": "Write clear, benefit-led copy aligned with the campaign tone.",
}

_SUBJECT_LINE_MIN_LEN = 40
_SUBJECT_LINE_MAX_LEN = 60
_PREVIEW_TEXT_MIN = 50
_PREVIEW_TEXT_MAX = 100

# Standard personalisation placeholders
_STD_PERSONALIZATION_TAGS = [
    "[FIRST_NAME]",
    "[LAST_NAME]",
    "[LOCATION]",
    "[COMPANY]",
    "[PRODUCT_NAME]",
]

# ── Schemas ───────────────────────────────────────────────────────────────────


class ContentGenerationInput(BaseModel):
    """Input schema for the content generation agent.

    Args:
        parsed_brief:   Structured campaign brief (from ``CampaignBriefParserAgent``).
        segment:        The customer segment this content targets.
        variant_id:     Identifier for this A/B variant (e.g. ``"variant_A"``).
        strategy:       Full campaign strategy (from ``CampaignStrategyAgent``).

    Example::

        ContentGenerationInput(
            parsed_brief=ParsedBrief(...),
            segment=SegmentOut(...),
            variant_id="variant_A",
            strategy=CampaignStrategy(...),
        )
    """

    parsed_brief: ParsedBrief
    segment: SegmentOut
    variant_id: str = Field(..., min_length=1)
    strategy: CampaignStrategy

    @field_validator("variant_id")
    @classmethod
    def normalise_variant_id(cls, v: str) -> str:
        return v.strip()


class EmailContent(BaseModel):
    """Structured email content output.

    Args:
        variant_id:             Matches the input ``variant_id``.
        segment_name:           Name of the targeted segment.
        subject_lines:          5–10 subject line options (40–60 characters).
        email_body:             Mobile-responsive HTML email body.
        preview_text:           50–100 char inbox preview snippet.
        personalization_tags:   Placeholder tokens used inside the body.
        tone:                   Actual tone applied (may refine brief tone).
        estimated_read_time:    Human-friendly read time (e.g. ``"1 min"``).

    Example::

        EmailContent(
            variant_id="variant_A",
            segment_name="millennials_active",
            subject_lines=["Ready to run faster? Here's how 🏃", ...],
            email_body="<html>...</html>",
            preview_text="Unlock your next PR with our new running shoes",
            personalization_tags=["[FIRST_NAME]", "[LOCATION]"],
            tone="friendly",
            estimated_read_time="1 min",
        )
    """

    variant_id: str
    segment_name: str
    subject_lines: list[str] = Field(..., min_length=5)
    email_body: str = Field(..., min_length=100)
    preview_text: str
    personalization_tags: list[str] = Field(default_factory=list)
    tone: str = "professional"
    estimated_read_time: str = "1 min"

    @field_validator("subject_lines")
    @classmethod
    def validate_subject_lines(cls, lines: list[str]) -> list[str]:
        """Strip blank entries; warn if some lines exceed character guidance."""
        cleaned = [l.strip() for l in lines if l and l.strip()]
        if len(cleaned) < 5:
            raise ValueError(f"Need at least 5 subject lines, got {len(cleaned)}")
        return cleaned

    @field_validator("preview_text")
    @classmethod
    def validate_preview(cls, v: str) -> str:
        v = v.strip()
        if len(v) < _PREVIEW_TEXT_MIN:
            # Pad rather than hard-fail — LLM may be slightly short
            v = v + " " * (_PREVIEW_TEXT_MIN - len(v))
        return v[:_PREVIEW_TEXT_MAX]

    @model_validator(mode="after")
    def extract_tags_from_body(self) -> "EmailContent":
        """Auto-detect personalisation tokens in the body if not supplied explicitly."""
        if not self.personalization_tags and self.email_body:
            found = re.findall(r"\[[A-Z_]+\]", self.email_body)
            self.personalization_tags = sorted(set(found))
        return self


# ── HTML template helpers ─────────────────────────────────────────────────────

_HTML_WRAPPER = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{subject}</title>
  <style>
    body {{ margin:0; padding:0; font-family: Arial, Helvetica, sans-serif; background:#f4f4f4; }}
    .wrapper {{ max-width:600px; margin:0 auto; background:#ffffff; }}
    .header  {{ background:{header_bg}; padding:24px 32px; text-align:center; }}
    .header h1 {{ color:#ffffff; font-size:24px; margin:0; }}
    .body    {{ padding:32px; color:#333333; line-height:1.6; }}
    .body h2 {{ color:{accent}; font-size:20px; margin-top:0; }}
    .body ul {{ padding-left:20px; }}
    .cta-btn {{ display:inline-block; margin:24px 0; padding:14px 32px;
                background:{accent}; color:#ffffff; text-decoration:none;
                border-radius:4px; font-size:16px; font-weight:bold; }}
    .footer  {{ background:#f4f4f4; padding:16px 32px; font-size:12px;
                color:#888888; text-align:center; }}
    @media (max-width:600px) {{
      .body {{ padding:20px; }}
      .cta-btn {{ display:block; text-align:center; }}
    }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header"><h1>{company_name}</h1></div>
    <div class="body">
      {body_content}
    </div>
    <div class="footer">
      <p>You received this email because you are on our list.<br/>
      <a href="[UNSUBSCRIBE_LINK]" style="color:#888888;">Unsubscribe</a> &nbsp;|&nbsp;
      <a href="[PRIVACY_POLICY_LINK]" style="color:#888888;">Privacy Policy</a></p>
      <p>&copy; 2026 {company_name}. All rights reserved.</p>
    </div>
  </div>
</body>
</html>"""

_ACCENT_COLORS: dict[str, str] = {
    "professional": "#1a73e8",
    "casual":       "#f4511e",
    "friendly":     "#34a853",
    "urgent":       "#d93025",
}
_HEADER_COLORS: dict[str, str] = {
    "professional": "#1a1a2e",
    "casual":       "#16213e",
    "friendly":     "#0f3460",
    "urgent":       "#950101",
}


# ── Prompt ────────────────────────────────────────────────────────────────────

_CONTENT_GEN_TEMPLATE = """\
You are an expert email marketing copywriter. Generate high-quality email content \
for the following campaign variant.

## Campaign context
- Product          : {product_name}
- Description      : {product_description}
- Campaign goal    : {campaign_goal}
- Preferred tone   : {preferred_tone}
- Key messages     : {key_messages}
- CTA link         : {cta_link}
- Budget           : {budget}

## Target segment
- Segment name     : {segment_name}
- Description      : {segment_description}
- Size             : {segment_size} customers
- Priority (1-5)   : {segment_priority}

## Variant
- Variant ID       : {variant_id}
- Archetype        : {archetype_label}
- Writing guidance : {archetype_guidance}

## Constraints
- Generate exactly 8 subject line options.
- Each subject line must be {min_chars}–{max_chars} characters long.
- Use personalisation token [FIRST_NAME] in at least one subject line.
- Preview text: a single sentence of {preview_min}–{preview_max} characters.
- Email body must be standard HTML (no ```html fences) with:
    * Greeting: "Hi [FIRST_NAME],"
    * h2 headline aligned to the variant archetype
    * 1–2 short paragraphs (benefit / feature / urgency / social proof per archetype)
    * Bullet list of the 3 most relevant key messages
    * A clearly visible CTA button: <a href="{cta_link}" ...> … </a>
    * Placeholder [LOCATION] used at least once in the body
- personalization_tags: list every [TOKEN] used in body + subject lines.
- tone: the actual tone applied (one of professional | casual | friendly | urgent).
- estimated_read_time: "< 1 min" or "1 min" or "2 min".

## Response format
Return ONLY a valid JSON object — no markdown fences, no extra text:

{{
  "variant_id"            : "{variant_id}",
  "segment_name"          : "{segment_name}",
  "subject_lines"         : ["<line1>", "<line2>", ..., "<line8>"],
  "email_body"            : "<full HTML string — NO backtick fences>",
  "preview_text"          : "<50-100 char preview>",
  "personalization_tags"  : ["[FIRST_NAME]", "[LOCATION]", ...],
  "tone"                  : "<tone>",
  "estimated_read_time"   : "<read time>"
}}
"""


# ── Agent ─────────────────────────────────────────────────────────────────────

class ContentGenerationAgent(BaseAgent):
    """Generates personalised HTML email content for each campaign variant.

    Inherits from :class:`~app.agents.base_agent.BaseAgent`.  Uses a variant-archetype
    system (benefit / feature / urgency / social-proof) to ensure A/B variants are
    meaningfully differentiated while maintaining brand consistency.

    Example::

        agent = ContentGenerationAgent(temperature=0.7)
        result = await agent.execute({
            "parsed_brief": brief.model_dump(),
            "segment":      segment.model_dump(),
            "variant_id":   "variant_A",
            "strategy":     strategy.model_dump(),
        })
        html_body = result["email_body"]
        subjects  = result["subject_lines"]
    """

    def __init__(self, **kwargs: Any) -> None:
        # Slightly higher temperature for creative copy diversity
        kwargs.setdefault("temperature", 0.75)
        kwargs.setdefault("max_tokens", 3000)
        super().__init__(**kwargs)

    # ── Public interface ──────────────────────────────────────────────────────

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Generate HTML email content for a single campaign variant.

        Args:
            input_data: Must match :class:`ContentGenerationInput` schema.

        Returns:
            Dict representation of :class:`EmailContent`.

        Raises:
            ValueError: If input validation fails or required fields cannot be produced.
        """
        t0 = time.perf_counter()

        cg_input: ContentGenerationInput = self._validate_input(
            input_data, ContentGenerationInput
        )
        brief = cg_input.parsed_brief
        segment = cg_input.segment
        variant_id = cg_input.variant_id

        self._log_action("execute_start", {
            "variant_id": variant_id,
            "segment": segment.segment_name,
            "goal": brief.campaign_goal,
        })

        # Determine archetype from the variant suffix (last uppercase letter)
        archetype_key = self._extract_archetype_key(variant_id)
        archetype = _VARIANT_ARCHETYPES.get(archetype_key, _DEFAULT_ARCHETYPE)

        prompt = self._build_prompt(brief, segment, variant_id, archetype)

        self._log_action("prompt_sent", {
            "variant_id": variant_id,
            "prompt_length": len(prompt),
        })

        raw = await self._retry_with_backoff(self._call_llm, prompt)

        self._log_action("llm_response_received", {
            "variant_id": variant_id,
            "response_length": len(raw),
        })

        content_dict = self._parse_llm_output(raw)
        content_dict = self._post_process(content_dict, brief, segment, variant_id)
        email_content: EmailContent = self._validate_input(content_dict, EmailContent)

        elapsed = round(time.perf_counter() - t0, 2)
        self._log_action("execute_complete", {
            "variant_id": variant_id,
            "subject_lines_count": len(email_content.subject_lines),  # type: ignore[union-attr]
            "personalization_tags": email_content.personalization_tags,  # type: ignore[union-attr]
            "estimated_read_time": email_content.estimated_read_time,  # type: ignore[union-attr]
            "execution_seconds": elapsed,
        })

        return email_content.model_dump()  # type: ignore[union-attr]

    # ── Prompt builder ────────────────────────────────────────────────────────

    def _build_prompt(
        self,
        brief: ParsedBrief,
        segment: SegmentOut,
        variant_id: str,
        archetype: dict[str, str],
    ) -> str:
        return _CONTENT_GEN_TEMPLATE.format(
            product_name=brief.product_name,
            product_description=brief.product_description,
            campaign_goal=brief.campaign_goal,
            preferred_tone=brief.preferred_tone,
            key_messages="; ".join(brief.key_messages) if brief.key_messages else "Not specified",
            cta_link=brief.cta_link or "#",
            budget=brief.budget if brief.budget else "Not specified",
            segment_name=segment.segment_name,
            segment_description=segment.description,
            segment_size=segment.size,
            segment_priority=segment.targeting_priority,
            variant_id=variant_id,
            archetype_label=archetype["label"],
            archetype_guidance=archetype["guidance"],
            min_chars=_SUBJECT_LINE_MIN_LEN,
            max_chars=_SUBJECT_LINE_MAX_LEN,
            preview_min=_PREVIEW_TEXT_MIN,
            preview_max=_PREVIEW_TEXT_MAX,
        )

    async def _call_llm(self, prompt: str) -> str:
        response = await self.llm.ainvoke(prompt)
        return response.content if hasattr(response, "content") else str(response)

    # ── Post-processing ───────────────────────────────────────────────────────

    def _post_process(
        self,
        data: dict[str, Any],
        brief: ParsedBrief,
        segment: SegmentOut,
        variant_id: str,
    ) -> dict[str, Any]:
        """Normalise LLM output and wrap the body in a responsive HTML shell if needed."""
        # Ensure identity fields are set correctly
        data["variant_id"] = variant_id
        data["segment_name"] = segment.segment_name

        # subject_lines: tolerate a dict wrapper from the LLM
        if isinstance(data.get("subject_lines"), dict):
            data["subject_lines"] = list(data["subject_lines"].values())
        if not data.get("subject_lines"):
            data["subject_lines"] = self._fallback_subject_lines(brief, segment, variant_id)

        # Ensure we meet minimum count
        if len(data.get("subject_lines", [])) < 5:
            data["subject_lines"] = (
                data.get("subject_lines", []) +
                self._fallback_subject_lines(brief, segment, variant_id)
            )

        # email_body: wrap bare HTML fragments in the responsive shell
        body = data.get("email_body", "")
        if body and not body.strip().lower().startswith("<!doctype"):
            tone = data.get("tone", brief.preferred_tone)
            data["email_body"] = self._wrap_html(
                body_content=body,
                company_name=brief.product_name,
                subject=data["subject_lines"][0],
                tone=tone,
            )

        # preview_text fallback
        if not data.get("preview_text"):
            data["preview_text"] = (
                f"Discover how {brief.product_name} can help you today – "
                f"exclusive offer for our {segment.segment_name} community."
            )[:_PREVIEW_TEXT_MAX]

        # tone fallback
        data.setdefault("tone", brief.preferred_tone)

        # estimated_read_time fallback
        if not data.get("estimated_read_time"):
            word_count = len(re.sub(r"<[^>]+>", "", data.get("email_body", "")).split())
            minutes = max(1, round(word_count / 200))
            data["estimated_read_time"] = "< 1 min" if minutes < 1 else f"{minutes} min"

        # personalization_tags fallback
        if not data.get("personalization_tags"):
            found = re.findall(r"\[[A-Z_]+\]", data.get("email_body", ""))
            for line in data.get("subject_lines", []):
                found += re.findall(r"\[[A-Z_]+\]", line)
            data["personalization_tags"] = sorted(set(found)) or ["[FIRST_NAME]"]

        return data

    # ── HTML helper ───────────────────────────────────────────────────────────

    @staticmethod
    def _wrap_html(
        body_content: str, company_name: str, subject: str, tone: str
    ) -> str:
        """Wrap an HTML fragment inside the responsive email shell."""
        accent = _ACCENT_COLORS.get(tone, _ACCENT_COLORS["professional"])
        header_bg = _HEADER_COLORS.get(tone, _HEADER_COLORS["professional"])
        return _HTML_WRAPPER.format(
            subject=subject,
            company_name=company_name,
            body_content=body_content,
            accent=accent,
            header_bg=header_bg,
        )

    # ── Fallback helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _extract_archetype_key(variant_id: str) -> str:
        """Extract the last uppercase letter from variant_id (e.g. 'variant_A' → 'A')."""
        match = re.search(r"[A-D]$", variant_id.upper())
        return match.group(0) if match else "A"

    @staticmethod
    def _fallback_subject_lines(
        brief: ParsedBrief, segment: SegmentOut, variant_id: str
    ) -> list[str]:
        """Generate simple fallback subject lines when the LLM response is unusable."""
        goal_map = {
            "awareness": "Discover",
            "conversion": "Get",
            "retention": "Come back to",
            "engagement": "Explore",
        }
        verb = goal_map.get(brief.campaign_goal, "Try")
        name = brief.product_name
        return [
            f"[FIRST_NAME], {verb} {name} today",
            f"Introducing {name} – just for you",
            f"Your exclusive {name} offer inside",
            f"Don't miss out on {name}",
            f"{verb} {name} – limited time",
        ]
