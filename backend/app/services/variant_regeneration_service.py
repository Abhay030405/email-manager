"""Variant regeneration service — creates improved variants from poor performers."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from app.db.repositories.variant_iteration_repo import VariantIterationRepository
from app.db.repositories.variant_repo import VariantRepository
from app.models.variant_iteration import VariantIteration
from app.services.performance_scoring_service import PerformanceScoringService

logger = logging.getLogger(__name__)

# Optimal send window: Wednesday 9 AM
_OPTIMAL_WEEKDAY = 2  # Wednesday
_OPTIMAL_HOUR = 9


class VariantRegenerationService:
    """Generates improved email variant content for poor-performing variants."""

    def __init__(
        self,
        performance_scoring_service: PerformanceScoringService,
        variant_iteration_repo: VariantIterationRepository,
        variant_repo: VariantRepository,
        content_generation_agent: Optional[Any] = None,
        strategy_agent: Optional[Any] = None,
    ) -> None:
        self.scoring_svc = performance_scoring_service
        self.iteration_repo = variant_iteration_repo
        self.variant_repo = variant_repo
        self.content_generation_agent = content_generation_agent
        self.strategy_agent = strategy_agent

    # ── Public API ────────────────────────────────────────────────────────────

    async def regenerate_variants(
        self,
        campaign_id: str,
        poor_performers: list[dict[str, Any]],
        insights: list[dict[str, Any]],
        iteration_number: int,
    ) -> list[dict[str, Any]]:
        """Regenerate improved variants for each poor performer.

        Returns a list of new variant specification dicts.
        """
        results: list[dict[str, Any]] = []

        for pp in poor_performers:
            variant_id = pp.get("variant_id", "")
            existing = await self.variant_repo.find_by_id(variant_id)
            if not existing:
                logger.warning("Variant %s not found — skipping regeneration", variant_id)
                continue

            relevant_insights = [
                i for i in insights
                if i.get("variant_id") in (variant_id, None)
            ]
            factors = [i.get("recommendation", "") for i in relevant_insights]

            candidates = await self.generate_variant_candidates(
                segment_name=existing.segment_name,
                previous_subject=existing.subject_line,
                previous_body=existing.email_body,
                optimization_factors=factors,
                num_candidates=3,
            )

            best = await self.select_best_variant(candidates)
            new_variant_id = str(uuid.uuid4())

            new_variant: dict[str, Any] = {
                "variant_id": new_variant_id,
                "campaign_id": campaign_id,
                "iteration_number": iteration_number,
                "segment_name": existing.segment_name,
                "subject_line": best["subject_line"],
                "email_body": best["email_body"],
                "send_time": _optimal_send_time(),
                "content_quality_score": best.get("content_quality_score", 0.0),
                "changes_from_previous": _compute_changes(
                    existing.subject_line, existing.email_body,
                    best["subject_line"], best["email_body"],
                ),
            }

            iteration = await self.track_variant_changes(
                campaign_id=campaign_id,
                variant_id=new_variant_id,
                iteration_number=iteration_number,
                previous_variant={"subject_line": existing.subject_line, "email_body": existing.email_body},
                new_variant={"subject_line": best["subject_line"], "email_body": best["email_body"]},
                improvements_applied=factors,
            )
            new_variant["iteration_id"] = iteration.iteration_id
            results.append(new_variant)

        return results

    async def generate_variant_candidates(
        self,
        segment_name: str,
        previous_subject: str,
        previous_body: str,
        optimization_factors: list[str],
        num_candidates: int = 3,
    ) -> list[dict[str, Any]]:
        """Generate candidate variants — uses agent if available, else rule-based."""
        if self.content_generation_agent:
            try:
                return await self._generate_via_agent(
                    segment_name, previous_subject, previous_body,
                    optimization_factors, num_candidates,
                )
            except Exception as exc:
                logger.warning("Content agent failed: %s — using rule-based fallback", exc)

        return _rule_based_candidates(
            segment_name, previous_subject, previous_body,
            optimization_factors, num_candidates,
        )

    async def select_best_variant(
        self,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Score all candidates and return the highest-quality one."""
        if not candidates:
            return _empty_variant()

        scored = []
        for c in candidates:
            quality = self.scoring_svc.score_content_quality(
                subject=c.get("subject_line", ""),
                body=c.get("email_body", ""),
                send_time=c.get("send_time"),
            )
            c["content_quality_score"] = quality["overall_score"]
            scored.append(c)

        return max(scored, key=lambda x: x.get("content_quality_score", 0.0))

    async def track_variant_changes(
        self,
        campaign_id: str,
        variant_id: str,
        iteration_number: int,
        previous_variant: dict[str, Any],
        new_variant: dict[str, Any],
        improvements_applied: list[str],
    ) -> VariantIteration:
        """Record field-level changes for a variant iteration."""
        changes: dict[str, Any] = {}
        for field in ("subject_line", "email_body"):
            old_val = previous_variant.get(field, "")
            new_val = new_variant.get(field, "")
            if old_val != new_val:
                changes[field] = {
                    "old_value": old_val[:200] if old_val else "",
                    "new_value": new_val[:200] if new_val else "",
                    "reason": "Optimisation based on performance insights",
                }

        quality = self.scoring_svc.score_content_quality(
            subject=new_variant.get("subject_line", ""),
            body=new_variant.get("email_body", ""),
            send_time=new_variant.get("send_time"),
        )

        iteration = VariantIteration(
            campaign_id=campaign_id,
            variant_id=variant_id,
            iteration_number=iteration_number,
            changes=changes,
            metrics={},
            content_quality_score=quality["overall_score"],
            optimization_factors_applied=improvements_applied,
        )
        return await self.iteration_repo.create(iteration)

    # ── Private ───────────────────────────────────────────────────────────────

    async def _generate_via_agent(
        self,
        segment_name: str,
        previous_subject: str,
        previous_body: str,
        optimization_factors: list[str],
        num_candidates: int,
    ) -> list[dict[str, Any]]:
        result = await self.content_generation_agent.execute({
            "segment_name": segment_name,
            "previous_subject": previous_subject,
            "previous_body": previous_body,
            "optimization_requirements": optimization_factors,
            "num_variants": num_candidates,
        })
        raw = result.get("variants", [])
        return raw[:num_candidates] if raw else []


# ── Pure helpers ──────────────────────────────────────────────────────────────

def _optimal_send_time() -> datetime:
    """Return the next Wednesday at 09:00 UTC."""
    now = datetime.utcnow()
    days_until = (_OPTIMAL_WEEKDAY - now.weekday()) % 7 or 7
    target = now + timedelta(days=days_until)
    return target.replace(hour=_OPTIMAL_HOUR, minute=0, second=0, microsecond=0)


def _compute_changes(
    old_subject: str, old_body: str, new_subject: str, new_body: str
) -> dict[str, Any]:
    changes: dict[str, Any] = {}
    if old_subject != new_subject:
        changes["subject_line"] = {"old": old_subject[:100], "new": new_subject[:100]}
    if old_body != new_body:
        changes["email_body"] = {"old": old_body[:100] + "...", "new": new_body[:100] + "..."}
    return changes


def _rule_based_candidates(
    segment_name: str,
    previous_subject: str,
    previous_body: str,
    optimization_factors: list[str],
    num_candidates: int,
) -> list[dict[str, Any]]:
    base_subject = previous_subject[:40].strip() if previous_subject else f"Exclusive offer for {segment_name}"
    base_body = previous_body if previous_body else (
        f"Dear valued {segment_name} member,\n\n"
        "We have a special offer just for you. Click here to learn more and take advantage "
        "of our limited-time deal.\n\nBest regards,\nThe Team"
    )

    templates = [
        {
            "subject_line": f"🎯 {base_subject} — Limited Time!",
            "email_body": (
                f"<p>Dear {segment_name} member,</p>"
                f"<p>{base_body[:150]}</p>"
                "<p><strong><a href='#'>👉 Claim Your Offer Now</a></strong></p>"
                "<p>This offer expires soon — act today!</p>"
            ),
            "send_time": _optimal_send_time(),
        },
        {
            "subject_line": f"Last chance: {base_subject[:45]}",
            "email_body": (
                f"<p>Hi there,</p>"
                "<p>Don't miss out on this exclusive opportunity crafted just for you.</p>"
                f"<p>{base_body[:120]}</p>"
                "<p><a href='#'>Click here to get started →</a></p>"
            ),
            "send_time": _optimal_send_time(),
        },
        {
            "subject_line": f"{{first_name}}, your {segment_name} exclusive awaits",
            "email_body": (
                "<p>Hi {{first_name}},</p>"
                "<p>We noticed you haven't taken advantage of your member benefits yet.</p>"
                f"<p>{base_body[:100]}</p>"
                "<p><strong><a href='#'>Get Started Today</a></strong></p>"
                "<p>Questions? Reply to this email.</p>"
            ),
            "send_time": _optimal_send_time(),
        },
    ]
    return templates[:num_candidates]


def _empty_variant() -> dict[str, Any]:
    return {
        "subject_line": "Your exclusive offer inside",
        "email_body": "<p>Click here to learn more.</p>",
        "send_time": _optimal_send_time(),
        "content_quality_score": 0.3,
    }
